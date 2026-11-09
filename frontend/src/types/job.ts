export type JobState =
  | "queued"
  | "inspecting"
  | "transcribing"
  | "selecting_clips"
  | "tracking_speakers"
  | "rendering"
  | "completed"
  | "failed"
  | "cancelled";

export interface Job {
  id: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  state: JobState;
  progress: number;
  stage_message: string;
  error: string | null;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  rotation: number;
  video_codec: string | null;
  audio_codec: string | null;
  has_audio: boolean;
  container_format: string | null;
  frame_rate: number | null;
  has_transcript: boolean;
  transcript_language: string | null;
  transcript_segment_count: number | null;
  has_speech: boolean | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface HealthCheck {
  available: boolean;
  version: string | null;
  detail: string | null;
}

export interface Health {
  status: "ok" | "degraded";
  app: string;
  version: string;
  environment: string;
  checks: Record<string, HealthCheck>;
  limits: {
    max_upload_bytes: number;
    allowed_formats: string[];
  };
}
