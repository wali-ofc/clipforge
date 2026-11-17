"use client";

import { useParams } from "next/navigation";

import { JobStatusView } from "@/components/JobStatusView";

export default function JobPage() {
  const params = useParams();
  const rawId = params?.id;
  const jobId = Array.isArray(rawId) ? (rawId[0] ?? "") : (rawId ?? "");

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper-0 px-5 py-3 sm:px-8">
        <p className="mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
          ClipForge / Local video workshop
        </p>
        <div className="hidden items-center gap-4 sm:flex">
          <span className="mono text-[10px] uppercase tracking-[0.16em] text-ink-400">
            Job / {jobId.slice(0, 8)}
          </span>
          <span className="tally tally--live text-ink-600">Local</span>
        </div>
      </div>

      <main className="mx-auto w-full max-w-[1120px] flex-1 px-5 pb-16 pt-7 sm:px-8">
        <JobStatusView jobId={jobId} />
      </main>
    </div>
  );
}
