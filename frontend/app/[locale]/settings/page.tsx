/**
 * Página de ajustes de la cuenta (requiere sesión).
 *
 * Es una ruta protegida en el cliente: si no hay sesión confirmada redirige a
 * login. La protección "real" la impone el backend (401 en /api/keys sin cookie);
 * esto es solo UX para no mostrar un formulario que fallaría.
 *
 * Contiene la info de la cuenta y el gestor de la clave BYOK.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';

import { ApiKeyManager } from '../../../components/ApiKeyManager';
import { useAuth } from '../../../components/AuthProvider';
import { ChangePasswordForm } from '../../../components/ChangePasswordForm';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const locale = useLocale();
  const router = useRouter();
  const { user, status } = useAuth();

  useEffect(() => {
    if (status === 'anonymous') {
      router.replace(`/${locale}/login`);
    }
  }, [status, locale, router]);

  // Mientras hidrata o si va a redirigir, no pintamos el contenido protegido.
  if (status !== 'authenticated' || !user) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-sm text-slate-500 dark:text-slate-400">{t('loading')}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">{t('subtitle')}</p>
      </header>

      <section className="mb-8 rounded-lg border border-slate-200 p-6 dark:border-slate-800">
        <h2 className="text-lg font-semibold">{t('account.title')}</h2>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-slate-500 dark:text-slate-400">{t('account.email')}</dt>
            <dd className="font-medium">{user.email}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-500 dark:text-slate-400">{t('account.role')}</dt>
            <dd className="font-medium">{t(`account.roles.${user.role}`)}</dd>
          </div>
        </dl>
      </section>

      <div className="mb-8">
        <ChangePasswordForm />
      </div>

      <ApiKeyManager />
    </main>
  );
}
