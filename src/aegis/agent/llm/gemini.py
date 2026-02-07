"""Gemini client for cloud LLM inference."""

from __future__ import annotations

import time
from typing import Any

import httpx
from pydantic import BaseModel

from aegis.agent.llm.json_utils import validate_json_with_schema
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import llm_request_duration_seconds, llm_requests_total


log = get_logger(__name__)


class GeminiClient:
    """Client for Google Gemini LLM inference."""

    def __init__(self) -> None:
        self.base_url = settings.gemini.base_url.rstrip("/")
        self.api_key = settings.gemini.api_key
        self.default_model = settings.gemini.model
        self.max_retries = settings.gemini.max_retries

    def is_available(self) -> bool:
        return bool(settings.gemini.enabled and self.api_key)

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        format_json: bool,
    ) -> dict[str, Any]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
                continue

            gemini_role = "user"
            if role in {"assistant", "ai", "model"}:
                gemini_role = "model"

            contents.append({"role": gemini_role, "parts": [{"text": content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if settings.gemini.top_p is not None:
            payload["generationConfig"]["topP"] = settings.gemini.top_p

        if format_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        return payload

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        format_json: bool = True,
    ) -> dict[str, Any]:
        """Send a chat completion request to Gemini."""
        if not self.is_available():
            raise RuntimeError("Gemini provider not available (missing API key)")

        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.gemini.temperature

        payload = self._build_payload(messages, temperature=temperature, format_json=format_json)

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                resp = httpx.post(
                    f"{self.base_url}/models/{model}:generateContent",
                    params={"key": self.api_key},
                    json=payload,
                    timeout=settings.gemini.timeout,
                )
                duration = time.time() - start_time

                retry_statuses = {429, 500, 502, 503, 504}
                if resp.status_code in retry_statuses and attempt < self.max_retries:
                    wait = 2**attempt
                    log.warning(
                        "gemini_retrying",
                        status_code=resp.status_code,
                        wait_seconds=wait,
                        attempt=attempt + 1,
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                content = None
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        content = parts[0].get("text")

                if not content:
                    raise ValueError("Gemini response missing content")

                llm_requests_total.labels(
                    model=model,
                    provider="gemini",
                    status="success",
                ).inc()
                llm_request_duration_seconds.labels(
                    model=model,
                    provider="gemini",
                ).observe(duration)

                return {"content": content, "model": model, "raw": data}

            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                llm_requests_total.labels(
                    model=model,
                    provider="gemini",
                    status="error",
                ).inc()
                if attempt < self.max_retries:
                    wait = 2**attempt
                    log.warning(
                        "gemini_request_failed_retrying",
                        error=str(exc),
                        attempt=attempt + 1,
                        wait_seconds=wait,
                    )
                    time.sleep(wait)
                    continue
                log.exception("gemini_request_failed", error=str(exc))
                raise

        raise RuntimeError(f"Gemini request failed: {last_error}")

    def chat_with_schema(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        model: str | None = None,
        temperature: float | None = None,
    ) -> Any:
        response = self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            format_json=True,
        )
        return validate_json_with_schema(response["content"], schema)


_client_cache: dict[str, GeminiClient] = {}


def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client instance."""
    cache_key = "default"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = GeminiClient()
    return _client_cache[cache_key]


__all__ = ["GeminiClient", "get_gemini_client"]
