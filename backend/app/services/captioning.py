"""Caption cue generation, formatting, and transcript-range extraction.

This module builds readable phrase-based captions from the stored transcript.
It never mutates the original transcript. Romanization is applied as a display
layer only.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

from app.schemas.transcript import Transcript, TranscriptSegment, TranscriptWord
from app.services.roman_urdu import has_urdu_script, romanize_text

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"\s+")
_SENTENCE_END = re.compile(r"[.!?۔؟!]+[\"')\]]*$")
_CLAUSE_END = re.compile(r"[,;:،؛]+[\"')\]]*$")

# Classic, caption-safe defaults. Burn-in is deliberately disabled: exported
# MP4s must stay clean, and Romanization is a display-only text layer.
CAPTION_DEFAULTS = {
    "language": "roman",
    "style": "classic",
    "font": "Arial",
    "position": "center",
    "burn": False,
}


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str
    display_text: str | None = None


@dataclass(frozen=True)
class CaptionWord:
    start: float
    end: float
    text: str


def _clean_text(text: str) -> str:
    return _WHITESPACE.sub(" ", str(text or "")).strip()


def _clean_cue_text(cue: CaptionCue) -> str:
    """Keep intentional display line breaks while normalizing each line."""
    raw = cue.display_text if cue.display_text is not None else cue.text
    lines = [_WHITESPACE.sub(" ", line).strip() for line in str(raw or "").splitlines()]
    return "\n".join(line for line in lines if line)


def wrap_caption_text(text: str, *, max_lines: int = 2, max_chars_per_line: int = 42) -> str:
    """Wrap classic captions into at most two readable lines.

    Words and punctuation are preserved; the character target is a soft one so
    unusually long phrases are split near the middle rather than truncated.
    """
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    max_lines = max(1, int(max_lines))
    if max_lines == 1 or len(cleaned) <= max_chars_per_line:
        return cleaned

    words = cleaned.split()
    if len(words) < 2:
        return cleaned

    best_split: tuple[int, int] | None = None
    for index in range(1, len(words)):
        left = " ".join(words[:index])
        right = " ".join(words[index:])
        if len(left) > max_chars_per_line or len(right) > max_chars_per_line:
            continue
        score = abs(len(left) - len(right))
        if best_split is None or score < best_split[0]:
            best_split = (score, index)

    split_at = best_split[1] if best_split else max(1, len(words) // 2)
    lines = [" ".join(words[:split_at]), " ".join(words[split_at:])]
    return "\n".join(line for line in lines[:max_lines] if line)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    hrs, rem = divmod(total_ms, 3_600_000)
    mins, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def _format_plain_timestamp(seconds: float) -> str:
    total = max(0.0, float(seconds))
    hrs = int(total // 3600)
    mins = int((total % 3600) // 60)
    secs = int(total % 60)
    if hrs:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_srt(cues: Iterable[CaptionCue]) -> str:
    lines: list[str] = []
    for index, cue in enumerate(cues, start=1):
        start = _format_srt_timestamp(cue.start)
        end = _format_srt_timestamp(max(cue.end, cue.start + 0.001))
        text = _clean_cue_text(cue)
        if not text:
            continue
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def format_transcript_txt(cues: Iterable[CaptionCue], *, include_timestamps: bool = True) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    paragraph_start: float | None = None
    paragraph_end: float | None = None

    def flush() -> None:
        nonlocal paragraph, paragraph_start, paragraph_end
        if not paragraph:
            return
        text = _clean_text(" ".join(paragraph))
        if include_timestamps and paragraph_start is not None and paragraph_end is not None:
            blocks.append(f"[{_format_plain_timestamp(paragraph_start)} - {_format_plain_timestamp(paragraph_end)}]")
        blocks.append(text)
        blocks.append("")
        paragraph = []
        paragraph_start = None
        paragraph_end = None

    for cue in cues:
        text = _clean_text(cue.text)
        if not text:
            continue
        if paragraph_start is None:
            paragraph_start = cue.start
        paragraph_end = cue.end
        paragraph.append(text)
        # Group into readable paragraphs; break on sentence end or when long.
        word_count = sum(len(p.split()) for p in paragraph)
        if _SENTENCE_END.search(text) or word_count >= 40:
            flush()
    flush()
    return "\n".join(blocks).rstrip() + ("\n" if blocks else "")


def _segment_words(segment: TranscriptSegment) -> list[CaptionWord]:
    words: list[CaptionWord] = []
    for word in segment.words:
        text = _clean_text(word.text)
        if not text:
            continue
        if word.end <= word.start:
            continue
        words.append(CaptionWord(start=float(word.start), end=float(word.end), text=text))
    words.sort(key=lambda w: (w.start, w.end))
    if words:
        return words
    # Fallback: synthesize a single word-like chunk from segment text.
    text = _clean_text(segment.text)
    if not text:
        return []
    return [CaptionWord(start=float(segment.start), end=float(segment.end), text=text)]


def collect_words(transcript: Transcript) -> list[CaptionWord]:
    collected: list[CaptionWord] = []
    for segment in transcript.segments:
        collected.extend(_segment_words(segment))
    collected.sort(key=lambda w: (w.start, w.end))
    return collected


def extract_words_for_range(
    transcript: Transcript,
    start_seconds: float,
    end_seconds: float,
    *,
    clip_relative: bool = False,
) -> list[CaptionWord]:
    start = float(start_seconds)
    end = float(end_seconds)
    if end <= start:
        return []

    extracted: list[CaptionWord] = []
    for word in collect_words(transcript):
        # Overlap test: include words overlapping the selected range.
        if word.end <= start or word.start >= end:
            continue
        ws = _clamp(word.start, start, end)
        we = _clamp(word.end, start, end)
        if we <= ws:
            # Zero-length after clamping (boundary touch) - skip.
            continue
        if clip_relative:
            ws -= start
            we -= start
        extracted.append(CaptionWord(start=round(ws, 3), end=round(max(we, ws + 0.001), 3), text=word.text))

    if not extracted:
        # Segment-level fallback when no word timestamps overlap usefully.
        for seg in transcript.segments:
            if seg.end <= start or seg.start >= end:
                continue
            text = _clean_text(seg.text)
            if not text:
                continue
            ss = _clamp(float(seg.start), start, end)
            se = _clamp(float(seg.end), start, end)
            if se <= ss:
                continue
            if clip_relative:
                ss -= start
                se -= start
            extracted.append(CaptionWord(start=round(ss, 3), end=round(max(se, ss + 0.001), 3), text=text))
    return extracted


def words_to_cues(
    words: Iterable[CaptionWord],
    *,
    max_words: int = 8,
    max_chars: int = 84,
) -> list[CaptionCue]:
    max_words = max(1, int(max_words))
    max_chars = max(20, int(max_chars))
    cues: list[CaptionCue] = []
    current: list[CaptionWord] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = _clean_text(" ".join(w.text for w in current))
        start = float(current[0].start)
        end = float(current[-1].end)
        if end <= start:
            end = start + 0.001
        cues.append(CaptionCue(start=round(start, 3), end=round(end, 3), text=text))
        current = []

    for word in words:
        text = _clean_text(word.text)
        if not text:
            continue
        candidate = current + [word]
        candidate_text = " ".join(w.text for w in candidate)
        should_break = False
        if current and len(candidate) > max_words:
            should_break = True
        elif current and len(candidate_text) > max_chars:
            should_break = True

        if should_break:
            flush()
            current = [word]
        else:
            current.append(word)

        current_text = _clean_text(" ".join(w.text for w in current))
        if _SENTENCE_END.search(current_text):
            flush()
        elif len(current) >= max_words:
            flush()
        elif len(current) >= max(4, max_words - 2) and _CLAUSE_END.search(current_text):
            flush()

    flush()
    return cues


def _apply_romanization(text: str, *, language: str | None) -> str:
    raw = _clean_text(text)
    if not raw or not has_urdu_script(raw):
        return raw
    # Romanization is display-only. A broken romanizer must never lose the
    # original caption text.
    try:
        return romanize_text(raw, language=language)
    except Exception:  # noqa: BLE001
        logger.exception("Romanization failed; falling back to original caption text")
        return raw


def display_cues(
    cues: Iterable[CaptionCue],
    *,
    language: str = "roman",
    source_language: str | None = None,
) -> list[CaptionCue]:
    """Return cues with display text applied.

    `language="roman"` romanizes Urdu-script text; Latin/mixed English is preserved.
    `language="original"` keeps original transcript text.
    """
    out: list[CaptionCue] = []
    lang = (language or "roman").strip().lower()
    for cue in cues:
        text = _clean_text(cue.text)
        if not text:
            continue
        if lang == "roman":
            text = _apply_romanization(text, language=source_language)
        out.append(
            CaptionCue(
                start=cue.start,
                end=cue.end,
                text=text,
                display_text=wrap_caption_text(text),
            )
        )
    return out


def captions_for_transcript(
    transcript: Transcript,
    *,
    language: str = "roman",
    max_words: int = 8,
) -> list[CaptionCue]:
    words = collect_words(transcript)
    cues = words_to_cues(words, max_words=max_words)
    return display_cues(cues, language=language, source_language=transcript.language)


def captions_for_range(
    transcript: Transcript,
    start_seconds: float,
    end_seconds: float,
    *,
    language: str = "roman",
    max_words: int = 8,
    clip_relative: bool = True,
) -> list[CaptionCue]:
    words = extract_words_for_range(
        transcript,
        start_seconds,
        end_seconds,
        clip_relative=clip_relative,
    )
    cues = words_to_cues(words, max_words=max_words)
    return display_cues(cues, language=language, source_language=transcript.language)


def captions_to_plain_text(cues: Iterable[CaptionCue], *, timestamped: bool = False) -> str:
    rendered: list[str] = []
    for cue in cues:
        text = _clean_text(cue.text)
        if not text:
            continue
        if timestamped:
            rendered.append(f"{_format_plain_timestamp(cue.start)} - {text}")
        else:
            rendered.append(text)
    return "\n".join(rendered).rstrip() + ("\n" if rendered else "")
