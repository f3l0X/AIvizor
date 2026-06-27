/**
 * Botón que alterna tema claro/oscuro.
 *
 * El estado real vive en la clase `dark` de <html> (la pone el script anti-FOUC
 * del layout antes del primer render). Al montar, sincronizamos el estado local
 * con esa clase para evitar discrepancias de hidratación.
 */

'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { applyTheme, getCurrentTheme, type Theme } from '../lib/theme';

export function ThemeToggle() {
  const t = useTranslations('common.theme');
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setTheme(getCurrentTheme());
    setMounted(true);
  }, []);

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    setTheme(next);
  };

  // Antes de montar no sabemos el tema real (SSR); renderizamos un placeholder
  // del mismo tamaño para no descuadrar el header ni provocar mismatch.
  const label = !mounted ? '' : theme === 'dark' ? t('toLight') : t('toDark');

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label || t('toggle')}
      title={label}
      className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-300 text-base transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
    >
      <span aria-hidden suppressHydrationWarning>
        {!mounted ? '🌓' : theme === 'dark' ? '☀️' : '🌙'}
      </span>
    </button>
  );
}
