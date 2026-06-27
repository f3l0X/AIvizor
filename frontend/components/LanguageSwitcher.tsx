/**
 * Conmutador de idioma de la interfaz (ES / EN).
 *
 * El locale vive como primer segmento de la ruta (next-intl con
 * localePrefix:'always'). Cambiar de idioma = navegar a la misma ruta con el
 * otro locale, preservando el resto del path y la query.
 */

'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';

import { locales, type Locale } from '../i18n';

export function LanguageSwitcher() {
  const current = useLocale() as Locale;
  const pathname = usePathname();
  const router = useRouter();

  // Nota: deliberadamente NO usamos useSearchParams aquí. En el App Router,
  // useSearchParams fuerza un CSR bailout del subárbol; como este componente
  // vive en el layout (Header), eso quitaría el header del SSR en todas las
  // rutas. El analyzer/trainer no dependen de query params, así que cambiar de
  // idioma preservando solo el path es suficiente.
  const switchTo = (target: Locale) => {
    if (target === current) return;
    // pathname incluye el locale como primer segmento: /es/analyze -> /en/analyze
    const segments = pathname.split('/');
    segments[1] = target;
    router.push(segments.join('/'));
  };

  return (
    <div className="inline-flex overflow-hidden rounded-md border border-slate-300 text-xs font-semibold dark:border-slate-700">
      {locales.map((loc) => {
        const active = loc === current;
        return (
          <button
            key={loc}
            type="button"
            onClick={() => switchTo(loc)}
            aria-current={active ? 'true' : undefined}
            className={
              active
                ? 'bg-brand px-2.5 py-1.5 text-white'
                : 'px-2.5 py-1.5 text-slate-600 transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
            }
          >
            {loc.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
