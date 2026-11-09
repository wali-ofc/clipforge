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
      const job = await uploadVideo(file, setProgress);
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
    <div className="relative rounded-3xl border border-white/10 bg-surface-900/75 p-4 shadow-[0_24px_80px_-32px_rgba(0,0,0,0.9)] backdrop-blur-xl sm:p-5">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-10 -top-px h-px bg-gradient-to-r from-transparent via-forge-400/60 to-transparent"
      />

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
              ? "border-forge-400 bg-forge-500/[0.07]"
              : "border-white/15 bg-white/[0.018] hover:border-forge-500/45 hover:bg-white/[0.03]",
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
              <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-forge-500/25 bg-forge-500/10 text-forge-300">
                <FileVideoIcon className="h-7 w-7" />
                <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border border-emerald-400/30 bg-emerald-400/15 text-emerald-300">
                  <CheckIcon className="h-3 w-3" />
                </span>
              </div>
              <p className="mt-4 max-w-full truncate text-sm font-medium text-zinc-100">
                {file.name}
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                {formatBytes(file.size)} · ready to upload
              </p>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  clearFile();
                }}
                disabled={isUploading}
                className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] font-medium text-zinc-400 transition hover:border-white/20 hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <XIcon className="h-3 w-3" />
                Choose another
              </button>
            </div>
          ) : (
            <div className="mx-auto flex max-w-sm flex-col items-center">
              <div
                className={[
                  "flex h-14 w-14 items-center justify-center rounded-2xl border text-forge-300 transition duration-200",
                  isDragging
                    ? "scale-105 border-forge-400/50 bg-forge-500/15"
                    : "border-white/10 bg-white/[0.035] group-hover:border-forge-500/30 group-hover:bg-forge-500/10",
                ].join(" ")}
              >
                <UploadCloudIcon className="h-7 w-7" />
              </div>
              <p className="mt-4 text-sm font-medium text-zinc-100">
                {isDragging ? "Drop your video here" : "Drag a video here"}
              </p>
              <p className="mt-1.5 text-xs leading-5 text-zinc-500">
                or <span className="text-forge-300">browse files</span> to get
                started
              </p>
              <p className="mt-4 text-[11px] text-zinc-600">
                {formats.join(" · ")} · up to {formatBytes(maxUpload)}
              </p>
            </div>
          )}
        </div>

        {healthError ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200"
          >
            <p>{healthError}</p>
            <button
              type="button"
              onClick={() => void loadHealth()}
              className="mt-2 font-medium text-red-100 underline decoration-red-300/40 underline-offset-4 hover:decoration-red-200"
            >
              Retry connection
            </button>
          </div>
        ) : null}

        {problem ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] px-4 py-3 text-sm text-amber-100"
          >
            {problem}
          </div>
        ) : null}

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200"
          >
            {error}
          </div>
        ) : null}

        {isUploading ? (
          <div className="mt-5" aria-live="polite">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-zinc-400">
                <SpinnerIcon className="h-3.5 w-3.5 animate-spin text-forge-300" />
                {progress >= 100
                  ? "Upload complete — inspecting video"
                  : "Uploading video"}
              </span>
              <span className="font-mono text-[11px] text-zinc-500">
                {progress}%
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-forge-500 to-forge-300 transition-[width] duration-200"
                style={{ width: `${Math.max(progress, 2)}%` }}
              />
            </div>
          </div>
        ) : null}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-[19rem] text-[11px] leading-5 text-zinc-600">
            {checkingHealth
              ? "Checking the local backend…"
              : "Your video is stored locally and inspected with ffprobe."}
          </p>
          <button
            type="submit"
            disabled={!canSubmit}
            className="group inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-forge-500 px-5 text-sm font-semibold text-[#1b0d04] shadow-[0_10px_30px_-10px_rgba(245,138,59,0.7)] transition hover:bg-forge-400 active:translate-y-px disabled:cursor-not-allowed disabled:bg-surface-700 disabled:text-zinc-500 disabled:shadow-none"
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

      <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.018] px-3.5 py-3 text-[11px] leading-5 text-zinc-500">
        <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-forge-500/25 bg-forge-500/10 text-[9px] font-semibold text-forge-300">
          1
        </span>
        <p>
          Phase 3 validates uploads, transcribes speech locally with Whisper,
          and selects candidate moments with a local Ollama model. Clip
          rendering is not enabled yet.
        </p>
      </div>
    </div>
  );
}
