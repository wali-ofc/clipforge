import Link from "next/link";

import { LogoMark } from "@/components/icons";

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
      <Link
        href="/"
        className="group flex items-center gap-3 rounded-xl"
      >
        <LogoMark className="h-9 w-9 transition-transform duration-300 group-hover:-rotate-3 group-hover:scale-[1.04]" />
        <div className="leading-none">
          <div className="text-[17px] font-semibold tracking-[-0.02em] text-ink-900">
            ClipForge
          </div>
          <div className="mt-1 text-[10px] font-medium uppercase tracking-[0.18em] text-ink-500">
            Local clip studio
          </div>
        </div>
      </Link>

      <div className="flex items-center gap-2 rounded-full border border-line bg-paper-50 px-3 py-1.5 text-[11px] font-medium text-ink-500">
        <span className="status-dot h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Runs on this machine
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-5 pb-8 pt-10 text-xs text-ink-400 sm:flex-row sm:items-center sm:justify-between sm:px-8">
      <p>ClipForge · local-first video clipping</p>
      <p>No cloud processing. No accounts. Your files stay local.</p>
    </footer>
  );
}
