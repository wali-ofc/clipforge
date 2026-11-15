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
  ScissorsIcon,
  SpinnerIcon,
  UploadCloudIcon,
  XIcon,
} from "@/components/icons";
import { ApiError, createSegmenterJob, getHealth } from "@/lib/api";
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

export function SegmenterForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [spec, setSpec] = useState("");
  const [frame, setFrame] = useState<"original" | "portrait_9_16">("original");
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
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
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
    spec.trim().length > 0 &&
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
      const job = await createSegmenterJob(file, spec, frame, {
        onProgress: setProgress,
      });
      router.push(`/jobs/${job.id}`);
    } catch (submitError) {
      const message =
        submitError instanceof ApiError
          ? submitError.message
          : "The segmenter request failed unexpectedly. Check timestamps and try again.";
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
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div
          role="button"
          tabIndex={isUploading ? -1 : 0}
          aria-label="Choose a video to segment"
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
          className={[
            "group relative cursor-pointer overflow-hidden rounded-2xl border border-dashed px-5 py-8 text-center transition duration-200 sm:px-8",
            isDragging
              ? "border-teal-500 bg-teal-50"
              : "border-line-strong bg-paper-50 hover:border-teal-300 hover:bg-paper-100",
            isUploading ? "cursor-default opacity-80" : "",
          ].join(" ")}
        >
          <input
            ref={inputRef}
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
                {formatBytes(file.size)} · ready to segment
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
                or upload a file from your device
              </p>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  if (!isUploading) {
                    inputRef.current?.click();
                  }
                }}
                disabled={isUploading}
                className="mt-4 inline-flex items-center gap-2 rounded-xl border border-teal-200 bg-white px-4 py-2 text-xs font-semibold text-teal-700 shadow-sm transition hover:border-teal-300 hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <UploadCloudIcon className="h-4 w-4" />
                Upload from device
              </button>
              <p className="mt-4 text-[11px] text-ink-400">
                {formats.join(" · ")} · up to {formatBytes(maxUpload)}
              </p>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-line bg-paper-50 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <label
              htmlFor="segment-spec"
              className="flex items-center gap-2 text-sm font-medium text-ink-900"
            >
              <ScissorsIcon className="h-4 w-4 text-teal-600" />
              Timestamps
            </label>
            <span className="text-[10px] text-ink-400">
              MM:SS or HH:MM:SS
            </span>
          </div>
          <textarea
            id="segment-spec"
            value={spec}
            onChange={(e) => setSpec(e.target.value)}
            disabled={isUploading}
            rows={5}
            placeholder={"1:23 - 2:23\n5:23 - 6:32\n\nOr join ranges into one clip:\n1:23 - 2:23, 5:23 - 6:32"}
            className="w-full resize-y rounded-lg border border-line bg-white px-3 py-2.5 font-mono text-xs leading-5 text-ink-900 placeholder:text-ink-400 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400 disabled:cursor-not-allowed disabled:opacity-60"
          />
          <div className="mt-2 space-y-1 text-[11px] leading-5 text-ink-500">
            <p>
              <span className="font-medium text-ink-700">New line</span> = separate output clip.
              {" "}
              <span className="font-medium text-ink-700">Commas in a line/group</span> = cut and join those ranges into one clip.
            </p>
            <p className="text-ink-400">
              Example: <span className="font-mono">1:23-2:23, 5:23-6:32</span> → one joined clip with both parts.
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-paper-50 p-4">
          <p className="text-sm font-medium text-ink-900">Output frame</p>
          <p className="mt-0.5 text-[11px] leading-5 text-ink-500">
            Choose whether to keep the original framing or produce a centered 9:16 portrait crop.
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <label
              className={[
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition",
                frame === "original"
                  ? "border-teal-300 bg-teal-50"
                  : "border-line bg-white hover:border-line-strong",
              ].join(" ")}
            >
              <input
                type="radio"
                name="segment-frame"
                value="original"
                checked={frame === "original"}
                onChange={() => setFrame("original")}
                disabled={isUploading}
                className="mt-0.5 text-teal-600 focus:ring-teal-500"
              />
              <span>
                <span className="block text-sm font-medium text-ink-900">Keep original</span>
                <span className="mt-0.5 block text-[11px] leading-5 text-ink-500">
                  Preserve source resolution and aspect ratio.
                </span>
              </span>
            </label>
            <label
              className={[
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition",
                frame === "portrait_9_16"
                  ? "border-teal-300 bg-teal-50"
                  : "border-line bg-white hover:border-line-strong",
              ].join(" ")}
            >
              <input
                type="radio"
                name="segment-frame"
                value="portrait_9_16"
                checked={frame === "portrait_9_16"}
                onChange={() => setFrame("portrait_9_16")}
                disabled={isUploading}
                className="mt-0.5 text-teal-600 focus:ring-teal-500"
              />
              <span>
                <span className="block text-sm font-medium text-ink-900">9:16 portrait</span>
                <span className="mt-0.5 block text-[11px] leading-5 text-ink-500">
                  Center-crop and output a vertical 9:16 frame.
                </span>
              </span>
            </label>
          </div>
        </div>

        {healthError ? (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <p>{healthError}</p>
            <button type="button" onClick={() => void loadHealth()} className="mt-2 font-medium text-red-800 underline decoration-red-300/40 underline-offset-4 hover:decoration-red-600">
              Retry connection
            </button>
          </div>
        ) : null}

        {problem ? (
          <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {problem}
          </div>
        ) : null}

        {error ? (
          <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        {isUploading ? (
          <div aria-live="polite">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-ink-500">
                <SpinnerIcon className="h-3.5 w-3.5 animate-spin text-teal-600" />
                {progress >= 100 ? "Upload complete — queuing" : "Uploading video"}
              </span>
              <span className="font-mono text-[11px] text-ink-500">{progress}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-paper-200">
              <div className="h-full rounded-full bg-teal-500 transition-[width] duration-200" style={{ width: `${Math.max(progress, 2)}%` }} />
            </div>
          </div>
        ) : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-[22rem] text-[11px] leading-5 text-ink-400">
            {checkingHealth
              ? "Checking the local backend…"
              : "Each line/group becomes one output. Comma-separated ranges in a group are joined into a single clip."}
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
                Create segments
                <ArrowRightIcon className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}