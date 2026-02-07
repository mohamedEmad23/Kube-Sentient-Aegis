"""Structured error utilities for shadow verification workflows."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


class ShadowWorkflowError(RuntimeError):
    """Structured exception for shadow workflow failures."""

    def __init__(
        self,
        *,
        code: str,
        phase: str,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error for logs/status surfaces."""
        return {
            "code": self.code,
            "phase": self.phase,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Serialize the error as a compact JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=True)


def ensure_shadow_error(
    error: Exception,
    *,
    code: str = "shadow_unexpected_error",
    phase: str = "shadow_workflow",
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> ShadowWorkflowError:
    """Normalize unknown exceptions into a structured shadow error."""
    if isinstance(error, ShadowWorkflowError):
        return error

    merged_details = dict(details or {})
    merged_details.setdefault("exception_type", type(error).__name__)

    return ShadowWorkflowError(
        code=code,
        phase=phase,
        message=str(error) or "Unknown shadow workflow error",
        retryable=retryable,
        details=merged_details,
    )


def parse_shadow_error(payload: str | None) -> ShadowWorkflowError | None:
    """Parse a serialized shadow error payload."""
    if not payload:
        return None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    code = data.get("code")
    phase = data.get("phase")
    message = data.get("message")
    if not isinstance(code, str) or not isinstance(phase, str) or not isinstance(message, str):
        return None

    details = data.get("details")
    timestamp = data.get("timestamp")
    return ShadowWorkflowError(
        code=code,
        phase=phase,
        message=message,
        retryable=bool(data.get("retryable", False)),
        details=details if isinstance(details, dict) else {},
        timestamp=timestamp if isinstance(timestamp, str) else None,
    )


__all__ = [
    "ShadowWorkflowError",
    "ensure_shadow_error",
    "parse_shadow_error",
]
