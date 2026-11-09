"""Minimal Ollama HTTP client used for clip selection.

The client talks to a locally running Ollama instance through its HTTP API.
It never loads a model directly; Ollama owns the model lifecycle. Structured
output is requested with a JSON schema so responses can be validated rather
than parsed from prose.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT_SECONDS = 5.0


class OllamaError(Exception):
    """A user-facing Ollama failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class OllamaMalformedResponse(OllamaError):
    """The model responded, but not with usable JSON."""


@dataclass(frozen=True)
class OllamaProbe:
    reachable: bool
    version: str | None = None
    models: tuple[str, ...] = ()
    model_available: bool | None = None
    detail: str | None = None


def _normalize_model_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        return cleaned
    return cleaned if ":" in cleaned else f"{cleaned}:latest"


def _model_is_available(configured: str, available: tuple[str, ...]) -> bool:
    target = _normalize_model_name(configured)
    return any(_normalize_model_name(name) == target for name in available)


class OllamaClient:
    """Synchronous client for the local Ollama HTTP API."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(
                settings.ollama_timeout_seconds,
                connect=min(_PROBE_TIMEOUT_SECONDS, settings.ollama_timeout_seconds),
            ),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OllamaClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def probe(self) -> OllamaProbe:
        """Check whether Ollama is running and the configured model is listed."""
        try:
            version_response = self._client.get(
                "/api/version", timeout=_PROBE_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as exc:
            return OllamaProbe(
                reachable=False,
                detail=(
                    f"Ollama is not reachable at {self.settings.ollama_base_url}. "
                    "Start it with `ollama serve` and retry. "
                    f"({type(exc).__name__})"
                ),
            )

        if version_response.status_code >= 400:
            return OllamaProbe(
                reachable=False,
                detail=(
                    f"Ollama at {self.settings.ollama_base_url} returned HTTP "
                    f"{version_response.status_code}."
                ),
            )

        version: str | None = None
        try:
            version_body = version_response.json()
            if isinstance(version_body, dict):
                raw_version = version_body.get("version")
                version = str(raw_version) if raw_version else None
        except ValueError:
            version = None

        try:
            tags_response = self._client.get(
                "/api/tags", timeout=_PROBE_TIMEOUT_SECONDS
            )
        except httpx.HTTPError:
            return OllamaProbe(
                reachable=True,
                version=version,
                model_available=None,
                detail="Ollama is running but its model list could not be read.",
            )

        if tags_response.status_code >= 400:
            return OllamaProbe(
                reachable=True,
                version=version,
                model_available=None,
                detail="Ollama is running but its model list could not be read.",
            )

        models: list[str] = []
        try:
            tags_body = tags_response.json()
            for entry in tags_body.get("models", []) if isinstance(tags_body, dict) else []:
                if isinstance(entry, dict):
                    name = entry.get("name") or entry.get("model")
                    if name:
                        models.append(str(name))
        except ValueError:
            models = []

        available = _model_is_available(
            self.settings.ollama_model, tuple(models)
        )
        detail = None
        if not available:
            detail = (
                f"Ollama is running but the model '{self.settings.ollama_model}' "
                f"is not installed. Run `ollama pull {self.settings.ollama_model}`."
            )
        return OllamaProbe(
            reachable=True,
            version=version,
            models=tuple(models),
            model_available=available,
            detail=detail,
        )

    def ensure_ready(self) -> OllamaProbe:
        """Raise an actionable error unless Ollama and the model are usable."""
        probe = self.probe()
        if not probe.reachable:
            raise OllamaError(
                "ollama_unavailable",
                probe.detail
                or (
                    f"Ollama is not reachable at {self.settings.ollama_base_url}. "
                    "Start it with `ollama serve` and retry."
                ),
            )
        if probe.model_available is False:
            raise OllamaError(
                "ollama_model_missing",
                probe.detail
                or (
                    f"The Ollama model '{self.settings.ollama_model}' is not "
                    f"installed. Run `ollama pull {self.settings.ollama_model}`."
                ),
            )
        return probe

    def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Run one non-streaming structured chat request and return JSON."""
        payload: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": self.settings.ollama_temperature,
                "num_ctx": self.settings.ollama_num_ctx,
            },
            "keep_alive": self.settings.ollama_keep_alive,
        }
        if not self.settings.ollama_think:
            payload["think"] = False

        try:
            response = self._client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise OllamaError(
                "ollama_timeout",
                (
                    "Ollama did not respond within "
                    f"{self.settings.ollama_timeout_seconds:.0f} seconds while "
                    "selecting clips. Try a smaller model or increase "
                    "OLLAMA_TIMEOUT_SECONDS."
                ),
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(
                "ollama_unavailable",
                (
                    f"Could not reach Ollama at {self.settings.ollama_base_url}. "
                    "Start it with `ollama serve` and retry. "
                    f"({type(exc).__name__})"
                ),
            ) from exc

        if response.status_code == 404:
            raise OllamaError(
                "ollama_model_missing",
                (
                    f"The Ollama model '{self.settings.ollama_model}' is not "
                    f"installed. Run `ollama pull {self.settings.ollama_model}`."
                ),
            )

        if response.status_code >= 400:
            snippet = response.text.strip().replace("\n", " ")[:300]
            raise OllamaError(
                "ollama_request_failed",
                (
                    f"Ollama returned HTTP {response.status_code} while selecting "
                    "clips."
                    + (f" {snippet}" if snippet else "")
                ),
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise OllamaMalformedResponse(
                "ollama_malformed_response",
                "Ollama returned a response that was not JSON.",
            ) from exc

        message = body.get("message") if isinstance(body, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaMalformedResponse(
                "ollama_malformed_response",
                "Ollama returned an empty response.",
            )

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Ollama returned non-JSON content for model %s: %s",
                self.settings.ollama_model,
                content[:200],
            )
            raise OllamaMalformedResponse(
                "ollama_malformed_response",
                "Ollama returned content that was not valid JSON.",
            ) from exc

        if not isinstance(parsed, dict):
            raise OllamaMalformedResponse(
                "ollama_malformed_response",
                "Ollama returned JSON that was not an object.",
            )
        return parsed
