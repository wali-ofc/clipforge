"use client";

import { useParams } from "next/navigation";

import { JobStatusView } from "@/components/JobStatusView";
import { SiteFooter, SiteHeader } from "@/components/SiteHeader";

export default function JobPage() {
  const params = useParams();
  const rawId = params?.id;
  const jobId = Array.isArray(rawId) ? (rawId[0] ?? "") : (rawId ?? "");

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-5 pb-16 sm:px-8">
        <JobStatusView jobId={jobId} />
      </main>
      <SiteFooter />
    </div>
  );
}
