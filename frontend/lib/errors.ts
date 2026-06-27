/**
 * Helper para traducir cualquier excepción en un mensaje útil para el usuario.
 *
 * Distinguimos 3 casos para que el mensaje guíe acción:
 *   - Network (TypeError de fetch): "no se pudo conectar" → revisar backend / VPN.
 *   - 4xx (ApiError.isClientError): suele ser payload mal formado → revisar input.
 *   - 5xx (ApiError.isServerError): backend o LLM provider falló → reintentar o
 *     reportar; mostramos `detail` si lo trae (incluye el provider en LLMError).
 *
 * Acepta una función de traducción genérica (next-intl) que debe exponer las
 * claves `error.network`, `error.client`, `error.server` y `error.generic`.
 */

import { ApiError } from './api';

// Laxa a propósito: el `t` de next-intl tiene una firma genérica compleja
// (TranslationValues con overloads rich/markup). Solo usamos la forma
// `(key, values) => string`, así que aceptamos cualquier `values` para que
// el `t` de next-intl sea asignable a este tipo sin fricción.
export type TranslateFn = (key: string, values?: Record<string, any>) => string;

export function errorMessage(e: unknown, t: TranslateFn): string {
  if (e instanceof ApiError) {
    if (e.isClientError) return t('error.client', { detail: e.detail ?? '' });
    if (e.isServerError) return t('error.server', { detail: e.detail ?? '' });
    return e.detail ?? t('error.generic');
  }
  // TypeError de fetch / red caída / CORS bloqueado.
  return t('error.network');
}
