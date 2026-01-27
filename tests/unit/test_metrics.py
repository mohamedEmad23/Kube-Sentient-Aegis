"""Test Prometheus metrics."""

from aegis.observability._metrics import (
    agent_iterations_total,
    incident_analysis_duration_seconds,
    llm_request_duration_seconds,
    shadow_environments_active,
    shadow_verifications_total,
    system_healthy,
)


def test_metrics_defined() -> None:
    """Test that metrics are defined."""
    assert incident_analysis_duration_seconds is not None
    assert agent_iterations_total is not None
    assert llm_request_duration_seconds is not None
    assert shadow_environments_active is not None
    assert shadow_verifications_total is not None
    assert system_healthy is not None


def test_counter_metric() -> None:
    """Test counter metric can be incremented."""
    # Note: agent_iterations_total uses 'agent_name', not 'agent'
    agent_iterations_total.labels(agent_name="rca_agent", status="success").inc()
    # Should not raise - we just verify the increment doesn't cause an error


def test_gauge_metric() -> None:
    """Test gauge metric can be set."""
    system_healthy.set(1)
    # Should not raise


def test_histogram_metric() -> None:
    """Test histogram metric can observe."""
    # incident_analysis_duration_seconds requires 'agent_name' label
    incident_analysis_duration_seconds.labels(agent_name="rca_agent").observe(0.5)
    # Should not raise
