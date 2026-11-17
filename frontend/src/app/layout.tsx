import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";

import { AppShell } from "@/components/AppShell";

const archivo = localFont({
  src: "./fonts/Archivo-Variable.woff2",
  variable: "--font-archivo",
  display: "swap",
});

const robotoMono = localFont({
  src: "./fonts/RobotoMono-Variable.woff2",
  variable: "--font-roboto-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ClipForge — Local video clipping",
  description:
    "Local-first video tools: AI Clipper for auto highlights and Segmenter for timestamp-based cutting and joining.",
};

export const viewport: Viewport = {
  themeColor: "#f2efe7",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${archivo.variable} ${robotoMono.variable}`}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
