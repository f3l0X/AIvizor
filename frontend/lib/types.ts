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
