"""Typed application configuration.

All settings can be overridden with environment variables. Values are loaded
from the project-root ``.env`` first, then ``backend/.env`` (which wins), and
finally from real environment variables (which win over both).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ClipForge"
    app_env: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # Storage
    data_dir: Path = Path("./data")
    database_url: str = "sqlite:///./data/clipforge.db"

    # Uploads
    max_upload_bytes: int = Field(default=5 * 1024**3, gt=0)
    upload_chunk_bytes: int = Field(default=1024 * 1024, gt=0)
    allowed_video_extensions: list[str] = Field(
        default_factory=lambda: ["mp4", "mov", "mkv"]
    )
    # Refuse new uploads when the data drive has less free space than this.
    min_free_disk_bytes: int = Field(default=1024**3, ge=0)

    # Job deletion
    # How long DELETE waits for an in-flight job to stop before removing files.
    delete_cancel_wait_seconds: float = Field(default=5.0, ge=0)

    # External media tools
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    ffprobe_timeout_seconds: float = Field(default=60.0, gt=0)

    # Background worker
    worker_autostart: bool = True
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0)
    worker_stop_timeout_seconds: float = Field(default=10.0, gt=0)

    # Whisper (Phase 2)
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = Field(default=4, ge=1)
    whisper_model_dir: Path = Path("./data/models")
    # None means auto-detect the spoken language.
    whisper_language: str | None = None
    whisper_beam_size: int = Field(default=5, ge=1, le=10)
    whisper_vad_filter: bool = True
    audio_extract_timeout_seconds: float = Field(default=3600.0, gt=0)

    # Ollama (Phase 3)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = Field(default=180.0, gt=0)
    ollama_temperature: float = Field(default=0.2, ge=0, le=2)
    ollama_num_ctx: int = Field(default=8192, ge=1024)
    ollama_keep_alive: str = "5m"
    ollama_think: bool = False

    # Clip selection (Phase 3)
    min_clip_seconds: float = Field(default=20.0, gt=0)
    max_clip_seconds: float = Field(default=60.0, gt=0)
    clip_hard_min_seconds: float = Field(default=15.0, gt=0)
    clip_hard_max_seconds: float = Field(default=90.0, gt=0)
    max_clips: int = Field(default=8, ge=1)
    clip_window_seconds: float = Field(default=180.0, gt=0)
    clip_window_overlap_seconds: float = Field(default=30.0, ge=0)
    clip_max_candidates_per_chunk: int = Field(default=4, ge=1, le=20)
    clip_score_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "hook": 0.25,
            "clarity": 0.25,
            "payoff": 0.20,
            "emotion_or_interest": 0.20,
            "conciseness": 0.10,
        }
    )

    # Rendering (Phase 5)
    output_width: int = Field(default=1080, gt=0)
    output_height: int = Field(default=1920, gt=0)
    output_fps: float = Field(default=30.0, gt=0, le=120)
    output_crf: int = Field(default=23, ge=0, le=51)
    output_preset: str = "veryfast"
    render_timeout_seconds: float = Field(default=600.0, gt=0)

    # Face sampling and speaker tracking (Phase 4)
    face_sample_fps: float = Field(default=2.0, gt=0, le=15.0)
    face_detector_model_path: Path = Path(
        "./data/models/face_detection_yunet_2023mar.onnx"
    )
    face_detector_score_threshold: float = Field(default=0.6, ge=0, le=1)
    face_detector_nms_threshold: float = Field(default=0.3, ge=0, le=1)
    face_detector_top_k: int = Field(default=5000, ge=1)
    face_detector_min_size: int = Field(default=32, ge=1)
    face_track_iou_threshold: float = Field(default=0.2, ge=0, le=1)
    face_track_max_gap_seconds: float = Field(default=1.0, gt=0)
    face_track_min_observations: int = Field(default=2, ge=1)
    speaker_confidence_threshold: float = Field(default=0.55, ge=0, le=1)
    speaker_switch_margin: float = Field(default=0.12, ge=0, le=1)
    crop_ema_alpha: float = Field(default=0.35, gt=0, le=1)
    crop_dead_zone_ratio: float = Field(default=0.015, ge=0, le=1)
    crop_max_speed_ratio: float = Field(default=0.5, gt=0)
    crop_hold_seconds: float = Field(default=2.0, ge=0)

    @field_validator("data_dir")
    @classmethod
    def _resolve_data_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = BACKEND_DIR / value
        return value.resolve()

    @field_validator("whisper_model_dir")
    @classmethod
    def _resolve_model_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = BACKEND_DIR / value
        return value.resolve()

    @field_validator("face_detector_model_path")
    @classmethod
    def _resolve_face_model_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = BACKEND_DIR / value
        return value.resolve()

    @field_validator("whisper_model")
    @classmethod
    def _normalize_whisper_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("WHISPER_MODEL must not be empty.")
        return cleaned

    @field_validator("whisper_language")
    @classmethod
    def _normalize_whisper_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @field_validator("ollama_base_url")
    @classmethod
    def _normalize_ollama_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned:
            raise ValueError("OLLAMA_BASE_URL must not be empty.")
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL must start with http:// or https://.")
        return cleaned

    @field_validator("ollama_model")
    @classmethod
    def _normalize_ollama_model(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("OLLAMA_MODEL must not be empty.")
        return cleaned

    @field_validator("clip_score_weights")
    @classmethod
    def _normalize_score_weights(cls, value: dict[str, float]) -> dict[str, float]:
        expected = {
            "hook",
            "clarity",
            "payoff",
            "emotion_or_interest",
            "conciseness",
        }
        cleaned = {key: float(weight) for key, weight in value.items()}
        if set(cleaned) != expected:
            missing = sorted(expected - set(cleaned))
            unknown = sorted(set(cleaned) - expected)
            details = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if unknown:
                details.append(f"unknown {', '.join(unknown)}")
            raise ValueError(
                "CLIP_SCORE_WEIGHTS must contain exactly: "
                + ", ".join(sorted(expected))
                + (f" ({'; '.join(details)})" if details else "")
            )
        if any(weight < 0 for weight in cleaned.values()):
            raise ValueError("CLIP_SCORE_WEIGHTS values must be non-negative.")
        total = sum(cleaned.values())
        if total <= 0:
            raise ValueError("CLIP_SCORE_WEIGHTS must have a positive total.")
        return {key: weight / total for key, weight in cleaned.items()}

    @field_validator("database_url")
    @classmethod
    def _resolve_database_url(cls, value: str) -> str:
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value

        raw_path = value[len(prefix) :]
        if raw_path in {":memory:", ""} or raw_path.startswith("file:"):
            return value

        path = Path(raw_path)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        return f"{prefix}{path.as_posix()}"

    @field_validator("allowed_video_extensions")
    @classmethod
    def _normalize_extensions(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            extension = item.strip().lower().lstrip(".")
            if extension and extension not in normalized:
                normalized.append(extension)
        if not normalized:
            raise ValueError("At least one allowed video extension is required.")
        return normalized

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def _validate_domain_settings(self) -> "Settings":
        if self.min_clip_seconds >= self.max_clip_seconds:
            raise ValueError("MIN_CLIP_SECONDS must be less than MAX_CLIP_SECONDS.")

        if self.clip_hard_min_seconds >= self.min_clip_seconds:
            raise ValueError(
                "CLIP_HARD_MIN_SECONDS must be less than MIN_CLIP_SECONDS."
            )

        if self.clip_hard_max_seconds <= self.max_clip_seconds:
            raise ValueError(
                "CLIP_HARD_MAX_SECONDS must be greater than MAX_CLIP_SECONDS."
            )

        if self.clip_window_overlap_seconds >= self.clip_window_seconds:
            raise ValueError(
                "CLIP_WINDOW_OVERLAP_SECONDS must be less than CLIP_WINDOW_SECONDS."
            )

        if self.output_width % 2 or self.output_height % 2:
            raise ValueError("OUTPUT_WIDTH and OUTPUT_HEIGHT must be even numbers.")

        target_ratio = 9 / 16
        actual_ratio = self.output_width / self.output_height
        if abs(actual_ratio - target_ratio) > 0.005:
            raise ValueError(
                "OUTPUT_WIDTH/OUTPUT_HEIGHT must be portrait 9:16 "
                "(for example 1080x1920 or 720x1280)."
            )

        return self

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def work_dir(self) -> Path:
        return self.data_dir / "work"

    @property
    def clips_dir(self) -> Path:
        return self.data_dir / "clips"

    @property
    def allowed_video_extensions_display(self) -> str:
        return ", ".join(f".{extension}" for extension in self.allowed_video_extensions)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
