/**
 * Tarjeta de un indicador.
 *
 * Estructura:
 *   [icono] [tipo traducido]
 *   ┌────────────────────────────┐
 *   │ evidence (monospace)       │  ← fragmento literal del input
 *   └────────────────────────────┘
 *   explanation (texto educativo)
 *
 * El monospace en la evidencia es deliberado: queremos que el usuario reconozca
 * que es el texto LITERAL del input, no una paráfrasis. Es la base didáctica
 * del Analyzer.
 */

import { useTranslations } from 'next-intl';
import type { Indicator, IndicatorType } from '../lib/types';

const ICON: Record<IndicatorType, string> = {
  sender_spoofing: '👤',
  lookalike_domain: '🔗',
  link_mismatch: '🕳️',
  urgency_language: '⏰',
  credential_request: '🔑',
  payment_request: '💳',
  brand_or_grammar_error: '✍️',
  suspicious_attachment: '📎',
  other: '⚠️',
};

interface IndicatorCardProps {
  indicator: Indicator;
}

export function IndicatorCard({ indicator }: IndicatorCardProps) {
  const t = useTranslations('analyzer.indicator');

  return (
    <article className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      <header className="flex items-center gap-2">
        <span aria-hidden className="text-lg leading-none">
          {ICON[indicator.type] ?? '⚠️'}
        </span>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700 dark:text-slate-300">
          {t(`type.${indicator.type}`)}
        </h3>
      </header>

      <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-md bg-slate-100 p-3 font-mono text-xs text-slate-800 dark:bg-slate-900 dark:text-slate-200">
        {indicator.evidence}
      </pre>

      <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
        {indicator.explanation}
      </p>
    </article>
  );
}
