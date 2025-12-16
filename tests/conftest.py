"""Pytest configuration and fixtures for AEGIS tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# Ensure we're using test configuration
os.environ.setdefault("AEGIS_ENV", "development")
os.environ.setdefault("AEGIS_SHADOW_ENABLED", "true")


@pytest.fixture(autouse=True)
def reset_settings() -> Generator[None, None, None]:
    """Reset settings cache before each test."""
    from aegis.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_kubernetes_client() -> Generator[MagicMock, None, None]:
    """Mock the Kubernetes client for tests."""
    with patch("kubernetes.client") as mock_client:
        # Setup common mocks
        mock_client.CoreV1Api.return_value = MagicMock()
        mock_client.AppsV1Api.return_value = MagicMock()
        mock_client.CustomObjectsApi.return_value = MagicMock()
        yield mock_client


@pytest.fixture
def mock_ollama_client() -> Generator[MagicMock, None, None]:
    """Mock the Ollama client for tests."""
    with patch("ollama.Client") as mock_client:
        instance = MagicMock()
        mock_client.return_value = instance

        # Default response for chat
        instance.chat.return_value = {
            "message": {
                "role": "assistant",
                "content": "Test response from LLM",
            },
            "eval_count": 50,
            "prompt_eval_count": 100,
        }
        yield instance


@pytest.fixture
def sample_pod_event() -> dict[str, Any]:
    """Sample Kubernetes pod event for testing."""
    return {
        "type": "MODIFIED",
        "object": {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "test-pod",
                "namespace": "default",
                "uid": "test-uid-12345",
            },
            "spec": {
                "containers": [
                    {
                        "name": "main",
                        "image": "nginx:latest",
                    }
                ],
            },
            "status": {
                "phase": "Running",
                "containerStatuses": [
                    {
                        "name": "main",
                        "ready": True,
                        "restartCount": 0,
                        "state": {"running": {"startedAt": "2024-01-01T00:00:00Z"}},
                    }
                ],
            },
        },
    }


@pytest.fixture
def sample_failing_pod_event() -> dict[str, Any]:
    """Sample Kubernetes pod event for a failing pod."""
    return {
        "type": "MODIFIED",
        "object": {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "failing-pod",
                "namespace": "default",
                "uid": "failing-uid-12345",
            },
            "spec": {
                "containers": [
                    {
                        "name": "main",
                        "image": "broken:latest",
                    }
                ],
            },
            "status": {
                "phase": "Running",
                "containerStatuses": [
                    {
                        "name": "main",
                        "ready": False,
                        "restartCount": 5,
                        "state": {
                            "waiting": {
                                "reason": "CrashLoopBackOff",
                                "message": "Back-off restarting failed container",
                            }
                        },
                        "lastState": {
                            "terminated": {
                                "exitCode": 1,
                                "reason": "Error",
                                "message": "Container failed",
                            }
                        },
                    }
                ],
            },
        },
    }


@pytest.fixture
def sample_aegis_incident() -> dict[str, Any]:
    """Sample AegisIncident custom resource."""
    return {
        "apiVersion": "aegis.io/v1alpha1",
        "kind": "AegisIncident",
        "metadata": {
            "name": "incident-12345",
            "namespace": "default",
        },
        "spec": {
            "severity": "high",
            "source": {
                "kind": "Pod",
                "name": "failing-pod",
                "namespace": "default",
            },
            "description": "Pod in CrashLoopBackOff",
            "detectedAt": "2024-01-01T00:00:00Z",
        },
        "status": {
            "phase": "Pending",
        },
    }


@pytest.fixture
def temp_env_vars() -> Generator[dict[str, str], None, None]:
    """Fixture to set temporary environment variables."""
    original_env = os.environ.copy()
    temp_vars: dict[str, str] = {}

    yield temp_vars

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
