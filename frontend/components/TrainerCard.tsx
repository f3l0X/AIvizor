/**
 * Carta del Trainer: muestra el contenido del sample y controles para
 * que el alumno responda (verdict + indicadores marcados).
 *
 * Estado local: la elección del alumno antes de pulsar enviar. Cuando hay
 * `feedback`, la carta entra en modo "revisión" (bloquea inputs y resalta
 * fallos).
 */

'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { INDICATOR_TYPES } from '../lib/types';
import type {
  Difficulty,
  IndicatorType,
  TrainingFeedback,
  TrainingSamplePublic,
  Verdict,
} from '../lib/types';

const VERDICTS: Verdict[] = ['legit', 'suspicious', 'phishing'];

const VERDICT_COLOR: Record<Verdict, string> = {
  legit: 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30',
  suspicious: 'border-amber-500 bg-amber-50 dark:bg-amber-950/30',
  phishing: 'border-red-500 bg-red-50 dark:bg-red-950/30',
};

interface TrainerCardProps {
  sample: TrainingSamplePublic;
  feedback: TrainingFeedback | null;
  isSubmitting: boolean;
  onSubmit: (verdict: Verdict, markedTypes: IndicatorType[]) => void;
  onNext: (nextDifficulty: Difficulty) => void;
}

export function TrainerCard({
  sample,
  feedback,
  isSubmitting,
  onSubmit,
  onNext,
}: TrainerCardProps) {
  const t = useTranslations('trainer');
  const tVerdict = useTranslations('analyzer.verdict');
  const tInd = useTranslations('analyzer.indicator');

  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [marked, setMarked] = useState<Set<IndicatorType>>(new Set());

  const locked = feedback !== null;

  const toggleType = (type: IndicatorType) => {
    if (locked) return;
    const next = new Set(marked);
    if (next.has(type)) next.delete(type);
    else next.add(type);
    setMarked(next);
  };

  const trueTypes = new Set<string>(feedback?.true_indicator_types ?? []);

  /** Estado visual de cada checkbox en modo feedback.
   *   - hit:           el alumno marcó un indicador verdadero  → ✓ verde
   *   - falsePositive: marcó algo que NO era indicador          → ✗ rojo
   *   - missed:        no marcó un indicador verdadero          → ⚠ ámbar
   *   - neutral:       no marcó y tampoco era verdadero         → sin badge
   */
  const stateOf = (
    type: IndicatorType,
  ): 'hit' | 'falsePositive' | 'missed' | 'neutral' => {
    if (!locked) return 'neutral';
    const wasMarked = marked.has(type);
    const isTrue = trueTypes.has(type);
    if (wasMarked && isTrue) return 'hit';
    if (wasMarked && !isTrue) return 'falsePositive';
    if (!wasMarked && isTrue) return 'missed';
    return 'neutral';
  };

  return (
    <article className="space-y-6 rounded-lg border border-slate-200 p-6 dark:border-slate-800">
      <header className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t('difficultyLabel', { level: sample.difficulty })} ·{' '}
          {t(`inputType.${sample.input_type}`)}
        </p>
      </header>

      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-md bg-slate-100 p-4 font-mono text-sm text-slate-800 dark:bg-slate-900 dark:text-slate-200">
        {sample.content}
      </pre>

      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {t('verdictQuestion')}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {VERDICTS.map((v) => {
            const isSelected = verdict === v;
            const base =
              'rounded-md border px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50';
            const style = isSelected
              ? VERDICT_COLOR[v]
              : 'border-slate-300 bg-white dark:border-slate-700 dark:bg-slate-900';
            return (
              <button
                key={v}
                type="button"
                disabled={locked || isSubmitting}
                onClick={() => setVerdict(v)}
                className={`${base} ${style}`}
              >
                {tVerdict(v)}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {t('indicatorsQuestion')}
        </p>
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {INDICATOR_TYPES.map((type) => {
            const checked = marked.has(type);
            const state = stateOf(type);

            const styleByState = {
              hit: 'border-emerald-500 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/30',
              falsePositive:
                'border-red-400 bg-red-50 dark:border-red-700 dark:bg-red-950/30',
              missed:
                'border-amber-400 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30',
              neutral: checked
                ? 'border-brand bg-brand/5'
                : 'border-slate-200 dark:border-slate-800',
            }[state];

            const badge = {
              hit: <span aria-hidden className="ml-auto text-emerald-700 dark:text-emerald-300">✓</span>,
              falsePositive: <span aria-hidden className="ml-auto text-red-700 dark:text-red-300">✗</span>,
              missed: <span aria-hidden className="ml-auto text-amber-700 dark:text-amber-300">⚠</span>,
              neutral: null,
            }[state];

            return (
              <label
                key={type}
                className={`flex cursor-pointer items-start gap-2 rounded-md border p-2 text-sm transition ${styleByState} ${locked ? 'cursor-default' : ''}`}
              >
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={checked}
                  disabled={locked || isSubmitting}
                  onChange={() => toggleType(type)}
                />
                <span className="leading-snug">{tInd(`type.${type}`)}</span>
                {badge}
              </label>
            );
          })}
        </div>
      </div>

      {!locked && (
        <button
          type="button"
          disabled={!verdict || isSubmitting}
          onClick={() => verdict && onSubmit(verdict, Array.from(marked))}
          className="inline-flex items-center justify-center rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? t('submitting') : t('submit')}
        </button>
      )}

      {feedback && (
        <FeedbackView feedback={feedback} onNext={onNext} />
      )}
    </article>
  );
}

function FeedbackView({
  feedback,
  onNext,
}: {
  feedback: TrainingFeedback;
  onNext: (nextDifficulty: Difficulty) => void;
}) {
  const t = useTranslations('trainer');
  const tInd = useTranslations('analyzer.indicator');

  const headerColor = feedback.correct
    ? 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-200'
    : 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200';

  return (
    <section
      aria-live="polite"
      className="space-y-4 rounded-md border border-slate-200 p-4 dark:border-slate-800"
    >
      <div className={`rounded-md px-3 py-2 text-sm font-semibold ${headerColor}`}>
        {feedback.correct ? t('feedback.correct') : t('feedback.wrong')} ·{' '}
        {t('feedback.score', { score: feedback.score })}
      </div>

      <p className="text-sm text-slate-700 dark:text-slate-300">{feedback.explanation}</p>

      {feedback.missed_indicators.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t('feedback.missed', { count: feedback.missed_indicators.length })}
          </p>
          <ul className="mt-2 space-y-2">
            {feedback.missed_indicators.map((ind, i) => (
              <li
                key={i}
                className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950/30"
              >
                <p className="font-semibold">{tInd(`type.${ind.type}`)}</p>
                <pre className="mt-1 whitespace-pre-wrap break-words font-mono text-xs text-slate-700 dark:text-slate-300">
                  {ind.evidence}
                </pre>
                <p className="mt-1 text-slate-700 dark:text-slate-300">{ind.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={() => onNext(feedback.next_difficulty)}
        className="inline-flex items-center justify-center rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark"
      >
        {t('feedback.nextLevel', { level: feedback.next_difficulty })}
      </button>
    </section>
  );
}
