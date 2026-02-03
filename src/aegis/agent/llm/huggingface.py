"""Hugging Face Inference API client for AEGIS."""

import json
import os
from typing import Type

from openai import OpenAI
from pydantic import BaseModel

from aegis.observability._logging import get_logger

log = get_logger(__name__)


class HuggingFaceClient:
    """Client for Hugging Face Inference API using OpenAI-compatible endpoint."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Initialize Hugging Face client.

        Args:
            api_key: Hugging Face API token (or set HF_TOKEN env var)
            model: Model ID to use (default: openai/gpt-oss-20b)
        """
        self.api_key = api_key or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise ValueError("HF_TOKEN or HUGGINGFACE_API_KEY environment variable not set")

        self.model = model or "openai/gpt-oss-20b"
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=self.api_key,
        )
        log.info(f"Hugging Face client initialized with model: {self.model}")

    def chat_with_schema(
        self,
        messages: list[dict[str, str]],
        schema: Type[BaseModel],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> BaseModel:
        """Chat with schema validation using Hugging Face Inference API."""
        target_model = model or self.model

        # Add schema instruction to the last user message
        schema_json = schema.model_json_schema()
        schema_instruction = f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema_json, indent=2)}\n\nImportant: Only output the JSON, no additional text."

        # Prepare messages for OpenAI API format
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "user":
                # Add schema to last user message
                if msg == messages[-1]:
                    formatted_messages.append({
                        "role": "user",
                        "content": msg["content"] + schema_instruction
                    })
                else:
                    formatted_messages.append(msg)
            else:
                formatted_messages.append(msg)

        log.info(f"Calling Hugging Face Router API: {target_model}", temperature=temperature)

        # Call OpenAI-compatible API
        response = self.client.chat.completions.create(
            model=target_model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=2048,
        )

        generated_text = response.choices[0].message.content

        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            if "```json" in generated_text:
                generated_text = generated_text.split("```json")[1].split("```")[0].strip()
            elif "```" in generated_text:
                generated_text = generated_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(generated_text)
        except (json.JSONDecodeError, IndexError) as e:
            log.error(f"Failed to parse JSON from response: {generated_text}", error=str(e))
            raise ValueError(f"Invalid JSON response from model: {generated_text[:200]}") from e

        return schema(**result_dict)


def get_huggingface_client(api_key: str | None = None, model: str | None = None) -> HuggingFaceClient:
    """Get or create Hugging Face client singleton."""
    return HuggingFaceClient(api_key=api_key, model=model)
