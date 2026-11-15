import type { Metadata, Viewport } from "next";
import "./globals.css";

import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "ClipForge — Local video tools",
  description:
    "Local-first video tools: AI Clipper for auto highlights and Segmenter for timestamp-based cutting and joining.",
};

export const viewport: Viewport = {
  themeColor: "#faf7ef",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
