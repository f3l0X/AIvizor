/**
 * Checklist vivo de la política de contraseñas.
 *
 * Compartido por el registro (AuthForm) y el cambio de contraseña
 * (ChangePasswordForm): los ✓ se encienden al teclear. La política es el espejo
 * de UI de los defaults del backend (lib/passwordPolicy.ts); la barrera real es
 * el 422 del servidor.
 */

'use client';

import { useTranslations } from 'next-intl';

import { checkPassword } from '../lib/passwordPolicy';

export function PasswordPolicyChecklist({ password }: { password: string }) {
  const t = useTranslations('auth.form.policy');
  return (
    <ul aria-live="polite" className="mt-2 space-y-0.5 text-xs">
      {checkPassword(password).map((c) => (
        <li
          key={c.code}
          className={
            c.met
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-slate-500 dark:text-slate-400'
          }
        >
          <span aria-hidden className="mr-1 inline-block w-3">
            {c.met ? '✓' : '·'}
          </span>
          {t(c.code)}
        </li>
      ))}
    </ul>
  );
}
