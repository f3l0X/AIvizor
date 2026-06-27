/**
 * Página del Trainer (cliente).
 *
 * Estado:
 *   - idle    → botón "Empezar" + selectores de tipo/dificultad inicial.
 *   - sample  → carta visible, esperando respuesta del alumno.
 *   - feedback→ feedback visible debajo de la carta, botón "Siguiente nivel N".
 *   - error   → banner de error sin destruir el progreso.
 *
 * La dificultad se gestiona en el cliente (el servidor sugiere la siguiente
 * pero el cliente puede ignorarla si quiere). Stateless en backend, simple
 * en frontend.
 */

'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { TrainerCard } from '../../../components/TrainerCard';
import { ApiError, trainAnswer, trainNext } from '../../../lib/api';
import type {
  Difficulty,
  IndicatorType,
  InputType,
  Language,
  TrainingFeedback,
  TrainingSamplePublic,
  Verdict,
} from '../../../lib/types';

type Status =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'sample'; sample: TrainingSamplePublic }
  | { kind: 'submitting'; sample: TrainingSamplePublic }
  | { kind: 'feedback'; sample: TrainingSamplePublic; feedback: TrainingFeedback }
  | { kind: 'error'; message: string };

const INPUT_TYPES: InputType[] = ['email', 'url', 'sms'];
const DIFFICULTIES: Difficulty[] = [1, 2, 3, 4, 5];

export default function TrainPage() {
  const t = useTranslations('trainer');
  const tCommon = useTranslations('analyzer.form');
  const locale = useLocale() as Language;

  const [inputType, setInputType] = useState<InputType>('email');
  const [difficulty, setDifficulty] = useState<Difficulty>(1);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });

  const fetchNext = async (diff: Difficulty) => {
    setStatus({ kind: 'loading' });
    try {
      const sample = await trainNext({ difficulty: diff, input_type: inputType, language: locale });
      setStatus({ kind: 'sample', sample });
    } catch (e) {
      setStatus({
        kind: 'error',
        message:
          e instanceof ApiError ? e.detail ?? t('error.generic') : t('error.network'),
      });
    }
  };

  const handleSubmitAnswer = async (verdict: Verdict, markedTypes: IndicatorType[]) => {
    if (status.kind !== 'sample') return;
    const sample = status.sample;
    setStatus({ kind: 'submitting', sample });
    try {
      const feedback = await trainAnswer({
        sample_id: sample.id,
        user_verdict: verdict,
        marked_indicator_types: markedTypes,
      });
      setStatus({ kind: 'feedback', sample, feedback });
    } catch (e) {
      setStatus({
        kind: 'error',
        message:
          e instanceof ApiError ? e.detail ?? t('error.generic') : t('error.network'),
      });
    }
  };

  const showCard = status.kind === 'sample' || status.kind === 'submitting' || status.kind === 'feedback';

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <Link
          href={`/${locale}`}
          className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          ← {t('back')}
        </Link>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">{t('title')}</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">{t('subtitle')}</p>
      </header>

      {status.kind === 'error' && (
        <div
          role="alert"
          className="mb-6 rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          <p className="font-semibold">{t('error.title')}</p>
          <p className="mt-1">{status.message}</p>
        </div>
      )}

      <section className="mb-6 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="input_type" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            {tCommon('inputTypeLabel')}
          </label>
          <select
            id="input_type"
            value={inputType}
            onChange={(e) => setInputType(e.target.value as InputType)}
            disabled={status.kind === 'loading' || status.kind === 'submitting'}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            {INPUT_TYPES.map((it) => (
              <option key={it} value={it}>
                {t(`inputType.${it}`)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="difficulty" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            {t('difficultyLabel', { level: difficulty })}
          </label>
          <select
            id="difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value) as Difficulty)}
            disabled={status.kind === 'loading' || status.kind === 'submitting'}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </section>

      <button
        type="button"
        disabled={status.kind === 'loading' || status.kind === 'submitting'}
        onClick={() => fetchNext(difficulty)}
        className="inline-flex items-center justify-center rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
      >
        {status.kind === 'loading'
          ? t('loadingSample')
          : showCard
            ? t('newSample')
            : t('start')}
      </button>

      {showCard && (
        <div className="mt-8">
          <TrainerCard
            sample={status.kind === 'feedback' ? status.sample : status.sample}
            feedback={status.kind === 'feedback' ? status.feedback : null}
            isSubmitting={status.kind === 'submitting'}
            onSubmit={handleSubmitAnswer}
            onNext={(nextDiff) => {
              setDifficulty(nextDiff);
              fetchNext(nextDiff);
            }}
          />
        </div>
      )}
    </main>
  );
}
