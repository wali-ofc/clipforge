"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AlertIcon,
  ArrowRightIcon,
  CheckIcon,
  FileVideoIcon,
  RegMarks,
  ScissorsIcon,
  SpinnerIcon,
  TrashIcon,
  UploadCloudIcon,
  XIcon,
} from "@/components/icons";
import {
  ApiError,
  createSource,
  createSourceSegment,
  deleteSource,
  getHealth,
  getSourceJobs,
  listSources,
} from "@/lib/api";
import { formatBytes, formatDate, formatDuration, stateLabel } from "@/lib/format";
import type { Health, Job, Source } from "@/types/job";

const FALLBACK_MAX_UPLOAD = 5 * 1024 ** 3;
const FALLBACK_FORMATS = [".mp4", ".mov", ".mkv"];

function toolsReady(health: Health | null): boolean {
  return (
    health?.checks.ffmpeg?.available === true &&
    health?.checks.ffprobe?.available === true
  );
}

export function SegmenterWorkspace() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [sources, setSources] = useState<Source[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [health, setHealth] = useState<Health | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [spec, setSpec] = useState("");
  const [frame, setFrame] = useState<"original" | "portrait_9_16">("original");
  const [cutting, setCutting] = useState(false);
  const [cutError, setCutError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const refreshSources = useCallback(async () => {
    const data = await listSources();
    setSources(data);
    return data;
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    (async () => {
      try {
        const [data] = await Promise.all([
          listSources(controller.signal),
          getHealth(controller.signal).then(
            (value) => {
              if (!cancelled) setHealth(value);
            },
            () => {
              // The cut form still works if only the health probe failed.
            },
          ),
        ]);
        if (cancelled) return;
        setSources(data);
        const requested = new URLSearchParams(window.location.search).get("source");
        const initial =
          data.find((source) => source.id === requested)?.id ?? data[0]?.id ?? null;
        setActiveId(initial);
        setShowUpload(data.length === 0);
      } catch (error) {
        if (cancelled) return;
        setListError(
          error instanceof Error
            ? error.message
            : "Could not load source projects.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!activeId) {
      setJobs([]);
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    getSourceJobs(activeId, controller.signal)
      .then((data) => {
        if (!cancelled) setJobs(data);
      })
      .catch(() => {
        if (!cancelled) setJobs([]);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [activeId]);

  const activeSource = sources.find((source) => source.id === activeId) ?? null;
  const maxUpload = health?.limits.max_upload_bytes ?? FALLBACK_MAX_UPLOAD;
  const formats = health?.limits.allowed_formats ?? FALLBACK_FORMATS;

  function selectSource(id: string) {
    setActiveId(id);
    setShowUpload(false);
    setCutError(null);
    window.history.replaceState(null, "", `/segmenter?source=${id}`);
  }

  function validateAndSetFile(candidate: File) {
    setUploadError(null);
    setProgress(0);
    const extension = `.${candidate.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!formats.includes(extension)) {
      setFile(null);
      setUploadError(`Unsupported file type. Choose ${formats.join(", ")}.`);
      return;
    }
    if (candidate.size === 0) {
      setFile(null);
      setUploadError("That file is empty. Choose a video with content.");
      return;
    }
    if (candidate.size > maxUpload) {
      setFile(null);
      setUploadError(
        `That file is ${formatBytes(candidate.size)}. The limit is ${formatBytes(maxUpload)}.`,
      );
      return;
    }
    setFile(candidate);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const candidate = event.target.files?.[0];
    if (candidate) validateAndSetFile(candidate);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (isUploading) return;
    const candidate = event.dataTransfer.files?.[0];
    if (candidate) validateAndSetFile(candidate);
  }

  async function handleCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || isUploading || !toolsReady(health)) return;

    setIsUploading(true);
    setUploadError(null);
    setProgress(0);
    try {
      const source = await createSource(file, { onProgress: setProgress });
      const data = await refreshSources();
      setFile(null);
      setShowUpload(false);
      selectSource(source.id);
      if (!data.length) setActiveId(source.id);
    } catch (error) {
      setUploadError(
        error instanceof ApiError ? error.message : "The upload failed unexpectedly.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleCut(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeSource || cutting || !spec.trim()) return;

    setCutting(true);
    setCutError(null);
    try {
      const job = await createSourceSegment(activeSource.id, spec, frame);
      router.push(`/jobs/${job.id}`);
    } catch (error) {
      setCutError(
        error instanceof ApiError ? error.message : "Could not queue the cut job.",
      );
      setCutting(false);
    }
  }

  async function handleDeleteSource() {
    if (!activeSource || deleting) return;
    const confirmed = window.confirm(
      `Delete this project and every clip cut from it? This cannot be undone.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    setCutError(null);
    try {
      await deleteSource(activeSource.id);
      const data = await refreshSources();
      setActiveId(data[0]?.id ?? null);
      setShowUpload(data.length === 0);
      if (data.length) {
        window.history.replaceState(null, "", `/segmenter?source=${data[0].id}`);
      } else {
        window.history.replaceState(null, "", "/segmenter");
      }
    } catch (error) {
      setCutError(
        error instanceof ApiError ? error.message : "Could not delete the project.",
      );
    } finally {
      setDeleting(false);
    }
  }

  const acceptedTypes = [
    ...formats,
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
  ].join(",");

  if (loading) {
    return (
      <div className="sheet p-6" aria-hidden="true">
        <div className="h-6 w-40 animate-pulse bg-paper-200" />
        <div className="mt-5 h-32 animate-pulse border border-line bg-paper-200/70" />
      </div>
    );
  }

  if (listError) {
    return (
      <div className="notice notice-bad" role="alert">
        <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="text-[13px] font-semibold text-bad-700">
            Could not load projects
          </p>
          <p className="mt-1 text-xs text-bad-700">{listError}</p>
          <button
            type="button"
            className="btn btn-ghost mt-3"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Project switcher */}
      {sources.length > 0 ? (
        <div className="sheet-flat">
          <div className="sheet-head">
            <span className="meta">Projects on this machine</span>
            <span className="mono text-[10px] text-ink-400">
              {String(sources.length).padStart(2, "0")}
            </span>
          </div>
          <div className="flex flex-wrap gap-2 p-3">
            {sources.map((source) => (
              <button
                key={source.id}
                type="button"
                onClick={() => selectSource(source.id)}
                data-selected={source.id === activeId}
                className="option max-w-full sm:min-w-[180px]"
              >
                <FileVideoIcon className="mt-0.5 h-4 w-4 shrink-0 text-accent-500" />
                <span className="block min-w-0 text-left">
                  <span className="block truncate text-[12px] font-bold text-ink-900">
                    {source.original_filename}
                  </span>
                  <span className="mono mt-0.5 block text-[10px] text-ink-500">
                    {source.job_count} cut{source.job_count === 1 ? "" : "s"} ·{" "}
                    {formatDuration(source.duration_seconds)}
                  </span>
                </span>
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setShowUpload(true);
                setActiveId(null);
              }}
              className="btn btn-ghost min-h-[44px]"
            >
              + New project
            </button>
          </div>
        </div>
      ) : null}

      {showUpload || !activeSource ? (
        <form onSubmit={handleCreateSource} noValidate className="sheet relative">
          <RegMarks />
          <div className="sheet-head">
            <span className="meta">New project / Upload</span>
            <span className="badge badge-accent">One upload, many cuts</span>
          </div>
          <div className="sheet-body">
            <div
              role="button"
              tabIndex={isUploading ? -1 : 0}
              aria-label="Choose a video to add as a project"
              aria-disabled={isUploading}
              onClick={() => !isUploading && inputRef.current?.click()}
              onKeyDown={(event) => {
                if (!isUploading && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  inputRef.current?.click();
                }
              }}
              onDragOver={(event) => {
                event.preventDefault();
                if (!isUploading) setIsDragging(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                setIsDragging(false);
              }}
              onDrop={handleDrop}
              data-dragging={isDragging}
              data-disabled={isUploading}
              className="dropzone flex min-h-[180px] flex-col items-center justify-center px-6 py-8 text-center"
            >
              <RegMarks />
              <input
                ref={inputRef}
                type="file"
                accept={acceptedTypes}
                className="hidden"
                onChange={handleInputChange}
                disabled={isUploading}
              />
              {file ? (
                <div className="flex max-w-full flex-col items-center">
                  <div className="relative flex h-11 w-11 items-center justify-center border border-accent-200 bg-accent-50 text-accent-500">
                    <FileVideoIcon className="h-5 w-5" />
                    <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center border border-ok-200 bg-ok-50 text-ok-700">
                      <CheckIcon className="h-3 w-3" />
                    </span>
                  </div>
                  <p className="mt-3 max-w-full truncate text-[14px] font-bold text-ink-900">
                    {file.name}
                  </p>
                  <p className="mono mt-1 text-[10px] text-ink-500">
                    {formatBytes(file.size)} · ready
                  </p>
                  <button
                    type="button"
                    disabled={isUploading}
                    onClick={(event) => {
                      event.stopPropagation();
                      setFile(null);
                      setProgress(0);
                    }}
                    className="btn btn-quiet mt-2 border border-line-strong"
                  >
                    <XIcon className="h-3.5 w-3.5" /> Choose another
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="flex h-11 w-11 items-center justify-center border border-line-strong bg-paper-0 text-ink-600">
                    <UploadCloudIcon className="h-5 w-5" />
                  </div>
                  <p className="mt-3 text-[14px] font-bold text-ink-900">
                    {isDragging ? "Drop the video here" : "Drop a video here"}
                  </p>
                  <p className="mt-1 text-xs text-ink-500">
                    Upload once, then cut as many timestamp batches as you like
                  </p>
                  <button
                    type="button"
                    disabled={isUploading}
                    onClick={(event) => {
                      event.stopPropagation();
                      inputRef.current?.click();
                    }}
                    className="btn btn-ghost mt-3"
                  >
                    Choose file
                  </button>
                  <p className="mono mt-3 text-[10px] uppercase tracking-[0.1em] text-ink-400">
                    {formats.join("  ·  ")} · up to {formatBytes(maxUpload)}
                  </p>
                </div>
              )}
            </div>

            {!toolsReady(health) ? (
              <p className="notice notice-warn mt-4 text-xs text-warn-700">
                <AlertIcon className="h-4 w-4 shrink-0" />
                FFmpeg and ffprobe must be available before a project can be created.
              </p>
            ) : null}
            {uploadError ? (
              <p className="notice notice-bad mt-4 text-xs text-bad-700" role="alert">
                <AlertIcon className="h-4 w-4 shrink-0" />
                {uploadError}
              </p>
            ) : null}

            {isUploading ? (
              <div className="mt-5" aria-live="polite">
                <div className="mb-2 flex justify-between">
                  <span className="text-xs text-ink-600">Uploading video</span>
                  <span className="timecode">{progress}%</span>
                </div>
                <div className="ruler">
                  <div className="ruler-fill" style={{ width: `${Math.max(progress, 2)}%` }} />
                  <div className="ruler-head" style={{ left: `${Math.max(progress, 2)}%` }} />
                </div>
              </div>
            ) : null}

            <div className="mt-6 flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="note text-[11px]">
                The file is probed once and stored locally. Each cut job reads the
                same source.
              </p>
              <button
                type="submit"
                disabled={!file || isUploading || !toolsReady(health)}
                className="btn btn-primary w-full sm:w-auto"
              >
                {isUploading ? (
                  <SpinnerIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Create project
                    <ArrowRightIcon className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <>
          <section className="sheet relative">
            <RegMarks />
            <div className="sheet-head">
              <div className="min-w-0">
                <p className="meta">Active project</p>
                <h2 className="title mt-1 truncate text-[16px]">
                  {activeSource.original_filename}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => void handleDeleteSource()}
                disabled={deleting}
                className="btn btn-danger"
              >
                {deleting ? (
                  <SpinnerIcon className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <TrashIcon className="h-3.5 w-3.5" />
                )}
                Delete project
              </button>
            </div>
            <div className="sheet-body">
              <dl>
                <div className="spec">
                  <dt className="spec-label">Duration</dt>
                  <dd className="data">{formatDuration(activeSource.duration_seconds)}</dd>
                </div>
                <div className="spec">
                  <dt className="spec-label">Resolution</dt>
                  <dd className="data">
                    {activeSource.width && activeSource.height
                      ? `${activeSource.width} × ${activeSource.height}`
                      : "—"}
                  </dd>
                </div>
                <div className="spec">
                  <dt className="spec-label">Cut jobs</dt>
                  <dd className="data">{String(activeSource.job_count).padStart(2, "0")}</dd>
                </div>
              </dl>
              <p className="mono mt-2 text-[10px] text-ink-400">
                {formatBytes(activeSource.size_bytes)} · added{" "}
                {formatDate(activeSource.created_at)}
              </p>
            </div>
          </section>

          <form onSubmit={handleCut} noValidate className="sheet relative">
            <RegMarks />
            <div className="sheet-head">
              <span className="meta">New cut / timestamps</span>
              <span className="badge badge-accent">
                <ScissorsIcon className="h-3 w-3" />
                Reuses the source
              </span>
            </div>
            <div className="sheet-body space-y-5">
              <div>
                <div className="mb-2 flex items-baseline justify-between gap-3">
                  <label htmlFor="segment-spec" className="text-[13px] font-bold text-ink-900">
                    Timestamps
                  </label>
                  <span className="mono text-[10px] uppercase tracking-[0.1em] text-ink-400">
                    MM:SS or HH:MM:SS
                  </span>
                </div>
                <textarea
                  id="segment-spec"
                  value={spec}
                  onChange={(event) => setSpec(event.target.value)}
                  disabled={cutting}
                  rows={5}
                  spellCheck={false}
                  placeholder={"1:23 - 2:23\n5:23 - 6:32\n\nOr join ranges into one clip:\n1:23 - 2:23, 5:23 - 6:32"}
                  className="field font-mono text-[12px] leading-6"
                />
                <div className="ruler mt-2 h-1.5" aria-hidden="true" />
                <p className="mono mt-2 text-[10px] leading-5 text-ink-500">
                  New line = separate clip · commas in a line = one joined clip
                </p>
              </div>

              <fieldset>
                <legend className="text-[13px] font-bold text-ink-900">Output frame</legend>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <label className="option" data-selected={frame === "original"}>
                    <input
                      type="radio"
                      name="segment-frame"
                      value="original"
                      checked={frame === "original"}
                      onChange={() => setFrame("original")}
                      disabled={cutting}
                      className="check mt-0.5"
                    />
                    <span>
                      <span className="block text-[13px] font-bold text-ink-900">
                        Keep original
                      </span>
                      <span className="mt-0.5 block text-[11px] text-ink-500">
                        Preserve source framing and resolution.
                      </span>
                    </span>
                  </label>
                  <label className="option" data-selected={frame === "portrait_9_16"}>
                    <input
                      type="radio"
                      name="segment-frame"
                      value="portrait_9_16"
                      checked={frame === "portrait_9_16"}
                      onChange={() => setFrame("portrait_9_16")}
                      disabled={cutting}
                      className="check mt-0.5"
                    />
                    <span>
                      <span className="block text-[13px] font-bold text-ink-900">
                        9:16 portrait
                      </span>
                      <span className="mt-0.5 block text-[11px] text-ink-500">
                        Centre-crop into a vertical frame.
                      </span>
                    </span>
                  </label>
                </div>
              </fieldset>

              {cutError ? (
                <p className="notice notice-bad text-xs text-bad-700" role="alert">
                  <AlertIcon className="h-4 w-4 shrink-0" />
                  {cutError}
                </p>
              ) : null}

              <div className="flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
                <p className="note text-[11px]">
                  Each cut becomes its own job with downloadable MP4s. Come back
                  here to cut more from the same video.
                </p>
                <button
                  type="submit"
                  disabled={!spec.trim() || cutting}
                  className="btn btn-primary w-full sm:w-auto"
                >
                  {cutting ? (
                    <SpinnerIcon className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Cut clips
                      <ArrowRightIcon className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>

          <section className="sheet">
            <div className="sheet-head">
              <h3 className="title">Cut history</h3>
              <span className="mono text-[10px] uppercase tracking-[0.12em] text-ink-400">
                {String(jobs.length).padStart(2, "0")} jobs
              </span>
            </div>
            <div className="sheet-body">
              {jobs.length === 0 ? (
                <p className="mono text-[11px] uppercase tracking-[0.12em] text-ink-400">
                  No cuts yet — enter timestamps above to make the first one.
                </p>
              ) : (
                <ul>
                  {jobs.map((job) => (
                    <li key={job.id} className="border-b border-line last:border-b-0">
                      <Link
                        href={`/jobs/${job.id}`}
                        className="group flex flex-wrap items-center justify-between gap-3 py-3 transition hover:text-accent-700"
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-mono text-[11px] text-ink-800">
                            {job.segment_spec?.replace(/\n/g, " · ") ?? "—"}
                          </span>
                          <span className="mono mt-1 block text-[10px] text-ink-400">
                            {formatDate(job.created_at)} · {job.clip_count} clip
                            {job.clip_count === 1 ? "" : "s"}
                          </span>
                        </span>
                        <span className="flex items-center gap-3">
                          <span
                            className={
                              job.state === "completed"
                                ? "badge badge-ok"
                                : job.state === "failed"
                                  ? "badge badge-bad"
                                  : "badge badge-accent"
                            }
                          >
                            {stateLabel(job.state)}
                          </span>
                          <ArrowRightIcon className="h-4 w-4 text-ink-400 transition group-hover:translate-x-0.5 group-hover:text-accent-500" />
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
