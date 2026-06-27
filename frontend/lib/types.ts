/**
 * Tipos del contrato Analyzer/Trainer.
 *
 * Espejo fiel de los esquemas Pydantic del backend
 * (backend/app/schemas/{common,analysis,training}.py). Si añades un
 * IndicatorType allí, añádelo aquí también — TypeScript no lo deriva
 * automáticamente y la UI lo consume por nombre.
 */

export type Language = 'es' | 'en';
export type InputType = 'email' | 'url' | 'sms';
export type Verdict = 'legit' | 'suspicious' | 'phishing';

export const INDICATOR_TYPES = [
  'sender_spoofing',
  'lookalike_domain',
  'link_mismatch',
  'urgency_language',
  'credential_request',
  'payment_request',
  'brand_or_grammar_error',
  'suspicious_attachment',
  'other',
] as const;

export type IndicatorType = (typeof INDICATOR_TYPES)[number];

/**
 * Qué tipos de indicador tienen sentido para cada formato de entrada.
 *
 * - email: todos (es el formato más rico).
 * - url:   prácticamente solo el dominio (no hay cabeceras, ni cuerpo, ni adjuntos).
 * - sms:   texto corto sin HTML ni adjuntos; sin sender headers ni link_mismatch.
 *
 * Mantener esta tabla aquí (no en backend) porque es decisión de UI; el backend
 * acepta cualquier IndicatorType para cualquier input_type — la restricción es
 * pedagógica.
 */
export const INDICATORS_BY_INPUT_TYPE: Record<InputType, readonly IndicatorType[]> = {
  email: INDICATOR_TYPES,
  url: ['lookalike_domain', 'other'],
  sms: [
    'lookalike_domain',
    'urgency_language',
    'credential_request',
    'payment_request',
    'brand_or_grammar_error',
    'other',
  ],
};

export interface Indicator {
  type: IndicatorType;
  evidence: string;
  explanation: string;
}

export interface AnalysisResult {
  risk_score: number; // 0-100
  verdict: Verdict;
  language: Language;
  summary: string;
  indicators: Indicator[];
}

export interface AnalyzeRequest {
  content: string;
  input_type: InputType;
  language?: Language;
}

// ---------------------------------------------------------------------------
// Trainer (Módulo B)
// ---------------------------------------------------------------------------

export type Difficulty = 1 | 2 | 3 | 4 | 5;

export interface TrainingNextRequest {
  difficulty: Difficulty;
  input_type: InputType;
  language: Language;
}

/** Sample que recibe el cliente: SIN la verdad. */
export interface TrainingSamplePublic {
  id: string;
  input_type: InputType;
  language: Language;
  difficulty: Difficulty;
  content: string;
}

export interface TrainingAnswer {
  sample_id: string;
  user_verdict: Verdict;
  marked_indicator_types: string[];
}

export interface TrainingFeedback {
  sample_id: string;
  correct: boolean;
  score: number; // 0-100
  missed_indicators: Indicator[];
  /** Tipos VERDADEROS del sample. Permite al UI distinguir aciertos de falsos positivos. */
  true_indicator_types: string[];
  explanation: string;
  next_difficulty: Difficulty;
}
