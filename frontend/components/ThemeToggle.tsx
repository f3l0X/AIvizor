/**
 * Botón que alterna tema claro/oscuro.
 *
 * El estado real vive en la clase `dark` de <html> (la pone el script anti-FOUC
 * del layout antes del primer render). Al montar, sincronizamos el estado local
 * con esa clase para evitar discrepancias de hidratación.
 */

'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { applyTheme, applyThemeClass, getStoredPreference, type Theme } from '../lib/theme';

export function ThemeToggle() {
  const t = useTranslations('common.theme');
  const pathname = usePathname();
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  // Reimponer el tema en cada cambio de ruta. Cambiar de locale re-renderiza el
  // layout y puede perder la clase `dark` del <html> (el script anti-FOUC solo
  // corre en la carga inicial). Releemos la preferencia persistida y la
  // reaplicamos para que el tema sobreviva a la navegación.
  useEffect(() => {
    const pref = getStoredPreference();
    applyThemeClass(pref);
    setTheme(pref);
    setMounted(true);
  }, [pathname]);

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
