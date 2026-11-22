"""Structured response models for Ollama clip selection.

These models describe the JSON the local LLM is asked to return. They are
separate from the persisted ``Clip`` rows: validation, boundary refinement,
scoring, and deduplication happen in application code.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMClipScores(BaseModel):
    """Scores proposed by the model, on a 0-10 scale."""

    hook: float = 5.0
    clarity: float = 5.0
    standalone: float = 5.0
    emotion_or_interest: float = 5.0
    payoff: float = 5.0


class LLMClip(BaseModel):
    start: float
    end: float
    title: str | None = None
    hook: str | None = None
    reason: str | None = None
    scores: LLMClipScores | None = None


class LLMClipSelection(BaseModel):
    clips: list[LLMClip] = Field(default_factory=list)


class CompactClipProposal(BaseModel):
    """One compact selection returned by the single shortlist request."""

    rank: int = 1
    start: float
    end: float
    score: float = 5.0
    category: str | None = None
    hook: str | None = None
