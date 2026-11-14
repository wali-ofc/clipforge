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
  ArrowRightIcon,
  CheckIcon,
  FileVideoIcon,
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
  if (!health) {
    return false;
  }
  const ffmpeg = health.checks.ffmpeg;
  const ffprobe = health.checks.ffprobe;
  return ffmpeg?.available === true && ffprobe?.available === true;
}

function toolProblem(health: Health | null): string | null {
  if (!health) {
    return null;
  }
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
      if (requestError instanceof DOMException && requestError.name === "AbortError") {
        return;
      }
      setHealth(null);
      setHealthError(
        requestError instanceof Error
          ? requestError.message
          : "Could not reach the local backend.",
      );
    } finally {
      if (!signal?.aborted) {
        setCheckingHealth(false);
      }
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
      setError(
        `Unsupported file type. Choose a ${formats.join(", ")} file.`,
      );
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
    if (candidate) {
      validateAndSetFile(candidate);
    }
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (isUploading) {
      return;
    }
    const candidate = event.dataTransfer.files?.[0];
    if (candidate) {
      validateAndSetFile(candidate);
    }
  }

  function clearFile() {
    if (isUploading) {
      return;
    }
    setFile(null);
    setProgress(0);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !canSubmit) {
      return;
    }

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
      const message =
        uploadError instanceof ApiError
          ? uploadError.message
          : "The upload failed unexpectedly. Check the backend logs and try again.";
      setError(message);
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
    <div className="rounded-2xl border border-line bg-white p-4 shadow-[0_1px_2px_rgba(23,33,30,0.04),0_18px_48px_-28px_rgba(23,33,30,0.28)] sm:p-5">
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
            if (!isUploading) {
              setIsDragging(true);
            }
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setIsDragging(false);
          }}
          onDrop={handleDrop}
          className={[
            "group relative cursor-pointer overflow-hidden rounded-2xl border border-dashed px-5 py-10 text-center transition duration-200 sm:px-8 sm:py-12",
            isDragging
              ? "border-teal-500 bg-teal-50"
              : "border-line-strong bg-paper-50 hover:border-teal-300 hover:bg-paper-100",
            isUploading ? "cursor-default opacity-80" : "",
          ].join(" ")}
        >
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
            <div className="mx-auto flex max-w-md flex-col items-center">
              <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-teal-200 bg-teal-50 text-teal-600">
                <FileVideoIcon className="h-7 w-7" />
                <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-600">
                  <CheckIcon className="h-3 w-3" />
                </span>
              </div>
              <p className="mt-4 max-w-full truncate text-sm font-medium text-ink-900">
                {file.name}
              </p>
              <p className="mt-1 text-xs text-ink-500">
                {formatBytes(file.size)} · ready to upload
              </p>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  clearFile();
                }}
                disabled={isUploading}
                className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-line bg-paper-100 px-3 py-1.5 text-[11px] font-medium text-ink-500 transition hover:border-line-strong hover:text-ink-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <XIcon className="h-3 w-3" />
                Choose another
              </button>
            </div>
          ) : (
            <div className="mx-auto flex max-w-sm flex-col items-center">
              <div
                className={[
                  "flex h-14 w-14 items-center justify-center rounded-2xl border text-teal-600 transition duration-200",
                  isDragging
                    ? "scale-105 border-teal-500 bg-teal-100"
                    : "border-line bg-paper-100 group-hover:border-teal-300 group-hover:bg-teal-50",
                ].join(" ")}
              >
                <UploadCloudIcon className="h-7 w-7" />
              </div>
              <p className="mt-4 text-sm font-medium text-ink-900">
                {isDragging ? "Drop your video here" : "Drag a video here"}
              </p>
              <p className="mt-1.5 text-xs leading-5 text-ink-500">
                or <span className="text-teal-600">browse files</span> to get
                started
              </p>
              <p className="mt-4 text-[11px] text-ink-400">
                {formats.join(" · ")} · up to {formatBytes(maxUpload)}
              </p>
            </div>
          )}
        </div>

        <div className="mt-4 rounded-xl border border-line bg-paper-50 px-4 py-3">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={speakerTracking}
              onChange={(event) => setSpeakerTracking(event.target.checked)}
              disabled={isUploading}
              className="mt-0.5 h-4 w-4 rounded border-line-strong text-teal-600 focus:ring-teal-500 disabled:cursor-not-allowed"
            />
            <span className="min-w-0">
              <span className="block text-sm font-medium text-ink-900">
                Speaker / face tracking
              </span>
              <span className="mt-0.5 block text-[11px] leading-5 text-ink-500">
                Keep on for podcasts or talking-head videos to follow the active
                speaker. Turn off for gameplay, screen recordings, or other
                non-podcast videos to use a stable centered 9:16 crop.
              </span>
            </span>
          </label>
        </div>

        {healthError ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            <p>{healthError}</p>
            <button
              type="button"
              onClick={() => void loadHealth()}
              className="mt-2 font-medium text-red-800 underline decoration-red-300/40 underline-offset-4 hover:decoration-red-600"
            >
              Retry connection
            </button>
          </div>
        ) : null}

        {problem ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
          >
            {problem}
          </div>
        ) : null}

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        ) : null}

        {isUploading ? (
          <div className="mt-5" aria-live="polite">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-ink-500">
                <SpinnerIcon className="h-3.5 w-3.5 animate-spin text-teal-600" />
                {progress >= 100
                  ? "Upload complete — inspecting video"
                  : "Uploading video"}
              </span>
              <span className="font-mono text-[11px] text-ink-500">
                {progress}%
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-paper-200">
              <div
                className="h-full rounded-full bg-teal-500 transition-[width] duration-200"
                style={{ width: `${Math.max(progress, 2)}%` }}
              />
            </div>
          </div>
        ) : null}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-[19rem] text-[11px] leading-5 text-ink-400">
            {checkingHealth
              ? "Checking the local backend…"
              : "Your video is stored locally and inspected with ffprobe."}
          </p>
          <button
            type="submit"
            disabled={!canSubmit}
            className="group inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-teal-500 px-5 text-sm font-semibold text-white shadow-[0_8px_20px_-10px_rgba(15,107,98,0.45)] transition hover:bg-teal-600 active:translate-y-px disabled:cursor-not-allowed disabled:bg-paper-300 disabled:text-ink-500 disabled:shadow-none"
          >
            {isUploading ? (
              <>
                <SpinnerIcon className="h-4 w-4 animate-spin" />
                Uploading
              </>
            ) : (
              <>
                Upload &amp; inspect
                <ArrowRightIcon className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" />
              </>
            )}
          </button>
        </div>
      </form>

      <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-line bg-paper-50 px-3.5 py-3 text-[11px] leading-5 text-ink-500">
        <span
          aria-hidden="true"
          className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500"
        />
        <p>
          Uploads are checked with ffprobe, transcribed locally with Whisper,
          and rendered as 9:16 clips. Speaker tracking is optional per upload.
          One job runs at a time; you can cancel or delete it from the job page.
        </p>
      </div>
    </div>
  );
}
