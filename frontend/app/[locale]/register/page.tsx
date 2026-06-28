/**
 * Página de registro.
 *
 * Encuadra el `AuthForm` en modo register. El backend hace auto-login al crear
 * la cuenta (deja la cookie), así que el flujo de éxito es idéntico al de login.
 */

'use client';

import { useTranslations } from 'next-intl';

import { AuthForm } from '../../../components/AuthForm';

export default function RegisterPage() {
  const t = useTranslations('auth.register');

  return (
    <main className="mx-auto flex max-w-md flex-col px-6 py-16">
      <h1 className="text-2xl font-bold tracking-tight">{t('title')}</h1>
      <p className="mt-2 mb-8 text-sm text-slate-600 dark:text-slate-400">{t('subtitle')}</p>
      <AuthForm mode="register" />
    </main>
  );
}
