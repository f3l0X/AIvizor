/**
 * Cliente HTTP del backend AIvizor.
 *
 * - `API_URL` viene de NEXT_PUBLIC_API_URL (configurable por entorno).
 * - Errores se exponen como `ApiError` para que la UI distinga 4xx (input del
 *   usuario) de 5xx (problema del backend / LLM provider).
 */

import type {
  AnalysisResult,
  AnalyzeRequest,
  TrainingAnswer,
  TrainingFeedback,
  TrainingNextRequest,
  TrainingSamplePublic,
} from './types';

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** True para errores del cliente (4xx). El usuario puede corregir y reintentar. */
  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /** True para errores del servidor o del LLM provider (5xx). */
  get isServerError(): boolean {
    return this.status >= 500;
  }
}

async function parseError(r: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const body = await r.json();
    detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body?.detail);
  } catch {
    // body no era JSON o estaba vacío
  }
  return new ApiError(`HTTP ${r.status}`, r.status, detail);
}

export async function getHealth(): Promise<{
  status: string;
  service: string;
  version: string;
  llm_provider: string;
}> {
  const r = await fetch(`${API_URL}/health`, { cache: 'no-store' });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function analyze(req: AnalyzeRequest): Promise<AnalysisResult> {
  const r = await fetch(`${API_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify(req),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function trainNext(req: TrainingNextRequest): Promise<TrainingSamplePublic> {
  const r = await fetch(`${API_URL}/api/train/next`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify(req),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function trainAnswer(answer: TrainingAnswer): Promise<TrainingFeedback> {
  const r = await fetch(`${API_URL}/api/train/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify(answer),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}
