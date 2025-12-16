"""Unit tests for Prometheus metrics."""

from __future__ import annotations

import pytest

from aegis.observability.metrics import MetricsCollector, get_metrics


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_metrics_collector_creation(self) -> None:
        """Test MetricsCollector can be created."""
        collector = MetricsCollector(namespace="test_aegis")

        assert collector is not None
        assert collector.namespace == "test_aegis"

    def test_set_build_info(self) -> None:
        """Test setting build info."""
        collector = MetricsCollector(namespace="test_build")

        # Should not raise
        collector.set_build_info(
            version="1.0.0",
            commit="abc123",
            build_date="2024-01-01",
        )

    def test_record_incident(self) -> None:
        """Test recording an incident."""
        collector = MetricsCollector(namespace="test_incident")

        # Should not raise
        collector.record_incident(
            severity="high",
            incident_type="crash_loop",
            namespace="default",
        )

    def test_record_llm_request(self) -> None:
        """Test recording LLM request metrics."""
        collector = MetricsCollector(namespace="test_llm")

        # Should not raise
        collector.record_llm_request(
            provider="ollama",
            model="llama3.2:3b",
            status="success",
            latency_seconds=1.5,
            input_tokens=100,
            output_tokens=50,
        )

    def test_record_llm_request_without_tokens(self) -> None:
        """Test recording LLM request without token counts."""
        collector = MetricsCollector(namespace="test_llm_no_tokens")

        # Should not raise
        collector.record_llm_request(
            provider="groq",
            model="llama-3.2-3b-preview",
            status="success",
            latency_seconds=0.5,
        )


class TestGetMetrics:
    """Tests for get_metrics function."""

    def test_get_metrics_singleton(self) -> None:
        """Test that get_metrics returns singleton."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_get_metrics_returns_collector(self) -> None:
        """Test that get_metrics returns a MetricsCollector."""
        metrics = get_metrics()

        assert isinstance(metrics, MetricsCollector)


class TestMetricLabels:
    """Tests for metric labels."""

    def test_incident_labels(self) -> None:
        """Test incident metric labels."""
        collector = MetricsCollector(namespace="test_labels")

        # Different label combinations should work
        collector.record_incident("low", "oom_kill", "production")
        collector.record_incident("critical", "node_not_ready", "kube-system")
        collector.record_incident("medium", "image_pull_error", "staging")

    def test_llm_labels(self) -> None:
        """Test LLM metric labels."""
        collector = MetricsCollector(namespace="test_llm_labels")

        # Different providers
        collector.record_llm_request("ollama", "llama3.2:3b", "success", 1.0)
        collector.record_llm_request("groq", "llama-3.2-3b", "success", 0.5)
        collector.record_llm_request("gemini", "gemini-pro", "error", 0.1)

        # Different statuses
        collector.record_llm_request("ollama", "llama3.2:3b", "timeout", 30.0)
