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
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (state === "failed") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (state === "cancelled") {
    return "border-line bg-paper-200 text-ink-700";
  }
  return "border-teal-200 bg-teal-50 text-teal-700";
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
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (state === "failed") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (state === "cancelled") {
    return "border-line bg-paper-200 text-ink-700";
  }
  return "border-teal-200 bg-teal-50 text-teal-700";
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
    <div className="rounded-xl border border-line bg-paper-50 px-3.5 py-3">
      <dt className="text-[10px] font-medium uppercase tracking-[0.16em] text-ink-400">
        {label}
      </dt>
      <dd
        className={[
          "mt-1.5 text-sm text-ink-800",
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
    case "disabled":
      return "Centered crop · tracking off";
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
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (clip.speaker_tracking_status === "fallback") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (clip.speaker_tracking_status === "disabled") {
    return "border-line bg-paper-100 text-ink-600";
  }
  return "border-line bg-paper-100 text-ink-500";
}

function fallbackNote(clip: Clip): string | null {
  switch (clip.speaker_tracking_status) {
    case "fallback":
      return "Speaker tracking used a stable fallback face, not active-speaker detection.";
    case "disabled":
      return "Speaker tracking was turned off for this job; this clip uses a stable centered 9:16 crop.";
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

function ClipCard({
  clip,
  index,
  jobKind,
}: {
  clip: Clip;
  index: number;
  jobKind: "ai_clipper" | "segmenter";
}) {
  const isSegmenter = jobKind === "segmenter";
  const score = !isSegmenter && clip.score == null ? null : clip.score == null ? null : Math.round(clip.score);
  const confidence =
    !isSegmenter && clip.speaker_tracking_confidence == null
      ? null
      : clip.speaker_tracking_confidence == null
        ? null
        : Math.round(clip.speaker_tracking_confidence * 100);
  const cropSamples = clip.crop_plan?.samples?.length ?? 0;
  const isRendered =
    clip.render_status === "completed" && Boolean(clip.output_filename);
  const isRendering = clip.render_status === "rendering";
  const isFailed = clip.render_status === "failed";
  const note = isSegmenter ? null : fallbackNote(clip);
  const tone =
    score == null
      ? "border-line bg-paper-100 text-ink-500"
      : score >= 75
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : score >= 55
          ? "border-teal-200 bg-teal-50 text-teal-700"
          : "border-amber-200 bg-amber-50 text-amber-800";
  const parts = (clip.component_scores as any)?.parts as
    | { start: number; end: number }[]
    | undefined;
  const joined = Boolean((clip.component_scores as any)?.joined);
  const outputFrame = ((clip.component_scores as any)?.output_frame ||
    (clip.tracking_details as any)?.output_frame ||
    "") as string;
  const aspectClass =
    isSegmenter && outputFrame === "original" && clip.width && clip.height
      ? ""
      : "aspect-[9/16]";
  const previewStyle =
    isSegmenter && outputFrame === "original" && clip.width && clip.height
      ? ({ aspectRatio: `${clip.width} / ${clip.height}` } as const)
      : undefined;

  return (
    <article className="flex flex-col rounded-2xl border border-line bg-paper-50 p-4 transition hover:border-line-strong sm:p-5">
      <div
        className={[
          "relative mx-auto w-full max-w-[260px] overflow-hidden rounded-xl border border-line bg-ink-900",
          aspectClass,
        ].join(" ")}
        style={previewStyle}
      >
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
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2.5 p-4 text-center">
            <SpinnerIcon className="h-6 w-6 animate-spin text-teal-300" />
            <p className="text-xs font-medium text-teal-100">
              Rendering MP4…
            </p>
          </div>
        ) : isFailed ? (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center text-red-300">
            <AlertIcon className="h-6 w-6 text-red-300" />
            <p className="text-[11px] font-medium leading-tight">
              Rendering failed
            </p>
          </div>
        ) : (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center text-paper-300">
            <FileVideoIcon className="h-6 w-6" />
            <p className="text-[11px]">Render pending</p>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
            {isSegmenter ? `Segment ${String(index + 1).padStart(2, "0")}` : `Clip ${String(index + 1).padStart(2, "0")}`}
          </p>
          <h3 className="mt-1.5 text-sm font-semibold leading-5 text-ink-900">
            {clip.title}
          </h3>
        </div>
        {!isSegmenter ? (
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
        ) : (
          <span className="shrink-0 rounded-lg border border-teal-200 bg-teal-50 px-2.5 py-1 font-mono text-[10px] font-semibold text-teal-700">
            {joined ? "JOINED" : "CUT"}
          </span>
        )}
      </div>

      {!isSegmenter && clip.hook ? (
        <p className="mt-2.5 text-xs leading-5 text-ink-700">{clip.hook}</p>
      ) : null}
      {clip.reason ? (
        <p className="mt-1.5 text-[11px] leading-5 text-ink-500">
          {clip.reason}
        </p>
      ) : null}

      {isSegmenter && joined && parts && parts.length > 1 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {parts.map((p, i) => (
            <span
              key={i}
              className="rounded-md border border-line bg-white px-1.5 py-0.5 font-mono text-[10px] text-ink-600"
            >
              {formatDuration(p.start)}–{formatDuration(p.end)}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-ink-500">
        <span>
          {formatDuration(clip.start_seconds)} – {formatDuration(clip.end_seconds)}
        </span>
        <span aria-hidden="true" className="text-ink-400">
          ·
        </span>
        <span>{formatDuration(clip.duration_seconds)}</span>
        {clip.width && clip.height ? (
          <>
            <span aria-hidden="true" className="text-ink-400">
              ·
            </span>
            <span>
              {clip.width}×{clip.height}
            </span>
          </>
        ) : null}
      </div>

      {!isSegmenter ? (
        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 border-t border-line pt-2.5">
          <span
            className={[
              "rounded-md border px-1.5 py-0.5 font-mono text-[10px]",
              trackingTone(clip),
            ].join(" ")}
          >
            {trackingLabel(clip)}
          </span>
          {confidence != null ? (
            <span className="font-mono text-[10px] text-ink-500">
              {confidence}% speaker confidence
            </span>
          ) : null}
          {cropSamples > 0 ? (
            <span className="font-mono text-[10px] text-ink-500">
              {cropSamples} crop samples
            </span>
          ) : null}
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 border-t border-line pt-2.5">
          <span className="rounded-md border border-line bg-white px-1.5 py-0.5 font-mono text-[10px] text-ink-600">
            {outputFrame === "portrait_9_16" ? "9:16 portrait" : "Original frame"}
          </span>
          {joined ? (
            <span className="font-mono text-[10px] text-ink-500">
              {parts?.length ?? 0} parts joined
            </span>
          ) : (
            <span className="font-mono text-[10px] text-ink-500">Single cut</span>
          )}
        </div>
      )}

      {note ? (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-2 text-[10px] leading-4 text-amber-800">
          <AlertIcon className="mt-px h-3 w-3 shrink-0" />
          <span>{note}</span>
        </p>
      ) : null}

      {isFailed && clip.error ? (
        <p className="mt-2 text-[10px] leading-4 text-red-600">
          Error: {clip.error}
        </p>
      ) : null}

      {isRendered ? (
        <div className="mt-auto border-t border-line pt-3">
          <a
            href={getClipFileUrl(clip.id, true)}
            download
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-teal-500 px-4 py-2.5 text-xs font-semibold text-white shadow-[0_8px_20px_-10px_rgba(15,107,98,0.4)] transition hover:bg-teal-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-500"
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
      <div className="h-40 animate-pulse rounded-2xl border border-line bg-paper-200/70" />
      <div className="h-24 animate-pulse rounded-2xl border border-line bg-paper-200/70" />
      <div className="h-48 animate-pulse rounded-2xl border border-line bg-paper-200/70" />
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
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-red-200 bg-red-50 text-red-600">
          <AlertIcon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-red-800">
            Could not load this job
          </h2>
          <p className="mt-1.5 text-sm leading-6 text-red-700">{message}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-800 transition hover:bg-red-100"
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

    const loadClips = () => {
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
    };

    loadClips();

    // Refresh while rendering so cards update from "rendering" to playable/downloadable.
    // Also re-fetch once the job reaches a terminal state to pick up final statuses.
    let interval: ReturnType<typeof setInterval> | undefined;
    if (!isTerminalState(job.state)) {
      interval = setInterval(loadClips, 2500);
    }

    return () => {
      cancelled = true;
      controller.abort();
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [job?.clip_count, job?.state, jobId, retryNonce]);

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
          className="inline-flex items-center gap-2 text-xs font-medium text-ink-500 transition hover:text-ink-700"
        >
          <span aria-hidden="true">←</span> Upload another video
        </Link>
        <div className="rounded-2xl border border-line bg-white p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-line bg-paper-100 text-ink-500">
            <FileVideoIcon className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-lg font-semibold text-ink-900">
            Job not found
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-ink-500">
            This job ID does not exist in the local database. It may have been
            deleted, or the link may be incorrect.
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-600"
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
          href={job?.kind === "segmenter" ? "/segmenter" : "/"}
          className="inline-flex items-center gap-2 text-xs font-medium text-ink-500 transition hover:text-ink-700"
        >
          <span aria-hidden="true">←</span>{" "}
          {job?.kind === "segmenter" ? "Back to Segmenter" : "Back to AI Clipper"}
        </Link>
      </div>

      {!job && !error ? <Skeleton /> : null}

      {!job && error ? (
        <ErrorState message={error} onRetry={retryNow} />
      ) : null}

      {job ? (
        <>
          <section className="overflow-hidden rounded-2xl border border-line bg-white shadow-[0_1px_2px_rgba(23,33,30,0.04),0_18px_48px_-28px_rgba(23,33,30,0.28)]">
            <div className="flex flex-col gap-4 border-b border-line px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-teal-200 bg-teal-50 text-teal-600">
                  <FileVideoIcon className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <h1 className="truncate text-[15px] font-semibold text-ink-900">
                    {job.original_filename}
                  </h1>
                  <p className="mt-0.5 text-xs text-ink-500">
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
                  className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-[11px] font-medium text-red-700 transition hover:border-red-300 hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-60"
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
                      className="text-sm font-semibold text-ink-900"
                      aria-live="polite"
                    >
                      {stateLabel(job.state)}
                    </h2>
                    <span className="font-mono text-xs text-ink-500">
                      {job.progress}%
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-ink-500">
                    {job.stage_message}
                  </p>
                </div>
              </div>

              <div className="relative mt-4 h-1.5 overflow-hidden rounded-full bg-paper-200">
                <div
                  className={[
                    "relative h-full overflow-hidden rounded-full transition-[width] duration-500",
                    job.state === "failed"
                      ? "bg-red-500"
                      : "bg-teal-500",
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
                <p className="mt-3 text-[11px] text-ink-400">
                  This page refreshes automatically. Jobs persist if you close
                  the tab. Cancelling stops the worker and deletes the upload,
                  work files, and any rendered clips.
                </p>
              ) : null}

              {deleteError ? (
                <p
                  role="alert"
                  className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[11px] leading-5 text-red-700"
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
              className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800 sm:flex-row sm:items-center sm:justify-between"
            >
              <span>Connection lost. Retrying automatically. {error}</span>
              <button
                type="button"
                onClick={retryNow}
                className="self-start font-medium text-amber-800 underline decoration-amber-300/40 underline-offset-4 sm:self-auto"
              >
                Retry now
              </button>
            </div>
          ) : null}

          {job.state === "failed" ? (
            <section className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4">
              <div className="flex items-start gap-3">
                <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                <div>
                  <h2 className="text-sm font-semibold text-red-800">
                    Processing failed
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-red-700">
                    {job.error ?? "The pipeline reported an unknown error."}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {job.state === "cancelled" ? (
            <section className="rounded-2xl border border-line bg-paper-50 px-5 py-4">
              <div className="flex items-start gap-3">
                <XIcon className="mt-0.5 h-4 w-4 shrink-0 text-ink-500" />
                <div>
                  <h2 className="text-sm font-semibold text-ink-800">
                    Job cancelled
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-ink-500">
                    Processing stopped before completion and temporary work
                    files were cleaned up. Delete the job to remove its upload
                    and any {job.kind === "segmenter" ? "segments" : "clips"} that were already rendered.
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {job.state === "completed" ? (
            <section className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4">
              <div className="flex items-start gap-3">
                <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <div>
                  <h2 className="text-sm font-semibold text-emerald-800">
                    {job.kind === "segmenter"
                      ? job.clip_count > 0
                        ? "Segments ready to download"
                        : "No segments produced"
                      : job.has_speech === false
                        ? "No useful speech found"
                        : job.clip_count > 0
                          ? "Clips rendered & ready to download"
                          : "No candidate clips found"}
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-emerald-700">
                    {job.kind === "segmenter"
                      ? job.clip_count > 0
                        ? `${job.clip_count} segment${job.clip_count === 1 ? "" : "s"} rendered from your timestamps (${job.segment_output_frame === "portrait_9_16" ? "9:16 portrait" : "original frame"}). Preview and download each clip below.`
                        : "Segmenting finished, but no downloadable outputs were produced. Check your timestamps and try again."
                      : job.has_speech === false
                        ? "The audio was processed but produced no usable speech segments. No clips were selected; crop planning and rendering were skipped."
                        : job.clip_count > 0
                          ? `${job.clip_count} short clip${job.clip_count === 1 ? "" : "s"} extracted and rendered in 9:16 portrait ${job.speaker_tracking_enabled ? "with speaker-aware framing" : "with a centered crop"}. Preview each clip and download the MP4 below.`
                          : "The transcript was processed, but no self-contained moment fit the configured duration range. Try a longer recording or adjust the clip limits."}
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {job.clip_count > 0 ? (
            <section className="rounded-2xl border border-line bg-white p-5 sm:p-6">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-500">
                  {job.kind === "segmenter" ? "Segments" : "Rendered clips"}
                </h2>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-400">
                  {job.kind === "segmenter"
                    ? `${job.segment_output_frame === "portrait_9_16" ? "9:16 portrait" : "original frame"} · by timestamp`
                    : `${job.clip_selection_model ?? "local model"} · heuristic score`}
                </span>
              </div>

              {clipsError ? (
                <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {clipsError}
                </p>
              ) : clips.length === 0 ? (
                <p className="text-xs text-ink-500">Loading clips…</p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {clips.map((clip, index) => (
                    <ClipCard
                      key={clip.id}
                      clip={clip}
                      index={index}
                      jobKind={(job.kind as "ai_clipper" | "segmenter") ?? "ai_clipper"}
                    />
                  ))}
                </div>
              )}

              <p className="mt-4 text-[11px] leading-5 text-ink-500">
                {job.kind === "segmenter"
                  ? "Each output is an H.264/AAC MP4 rendered from your requested timestamps. Joined groups combine multiple ranges into a single downloadable clip in the order provided."
                  : "Clips are H.264 video with AAC audio in 9:16 portrait at the configured resolution. Clip potential is a deterministic weighted score from hook, clarity, payoff, interest, and conciseness — not a virality prediction. Speaker tracking is optional per upload; when it is off, or when confidence is low or a face is missing, the clip uses an explicit centered/stable fallback and the card says so."}
              </p>
            </section>
          ) : null}

          {job.kind !== "segmenter" && job.has_transcript ? (
            <section className="rounded-2xl border border-line bg-white p-5 sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-500">
                  Transcript
                </h2>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-400">
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
              <p className="mt-3 text-[11px] leading-5 text-ink-400">
                Word-level timestamps are stored in the job work directory.
                Captions are not generated or burned into any video.
              </p>
            </section>
          ) : null}

          <section className="rounded-2xl border border-line bg-white p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-500">
                Media details
              </h2>
              <button
                type="button"
                onClick={() => void copyJobId()}
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-paper-100 px-2 py-1 font-mono text-[10px] text-ink-500 transition hover:border-line-strong hover:text-ink-700"
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
