"""Test structured logging."""

from aegis.observability._logging import get_logger


def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")


def test_logger_methods():
    """Test logger methods work."""
    logger = get_logger("test")

    # Should not raise
    logger.info("test_message", key="value")
    logger.debug("debug_message")
    logger.warning("warning_message")
    logger.error("error_message")
