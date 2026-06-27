/**
 * Semáforo visual del resultado del Analyzer.
 *
 * Muestra el `risk_score` (0-100) y el `verdict` con un color coherente con
 * `docs/architecture/security.md` (legit→verde, suspicious→ámbar, phishing→rojo).
 * El score se renderiza como barra horizontal: la parte coloreada cubre N% del
 * track, y un puntero negro marca la posición exacta para que sea legible aunque
 * el color sea ambiguo (accesibilidad básica).
 */

import { useTranslations } from 'next-intl';
import type { Verdict } from '../lib/types';

interface RiskMeterProps {
  score: number; // 0-100
  verdict: Verdict;
}

const VERDICT_BAR: Record<Verdict, string> = {
  legit: 'bg-emerald-500',
  suspicious: 'bg-amber-500',
  phishing: 'bg-red-500',
};

const VERDICT_BADGE: Record<Verdict, string> = {
  legit: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-200',
  suspicious: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200',
  phishing: 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200',
};

export function RiskMeter({ score, verdict }: RiskMeterProps) {
  const t = useTranslations('analyzer.verdict');
  const clamped = Math.max(0, Math.min(100, score));

  return (
    <div className="rounded-lg border border-slate-200 p-6 dark:border-slate-800">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t('label')}
          </p>
          <p className="mt-1 text-3xl font-bold tabular-nums">{clamped}/100</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${VERDICT_BADGE[verdict]}`}
        >
          {t(verdict)}
        </span>
      </div>

      <div
        className="relative mt-4 h-3 w-full rounded-full bg-slate-200 dark:bg-slate-800"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-3 rounded-full transition-all ${VERDICT_BAR[verdict]}`}
          style={{ width: `${clamped}%` }}
        />
        <div
          className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 bg-slate-900 dark:bg-white"
          style={{ left: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
