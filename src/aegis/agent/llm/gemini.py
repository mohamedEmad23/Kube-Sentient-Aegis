"""Google Gemini API client for AEGIS."""

import json
import os
from typing import Type

import google.generativeai as genai
from pydantic import BaseModel

from aegis.observability._logging import get_logger

log = get_logger(__name__)


class GeminiClient:
    """Client for Google Gemini API."""

    def __init__(self, api_key: str | None = None):
        """Initialize Gemini client."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=self.api_key)
        log.info("Gemini client initialized")

    def chat_with_schema(
        self,
        messages: list[dict[str, str]],
        schema: Type[BaseModel],
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.3,
    ) -> BaseModel:
        """Chat with schema validation using Gemini."""
        # Always use Gemini model, ignore passed model name (which may be Ollama model)
        gemini_model = "gemini-3-flash-preview"

        system_instruction = None
        prompt_parts = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                prompt_parts.append(msg["content"])

        prompt = "\n\n".join(prompt_parts)

        model_config = {
            "temperature": temperature,
            "response_mime_type": "application/json",
        }

        if system_instruction:
            model_instance = genai.GenerativeModel(
                model_name=gemini_model,
                generation_config=model_config,
                system_instruction=system_instruction,
            )
        else:
            model_instance = genai.GenerativeModel(
                model_name=gemini_model,
                generation_config=model_config,
            )

        schema_json = schema.model_json_schema()
        full_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema_json, indent=2)}"

        log.info(f"Calling Gemini {gemini_model}", temperature=temperature)

        response = model_instance.generate_content(full_prompt)
        result_dict = json.loads(response.text)

        return schema(**result_dict)


def get_gemini_client(api_key: str | None = None) -> GeminiClient:
    """Get or create Gemini client singleton."""
    return GeminiClient(api_key=api_key)
