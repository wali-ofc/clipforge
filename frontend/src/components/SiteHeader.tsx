import Link from "next/link";

import { LogoMark } from "@/components/icons";

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
      <Link href="/" className="flex items-center gap-3" aria-label="ClipForge home">
        <LogoMark className="h-9 w-9" />
        <span className="block leading-none">
          <span className="block text-[15px] font-extrabold tracking-[-0.04em] text-ink-900">
            CLIPFORGE
          </span>
          <span className="mono mt-1 block text-[9px] uppercase tracking-[0.18em] text-ink-500">
            Local video workshop
          </span>
        </span>
      </Link>

      <span className="tally tally--live text-ink-600">Runs on this machine</span>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-5 pb-8 pt-10 text-xs text-ink-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
      <p>ClipForge · local-first video clipping</p>
      <p className="mono text-[10px] uppercase tracking-[0.1em]">
        No cloud processing. No accounts. Files stay local.
      </p>
    </footer>
  );
}
