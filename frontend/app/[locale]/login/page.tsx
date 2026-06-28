/**
 * Página de inicio de sesión.
 *
 * Solo encuadra el `AuthForm` en modo login; toda la lógica (submit, errores,
 * redirección) vive en el formulario, que ya habla con el AuthProvider.
 */

'use client';

import { useTranslations } from 'next-intl';

import { AuthForm } from '../../../components/AuthForm';

export default function LoginPage() {
  const t = useTranslations('auth.login');

  return (
    <main className="mx-auto flex max-w-md flex-col px-6 py-16">
      <h1 className="text-2xl font-bold tracking-tight">{t('title')}</h1>
      <p className="mt-2 mb-8 text-sm text-slate-600 dark:text-slate-400">{t('subtitle')}</p>
      <AuthForm mode="login" />
    </main>
  );
}
