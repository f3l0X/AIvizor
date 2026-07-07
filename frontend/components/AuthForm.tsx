/**
 * Formulario de credenciales compartido por las páginas de login y registro.
 *
 * Login y registro comparten campos (email + contraseña) y casi todo el flujo;
 * solo cambia el endpoint, los textos y, en registro, la longitud mínima de la
 * contraseña (el backend exige >= 8 al crear). El `mode` decide esas diferencias.
 *
 * Tras éxito redirige a `next` (o a la home del locale). El padre no necesita
 * gestionar nada: el AuthProvider ya tiene la sesión en memoria.
 */

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { useAuth } from './AuthProvider';
import { PasswordPolicyChecklist } from './PasswordPolicyChecklist';
import { errorMessage } from '../lib/errors';
import { passwordMeetsPolicy } from '../lib/passwordPolicy';

type Mode = 'login' | 'register';

export function AuthForm({ mode }: { mode: Mode }) {
  const t = useTranslations('auth');
  const locale = useLocale();
  const router = useRouter();
  const { login, register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // El registro exige la política de contraseñas completa (checklist en vivo,
  // espejo del backend); el login solo pide que no esté vacía (el backend
  // valida las credenciales completas).
  const minLength = mode === 'register' ? 8 : 1;
  const passwordOk =
    mode === 'register' ? passwordMeetsPolicy(password) : password.length >= minLength;
  const canSubmit = email.trim().length > 0 && passwordOk && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const credentials = { email: email.trim(), password };
      if (mode === 'register') {
        await register(credentials);
      } else {
        await login(credentials);
      }
      router.push(`/${locale}`);
    } catch (err) {
      setError(errorMessage(err, t));
      setSubmitting(false);
    }
  };

  const otherMode: Mode = mode === 'login' ? 'register' : 'login';

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </div>
      )}

      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          {t('form.email')}
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={254}
          className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2.5 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          {t('form.password')}
        </label>
        <input
          id="password"
          type="password"
          autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={minLength}
          maxLength={128}
          className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2.5 text-sm text-slate-900 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        />
        {mode === 'register' && <PasswordPolicyChecklist password={password} />}
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-950"
      >
        {submitting && (
          <span
            aria-hidden
            className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white"
          />
        )}
        {submitting ? t(`${mode}.submitting`) : t(`${mode}.submit`)}
      </button>

      <p className="text-center text-sm text-slate-600 dark:text-slate-400">
        {t(`${mode}.switchPrompt`)}{' '}
        <Link
          href={`/${locale}/${otherMode}`}
          className="font-semibold text-brand underline-offset-2 hover:underline"
        >
          {t(`${mode}.switchLink`)}
        </Link>
      </p>
    </form>
  );
}
