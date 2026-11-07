import Link from "next/link";

import { LogoMark } from "@/components/icons";

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
      <Link
        href="/"
        className="group flex items-center gap-3 rounded-xl focus-visible:outline-none"
      >
        <LogoMark className="h-9 w-9 transition-transform duration-300 group-hover:-rotate-3 group-hover:scale-[1.04]" />
        <div className="leading-none">
          <div className="text-[17px] font-semibold tracking-[-0.02em] text-zinc-50">
            ClipForge
          </div>
          <div className="mt-1 text-[10px] font-medium uppercase tracking-[0.18em] text-zinc-500">
            Local clip studio
          </div>
        </div>
      </Link>

      <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.025] px-3 py-1.5 text-[11px] font-medium text-zinc-400 backdrop-blur">
        <span className="status-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
        Runs on this machine
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-5 pb-8 pt-10 text-xs text-zinc-600 sm:flex-row sm:items-center sm:justify-between sm:px-8">
      <p>ClipForge · local-first video clipping</p>
      <p>No cloud processing. No accounts. Your files stay local.</p>
    </footer>
  );
}
