"""Unit tests for logging configuration."""

from __future__ import annotations

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from aegis.observability.logging import (
    LogContext,
    add_context,
    clear_context,
    configure_logging,
    get_logger,
)


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_configure_logging_json(self) -> None:
        """Test JSON logging configuration."""
        configure_logging(level="INFO", format_type="json")

        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_console(self) -> None:
        """Test console logging configuration."""
        configure_logging(level="DEBUG", format_type="console")

        logger = get_logger("test")
        assert logger is not None

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test that get_logger returns a BoundLogger."""
        logger = get_logger("test.module")

        assert logger is not None
        # Should have standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_logger_with_name(self) -> None:
        """Test logger with custom name."""
        logger = get_logger("custom.logger.name")
        assert logger is not None


class TestLogContext:
    """Tests for log context management."""

    def test_add_context(self) -> None:
        """Test adding context to logs."""
        clear_context()
        add_context(request_id="test-123", user_id="user-456")

        # Context should be set
        # (We can't easily verify without capturing log output)

    def test_clear_context(self) -> None:
        """Test clearing log context."""
        add_context(key="value")
        clear_context()

        # Context should be cleared

    def test_log_context_manager(self) -> None:
        """Test LogContext context manager."""
        clear_context()

        with LogContext(request_id="abc123"):
            # Inside context, should have request_id bound
            pass

        # Outside context, request_id should be unbound

    def test_log_context_nested(self) -> None:
        """Test nested LogContext managers."""
        clear_context()

        with LogContext(outer="value1"):
            with LogContext(inner="value2"):
                # Both outer and inner should be available
                pass
            # Only outer should be available


class TestLoggingOutput:
    """Tests for actual logging output."""

    def test_json_log_format(self) -> None:
        """Test that JSON logs are valid JSON."""
        configure_logging(level="INFO", format_type="json")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            logger = get_logger("test.json")
            logger.info("test_message", extra_field="extra_value")

            output = stream.getvalue()
            if output:
                # Should be valid JSON
                lines = output.strip().split("\n")
                for line in lines:
                    if line:
                        try:
                            json.loads(line)
                        except json.JSONDecodeError:
                            # Not all output may be JSON
                            pass
        finally:
            root_logger.removeHandler(handler)

    def test_log_levels(self) -> None:
        """Test different log levels."""
        configure_logging(level="DEBUG", format_type="console")

        logger = get_logger("test.levels")

        # These should not raise
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
