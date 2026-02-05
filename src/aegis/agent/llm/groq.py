"""Groq client for cloud LLM inference.

Uses Groq's OpenAI-compatible chat completions API.
"""

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


class GroqClient:
    """Client for Groq LLM inference."""

    def __init__(self) -> None:
        base_url = settings.groq.base_url.rstrip("/")
        if not base_url.endswith("/openai/v1"):
            base_url = f"{base_url}/openai/v1"
        self.base_url = base_url
        self.api_key = settings.groq.api_key
        self.default_model = settings.groq.model
        self.max_retries = settings.groq.max_retries
        self.fallback_models = settings.groq.fallback_model_list()

    def is_available(self) -> bool:
        return bool(settings.groq.enabled and self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("Groq API key not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        format_json: bool = True,
    ) -> dict[str, Any]:
        """Send chat completion request to Groq.

        Returns a dict with content, model, and raw response.
        """
        if not self.is_available():
            raise RuntimeError("Groq provider not available (missing API key)")

        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.groq.temperature

        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if settings.groq.top_p is not None:
            payload["top_p"] = settings.groq.top_p
        if format_json:
            payload["response_format"] = {"type": "json_object"}

        candidate_models = [model]
        for fallback in self.fallback_models:
            if fallback and fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error: Exception | None = None
        for candidate in candidate_models:
            payload["model"] = candidate
            for attempt in range(self.max_retries + 1):
                try:
                    start_time = time.time()
                    resp = httpx.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                        timeout=settings.groq.timeout,
                    )
                    duration = time.time() - start_time

                    retry_statuses = {429, 500, 502, 503, 504}
                    if resp.status_code in retry_statuses and attempt < self.max_retries:
                        wait = 2**attempt
                        log.warning(
                            "groq_retrying",
                            status_code=resp.status_code,
                            wait_seconds=wait,
                            attempt=attempt + 1,
                        )
                        time.sleep(wait)
                        continue

                    if resp.status_code == 404:
                        log.warning(
                            "groq_model_not_found",
                            model=candidate,
                            status_code=resp.status_code,
                            response=resp.text[:200],
                        )
                        break

                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    content = None
                    if choices:
                        content = choices[0].get("message", {}).get("content")

                    if not content:
                        raise ValueError("Groq response missing content")

                    llm_requests_total.labels(
                        model=candidate,
                        provider="groq",
                        status="success",
                    ).inc()
                    llm_request_duration_seconds.labels(
                        model=candidate,
                        provider="groq",
                    ).observe(duration)

                    return {
                        "content": content,
                        "model": data.get("model", candidate),
                        "raw": data,
                    }

                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc
                    llm_requests_total.labels(
                        model=candidate,
                        provider="groq",
                        status="error",
                    ).inc()
                    if attempt < self.max_retries:
                        wait = 2**attempt
                        log.warning(
                            "groq_request_failed_retrying",
                            error=str(exc),
                            attempt=attempt + 1,
                            wait_seconds=wait,
                        )
                        time.sleep(wait)
                        continue
                    log.exception(
                        "groq_request_failed",
                        error=str(exc),
                        model=candidate,
                        base_url=self.base_url,
                    )
                    raise

        raise RuntimeError(f"Groq request failed: {last_error}")

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


_client_cache: dict[str, GroqClient] = {}


def get_groq_client() -> GroqClient:
    """Get or create Groq client instance."""
    cache_key = "default"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = GroqClient()
    return _client_cache[cache_key]


__all__ = ["GroqClient", "get_groq_client"]
