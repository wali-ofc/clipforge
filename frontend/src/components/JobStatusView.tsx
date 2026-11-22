"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AlertIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckIcon,
  CopyIcon,
  DownloadIcon,
  FileVideoIcon,
  RegMarks,
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
  if (state === "completed") return "badge badge-ok";
  if (state === "failed") return "badge badge-bad";
  if (state === "cancelled") return "badge";
  return "badge badge-accent";
}

function StatusIcon({ state }: { state: JobState }) {
  if (state === "completed") return <CheckIcon className="h-5 w-5" />;
  if (state === "failed") return <AlertIcon className="h-5 w-5" />;
  if (state === "cancelled") return <XIcon className="h-5 w-5" />;
  return <SpinnerIcon className="h-5 w-5 animate-spin" />;
}

function statusIconClasses(state: JobState): string {
  if (state === "completed") return "border-ok-200 bg-ok-50 text-ok-700";
  if (state === "failed") return "border-bad-200 bg-bad-50 text-bad-700";
  if (state === "cancelled") return "border-line-strong bg-paper-100 text-ink-600";
  return "border-accent-200 bg-accent-50 text-accent-500";
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
    <div className="spec">
      <dt className="spec-label">{label}</dt>
      <dd className={mono ? "data break-all" : "text-[13px] text-ink-800"}>
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
      return "Centred crop · tracking off";
    case "unavailable":
      return "Centre crop · unavailable";
    case "failed":
      return "Centre crop · tracking failed";
    case "no_faces":
      return "No face · centre crop";
    case "no_frames":
      return "No frames · centre crop";
    case "pending":
      return "Tracking pending";
    default:
      return clip.speaker_tracking_status;
  }
}

function trackingTone(clip: Clip): string {
  if (clip.speaker_tracking_status === "tracked") return "badge badge-ok";
  if (clip.speaker_tracking_status === "fallback") return "badge badge-warn";
  if (clip.speaker_tracking_status === "disabled") return "badge";
  return "badge";
}

function fallbackNote(clip: Clip): string | null {
  switch (clip.speaker_tracking_status) {
    case "fallback":
      return "Speaker tracking used a stable fallback face, not active-speaker detection.";
    case "disabled":
      return "Speaker tracking was turned off for this job; this clip uses a stable centred 9:16 crop.";
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
  const score =
    !isSegmenter && clip.score == null ? null : Math.round(clip.score ?? 0);
  const confidence =
    !isSegmenter && clip.speaker_tracking_confidence == null
      ? null
      : Math.round((clip.speaker_tracking_confidence ?? 0) * 100);
  const cropSamples = clip.crop_plan?.samples?.length ?? 0;
  const isRendered =
    clip.render_status === "completed" && Boolean(clip.output_filename);
  const isRendering = clip.render_status === "rendering";
  const isFailed = clip.render_status === "failed";
  const note = isSegmenter ? null : fallbackNote(clip);
  const scoreTone =
    score == null
      ? "badge"
      : score >= 75
        ? "badge badge-ok"
        : score >= 55
          ? "badge badge-accent"
          : "badge badge-warn";
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
    <article className="sheet-flat flex flex-col p-4">
      <div
        className={["preview-frame mx-auto w-full max-w-[248px]", aspectClass].join(" ")}
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
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center">
            <SpinnerIcon className="h-6 w-6 animate-spin text-accent-300" />
            <p className="mono text-[10px] uppercase tracking-[0.14em] text-paper-0">
              Rendering MP4…
            </p>
          </div>
        ) : isFailed ? (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center text-bad-100">
            <AlertIcon className="h-6 w-6" />
            <p className="text-[11px] font-semibold">Rendering failed</p>
          </div>
        ) : (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center text-paper-300">
            <FileVideoIcon className="h-6 w-6" />
            <p className="mono text-[10px] uppercase tracking-[0.14em]">
              Render pending
            </p>
          </div>
        )}
        <RegMarks />
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="tally text-ink-500">
          {isSegmenter ? "Segment" : "Clip"} {String(index + 1).padStart(2, "0")}
        </span>
        {!isSegmenter ? (
          <span
            className={scoreTone}
            title="Heuristic clip potential, not a virality prediction"
          >
            Score {score ?? "—"}/100
          </span>
        ) : (
          <span className="badge badge-accent">{joined ? "Joined" : "Cut"}</span>
        )}
      </div>

      <h3 className="title mt-2 text-[15px]">{clip.title}</h3>
      {!isSegmenter && clip.hook ? (
        <p className="mt-2 text-[13px] leading-5 text-ink-700">{clip.hook}</p>
      ) : null}
      {clip.reason ? (
        <p className="mt-1.5 text-xs leading-5 text-ink-500">{clip.reason}</p>
      ) : null}

      {isSegmenter && joined && parts && parts.length > 1 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {parts.map((p, i) => (
            <span key={i} className="badge">
              {formatDuration(p.start)}–{formatDuration(p.end)}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line pt-3">
        <span className="timecode">
          {formatDuration(clip.start_seconds)} – {formatDuration(clip.end_seconds)}
        </span>
        <span className="data text-ink-400" aria-hidden="true">/</span>
        <span className="timecode">{formatDuration(clip.duration_seconds)}</span>
        {clip.width && clip.height ? (
          <>
            <span className="data text-ink-400" aria-hidden="true">/</span>
            <span className="data">
              {clip.width}×{clip.height}
            </span>
          </>
        ) : null}
      </div>
      <div className="ruler mt-2 h-1.5" aria-hidden="true" />

      {!isSegmenter ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={trackingTone(clip)}>{trackingLabel(clip)}</span>
          {confidence != null ? (
            <span className="data text-ink-500">{confidence}% confidence</span>
          ) : null}
          {cropSamples > 0 ? (
            <span className="data text-ink-500">{cropSamples} crop samples</span>
          ) : null}
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="badge">
            {outputFrame === "portrait_9_16" ? "9:16 portrait" : "Original frame"}
          </span>
          <span className="data text-ink-500">
            {joined ? `${parts?.length ?? 0} parts joined` : "Single cut"}
          </span>
        </div>
      )}

      {note ? (
        <p className="notice notice-warn mt-3 text-[11px] leading-4 text-warn-700">
          <AlertIcon className="mt-px h-3.5 w-3.5 shrink-0" />
          <span>{note}</span>
        </p>
      ) : null}

      {isFailed && clip.error ? (
        <p className="mt-2 text-[11px] leading-4 text-bad-700">
          Error: {clip.error}
        </p>
      ) : null}

      {isRendered ? (
        <a
          href={getClipFileUrl(clip.id, true)}
          download
          className="btn btn-primary mt-auto w-full border-t-0 pt-4"
        >
          <DownloadIcon className="h-4 w-4" />
          Download MP4
        </a>
      ) : null}
    </article>
  );
}

function Skeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="h-28 animate-pulse border border-line bg-paper-200/70" />
      <div className="h-20 animate-pulse border border-line bg-paper-200/70" />
      <div className="h-56 animate-pulse border border-line bg-paper-200/70" />
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
    <div className="notice notice-bad p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-bad-200 bg-bad-50 text-bad-700">
          <AlertIcon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="title text-bad-700">Could not load this job</h2>
          <p className="mt-1.5 text-sm leading-6 text-bad-700">{message}</p>
          <button
            type="button"
            onClick={onRetry}
            className="btn btn-ghost mt-4"
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
          if (cancelled) return;
          setClips(data);
          setClipsError(null);
        })
        .catch((requestError) => {
          if (cancelled) return;
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

    let interval: ReturnType<typeof setInterval> | undefined;
    if (!isTerminalState(job.state)) {
      interval = setInterval(loadClips, 2500);
    }

    return () => {
      cancelled = true;
      controller.abort();
      if (interval) clearInterval(interval);
    };
  }, [job?.clip_count, job?.state, jobId, retryNonce]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const data = await getJob(jobId);
        if (cancelled) return;
        setJob(data);
        setError(null);
        setNotFound(false);
        if (!isTerminalState(data.state)) {
          timer = setTimeout(tick, 2000);
        }
      } catch (requestError) {
        if (cancelled) return;
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
      if (timer) clearTimeout(timer);
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
    if (!job || deleting) return;
    const active = !isTerminalState(job.state);
    const confirmed = window.confirm(
      active
        ? "Cancel this job and delete its upload, work files, and rendered clips? This cannot be undone."
        : "Delete this job and all of its media? This cannot be undone.",
    );
    if (!confirmed) return;

    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteJob(job.id);
      router.push("/");
    } catch (requestError) {
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
        <Link href="/" className="btn btn-quiet">
          <ArrowLeftIcon className="h-4 w-4" /> Upload another video
        </Link>
        <div className="sheet p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center border border-line-strong bg-paper-50 text-ink-500">
            <FileVideoIcon className="h-6 w-6" />
          </div>
          <h1 className="title mt-4 text-lg">Job not found</h1>
          <p className="note mx-auto mt-2 text-center">
            This job ID does not exist in the local database. It may have been
            deleted, or the link may be incorrect.
          </p>
          <Link href="/" className="btn btn-primary mt-6">
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
          href={
            job?.source_id
              ? `/segmenter?source=${job.source_id}`
              : job?.kind === "segmenter"
                ? "/segmenter"
                : "/"
          }
          className="btn btn-quiet"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          {job?.source_id
            ? "Back to project"
            : job?.kind === "segmenter"
              ? "Back to Segmenter"
              : "Back to AI Clipper"}
        </Link>
        <span className="mono text-[10px] uppercase tracking-[0.14em] text-ink-400">
          Job sheet / {jobId.slice(0, 8)}
        </span>
      </div>

      {!job && !error ? <Skeleton /> : null}
      {!job && error ? <ErrorState message={error} onRetry={retryNow} /> : null}

      {job ? (
        <>
          <section className="sheet relative">
            <RegMarks />
            <div className="sheet-head">
              <div className="min-w-0">
                <p className="meta">Source / {job.kind === "segmenter" ? "Segmenter" : "AI Clipper"}</p>
                <h1 className="title mt-1 truncate text-[17px]">
                  {job.original_filename}
                </h1>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <span className={badgeClasses(job.state)}>
                  {!isTerminalState(job.state) ? (
                    <span className="status-dot h-1.5 w-1.5 rounded-full bg-current" />
                  ) : null}
                  {stateLabel(job.state)}
                </span>
                <button
                  type="button"
                  onClick={() => void removeJob()}
                  disabled={deleting}
                  className="btn btn-danger"
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

            <div className="sheet-body">
              <div className="flex items-start gap-3">
                <div
                  className={[
                    "flex h-10 w-10 shrink-0 items-center justify-center border",
                    statusIconClasses(job.state),
                  ].join(" ")}
                >
                  <StatusIcon state={job.state} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-4">
                    <h2 className="text-[15px] font-bold tracking-[-0.02em] text-ink-900" aria-live="polite">
                      {stateLabel(job.state)}
                    </h2>
                    <span className="timecode text-[13px]">{job.progress}%</span>
                  </div>
                  <p className="mt-1 text-[13px] leading-6 text-ink-600">
                    {job.stage_message}
                  </p>
                </div>
              </div>

              <div className="ruler mt-4 h-2.5">
                <div
                  className="ruler-fill"
                  data-bad={job.state === "failed"}
                  style={{ width: `${job.progress > 0 ? job.progress : 2}%` }}
                />
                <div
                  className="ruler-head"
                  style={{ left: `${job.progress > 0 ? job.progress : 2}%` }}
                />
              </div>

              {!isTerminalState(job.state) ? (
                <p className="mono mt-3 text-[10px] uppercase leading-5 tracking-[0.1em] text-ink-400">
                  Auto-refreshing · jobs persist if you close this tab ·
                  cancelling removes the upload and rendered files
                </p>
              ) : null}

              {deleteError ? (
                <p role="alert" className="notice notice-bad mt-3 text-[11px] text-bad-700">
                  <AlertIcon className="mt-px h-3.5 w-3.5 shrink-0" />
                  <span>{deleteError}</span>
                </p>
              ) : null}
            </div>
          </section>

          {error ? (
            <div className="notice notice-warn" role="alert">
              <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs leading-5 text-warn-700">
                  Connection lost. Retrying automatically. {error}
                </p>
              </div>
              <button
                type="button"
                onClick={retryNow}
                className="btn btn-quiet text-warn-700 underline underline-offset-4"
              >
                Retry now
              </button>
            </div>
          ) : null}

          {job.state === "failed" ? (
            <section className="notice notice-bad">
              <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <h2 className="title text-bad-700">Processing failed</h2>
                <p className="mt-1 text-sm leading-6 text-bad-700">
                  {job.error ?? "The pipeline reported an unknown error."}
                </p>
              </div>
            </section>
          ) : null}

          {job.state === "cancelled" ? (
            <section className="notice">
              <XIcon className="mt-0.5 h-4 w-4 shrink-0 text-ink-500" />
              <div>
                <h2 className="title">Job cancelled</h2>
                <p className="note mt-1">
                  Processing stopped before completion and temporary work files
                  were cleaned up. Delete the job to remove its upload and any{" "}
                  {job.kind === "segmenter" ? "segments" : "clips"} already rendered.
                </p>
              </div>
            </section>
          ) : null}

          {job.state === "completed" ? (
            <section className="notice notice-ok">
              <CheckIcon className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <h2 className="title text-ok-700">
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
                <p className="mt-1 text-[13px] leading-6 text-ok-700">
                  {job.kind === "segmenter"
                    ? job.clip_count > 0
                      ? `${job.clip_count} segment${job.clip_count === 1 ? "" : "s"} rendered from your timestamps (${job.segment_output_frame === "portrait_9_16" ? "9:16 portrait" : "original frame"}). Preview and download each clip below.`
                      : "Segmenting finished, but no downloadable outputs were produced. Check your timestamps and try again."
                    : job.has_speech === false
                      ? "The audio was processed but produced no usable speech segments. No clips were selected; crop planning and rendering were skipped."
                      : job.clip_count > 0
                        ? `${job.clip_count} short clip${job.clip_count === 1 ? "" : "s"} extracted in 9:16 portrait ${job.speaker_tracking_enabled ? "with speaker-aware framing" : "with a centred crop"}. Preview and download each MP4 below.`
                        : "The transcript was processed, but no self-contained moment fit the configured duration range. Try a longer recording or adjust the clip limits."}
                </p>
              </div>
            </section>
          ) : null}

          {job.clip_count > 0 ? (
            <section className="sheet">
              <div className="section-head mx-5 mt-5">
                <h2 className="title">
                  {job.kind === "segmenter" ? "Segments" : "Rendered clips"}
                </h2>
                <span className="mono text-[10px] uppercase tracking-[0.12em] text-ink-400">
                  {job.kind === "segmenter"
                    ? `${job.segment_output_frame === "portrait_9_16" ? "9:16 portrait" : "original frame"} · by timestamp`
                    : `${job.clip_selection_model ?? "local model"} · heuristic score`}
                </span>
              </div>
              <div className="sheet-body">
                {clipsError ? (
                  <p className="notice notice-warn text-xs text-warn-700">
                    {clipsError}
                  </p>
                ) : clips.length === 0 ? (
                  <p className="mono text-[11px] uppercase tracking-[0.12em] text-ink-400">
                    Loading clips…
                  </p>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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

                <p className="note mt-5 border-t border-line pt-4 text-[11px]">
                  {job.kind === "segmenter"
                    ? "Each output is an H.264/AAC MP4 rendered from your requested timestamps. Joined groups combine multiple ranges in the order provided."
                    : "Clips are H.264/AAC MP4s in 9:16 portrait. Clip potential is a deterministic weighted score — a ranking aid, not a virality prediction. When tracking is off, low-confidence, or no face is found, the clip uses an explicit centred/stable fallback and the card says so."}
                </p>
              </div>
            </section>
          ) : null}

          {job.kind !== "segmenter" && job.has_transcript ? (
            <section className="sheet">
              <div className="sheet-head">
                <h2 className="title">Transcript</h2>
                <span className="mono text-[10px] uppercase tracking-[0.12em] text-ink-400">
                  internal data
                </span>
              </div>
              <div className="sheet-body">
                <div className="sm:grid sm:grid-cols-3 sm:gap-x-8">
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
                </div>
                <p className="note mt-3 text-[11px]">
                  Word-level timestamps are stored in the job work directory.
                  Captions are not generated or burned into any video.
                </p>
              </div>
            </section>
          ) : null}

          <section className="sheet">
            <div className="sheet-head">
              <h2 className="title">Media details</h2>
              <button
                type="button"
                onClick={() => void copyJobId()}
                className="btn btn-quiet border border-line"
                title="Copy job ID"
              >
                <CopyIcon className="h-3.5 w-3.5" />
                {copied ? "copied" : "job id"}
              </button>
            </div>
            <div className="sheet-body">
              <div className="sm:grid sm:grid-cols-3 sm:gap-x-8">
                <Detail label="Duration" value={formatDuration(job.duration_seconds)} />
                <Detail
                  label="Resolution"
                  value={formatResolution(job.width, job.height)}
                />
                <Detail label="Frame rate" value={formatFrameRate(job.frame_rate)} />
                <Detail label="Video" value={job.video_codec?.toUpperCase() ?? "—"} />
                <Detail
                  label="Audio"
                  value={
                    job.has_audio
                      ? (job.audio_codec?.toUpperCase() ?? "Present")
                      : "No audio stream"
                  }
                />
                <Detail label="Rotation" value={job.rotation ? `${job.rotation}°` : "None"} />
              </div>
              <div className="sm:grid sm:grid-cols-2 sm:gap-x-8">
                <Detail label="Container" value={job.container_format ?? "—"} mono />
                <Detail label="Job ID" value={job.id} mono />
              </div>
              <p className="mono mt-2 text-[10px] text-ink-400">
                {formatBytes(job.size_bytes)} · uploaded {formatDate(job.created_at)}
              </p>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
