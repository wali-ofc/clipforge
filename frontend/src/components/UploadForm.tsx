"use client";

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
  SpinnerIcon,
  UploadCloudIcon,
  XIcon,
} from "@/components/icons";
import { ApiError, getHealth, uploadVideo } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import type { Health } from "@/types/job";

const FALLBACK_MAX_UPLOAD = 5 * 1024 ** 3;
const FALLBACK_FORMATS = [".mp4", ".mov", ".mkv"];

function mediaToolsReady(health: Health | null): boolean {
  if (!health) return false;
  return (
    health.checks.ffmpeg?.available === true &&
    health.checks.ffprobe?.available === true
  );
}

function toolProblem(health: Health | null): string | null {
  if (!health) return null;
  for (const name of ["ffmpeg", "ffprobe"] as const) {
    const check = health.checks[name];
    if (check && !check.available) {
      return check.detail ?? `${name} is not available on this machine.`;
    }
  }
  return null;
}

export function UploadForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [speakerTracking, setSpeakerTracking] = useState(true);

  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [checkingHealth, setCheckingHealth] = useState(true);

  const loadHealth = useCallback(async (signal?: AbortSignal) => {
    setCheckingHealth(true);
    try {
      const result = await getHealth(signal);
      setHealth(result);
      setHealthError(null);
    } catch (requestError) {
      if (
        requestError instanceof DOMException &&
        requestError.name === "AbortError"
      ) {
        return;
      }
      setHealth(null);
      setHealthError(
        requestError instanceof Error
          ? requestError.message
          : "Could not reach the local backend.",
      );
    } finally {
      if (!signal?.aborted) setCheckingHealth(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadHealth(controller.signal);
    return () => controller.abort();
  }, [loadHealth]);

  const maxUpload = health?.limits.max_upload_bytes ?? FALLBACK_MAX_UPLOAD;
  const formats = health?.limits.allowed_formats ?? FALLBACK_FORMATS;
  const problem = toolProblem(health);
  const canSubmit =
    Boolean(file) &&
    !isUploading &&
    !checkingHealth &&
    !healthError &&
    mediaToolsReady(health);

  function validateAndSetFile(candidate: File) {
    setError(null);
    setProgress(0);
    const extension = `.${candidate.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!formats.includes(extension)) {
      setFile(null);
      setError(`Unsupported file type. Choose a ${formats.join(", ")} file.`);
      return;
    }
    if (candidate.size === 0) {
      setFile(null);
      setError("That file is empty. Choose a video with content.");
      return;
    }
    if (candidate.size > maxUpload) {
      setFile(null);
      setError(
        `That file is ${formatBytes(candidate.size)}. The current limit is ${formatBytes(maxUpload)}.`,
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

  function clearFile() {
    if (isUploading) return;
    setFile(null);
    setProgress(0);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !canSubmit) return;

    setIsUploading(true);
    setProgress(0);
    setError(null);

    try {
      const job = await uploadVideo(file, {
        onProgress: setProgress,
        speakerTracking,
      });
      router.push(`/jobs/${job.id}`);
    } catch (uploadError) {
      setError(
        uploadError instanceof ApiError
          ? uploadError.message
          : "The upload failed unexpectedly. Check the backend logs and try again.",
      );
      setIsUploading(false);
    }
  }

  const acceptedTypes = [
    ...formats,
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
  ].join(",");

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div
        role="button"
        tabIndex={isUploading ? -1 : 0}
        aria-label="Choose a video to upload"
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
        className="dropzone flex min-h-[220px] flex-col items-center justify-center px-6 py-9 text-center"
      >
        <RegMarks />
        <input
          ref={inputRef}
          id="video-file"
          type="file"
          accept={acceptedTypes}
          className="hidden"
          onChange={handleInputChange}
          disabled={isUploading}
        />

        {file ? (
          <div className="flex max-w-full flex-col items-center">
            <div className="relative flex h-12 w-12 items-center justify-center border border-accent-200 bg-accent-50 text-accent-500">
              <FileVideoIcon className="h-6 w-6" />
              <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center border border-ok-200 bg-ok-50 text-ok-700">
                <CheckIcon className="h-3 w-3" />
              </span>
            </div>
            <p className="mt-4 max-w-full truncate text-[15px] font-bold tracking-[-0.02em] text-ink-900">
              {file.name}
            </p>
            <p className="mono mt-1.5 text-[11px] text-ink-500">
              {formatBytes(file.size)} · ready to upload
            </p>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                clearFile();
              }}
              disabled={isUploading}
              className="btn btn-quiet mt-3 border border-line-strong"
            >
              <XIcon className="h-3.5 w-3.5" />
              Choose another
            </button>
          </div>
        ) : (
          <div className="flex max-w-sm flex-col items-center">
            <div
              className={[
                "flex h-12 w-12 items-center justify-center border transition-colors duration-200",
                isDragging
                  ? "border-accent-500 bg-accent-50 text-accent-500"
                  : "border-line-strong bg-paper-0 text-ink-600",
              ].join(" ")}
            >
              <UploadCloudIcon className="h-6 w-6" />
            </div>
            <p className="mt-4 text-[15px] font-bold tracking-[-0.02em] text-ink-900">
              {isDragging ? "Drop the video here" : "Drop a video here"}
            </p>
            <p className="mt-1 text-xs text-ink-500">
              or choose a file from this machine
            </p>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                if (!isUploading) inputRef.current?.click();
              }}
              disabled={isUploading}
              className="btn btn-ghost mt-4"
            >
              <UploadCloudIcon className="h-4 w-4" />
              Choose file
            </button>
            <p className="mono mt-4 text-[10px] uppercase tracking-[0.1em] text-ink-400">
              {formats.join("  ·  ")}  ·  up to {formatBytes(maxUpload)}
            </p>
          </div>
        )}
      </div>

      <label className="mt-5 flex cursor-pointer items-start gap-3 border-t border-line pt-4">
        <input
          type="checkbox"
          checked={speakerTracking}
          onChange={(event) => setSpeakerTracking(event.target.checked)}
          disabled={isUploading}
          className="check mt-0.5"
        />
        <span className="block min-w-0">
          <span className="block text-[13px] font-bold tracking-[-0.02em] text-ink-900">
            Speaker / face tracking
          </span>
          <span className="mt-1 block text-xs leading-5 text-ink-500">
            Follows the active speaker for talking-head videos. Turn off for
            gameplay or screen recordings to use a stable centred 9:16 crop.
          </span>
        </span>
      </label>

      {healthError ? (
        <div role="alert" className="notice notice-bad mt-4">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-bad-700">
              Backend unreachable
            </p>
            <p className="mt-0.5 text-xs leading-5 text-bad-700">{healthError}</p>
            <button
              type="button"
              onClick={() => void loadHealth()}
              className="btn btn-quiet mt-1 text-bad-700 underline underline-offset-4"
            >
              Retry connection
            </button>
          </div>
        </div>
      ) : null}

      {problem ? (
        <div role="alert" className="notice notice-warn mt-4">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="text-xs leading-5 text-warn-700">{problem}</p>
        </div>
      ) : null}

      {error ? (
        <div role="alert" className="notice notice-bad mt-4">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="text-xs leading-5 text-bad-700">{error}</p>
        </div>
      ) : null}

      {isUploading ? (
        <div className="mt-5" aria-live="polite">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-xs text-ink-600">
              <SpinnerIcon className="h-3.5 w-3.5 animate-spin text-accent-500" />
              {progress >= 100
                ? "Upload complete — inspecting video"
                : "Uploading video"}
            </span>
            <span className="timecode">{progress}%</span>
          </div>
          <div className="ruler">
            <div
              className="ruler-fill"
              style={{ width: `${Math.max(progress, 2)}%` }}
            />
            <div
              className="ruler-head"
              style={{ left: `${Math.max(progress, 2)}%` }}
            />
          </div>
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="note max-w-[19rem] text-[11px]">
          {checkingHealth
            ? "Checking the local backend…"
            : "Stored locally and inspected with ffprobe before processing."}
        </p>
        <button
          type="submit"
          disabled={!canSubmit}
          className="btn btn-primary w-full sm:w-auto"
        >
          {isUploading ? (
            <>
              <SpinnerIcon className="h-4 w-4 animate-spin" />
              Uploading
            </>
          ) : (
            <>
              Upload &amp; inspect
              <ArrowRightIcon className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
