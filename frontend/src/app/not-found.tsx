import Link from "next/link";

import { SiteFooter, SiteHeader } from "@/components/SiteHeader";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-4xl flex-1 items-center justify-center px-5 pb-16 sm:px-8">
        <div className="w-full rounded-2xl border border-white/10 bg-surface-900/70 p-8 text-center">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-forge-300">
            404
          </p>
          <h1 className="mt-3 text-xl font-semibold text-zinc-100">
            That page does not exist
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-zinc-500">
            Return to the upload screen to start a new job.
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-forge-500 px-4 py-2.5 text-sm font-semibold text-[#1b0d04] transition hover:bg-forge-400"
          >
            Back to upload
          </Link>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
