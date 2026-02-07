"""LLM router with provider selection and Ollama fallback."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from aegis.agent.llm.gemini import get_gemini_client
from aegis.agent.llm.groq import get_groq_client
from aegis.agent.llm.ollama import get_ollama_client
from aegis.config.settings import LLMProvider, settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)


def _normalize_provider(provider: str | LLMProvider) -> str:
    if isinstance(provider, LLMProvider):
        return provider.value
    return str(provider).lower()


def get_llm_client(provider: str | LLMProvider) -> Any:
    provider_value = _normalize_provider(provider)
    if provider_value == LLMProvider.GROQ.value:
        return get_groq_client()
    if provider_value == LLMProvider.GEMINI.value:
        return get_gemini_client()
    return get_ollama_client()


def provider_is_available(provider: str | LLMProvider) -> bool:
    client = get_llm_client(provider)
    try:
        return bool(client.is_available())
    except Exception:
        return False


def _resolve_model(provider: str, model: str | None) -> str:
    if provider in {LLMProvider.GROQ.value, LLMProvider.GEMINI.value}:
        if model and ":" in model:
            log.warning(
                "llm_model_mismatch",
                provider=provider,
                configured_model=model,
                fallback_model=(
                    settings.groq.model
                    if provider == LLMProvider.GROQ.value
                    else settings.gemini.model
                ),
            )
            return settings.groq.model if provider == LLMProvider.GROQ.value else settings.gemini.model
    if model:
        return model
    if provider == LLMProvider.GROQ.value:
        return settings.groq.model
    if provider == LLMProvider.GEMINI.value:
        return settings.gemini.model
    return settings.ollama.model


def chat_with_schema_with_fallback(
    *,
    messages: list[dict[str, str]],
    schema: type[BaseModel],
    provider: str | LLMProvider,
    model: str | None = None,
    temperature: float | None = None,
    fallback_model: str | None = None,
    allow_fallback: bool = True,
) -> tuple[Any, str, str]:
    """Run LLM request with provider selection and Ollama fallback.

    Returns (result, provider_used, model_used).
    """
    primary_provider = _normalize_provider(provider)
    primary_model = _resolve_model(primary_provider, model)

    primary_client = get_llm_client(primary_provider)
    if not provider_is_available(primary_provider):
        if not allow_fallback or primary_provider == LLMProvider.OLLAMA.value:
            raise RuntimeError(f"Primary provider {primary_provider} is not available")
        log.warning("llm_provider_unavailable", provider=primary_provider)
    else:
        try:
            result = primary_client.chat_with_schema(
                messages=messages,
                schema=schema,
                model=primary_model,
                temperature=temperature,
            )
            return result, primary_provider, primary_model
        except Exception as exc:
            if not allow_fallback or primary_provider == LLMProvider.OLLAMA.value:
                raise
            log.warning("llm_primary_failed", provider=primary_provider, error=str(exc))

    fallback_provider = LLMProvider.OLLAMA.value
    fallback_client = get_llm_client(fallback_provider)
    if not provider_is_available(fallback_provider):
        raise RuntimeError("Ollama fallback is not available")

    fallback_model = fallback_model or settings.ollama.model
    result = fallback_client.chat_with_schema(
        messages=messages,
        schema=schema,
        model=fallback_model,
        temperature=temperature,
    )
    return result, fallback_provider, fallback_model


__all__ = ["chat_with_schema_with_fallback", "get_llm_client", "provider_is_available"]
