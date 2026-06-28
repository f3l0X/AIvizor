/**
 * Llamada a la acción de sesión en la home.
 *
 * - anónimo     → invita a crear cuenta / iniciar sesión (engancha el BYOK).
 * - autenticado → atajo a los ajustes de la cuenta.
 * - loading     → no pinta nada (evita parpadeo al hidratar).
 *
 * Es un client component embebido en la home (server component): la home sigue
 * siendo estática salvo este bloque.
 */

'use client';

import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import { useAuth } from './AuthProvider';

export function HomeAuthCta() {
  const t = useTranslations('home.cta');
  const locale = useLocale();
  const { user, status } = useAuth();

  if (status === 'loading') return null;

  if (status === 'authenticated') {
    return (
      <p className="mt-10 text-sm text-slate-600 dark:text-slate-400">
        {t('signedInAs', { email: user?.email ?? '' })}{' '}
        <Link
          href={`/${locale}/settings`}
          className="font-semibold text-brand underline-offset-2 hover:underline"
        >
          {t('manageAccount')}
        </Link>
      </p>
    );
  }

  return (
    <div className="mt-10 rounded-lg border border-slate-200 bg-white/50 p-5 dark:border-slate-800 dark:bg-slate-900/40">
      <p className="text-sm text-slate-600 dark:text-slate-400">{t('prompt')}</p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Link
          href={`/${locale}/register`}
          className="inline-flex items-center justify-center rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-dark"
        >
          {t('register')}
        </Link>
        <Link
          href={`/${locale}/login`}
          className="text-sm font-semibold text-brand underline-offset-2 hover:underline"
        >
          {t('login')}
        </Link>
      </div>
    </div>
  );
}
