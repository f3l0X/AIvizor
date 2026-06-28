import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { AuthProvider } from '../../components/AuthProvider';
import { Header } from '../../components/Header';
import { locales, type Locale } from '../../i18n';
import { themeInitScript } from '../../lib/theme';
import '../globals.css';

export const metadata: Metadata = {
  title: 'AIvizor — See the phish before it bites',
  description: 'Anti-phishing analyzer + trainer powered by AI.',
};

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  if (!locales.includes(locale as Locale)) notFound();

  const messages = await getMessages();

  return (
    // suppressHydrationWarning: el script anti-FOUC modifica la clase de <html>
    // antes de la hidratación, así que el cliente no coincidirá con el HTML del
    // servidor en ese atributo — es esperado y no un error real.
    <html lang={locale} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <Header />
            {children}
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
