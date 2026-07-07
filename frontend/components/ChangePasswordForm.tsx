/**
 * Cambio de contraseña del propio usuario (pantalla de ajustes).
 *
 * Pide la contraseña actual (re-autenticación: una sesión abierta no basta) y la
 * nueva con el mismo checklist vivo del registro. El backend re-verifica ambas
 * (400 si la actual no coincide, 422 si la nueva no cumple la política). La
 * sesión sigue siendo válida tras el cambio.
 */

'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { PasswordPolicyChecklist } from './PasswordPolicyChecklist';
import { changePassword } from '../lib/api';
import { errorMessage } from '../lib/errors';
import { passwordMeetsPolicy } from '../lib/passwordPolicy';

export function ChangePasswordForm() {
  const t = useTranslations('settings.password');

  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canSubmit = current.length > 0 && passwordMeetsPolicy(next) && !busy;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await changePassword(current, next);
      // Nunca conservamos contraseñas en el estado tras usarlas.
      setCurrent('');
      setNext('');
      setNotice(t('changed'));
    } catch (err) {
      setError(errorMessage(err, t));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rounded-lg border border-slate-200 p-6 dark:border-slate-800">
      <h2 className="text-lg font-semibold">{t('title')}</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t('description')}</p>

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </div>
      )}
      {notice && (
        <div
          role="status"
          className="mt-4 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
        >
          {notice}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 space-y-4" noValidate>
        <div>
          <label
            htmlFor="current_password"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            {t('currentLabel')}
          </label>
          <input
            id="current_password"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
            maxLength={128}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2.5 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
        </div>

        <div>
          <label
            htmlFor="new_password"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            {t('newLabel')}
          </label>
          <input
            id="new_password"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
            minLength={8}
            maxLength={128}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2.5 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
          <PasswordPolicyChecklist password={next} />
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-950"
        >
          {busy && (
            <span
              aria-hidden
              className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
          )}
          {t('submit')}
        </button>
      </form>
    </section>
  );
}
