"""A/B benchmark for ClipForge clip selection.

Loads an existing transcript and runs one selection pass with either the new
compact strategy or the legacy window-by-window strategy. Only timings, token
counts and clip intervals are printed; transcript text is never logged.

Example (PowerShell, from ``backend/``)::

    .\\.venv\\Scripts\\python.exe scripts/bench_selection.py `
        --mode compact `
        --transcript data/work/<job-id>/transcript.json `
        --duration 396.823

Use ``--mode legacy`` for the other side of the comparison. Both runs must use
the same video duration and transcript, and Ollama should already be running
with the model named by ``OLLAMA_MODEL`` installed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.schemas.transcript import Transcript  # noqa: E402
from app.services.clip_selection import OllamaClipSelector, create_clip_selector  # noqa: E402
from app.services.compact_selection import estimate_tokens  # noqa: E402
from app.services.ollama import OllamaClient  # noqa: E402


class TrackingClient:
    """Wraps the real client to count prompt size and server-reported timings."""

    def __init__(self, settings: Settings, calls: list[dict]) -> None:
        self._client = OllamaClient(settings)
        self.calls = calls

    def ensure_ready(self):
        return self._client.ensure_ready()

    def _record(self, system: str, user: str, schema: dict, num_predict):
        started = time.perf_counter()
        response = self._client.chat_json_result(
            system=system, user=user, schema=schema, num_predict=num_predict
        )
        wall = time.perf_counter() - started
        stats = response.stats
        self.calls.append(
            {
                "system_chars": len(system),
                "user_chars": len(user),
                "total_chars": len(system) + len(user),
                "estimated_tokens": estimate_tokens(system + user),
                "wall_seconds": round(wall, 3),
                "prompt_eval_tokens": stats.prompt_eval_count,
                "prompt_eval_seconds": stats.prompt_eval_seconds,
                "generation_tokens": stats.eval_count,
                "generation_seconds": stats.eval_seconds,
                "load_seconds": stats.load_seconds,
                "server_total_seconds": stats.total_seconds,
            }
        )
        return response

    def chat_json(self, *, system: str, user: str, schema: dict):
        return self._record(system, user, schema, None).payload

    def chat_json_result(self, *, system: str, user: str, schema: dict, num_predict=None):
        return self._record(system, user, schema, num_predict)

    def close(self):
        self._client.close()


def build_settings(mode: str) -> Settings:
    """Use the project .env, overriding only the selection mode under test."""
    return Settings(clip_selection_mode=mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("compact", "legacy"), required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    settings = build_settings(args.mode)
    transcript = Transcript.model_validate_json(
        args.transcript.read_text(encoding="utf-8")
    )
    calls: list[dict] = []

    if args.mode == "legacy":
        selector = OllamaClipSelector(
            settings, client_factory=lambda: TrackingClient(settings, calls)
        )
    else:
        selector = create_clip_selector(
            settings, client_factory=lambda: TrackingClient(settings, calls)
        )

    started = time.perf_counter()
    candidates = selector.select(transcript, args.duration)
    wall = time.perf_counter() - started

    summary = {
        "mode": args.mode,
        "model": settings.ollama_model,
        "video_seconds": args.duration,
        "transcript_segments": len(transcript.segments),
        "selection_wall_seconds": round(wall, 3),
        "requests": len(calls),
        "candidates_returned": len(candidates),
        "candidate_intervals": [
            [round(candidate.start, 2), round(candidate.end, 2)]
            for candidate in candidates
        ],
        "prompt_chars": sum(call["total_chars"] for call in calls),
        "estimated_tokens_sent": sum(call["estimated_tokens"] for call in calls),
        "server_prompt_eval_tokens": sum(
            call["prompt_eval_tokens"] or 0 for call in calls
        ),
        "server_generation_tokens": sum(
            call["generation_tokens"] or 0 for call in calls
        ),
        "server_prompt_eval_seconds": round(
            sum(call["prompt_eval_seconds"] or 0 for call in calls), 3
        ),
        "server_generation_seconds": round(
            sum(call["generation_seconds"] or 0 for call in calls), 3
        ),
        "server_load_seconds": round(
            sum(call["load_seconds"] or 0 for call in calls), 3
        ),
        "calls": calls,
    }

    print(json.dumps(summary, indent=2))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
