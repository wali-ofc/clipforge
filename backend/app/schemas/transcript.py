"""Transcript schema.

This is the internal transcript format written to
``data/work/<job-id>/transcript.json``. Timestamps are absolute seconds
relative to the source video and are never re-based to a clip.

Caption and Romanization layers are derived on demand from this data; the
stored transcript and its timestamps are never rewritten.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class TranscriptWord(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Transcript word text must not be empty.")
        return cleaned

    @model_validator(mode="after")
    def _validate_range(self) -> "TranscriptWord":
        if self.end <= self.start:
            raise ValueError("Transcript word end must be greater than start.")
        return self


class TranscriptSegment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str
    words: list[TranscriptWord] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Transcript segment text must not be empty.")
        return cleaned

    @model_validator(mode="after")
    def _validate_range(self) -> "TranscriptSegment":
        if self.end <= self.start:
            raise ValueError("Transcript segment end must be greater than start.")
        return self


class Transcript(BaseModel):
    """Timestamped transcript for one source video."""

    language: str | None = None
    language_probability: float | None = Field(default=None, ge=0, le=1)
    duration: float = Field(ge=0)
    model: str
    has_speech: bool
    created_at: datetime
    segments: list[TranscriptSegment] = Field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(len(segment.words) for segment in self.segments)
