/**
 * Página del Analyzer (cliente).
 *
 * Estado:
 *   - idle      → muestra solo el formulario.
 *   - loading   → formulario deshabilitado + indicador de carga.
 *   - success   → resultado debajo del formulario; botón "analizar otro".
 *   - error     → banner de error encima del formulario (no destruye el input).
 *
 * El idioma del análisis se inicializa con el locale de la URL (next-intl) pero
 * el usuario puede sobreescribirlo desde el selector del formulario.
 */

'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { AnalysisResultView } from '../../../components/AnalysisResultView';
import { AnalyzeForm } from '../../../components/AnalyzeForm';
import { analyze, ApiError } from '../../../lib/api';
import type { AnalysisResult, AnalyzeRequest, Language } from '../../../lib/types';

type Status =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; result: AnalysisResult }
  | { kind: 'error'; message: string };

export default function AnalyzePage() {
  const t = useTranslations('analyzer');
  const locale = useLocale() as Language;

  const [status, setStatus] = useState<Status>({ kind: 'idle' });

  const handleSubmit = async (req: AnalyzeRequest) => {
    setStatus({ kind: 'loading' });
    try {
      const result = await analyze(req);
      setStatus({ kind: 'success', result });
    } catch (e) {
      const message =
        e instanceof ApiError
          ? e.detail ?? t('error.generic')
          : t('error.network');
      setStatus({ kind: 'error', message });
    }
  };

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

      <AnalyzeForm
        defaultLanguage={locale}
        onSubmit={handleSubmit}
        isLoading={status.kind === 'loading'}
      />

      {status.kind === 'success' && (
        <div className="mt-10">
          <AnalysisResultView result={status.result} />
        </div>
      )}
    </main>
  );
}
