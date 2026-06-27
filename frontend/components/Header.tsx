/**
 * Cabecera global: marca + navegación + selector de idioma + toggle de tema.
 *
 * El bloque de la derecha (`actions`) está pensado para crecer: en Fase 7.4 se
 * añadirá aquí el estado de sesión (usuario / login / logout) junto a los
 * selectores de idioma y tema.
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';

import { LanguageSwitcher } from './LanguageSwitcher';
import { ThemeToggle } from './ThemeToggle';

export function Header() {
  const t = useTranslations('common.nav');
  const locale = useLocale();
  const pathname = usePathname();

  const links = [
    { href: `/${locale}/analyze`, label: t('analyzer') },
    { href: `/${locale}/train`, label: t('trainer') },
  ];

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-slate-50/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-3">
        <Link href={`/${locale}`} className="text-lg font-bold tracking-tight">
          AIvizor
        </Link>

        <nav className="hidden items-center gap-1 sm:flex">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? 'page' : undefined}
                className={
                  active
                    ? 'rounded-md px-3 py-1.5 text-sm font-semibold text-brand'
                    : 'rounded-md px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                }
              >
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
          {/* Fase 7.4: aquí irá el estado de sesión (usuario / login / logout). */}
        </div>
      </div>
    </header>
  );
}
