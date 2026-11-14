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
  clip_count: number;
  clip_selection_model: string | null;
  speaker_tracking_enabled: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface CropPlanSample {
  time: number;
  x: number;
  y: number;
  crop_width: number;
  crop_height: number;
  confidence: number;
  status: string;
  face_count: number;
}

export interface CropPlan {
  version?: number;
  coordinate_space?: string;
  time_space?: string;
  method?: string;
  target_aspect?: number;
  source?: { width: number; height: number };
  crop?: { width: number; height: number };
  samples?: CropPlanSample[];
}

export interface Clip {
  id: string;
  job_id: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  title: string;
  hook: string | null;
  reason: string | null;
  score: number | null;
  component_scores: Record<string, number | string | Record<string, number>>;
  output_filename: string | null;
  width: number | null;
  height: number | null;
  speaker_tracking_status: string;
  speaker_tracking_confidence: number | null;
  crop_plan: CropPlan;
  tracking_details: Record<string, unknown>;
  render_status: string;
  error: string | null;
  created_at: string;
  updated_at: string;
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
