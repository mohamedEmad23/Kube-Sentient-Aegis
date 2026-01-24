"""Ollama client for local LLM inference.

Provides a production-ready client for interacting with Ollama:
- Synchronous chat completions with JSON mode
- Automatic retry logic with exponential backoff
- Request/response logging and metrics
- Error handling for connection failures
- Support for multiple models (phi3:mini, deepseek-coder, llama3.1)
"""

import re
import time
from typing import Any

from ollama import ChatResponse, Client, ResponseError
from pydantic import BaseModel

from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import llm_request_duration_seconds, llm_requests_total


log = get_logger(__name__)


class OllamaClient:
    """Client for Ollama LLM inference with production features."""

    def __init__(self) -> None:
        """Initialize Ollama client with settings from config."""
        self.client = Client(
            host=settings.ollama.base_url,
            timeout=settings.ollama.timeout,
        )
        self.default_model = settings.ollama.model
        self.max_retries = settings.ollama.max_retries

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        format_json: bool = True,
        json_schema: dict[str, Any] | None = None,
    ) -> ChatResponse:
        """Send chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (defaults to settings.ollama.model)
            temperature: Sampling temperature (defaults to settings.ollama.temperature)
            format_json: Whether to request JSON formatted response
            json_schema: Optional Pydantic model schema for structured output

        Returns:
            ChatResponse: Ollama response object

        Raises:
            ResponseError: If Ollama API returns an error after retries
            ConnectionError: If connection to Ollama fails after retries

        Example:
            >>> client = OllamaClient()
            >>> response = client.chat(
            ...     messages=[{"role": "user", "content": "Analyze this error"}],
            ...     model="phi3:mini",
            ...     format_json=True
            ... )
            >>> print(response.message.content)
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.ollama.temperature

        # Build options
        options = {
            "temperature": temperature,
            "top_p": settings.ollama.top_p,
            "num_ctx": settings.ollama.num_ctx,
        }

        # Configure JSON output
        format_param: dict[str, Any] | str | None = None
        if format_json and json_schema:
            # Pydantic schema for structured output
            format_param = json_schema
        elif format_json:
            # Generic JSON format
            format_param = "json"

        # Retry logic with exponential backoff
        last_error: Exception = Exception("Max retries exceeded")
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                response: ChatResponse = self.client.chat(
                    model=model,
                    messages=messages,
                    format=format_param,
                    options=options,
                )

                duration = time.time() - start_time

                # Record metrics
                llm_requests_total.labels(model=model, status="success").inc()
                llm_request_duration_seconds.labels(model=model).observe(duration)

            except ResponseError as e:
                last_error = e
                llm_requests_total.labels(model=model, status="error").inc()

                log.warning(
                    "ollama_response_error",
                    model=model,
                    error=e.error,
                    status_code=e.status_code,
                    attempt=attempt + 1,
                )

                # Don't retry on 404 (model not found)
                http_not_found = 404
                if e.status_code == http_not_found:
                    log.exception(
                        "ollama_model_not_found",
                        model=model,
                        suggestion=f"Run: ollama pull {model}",
                    )
                    raise

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    log.debug("retrying_request", wait_seconds=wait_time)
                    time.sleep(wait_time)

            except ConnectionError as e:
                last_error = e
                llm_requests_total.labels(model=model, status="connection_error").inc()

                log.warning(
                    "ollama_connection_error",
                    model=model,
                    error=str(e),
                    attempt=attempt + 1,
                )

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    log.debug("retrying_connection", wait_seconds=wait_time)
                    time.sleep(wait_time)

            else:
                return response

        # All retries exhausted
        log.error(
            "ollama_request_failed",
            model=model,
            max_retries=self.max_retries,
            last_error=str(last_error),
        )
        raise last_error

    def chat_with_schema(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        model: str | None = None,
        temperature: float | None = None,
    ) -> Any:
        """Send chat request with Pydantic schema validation.

        Args:
            messages: List of message dicts
            schema: Pydantic model class for response validation
            model: Model name (optional)
            temperature: Sampling temperature (optional)

        Returns:
            Validated Pydantic model instance matching the schema type

        Raises:
            ValidationError: If response doesn't match schema
            ResponseError: If Ollama API error

        Example:
            >>> from pydantic import BaseModel
            >>> class AnalysisResult(BaseModel):
            ...     root_cause: str
            ...     severity: str
            ...     confidence: float
            >>>
            >>> client = OllamaClient()
            >>> result = client.chat_with_schema(
            ...     messages=[{"role": "user", "content": "Analyze this"}],
            ...     schema=AnalysisResult
            ... )
            >>> print(result.root_cause)
        """
        response = self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            format_json=True,
            json_schema=schema.model_json_schema(),
        )

        # Parse and validate JSON response
        if response.message.content is None:
            msg = f"Ollama returned empty content for model {response.model}"
            log.error("ollama_empty_content", model=response.model)
            raise ValueError(msg)

        try:
            validated = schema.model_validate_json(response.message.content)
        except Exception as e:
            # Try to extract JSON from markdown code blocks
            content = response.message.content
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if not json_match:
                json_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)

            if json_match:
                try:
                    validated = schema.model_validate_json(json_match.group(1))
                except ValueError as extraction_error:
                    log.warning(
                        "schema_extraction_failed",
                        schema=schema.__name__,
                        error=str(extraction_error),
                    )
                else:
                    return validated

            log.exception(
                "schema_validation_failed",
                schema=schema.__name__,
                raw_content=response.message.content[:500] if response.message.content else "None",
            )
            raise ValueError(
                f"Failed to validate response against {schema.__name__} schema: {e}"
            ) from e
        else:
            log.debug(
                "schema_validation_success",
                schema=schema.__name__,
                model=model or self.default_model,
            )
            return validated

    def is_available(self) -> bool:
        """Check if Ollama server is available.

        Returns:
            bool: True if server responds, False otherwise
        """
        try:
            # Try to list models as health check
            self.client.list()
        except (ConnectionError, ResponseError) as e:
            log.warning("ollama_health_check_failed", error=str(e))
            return False
        else:
            log.debug("ollama_health_check_passed")
            return True


# Module-level client cache
_client_cache: dict[str, OllamaClient] = {}


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client instance.

    Returns:
        OllamaClient: Cached client instance
    """
    cache_key = "default"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = OllamaClient()
    return _client_cache[cache_key]


__all__ = ["OllamaClient", "get_ollama_client"]
