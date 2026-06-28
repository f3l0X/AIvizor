/**
 * Estado de sesión en la cabecera.
 *
 * - loading       → placeholder discreto (evita parpadeo login↔usuario al hidratar).
 * - anónimo       → enlaces "Entrar" / "Crear cuenta".
 * - autenticado   → email (enlaza a Ajustes) + botón "Salir".
 *
 * Vive dentro del Header, que es client component; consume `useAuth()`.
 */

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';

import { useAuth } from './AuthProvider';

export function SessionNav() {
  const t = useTranslations('auth.nav');
  const locale = useLocale();
  const router = useRouter();
  const { user, status, logout } = useAuth();

  if (status === 'loading') {
    // Caja del mismo alto que el contenido real para no descuadrar el header.
    return <div aria-hidden className="h-9 w-20 animate-pulse rounded-md bg-slate-200/60 dark:bg-slate-800/60" />;
  }

  if (status === 'anonymous') {
    return (
      <div className="flex items-center gap-1">
        <Link
          href={`/${locale}/login`}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {t('login')}
        </Link>
        <Link
          href={`/${locale}/register`}
          className="rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-dark"
        >
          {t('register')}
        </Link>
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
    router.push(`/${locale}`);
  };

  return (
    <div className="flex items-center gap-2">
      {/* El distintivo de admin enlaza al panel de gestión (Fase 7.5). */}
      {user?.role === 'admin' && (
        <Link
          href={`/${locale}/admin`}
          title={t('adminPanel')}
          className="rounded-full bg-brand/10 px-2 py-0.5 text-xs font-semibold text-brand transition hover:bg-brand/20 dark:bg-brand/20 dark:hover:bg-brand/30"
        >
          {t('adminBadge')}
        </Link>
      )}
      <Link
        href={`/${locale}/settings`}
        title={t('settings')}
        className="max-w-[12rem] truncate rounded-md px-2.5 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
      >
        {user?.email}
      </Link>
      <button
        type="button"
        onClick={handleLogout}
        className="rounded-md border border-slate-300 px-2.5 py-1.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        {t('logout')}
      </button>
    </div>
  );
}
