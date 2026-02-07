"""Shared JSON extraction and schema validation helpers for LLM responses."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_CODE_BLOCK_RE = re.compile(r"```\s*(.*?)\s*```", re.DOTALL)


def _extract_braced_json(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def _extract_bracket_json(text: str) -> str | None:
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def extract_json_candidates(content: str) -> list[str]:
    """Return possible JSON strings extracted from a response."""
    candidates: list[str] = []

    for match in _JSON_BLOCK_RE.findall(content):
        if match.strip():
            candidates.append(match.strip())

    if not candidates:
        for match in _CODE_BLOCK_RE.findall(content):
            if match.strip():
                candidates.append(match.strip())

    braced = _extract_braced_json(content)
    if braced:
        candidates.append(braced)

    bracketed = _extract_bracket_json(content)
    if bracketed:
        candidates.append(bracketed)

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)

    return unique


def validate_json_with_schema(content: str, schema: type[BaseModel]) -> Any:
    """Validate JSON content against a Pydantic schema.

    Tries raw content first, then extracted JSON candidates.
    """
    if not content:
        raise ValueError("LLM returned empty content")

    def _try_validate(raw: str) -> Any | None:
        try:
            return schema.model_validate_json(raw)
        except Exception:
            return None

    validated = _try_validate(content)
    if validated is not None:
        return validated

    for candidate in extract_json_candidates(content):
        validated = _try_validate(candidate)
        if validated is not None:
            return validated
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        try:
            return schema.model_validate(parsed)
        except Exception:
            continue

    raise ValueError(f"Failed to validate response against {schema.__name__} schema")
