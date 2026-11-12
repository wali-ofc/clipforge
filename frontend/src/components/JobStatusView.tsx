"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AlertIcon,
  ArrowRightIcon,
  CheckIcon,
  CopyIcon,
  DownloadIcon,
  FileVideoIcon,
  SpinnerIcon,
  TrashIcon,
  XIcon,
} from "@/components/icons";
import {
  ApiError,
  deleteJob,
  getClipFileUrl,
  getJob,
  getJobClips,
} from "@/lib/api";
import {
  formatBytes,
  formatDate,
  formatDuration,
  formatFrameRate,
  formatResolution,
  isTerminalState,
  stateLabel,
} from "@/lib/format";
import type { Clip, Job, JobState } from "@/types/job";

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

function trackingLabel(clip: Clip): string {
  switch (clip.speaker_tracking_status) {
    case "tracked":
      return "Speaker-aware tracking";
    case "single_face":
      return "Single-face tracking";
    case "fallback":
      return "Stable fallback face";
    case "unavailable":
      return "Centre crop · tracking unavailable";
    case "failed":
      return "Centre crop · tracking failed";
    case "no_faces":
      return "No face detected · centre crop";
    case "no_frames":
      return "No frames sampled · centre crop";
    case "pending":
      return "Tracking pending";
    default:
      return clip.speaker_tracking_status;
  }
}

function trackingTone(clip: Clip): string {
  if (clip.speaker_tracking_status === "tracked") {
    return "border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200";
  }
  if (clip.speaker_tracking_status === "fallback") {
    return "border-amber-400/20 bg-amber-400/[0.06] text-amber-200";
  }
  return "border-white/10 bg-white/[0.03] text-zinc-400";
}

function fallbackNote(clip: Clip): string | null {
  switch (clip.speaker_tracking_status) {
    case "fallback":
      return "Speaker tracking used a stable fallback face, not active-speaker detection.";
    case "unavailable":
      return "Speaker tracking was unavailable; this clip uses a centre crop.";
    case "failed":
      return "Speaker tracking failed; this clip uses a centre crop.";
    case "no_faces":
      return "No face was detected; this clip uses a centre crop.";
    case "no_frames":
      return "No frames could be sampled; this clip uses a centre crop.";
    default:
      return null;
  }
}

function ClipCard({ clip, index }: { clip: Clip; index: number }) {
  const score = clip.score == null ? null : Math.round(clip.score);
  const confidence =
    clip.speaker_tracking_confidence == null
      ? null
      : Math.round(clip.speaker_tracking_confidence * 100);
  const cropSamples = clip.crop_plan?.samples?.length ?? 0;
  const isRendered =
    clip.render_status === "completed" && Boolean(clip.output_filename);
  const isRendering = clip.render_status === "rendering";
  const isFailed = clip.render_status === "failed";
  const note = fallbackNote(clip);
  const tone =
    score == null
      ? "border-white/10 bg-white/[0.03] text-zinc-400"
      : score >= 75
        ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
        : score >= 55
          ? "border-forge-500/25 bg-forge-500/10 text-forge-200"
          : "border-amber-400/20 bg-amber-400/10 text-amber-200";

  return (
    <article className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 transition hover:border-white/[0.14] sm:p-5">
      <div className="relative mx-auto aspect-[9/16] w-full max-w-[220px] overflow-hidden rounded-xl border border-white/[0.08] bg-black/60">
        {isRendered ? (
          <video
            src={getClipFileUrl(clip.id)}
            controls
            playsInline
            preload="metadata"
            aria-label={`Preview of ${clip.title}`}
            className="h-full w-full object-contain"
          />
        ) : isRendering ? (
          <div className="flex h-full flex-col items-center justify-center gap-2.5 p-4 text-center">
            <SpinnerIcon className="h-6 w-6 animate-spin text-forge-400" />
            <p className="text-xs font-medium text-forge-200">
              Rendering 9:16 MP4…
            </p>
          </div>
        ) : isFailed ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-red-300">
            <AlertIcon className="h-6 w-6 text-red-400" />
            <p className="text-[11px] font-medium leading-tight">
              Rendering failed
            </p>
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-zinc-500">
            <FileVideoIcon className="h-6 w-6" />
            <p className="text-[11px]">Render pending</p>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-zinc-400">
            Clip {String(index + 1).padStart(2, "0")}
          </p>
          <h3 className="mt-1.5 text-sm font-semibold leading-5 text-zinc-100">
            {clip.title}
          </h3>
        </div>
        <span
          className={[
            "shrink-0 rounded-lg border px-2.5 py-1 font-mono text-[11px] font-semibold",
            tone,
          ].join(" ")}
          title="Heuristic clip potential, not a virality prediction"
        >
          {score == null ? "—" : score}
          <span className="ml-0.5 text-[9px] font-normal opacity-70">/100</span>
        </span>
      </div>

      {clip.hook ? (
        <p className="mt-2.5 text-xs leading-5 text-zinc-300">{clip.hook}</p>
      ) : null}
      {clip.reason ? (
        <p className="mt-1.5 text-[11px] leading-5 text-zinc-400">
          {clip.reason}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-zinc-400">
        <span>
          {formatDuration(clip.start_seconds)} – {formatDuration(clip.end_seconds)}
        </span>
        <span aria-hidden="true" className="text-zinc-700">
          ·
        </span>
        <span>{formatDuration(clip.duration_seconds)}</span>
        {clip.width && clip.height ? (
          <>
            <span aria-hidden="true" className="text-zinc-700">
              ·
            </span>
            <span>
              {clip.width}×{clip.height}
            </span>
          </>
        ) : null}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 border-t border-white/[0.05] pt-2.5">
        <span
          className={[
            "rounded-md border px-1.5 py-0.5 font-mono text-[10px]",
            trackingTone(clip),
          ].join(" ")}
        >
          {trackingLabel(clip)}
        </span>
        {confidence != null ? (
          <span className="font-mono text-[10px] text-zinc-400">
            {confidence}% speaker confidence
          </span>
        ) : null}
        {cropSamples > 0 ? (
          <span className="font-mono text-[10px] text-zinc-400">
            {cropSamples} crop samples
          </span>
        ) : null}
      </div>

      {note ? (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-amber-400/15 bg-amber-400/[0.05] px-2.5 py-2 text-[10px] leading-4 text-amber-200/80">
          <AlertIcon className="mt-px h-3 w-3 shrink-0" />
          <span>{note}</span>
        </p>
      ) : null}

      {isFailed && clip.error ? (
        <p className="mt-2 text-[10px] leading-4 text-red-300/80">
          Error: {clip.error}
        </p>
      ) : null}

      {isRendered ? (
        <div className="mt-auto border-t border-white/[0.06] pt-3">
          <a
            href={getClipFileUrl(clip.id, true)}
            download
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-forge-500 px-4 py-2.5 text-xs font-semibold text-[#1b0d04] shadow-[0_10px_24px_-12px_rgba(245,138,59,0.6)] transition hover:bg-forge-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-300"
          >
            <DownloadIcon className="h-4 w-4" />
            Download MP4
          </a>
        </div>
      ) : null}
    </article>
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
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
  const [copied, setCopied] = useState(false);
  const [clips, setClips] = useState<Clip[]>([]);
  const [clipsError, setClipsError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || job.clip_count <= 0) {
      setClips([]);
      setClipsError(null);
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    getJobClips(jobId, controller.signal)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setClips(data);
        setClipsError(null);
      })
      .catch((requestError) => {
        if (cancelled) {
          return;
        }
        if (
          requestError instanceof DOMException &&
          requestError.name === "AbortError"
        ) {
          return;
        }
        setClipsError(
          requestError instanceof Error
            ? requestError.message
            : "Could not load clip candidates.",
        );
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [job?.clip_count, jobId, retryNonce]);

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

  async function removeJob() {
    if (!job || deleting) {
      return;
    }

    const active = !isTerminalState(job.state);
    const confirmed = window.confirm(
      active
        ? "Cancel this job and delete its upload, work files, and rendered clips? This cannot be undone."
        : "Delete this job and all of its media? This cannot be undone.",
    );
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteJob(job.id);
      router.push("/");
    } catch (requestError) {
      // Already gone (for example, deleted from another tab) counts as success.
      if (requestError instanceof ApiError && requestError.status === 404) {
        router.push("/");
        return;
      }
      setDeleteError(
        requestError instanceof Error
          ? requestError.message
          : "Could not delete this job.",
      );
      setDeleting(false);
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
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-600">
          Phase 7 · hardening
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
              <div className="flex shrink-0 flex-wrap items-center gap-2 self-start sm:self-auto">
                <span
                  className={[
                    "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium",
                    badgeClasses(job.state),
                  ].join(" ")}
                >
                  {!isTerminalState(job.state) ? (
                    <span className="status-dot h-1.5 w-1.5 rounded-full bg-current" />
                  ) : null}
                  {stateLabel(job.state)}
                </span>
                <button
                  type="button"
                  onClick={() => void removeJob()}
                  disabled={deleting}
                  className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-full border border-red-400/20 bg-red-400/[0.05] px-3 py-1.5 text-[11px] font-medium text-red-200 transition hover:border-red-400/35 hover:bg-red-400/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400/60 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deleting ? (
                    <SpinnerIcon className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <TrashIcon className="h-3.5 w-3.5" />
                  )}
                  {deleting
                    ? isTerminalState(job.state)
                      ? "Deleting…"
                      : "Cancelling…"
                    : isTerminalState(job.state)
                      ? "Delete job & media"
                      : "Cancel & delete job"}
                </button>
              </div>
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
                  the tab. Cancelling stops the worker and deletes the upload,
                  work files, and any rendered clips.
                </p>
              ) : null}

              {deleteError ? (
                <p
                  role="alert"
                  className="mt-3 flex items-start gap-2 rounded-lg border border-red-400/20 bg-red-400/[0.05] px-3 py-2 text-[11px] leading-5 text-red-200"
                >
                  <AlertIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>{deleteError}</span>
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
                    Processing failed
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-red-200/80">
                    {job.error ?? "The pipeline reported an unknown error."}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {job.state === "cancelled" ? (
            <section className="rounded-2xl border border-white/10 bg-white/[0.02] px-5 py-4">
              <div className="flex items-start gap-3">
                <XIcon className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                <div>
                  <h2 className="text-sm font-semibold text-zinc-200">
                    Job cancelled
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-zinc-400">
                    Processing stopped before completion and temporary work
                    files were cleaned up. Delete the job to remove its upload
                    and any clips that were already rendered.
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
                    {job.has_speech === false
                      ? "No useful speech found"
                      : job.clip_count > 0
                        ? "Clips rendered & ready to download"
                        : "No candidate clips found"}
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-forge-200/65">
                    {job.has_speech === false
                      ? "The audio was processed but produced no usable speech segments. No clips were selected; speaker tracking and rendering were skipped."
                      : job.clip_count > 0
                        ? `${job.clip_count} short clip${job.clip_count === 1 ? "" : "s"} extracted and rendered in 9:16 portrait with speaker-aware framing. Preview each clip and download the MP4 below.`
                        : "The transcript was processed, but no self-contained moment fit the configured duration range. Try a longer recording or adjust the clip limits."}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {job.clip_count > 0 ? (
            <section className="rounded-2xl border border-white/10 bg-surface-900/60 p-5 sm:p-6">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
                  Rendered clips
                </h2>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-zinc-700">
                  {job.clip_selection_model ?? "local model"} · heuristic score
                </span>
              </div>

              {clipsError ? (
                <p className="rounded-lg border border-amber-400/20 bg-amber-400/[0.05] px-3 py-2 text-xs text-amber-100">
                  {clipsError}
                </p>
              ) : clips.length === 0 ? (
                <p className="text-xs text-zinc-500">Loading clip candidates…</p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {clips.map((clip, index) => (
                    <ClipCard key={clip.id} clip={clip} index={index} />
                  ))}
                </div>
              )}

              <p className="mt-4 text-[11px] leading-5 text-zinc-400">
                Clips are H.264 video with AAC audio in 9:16 portrait at the
                configured resolution. Clip potential is a deterministic
                weighted score from hook, clarity, payoff, interest, and
                conciseness — not a virality prediction. When active-speaker
                confidence is low or a face is missing, the planner uses an
                explicit fallback and the card says so instead of claiming
                speaker tracking.
              </p>
            </section>
          ) : null}

          {job.has_transcript ? (
            <section className="rounded-2xl border border-white/10 bg-surface-900/60 p-5 sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
                  Transcript
                </h2>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-zinc-700">
                  internal data
                </span>
              </div>
              <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                <Detail
                  label="Language"
                  value={job.transcript_language?.toUpperCase() ?? "Not detected"}
                />
                <Detail
                  label="Segments"
                  value={String(job.transcript_segment_count ?? 0)}
                />
                <Detail
                  label="Speech"
                  value={job.has_speech ? "Detected" : "None detected"}
                />
              </dl>
              <p className="mt-3 text-[11px] leading-5 text-zinc-600">
                Word-level timestamps are stored in the job work directory.
                Captions are not generated or burned into any video.
              </p>
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
