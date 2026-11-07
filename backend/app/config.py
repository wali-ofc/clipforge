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

    # Ollama (Phase 3)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = Field(default=180.0, gt=0)

    # Clip selection (Phase 3)
    min_clip_seconds: float = Field(default=20.0, gt=0)
    max_clip_seconds: float = Field(default=60.0, gt=0)
    max_clips: int = Field(default=8, ge=1)

    # Rendering (Phase 5)
    output_width: int = Field(default=1080, gt=0)
    output_height: int = Field(default=1920, gt=0)
    output_crf: int = Field(default=23, ge=0, le=51)
    output_preset: str = "veryfast"

    # Face sampling (Phase 4)
    face_sample_fps: float = Field(default=2.0, gt=0)

    @field_validator("data_dir")
    @classmethod
    def _resolve_data_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = BACKEND_DIR / value
        return value.resolve()

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
