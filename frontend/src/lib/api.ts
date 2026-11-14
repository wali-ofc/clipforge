import type { Clip, Health, Job } from "@/types/job";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  status?: number;
  code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function networkError(): ApiError {
  return new ApiError(
    `Could not reach the ClipForge backend at ${API_BASE_URL}. Make sure it is running.`,
    undefined,
    "network_error",
  );
}

function messageFromDetail(detail: unknown): {
  message: string;
  code?: string;
} | null {
  if (typeof detail === "string") {
    return { message: detail };
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
    return messages.length ? { message: messages.join(" ") } : null;
  }

  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; code?: unknown };
    if (typeof record.message === "string") {
      return {
        message: record.message,
        code: typeof record.code === "string" ? record.code : undefined,
      };
    }
  }

  return null;
}

function errorFromResponse(
  status: number,
  body: unknown,
  fallback: string,
): ApiError {
  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail: unknown }).detail
      : undefined;
  const parsed = messageFromDetail(detail);
  return new ApiError(
    parsed?.message ?? fallback,
    status,
    parsed?.code,
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/health`, {
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw networkError();
  }

  const body = await readJson(response);
  if (!response.ok) {
    throw errorFromResponse(
      response.status,
      body,
      "The backend health check failed.",
    );
  }
  return body as Health;
}

export async function getJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<Job> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/api/jobs/${encodeURIComponent(jobId)}`,
      { cache: "no-store", signal },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw networkError();
  }

  const body = await readJson(response);
  if (!response.ok) {
    throw errorFromResponse(
      response.status,
      body,
      `Could not load job ${jobId}.`,
    );
  }
  return body as Job;
}

export async function getJobClips(
  jobId: string,
  signal?: AbortSignal,
): Promise<Clip[]> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/clips`,
      { cache: "no-store", signal },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw networkError();
  }

  const body = await readJson(response);
  if (!response.ok) {
    throw errorFromResponse(
      response.status,
      body,
      `Could not load clips for job ${jobId}.`,
    );
  }
  return body as Clip[];
}

/**
 * Cancel a queued or active job and delete its record, upload, work files, and
 * rendered clips. Terminal jobs are deleted immediately.
 */
export async function deleteJob(jobId: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/api/jobs/${encodeURIComponent(jobId)}`,
      { method: "DELETE" },
    );
  } catch {
    throw networkError();
  }

  if (response.ok) {
    return;
  }

  const body = await readJson(response);
  throw errorFromResponse(
    response.status,
    body,
    `Could not delete job ${jobId}.`,
  );
}

export function uploadVideo(
  file: File,
  options?: {
    onProgress?: (percent: number) => void;
    speakerTracking?: boolean;
  },
): Promise<Job> {
  const onProgress = options?.onProgress;
  const speakerTracking = options?.speakerTracking ?? true;

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/api/jobs`);
    request.responseType = "text";

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) {
        return;
      }
      onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
    };

    request.onerror = () => reject(networkError());
    request.onabort = () =>
      reject(new ApiError("The upload was cancelled.", undefined, "aborted"));

    request.onload = () => {
      let body: unknown = null;
      try {
        body = request.responseText ? JSON.parse(request.responseText) : null;
      } catch {
        body = null;
      }

      if (request.status >= 200 && request.status < 300) {
        resolve(body as Job);
        return;
      }

      reject(
        errorFromResponse(
          request.status,
          body,
          "The upload failed. Check the backend logs and try again.",
        ),
      );
    };

    const form = new FormData();
    form.append("file", file);
    form.append("speaker_tracking", speakerTracking ? "true" : "false");
    request.send(form);
  });
}

/**
 * URL for a rendered clip. The browser streams the file from the backend; it
 * never receives a filesystem path. `download` asks the backend for an
 * attachment with a safe filename.
 */
export function getClipFileUrl(clipId: string, download = false): string {
  const base = `${API_BASE_URL}/api/clips/${encodeURIComponent(clipId)}/file`;
  return download ? `${base}?download=true` : base;
}
