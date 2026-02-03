<<<<<<< HEAD
"""AEGIS structured logging with JSON formatting.

Provides production-ready structured logging using structlog with:
- JSON format for machine parsing (production)
- Colorful console output for development
- Automatic log level handling
- ISO timestamps
- Exception formatting
"""

import logging
import sys
from typing import Any, cast

import structlog
from structlog.types import FilteringBoundLogger, Processor

from aegis.config.settings import settings


def configure_logging() -> FilteringBoundLogger:
    """Configure structlog for the application.

    Configures structured logging with JSON output for production
    and colorful console output for development.

    Returns:
        FilteringBoundLogger: Configured logger instance
    """
    # Shared processors for both console and JSON output
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    # Determine output format based on environment
    processors: list[Processor]
    if settings.observability.log_format == "json" or settings.is_production:
        # JSON format for production/aggregation
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(sort_keys=True),
        ]
    else:
        # Colorful console for development
        processors = [
            *shared_processors,
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(
                colors=True,
                pad_event=25,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.observability.log_level.value)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.getLevelName(settings.observability.log_level.value),
    )

    return cast(FilteringBoundLogger, structlog.get_logger())


def get_logger(name: str | None = None, **initial_context: Any) -> FilteringBoundLogger:
    """Get a logger instance with optional initial context.

    Args:
        name: Optional logger name (typically module name)
        **initial_context: Initial context to bind to logger

    Returns:
        FilteringBoundLogger: Logger instance with bound context

    Example:
        >>> log = get_logger(__name__, component="agent")
        >>> log.info("starting_analysis", pod="nginx-crashloop")
        {
          "component": "agent",
          "event": "starting_analysis",
          "level": "info",
          "pod": "nginx-crashloop",
          "timestamp": "2026-01-09T12:34:56.789Z"
        }
    """
    logger = structlog.get_logger(name) if name else structlog.get_logger()

    if initial_context:
        logger = logger.bind(**initial_context)

    return cast(FilteringBoundLogger, logger)


# Initialize logging on module import
configure_logging()


# Convenience logger for quick usage
log = get_logger("aegis")


__all__ = ["configure_logging", "get_logger", "log"]
=======
"""AEGIS structured logging with JSON formatting.

Provides production-ready structured logging using structlog with:
- JSON format for machine parsing (production)
- Colorful console output for development
- Automatic log level handling
- ISO timestamps
- Exception formatting
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger

from aegis.config.settings import settings


def configure_logging() -> FilteringBoundLogger:
    """Configure structlog for the application.

    Configures structured logging with JSON output for production
    and colorful console output for development.

    Returns:
        FilteringBoundLogger: Configured logger instance
    """
    # Shared processors for both console and JSON output
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    # Determine output format based on environment
    if settings.observability.log_format == "json" or settings.is_production:
        # JSON format for production/aggregation
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(sort_keys=True),
        ]
    else:
        # Colorful console for development
        processors = [
            *shared_processors,
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(
                colors=True,
                pad_event=25,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.observability.log_level.value)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.getLevelName(settings.observability.log_level.value),
    )

    return structlog.get_logger()


def get_logger(name: str | None = None, **initial_context: Any) -> FilteringBoundLogger:
    """Get a logger instance with optional initial context.

    Args:
        name: Optional logger name (typically module name)
        **initial_context: Initial context to bind to logger

    Returns:
        FilteringBoundLogger: Logger instance with bound context

    Example:
        >>> log = get_logger(__name__, component="agent")
        >>> log.info("starting_analysis", pod="nginx-crashloop")
        {
          "component": "agent",
          "event": "starting_analysis",
          "level": "info",
          "pod": "nginx-crashloop",
          "timestamp": "2026-01-09T12:34:56.789Z"
        }
    """
    logger = structlog.get_logger(name) if name else structlog.get_logger()

    if initial_context:
        logger = logger.bind(**initial_context)

    return logger


# Initialize logging on module import
configure_logging()


# Convenience logger for quick usage
log = get_logger("aegis")


__all__ = ["configure_logging", "get_logger", "log"]
>>>>>>> main
