/**
 * Formulario del Analyzer.
 *
 * Controla todo el estado de entrada localmente (textarea + selectores).
 * El submit lo gestiona el padre (página) para que la página decida qué hacer
 * con el resultado (mostrar, persistir en URL, etc.).
 */

'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { loadSampleFor } from '../lib/samples';
import type { AnalyzeRequest, InputType, Language } from '../lib/types';

interface AnalyzeFormProps {
  defaultLanguage: Language;
  onSubmit: (req: AnalyzeRequest) => void;
  isLoading: boolean;
}

const INPUT_TYPES: InputType[] = ['email', 'url', 'sms'];

export function AnalyzeForm({ defaultLanguage, onSubmit, isLoading }: AnalyzeFormProps) {
  const t = useTranslations('analyzer.form');

  const [content, setContent] = useState('');
  const [inputType, setInputType] = useState<InputType>('email');
  const [language, setLanguage] = useState<Language>(defaultLanguage);

  const canSubmit = content.trim().length > 0 && !isLoading;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit({ content, input_type: inputType, language });
      }}
      className="space-y-4"
    >
      <div>
        <label
          htmlFor="content"
          className="block text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          {t('contentLabel')}
        </label>
        <textarea
          id="content"
          rows={10}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={t('contentPlaceholder')}
          className="mt-1 block w-full resize-y rounded-md border border-slate-300 bg-white p-3 font-mono text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          required
          maxLength={20000}
        />
        <div className="mt-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <button
            type="button"
            onClick={() => setContent(loadSampleFor(language, inputType).content)}
            disabled={isLoading}
            className="text-brand underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t('loadSample')}
          </button>
          <span>{content.length} / 20000</span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="input_type"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            {t('inputTypeLabel')}
          </label>
          <select
            id="input_type"
            value={inputType}
            onChange={(e) => setInputType(e.target.value as InputType)}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          >
            {INPUT_TYPES.map((it) => (
              <option key={it} value={it}>
                {t(`inputType.${it}`)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="language"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            {t('languageLabel')}
          </label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="es">Español</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex items-center justify-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-950"
      >
        {isLoading && (
          <span
            aria-hidden
            className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white"
          />
        )}
        {isLoading ? t('submitting') : t('submit')}
      </button>
    </form>
  );
}
