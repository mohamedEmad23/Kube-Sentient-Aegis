"""Structured logging configuration for AEGIS.

Uses structlog for structured JSON logging in production
and colorized console output in development.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Mapping


def configure_logging(
    level: str = "INFO",
    format_type: str = "json",
    service_name: str = "aegis",
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format_type: Output format ("json" or "console").
        service_name: Service name to include in log entries.
    """
    # Determine if we're in development mode
    is_development: bool = format_type == "console"

    # Shared processors for all log entries
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_development:
        # Console output for development
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.rich_traceback,
            ),
        ]
    else:
        # JSON output for production
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Format for stdlib logger (passed through structlog)
    handler.setFormatter(logging.Formatter("%(message)s"))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, level.upper()))

    # Reduce noise from third-party libraries
    for noisy_logger in [
        "httpx",
        "httpcore",
        "urllib3",
        "asyncio",
        "kubernetes",
        "kopf",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module).

    Returns:
        A configured structlog logger.
    """
    return structlog.get_logger(name)


def add_context(**kwargs: Any) -> None:
    """Add context to all subsequent log entries in the current context.

    This uses contextvars so the context is preserved across async calls.

    Args:
        **kwargs: Key-value pairs to add to log context.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


class LogContext:
    """Context manager for adding temporary log context.

    Example:
        with LogContext(request_id="abc123", user_id="user1"):
            logger.info("Processing request")
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize with context key-value pairs."""
        self._context = kwargs
        self._token: structlog.contextvars.Token | None = None

    def __enter__(self) -> "LogContext":
        """Add context on entry."""
        self._token = structlog.contextvars.bind_contextvars(**self._context)
        return self

    def __exit__(self, *args: Any) -> None:
        """Remove context on exit."""
        if self._token is not None:
            structlog.contextvars.reset_contextvars(self._token)
