import { useTranslations } from 'next-intl';
import Link from 'next/link';

export default function HomePage() {
  const t = useTranslations('home');

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">
      <h1 className="text-5xl font-bold tracking-tight">AIvizor</h1>
      <p className="mt-4 text-xl text-slate-600 dark:text-slate-400">{t('tagline')}</p>

      <div className="mt-12 grid gap-4 sm:grid-cols-2">
        <Link
          href="analyze"
          className="rounded-lg border border-slate-200 p-6 transition hover:border-brand hover:shadow-md dark:border-slate-800"
        >
          <h2 className="text-xl font-semibold">{t('analyzer.title')}</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            {t('analyzer.description')}
          </p>
        </Link>
        <Link
          href="train"
          className="rounded-lg border border-slate-200 p-6 transition hover:border-brand hover:shadow-md dark:border-slate-800"
        >
          <h2 className="text-xl font-semibold">{t('trainer.title')}</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            {t('trainer.description')}
          </p>
        </Link>
      </div>
    </main>
  );
}
