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

// ---------------------------------------------------------------------------
// Auth (Fase 7.2 backend / 7.4 frontend)
//
// Espejo de backend/app/schemas/auth.py. La sesión vive en una cookie httpOnly
// (`access_token`) que el frontend NO manipula: basta con credentials:'include'.
// ---------------------------------------------------------------------------

export type Role = 'user' | 'admin';

/** Vista pública del usuario (sin contraseña ni hash). Espejo de `UserPublic`. */
export interface UserPublic {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string; // ISO 8601
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/** Cambios que un admin aplica a otra cuenta (PATCH parcial). Espejo de
 * `UserAdminUpdate`: solo se envía lo que cambia. */
export interface UserAdminUpdate {
  is_active?: boolean;
  role?: Role;
}

// ---------------------------------------------------------------------------
// BYOK — Bring Your Own Key (Fase 7.3 backend / 7.4 frontend)
//
// Espejo de backend/app/schemas/byok.py. El `mock` no admite BYOK: el provider
// se restringe a gemini/claude. La clave en claro SOLO se envía (PUT); cualquier
// lectura devuelve la máscara (`••••wxyz`).
// ---------------------------------------------------------------------------

export type ByokProvider = 'gemini' | 'claude';

export interface ByokModelOption {
  id: string;
  label: string;
}

/**
 * Modelos sugeridos por proveedor para el desplegable de BYOK.
 *
 * Es una decisión de UI (como INDICATORS_BY_INPUT_TYPE): el backend acepta
 * cualquier string de modelo, así que esta lista solo facilita la elección. Si
 * el usuario necesita otro, el formulario ofrece la opción "Personalizado".
 * Mantener los IDs en sintonía con los que reconoce cada proveedor.
 */
export const BYOK_MODELS_BY_PROVIDER: Record<ByokProvider, readonly ByokModelOption[]> = {
  gemini: [
    { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
    { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
  ],
  claude: [
    { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5' },
    { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
    { id: 'claude-opus-4-8', label: 'Claude Opus 4.8' },
  ],
};

/** Alta/reemplazo de la clave. `model` opcional (default del provider). */
export interface ApiKeyCreate {
  provider: ByokProvider;
  api_key: string;
  model?: string | null;
}

/** Vista pública de la clave: nunca la clave en claro, solo su máscara. */
export interface ApiKeyPublic {
  provider: ByokProvider;
  model: string | null;
  masked_key: string;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
