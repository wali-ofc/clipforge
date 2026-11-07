import type { JobState } from "@/types/job";

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** exponent;
  return `${exponent === 0 ? Math.round(value) : value.toFixed(1)} ${units[exponent]}`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) {
    return "—";
  }
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remaining = total % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatResolution(
  width: number | null,
  height: number | null,
): string {
  if (!width || !height) {
    return "—";
  }
  return `${width} × ${height}`;
}

export function formatFrameRate(rate: number | null): string {
  if (!rate) {
    return "—";
  }
  return `${rate.toFixed(rate % 1 === 0 ? 0 : 2)} fps`;
}

const STATE_LABELS: Record<JobState, string> = {
  queued: "Queued",
  inspecting: "Inspecting source",
  transcribing: "Transcribing audio",
  selecting_clips: "Selecting moments",
  tracking_speakers: "Tracking speakers",
  rendering: "Rendering clips",
  completed: "Validated",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function stateLabel(state: JobState): string {
  return STATE_LABELS[state] ?? state;
}

export function isTerminalState(state: JobState): boolean {
  return state === "completed" || state === "failed" || state === "cancelled";
}
