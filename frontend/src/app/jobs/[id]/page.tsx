"use client";

import { useParams } from "next/navigation";

import { JobStatusView } from "@/components/JobStatusView";

export default function JobPage() {
  const params = useParams();
  const rawId = params?.id;
  const jobId = Array.isArray(rawId) ? (rawId[0] ?? "") : (rawId ?? "");

  return (
    <div className="flex min-h-full flex-col">
      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pb-16 pt-6 sm:px-8">
        <JobStatusView jobId={jobId} />
      </main>
    </div>
  );
}
