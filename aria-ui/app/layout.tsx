import type { Metadata, Viewport } from "next";
import { Geist_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import SwRegister from "../components/SwRegister";
import TitleBar from "../components/TitleBar";
import { ReactNode } from "react";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#000000",
};

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

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${spaceGrotesk.variable} ${geistMono.variable} antialiased bg-black text-slate-200 overflow-x-hidden`}
      >
        <TitleBar />
        <SwRegister />
        {children}
      </body>
    </html>
  );
}
