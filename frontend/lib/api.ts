/**
 * Cliente HTTP del backend AIvizor.
 *
 * - `API_URL` viene de NEXT_PUBLIC_API_URL (configurable por entorno).
 * - Errores se exponen como `ApiError` para que la UI distinga 4xx (input del
 *   usuario) de 5xx (problema del backend / LLM provider).
 * - TODAS las peticiones van con `credentials: 'include'`: la sesión vive en una
 *   cookie httpOnly (`access_token`) que el navegador adjunta sola. Analyzer y
 *   Trainer también la envían para que el backend resuelva la clave BYOK del
 *   usuario logueado (si la tiene); el anónimo sigue funcionando sin cookie.
 */

import type {
  AnalysisResult,
  AnalyzeRequest,
  ApiKeyCreate,
  ApiKeyPublic,
  LoginRequest,
  RegisterRequest,
  TrainingAnswer,
  TrainingFeedback,
  TrainingNextRequest,
  TrainingSamplePublic,
  UserAdminUpdate,
  UserPublic,
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
  const r = await fetch(`${API_URL}/health`, { cache: 'no-store', credentials: 'include' });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function analyze(req: AnalyzeRequest): Promise<AnalysisResult> {
  const r = await fetch(`${API_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    credentials: 'include',
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
    credentials: 'include',
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
    credentials: 'include',
    body: JSON.stringify(answer),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

// ---------------------------------------------------------------------------
// Auth (Fase 7.4)
//
// register/login dejan la cookie httpOnly en la respuesta y devuelven UserPublic.
// getMe() recupera la sesión actual: 401 si no hay (lo traducimos a null arriba,
// en el AuthProvider, no aquí — aquí 401 es un ApiError como cualquier otro).
// ---------------------------------------------------------------------------

export async function register(req: RegisterRequest): Promise<UserPublic> {
  const r = await fetch(`${API_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    credentials: 'include',
    body: JSON.stringify(req),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function login(req: LoginRequest): Promise<UserPublic> {
  const r = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    credentials: 'include',
    body: JSON.stringify(req),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function logout(): Promise<void> {
  const r = await fetch(`${API_URL}/api/auth/logout`, {
    method: 'POST',
    cache: 'no-store',
    credentials: 'include',
  });
  if (!r.ok) throw await parseError(r);
}

export async function getMe(): Promise<UserPublic> {
  const r = await fetch(`${API_URL}/api/auth/me`, {
    cache: 'no-store',
    credentials: 'include',
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

// ---------------------------------------------------------------------------
// BYOK (Fase 7.4)
//
// getApiKey() devuelve 404 si el usuario no tiene clave configurada: el llamante
// debe tratar 404 como "sin clave", no como error. putApiKey() hace upsert.
// ---------------------------------------------------------------------------

export async function getApiKey(): Promise<ApiKeyPublic> {
  const r = await fetch(`${API_URL}/api/keys`, {
    cache: 'no-store',
    credentials: 'include',
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function putApiKey(req: ApiKeyCreate): Promise<ApiKeyPublic> {
  const r = await fetch(`${API_URL}/api/keys`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    credentials: 'include',
    body: JSON.stringify(req),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function deleteApiKey(): Promise<void> {
  const r = await fetch(`${API_URL}/api/keys`, {
    method: 'DELETE',
    cache: 'no-store',
    credentials: 'include',
  });
  if (!r.ok) throw await parseError(r);
}

// ---------------------------------------------------------------------------
// Admin (Fase 7.5)
//
// Requieren sesión de administrador (401 sin login, 403 si no es admin). El
// backend impide que un admin se modifique/borre a sí mismo (400).
// ---------------------------------------------------------------------------

export async function adminListUsers(): Promise<UserPublic[]> {
  const r = await fetch(`${API_URL}/api/admin/users`, {
    cache: 'no-store',
    credentials: 'include',
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function adminUpdateUser(
  userId: string,
  patch: UserAdminUpdate,
): Promise<UserPublic> {
  const r = await fetch(`${API_URL}/api/admin/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    credentials: 'include',
    body: JSON.stringify(patch),
  });
  if (!r.ok) throw await parseError(r);
  return r.json();
}

export async function adminDeleteUser(userId: string): Promise<void> {
  const r = await fetch(`${API_URL}/api/admin/users/${userId}`, {
    method: 'DELETE',
    cache: 'no-store',
    credentials: 'include',
  });
  if (!r.ok) throw await parseError(r);
}
