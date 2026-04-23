import type { Metadata, Viewport } from "next";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#000000",
};
import { Geist_Mono, Space_Grotesk } from "next/font/google";
import "../globals.css";
import SwRegister from "../../components/SwRegister";
import { ReactNode } from "react";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ZANA — Aeon Cognitivo",
  description: "Tu sistema cognitivo soberano. Escucha, ve, razona.",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "ZANA" },
  other: { "mobile-web-app-capable": "yes" },
};

const locales = ['en', 'es', 'pt', 'fr', 'de', 'it'];

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function RootLayout({
  children,
  params
}: Readonly<{
  children: ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;
  if (!locales.includes(locale)) {
    notFound();
  }

  const messages = await getMessages({locale});

  return (
    <html lang={locale} className="dark">
      <body
        className={`${spaceGrotesk.variable} ${geistMono.variable} antialiased bg-black text-slate-200 overflow-x-hidden`}
      >
        <NextIntlClientProvider messages={messages} locale={locale}>
          <SwRegister />
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
