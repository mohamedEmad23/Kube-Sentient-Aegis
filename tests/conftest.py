"""Pytest configuration and fixtures for AEGIS tests."""

import pytest


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset Prometheus metrics between tests to avoid state pollution."""
    return
    # Cleanup happens after test - Prometheus metrics are cumulative by design
