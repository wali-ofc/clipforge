import Link from "next/link";

import { ArrowRightIcon, RegMarks } from "@/components/icons";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper-0 px-5 py-3 sm:px-8">
        <p className="mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
          ClipForge / Local video workshop
        </p>
        <span className="tally tally--live text-ink-600">Local</span>
      </div>

      <main className="mx-auto flex w-full max-w-[680px] flex-1 items-center px-5 py-16 sm:px-8">
        <div className="sheet relative w-full p-10 text-center">
          <RegMarks />
          <p className="mono text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-500">
            404 / No such sheet
          </p>
          <h1 className="display-sm mt-4">This page does not exist.</h1>
          <p className="note mx-auto mt-4 text-center">
            Return to the upload screen to start a new job.
          </p>
          <Link href="/" className="btn btn-primary mt-7">
            Back to upload
            <ArrowRightIcon className="h-4 w-4" />
          </Link>
        </div>
      </main>
    </div>
  );
}
