/**
 * Panel de administración (requiere rol admin).
 *
 * Doble protección en cliente: redirige a la home si la sesión es anónima o si
 * el usuario no es admin. La barrera real la pone el backend (403 en /api/admin
 * para no-admins); esto es solo UX para no mostrar un panel que fallaría.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';

import { AdminUserTable } from '../../../components/AdminUserTable';
import { useAuth } from '../../../components/AuthProvider';

export default function AdminPage() {
  const t = useTranslations('admin');
  const locale = useLocale();
  const router = useRouter();
  const { user, status } = useAuth();

  const isAdmin = status === 'authenticated' && user?.role === 'admin';

  useEffect(() => {
    // Anónimo → login; logueado pero no admin → home (no tiene nada que ver aquí).
    if (status === 'anonymous') {
      router.replace(`/${locale}/login`);
    } else if (status === 'authenticated' && user?.role !== 'admin') {
      router.replace(`/${locale}`);
    }
  }, [status, user, locale, router]);

  if (!isAdmin) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-sm text-slate-500 dark:text-slate-400">{t('loading')}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">{t('subtitle')}</p>
      </header>

      <AdminUserTable />
    </main>
  );
}
