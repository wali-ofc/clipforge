"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AlertIcon,
  ArrowRightIcon,
  CheckIcon,
  CopyIcon,
  FileVideoIcon,
  SpinnerIcon,
  XIcon,
} from "@/components/icons";
import { ApiError, getJob } from "@/lib/api";
import {
  formatBytes,
  formatDate,
  formatDuration,
  formatFrameRate,
  formatResolution,
  isTerminalState,
  stateLabel,
} from "@/lib/format";
import type { Job, JobState } from "@/types/job";

function badgeClasses(state: JobState): string {
  if (state === "completed") {
    return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200";
  }
  if (state === "failed") {
    return "border-red-400/25 bg-red-400/10 text-red-200";
  }
  if (state === "cancelled") {
    return "border-white/10 bg-white/5 text-zinc-400";
  }
  return "border-forge-500/25 bg-forge-500/10 text-forge-200";
}

function StatusIcon({ state }: { state: JobState }) {
  if (state === "completed") {
    return <CheckIcon className="h-5 w-5" />;
  }
  if (state === "failed") {
    return <AlertIcon className="h-5 w-5" />;
  }
  if (state === "cancelled") {
    return <XIcon className="h-5 w-5" />;
  }
  return <SpinnerIcon className="h-5 w-5 animate-spin" />;
}

function statusIconClasses(state: JobState): string {
  if (state === "completed") {
    return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200";
  }
  if (state === "failed") {
    return "border-red-400/25 bg-red-400/10 text-red-200";
  }
  return "border-forge-500/25 bg-forge-500/10 text-forge-200";
}

function Detail({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.018] px-3.5 py-3">
      <dt className="text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-600">
        {label}
      </dt>
      <dd
        className={[
          "mt-1.5 text-sm text-zinc-200",
          mono ? "font-mono text-[12px]" : "",
        ].join(" ")}
      >
        {value}
      </dd>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-5" aria-hidden="true">
      <div className="h-40 animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.02]" />
      <div className="h-24 animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.02]" />
      <div className="h-48 animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.02]" />
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-2xl border border-red-400/20 bg-red-400/[0.05] p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-red-400/20 bg-red-400/10 text-red-300">
          <AlertIcon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-red-100">
            Could not load this job
          </h2>
          <p className="mt-1.5 text-sm leading-6 text-red-200/80">{message}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-300/20 bg-red-300/[0.06] px-3 py-2 text-xs font-medium text-red-100 transition hover:bg-red-300/10"
          >
            Try again
            <ArrowRightIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function JobStatusView({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const data = await getJob(jobId);
        if (cancelled) {
          return;
        }
        setJob(data);
        setError(null);
        setNotFound(false);
        if (!isTerminalState(data.state)) {
          timer = setTimeout(tick, 2000);
        }
      } catch (requestError) {
        if (cancelled) {
          return;
        }
        if (requestError instanceof ApiError && requestError.status === 404) {
          setNotFound(true);
          setError(null);
          return;
        }
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not load the job status.",
        );
        timer = setTimeout(tick, 3000);
      }
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [jobId, retryNonce]);

  function retryNow() {
    setError(null);
    setNotFound(false);
    setRetryNonce((value) => value + 1);
  }

  async function copyJobId() {
    try {
      await navigator.clipboard.writeText(job?.id ?? jobId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  if (notFound) {
    return (
      <div className="space-y-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-zinc-500 transition hover:text-zinc-300"
        >
          <span aria-hidden="true">←</span> Upload another video
        </Link>
        <div className="rounded-2xl border border-white/10 bg-surface-900/75 p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03] text-zinc-400">
            <FileVideoIcon className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-lg font-semibold text-zinc-100">
            Job not found
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-zinc-500">
            This job ID does not exist in the local database. It may have been
            deleted, or the link may be incorrect.
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-forge-500 px-4 py-2.5 text-sm font-semibold text-[#1b0d04] transition hover:bg-forge-400"
          >
            Back to upload
            <ArrowRightIcon className="h-4 w-4" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-zinc-500 transition hover:text-zinc-300"
        >
          <span aria-hidden="true">←</span> Upload another video
        </Link>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-700">
          Phase 1 · validation
        </span>
      </div>

      {!job && !error ? <Skeleton /> : null}

      {!job && error ? (
        <ErrorState message={error} onRetry={retryNow} />
      ) : null}

      {job ? (
        <>
          <section className="reveal overflow-hidden rounded-2xl border border-white/10 bg-surface-900/75 shadow-[0_24px_80px_-40px_rgba(0,0,0,0.9)]">
            <div className="flex flex-col gap-4 border-b border-white/[0.06] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-forge-500/20 bg-forge-500/10 text-forge-300">
                  <FileVideoIcon className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <h1 className="truncate text-[15px] font-semibold text-zinc-100">
                    {job.original_filename}
                  </h1>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    {formatBytes(job.size_bytes)} · uploaded{" "}
                    {formatDate(job.created_at)}
                  </p>
                </div>
              </div>
              <span
                className={[
                  "inline-flex shrink-0 items-center gap-1.5 self-start rounded-full border px-3 py-1.5 text-[11px] font-medium sm:self-auto",
                  badgeClasses(job.state),
                ].join(" ")}
              >
                {!isTerminalState(job.state) ? (
                  <span className="status-dot h-1.5 w-1.5 rounded-full bg-current" />
                ) : null}
                {stateLabel(job.state)}
              </span>
            </div>

            <div className="px-5 py-5 sm:px-6">
              <div className="flex items-start gap-3">
                <div
                  className={[
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border",
                    statusIconClasses(job.state),
                  ].join(" ")}
                >
                  <StatusIcon state={job.state} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-4">
                    <h2
                      className="text-sm font-semibold text-zinc-100"
                      aria-live="polite"
                    >
                      {stateLabel(job.state)}
                    </h2>
                    <span className="font-mono text-xs text-zinc-500">
                      {job.progress}%
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-zinc-400">
                    {job.stage_message}
                  </p>
                </div>
              </div>

              <div className="relative mt-4 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className={[
                    "relative h-full overflow-hidden rounded-full transition-[width] duration-500",
                    job.state === "failed"
                      ? "bg-red-400"
                      : "bg-gradient-to-r from-forge-500 to-forge-300",
                    !isTerminalState(job.state) && job.progress < 100
                      ? "progress-sheen"
                      : "",
                  ].join(" ")}
                  style={{
                    width: `${job.progress > 0 ? job.progress : 2}%`,
                  }}
                />
              </div>

              {!isTerminalState(job.state) ? (
                <p className="mt-3 text-[11px] text-zinc-600">
                  This page refreshes automatically. Jobs persist if you close
                  the tab.
                </p>
              ) : null}
            </div>
          </section>

          {error ? (
            <div
              role="alert"
              className="flex flex-col gap-3 rounded-xl border border-amber-400/20 bg-amber-400/[0.05] px-4 py-3 text-xs text-amber-100 sm:flex-row sm:items-center sm:justify-between"
            >
              <span>Connection lost. Retrying automatically. {error}</span>
              <button
                type="button"
                onClick={retryNow}
                className="self-start font-medium text-amber-200 underline decoration-amber-300/40 underline-offset-4 sm:self-auto"
              >
                Retry now
              </button>
            </div>
          ) : null}

          {job.state === "failed" ? (
            <section className="rounded-2xl border border-red-400/20 bg-red-400/[0.045] px-5 py-4">
              <div className="flex items-start gap-3">
                <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-red-300" />
                <div>
                  <h2 className="text-sm font-semibold text-red-100">
                    Upload failed validation
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-red-200/80">
                    {job.error ?? "The pipeline reported an unknown error."}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {job.state === "completed" ? (
            <section className="rounded-2xl border border-forge-500/20 bg-forge-500/[0.05] px-5 py-4">
              <div className="flex items-start gap-3">
                <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-forge-300" />
                <div>
                  <h2 className="text-sm font-semibold text-forge-200">
                    Source validated
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-forge-200/65">
                    The file is readable and its media metadata is stored. Clip
                    generation is not enabled in this Phase 1 build — the next
                    phases add transcription, moment selection, speaker
                    tracking, and 9:16 rendering.
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          <section className="rounded-2xl border border-white/10 bg-surface-900/60 p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
                Media details
              </h2>
              <button
                type="button"
                onClick={() => void copyJobId()}
                className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.07] bg-white/[0.025] px-2 py-1 font-mono text-[10px] text-zinc-500 transition hover:border-white/15 hover:text-zinc-300"
                title="Copy job ID"
              >
                <CopyIcon className="h-3 w-3" />
                {copied ? "copied" : "job id"}
              </button>
            </div>

            <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
              <Detail label="Duration" value={formatDuration(job.duration_seconds)} />
              <Detail
                label="Resolution"
                value={formatResolution(job.width, job.height)}
              />
              <Detail
                label="Frame rate"
                value={formatFrameRate(job.frame_rate)}
              />
              <Detail
                label="Video"
                value={job.video_codec?.toUpperCase() ?? "—"}
              />
              <Detail
                label="Audio"
                value={
                  job.has_audio
                    ? (job.audio_codec?.toUpperCase() ?? "Present")
                    : "No audio stream"
                }
              />
              <Detail
                label="Rotation"
                value={job.rotation ? `${job.rotation}°` : "None"}
              />
            </dl>

            <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
              <Detail
                label="Container"
                value={job.container_format ?? "—"}
                mono
              />
              <Detail label="Job ID" value={job.id} mono />
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
