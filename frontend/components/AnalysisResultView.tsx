/**
 * Composición de la salida del Analyzer: RiskMeter + summary + lista de indicadores.
 *
 * No tiene estado: recibe `AnalysisResult` y lo pinta. La página decide cuándo
 * montarla y cuándo desmontarla (típicamente: tras un análisis exitoso).
 */

import { useTranslations } from 'next-intl';
import type { AnalysisResult } from '../lib/types';
import { IndicatorCard } from './IndicatorCard';
import { RiskMeter } from './RiskMeter';

interface AnalysisResultViewProps {
  result: AnalysisResult;
}

export function AnalysisResultView({ result }: AnalysisResultViewProps) {
  const t = useTranslations('analyzer.result');

  return (
    <section
      aria-live="polite"
      aria-label={t('ariaLabel')}
      className="space-y-6"
    >
      <RiskMeter score={result.risk_score} verdict={result.verdict} />

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t('summary')}
        </h2>
        <p className="mt-2 text-base text-slate-800 dark:text-slate-200">{result.summary}</p>
      </div>

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t('indicators', { count: result.indicators.length })}
        </h2>
        {result.indicators.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            {t('noIndicators')}
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {result.indicators.map((ind, i) => (
              <li key={i}>
                <IndicatorCard indicator={ind} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
