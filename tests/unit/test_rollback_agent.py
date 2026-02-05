"""Unit tests for the Rollback Agent.

Tests snapshot capture, error rate monitoring, rollback execution, and
the main rollback agent LangGraph node.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kubernetes import client
from langchain_core.runnables import RunnableConfig

from aegis.agent.agents.rollback_agent import (
    ROLLBACK_MONITORING_WINDOW_MINUTES,
    capture_pre_deployment_snapshot,
    execute_rollback,
    monitor_error_rate,
    rollback_agent,
)
from aegis.agent.state import IncidentState


@pytest.mark.asyncio
async def test_capture_predeploy_snapshot_deployment():
    """Test snapshot captures deployment configuration."""
    # Mock Kubernetes API
    apps_api = MagicMock(spec=client.AppsV1Api)
    core_api = MagicMock(spec=client.CoreV1Api)

    # Mock deployment response
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name="test-deploy",
            namespace="default",
            labels={"app": "test"},
            resource_version="12345",
            uid="abc-123",
        ),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "test"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="app",
                            image="nginx:latest",
                        )
                    ]
                ),
            ),
        ),
    )

    apps_api.read_namespaced_deployment.return_value = deployment

    # Mock Prometheus client for baseline error rate
    with patch("aegis.agent.agents.rollback_agent.PrometheusClient") as mock_prom:
        mock_client = AsyncMock()
        mock_client.query_error_rate.return_value = 0.02  # 2% baseline
        mock_prom.return_value = mock_client

        snapshot = await capture_pre_deployment_snapshot(
            namespace="default",
            resource_name="test-deploy",
            resource_type="Deployment",
            apps_api=apps_api,
            core_api=core_api,
        )

    # Verify snapshot structure
    assert "pre_deployment_snapshot" in snapshot
    assert "baseline_error_rate" in snapshot
    assert snapshot["baseline_error_rate"] == 0.02
    assert snapshot["timestamp"] is not None

    # Verify deployment was captured
    deployment_snapshot = snapshot["pre_deployment_snapshot"]["deployment"]
    assert deployment_snapshot["metadata"]["name"] == "test-deploy"
    assert deployment_snapshot["spec"]["replicas"] == 3

    # Verify server-managed metadata removed
    assert "resourceVersion" not in deployment_snapshot["metadata"]
    assert "uid" not in deployment_snapshot["metadata"]


@pytest.mark.asyncio
async def test_monitor_error_rate_stable():
    """Test monitoring detects stable deployment (no rollback needed)."""
    with patch("aegis.agent.agents.rollback_agent.PrometheusClient") as mock_prom:
        mock_client = AsyncMock()
        mock_client.query_error_rate.return_value = 0.03  # 3% current rate
        mock_prom.return_value = mock_client

        current_rate, should_rollback, reason = await monitor_error_rate(
            namespace="default",
            resource_name="test-app",
            baseline_error_rate=0.02,  # 2% baseline
            monitoring_window_minutes=1,
        )

        # 3% vs 2% baseline = 50% increase, below 20% threshold for rollback
        assert should_rollback is False
        assert reason == ""
        assert current_rate == 0.03


@pytest.mark.asyncio
async def test_monitor_error_rate_spike():
    """Test monitoring detects error rate spike (rollback needed)."""
    with patch("aegis.agent.agents.rollback_agent.PrometheusClient") as mock_prom:
        mock_client = AsyncMock()
        mock_client.query_error_rate.return_value = 0.30  # 30% current rate
        mock_prom.return_value = mock_client

        current_rate, should_rollback, reason = await monitor_error_rate(
            namespace="default",
            resource_name="test-app",
            baseline_error_rate=0.10,  # 10% baseline
            monitoring_window_minutes=ROLLBACK_MONITORING_WINDOW_MINUTES,
        )

        # 30% vs 10% baseline = 200% increase, above 20% threshold
        assert should_rollback is True
        assert "error rate spike" in reason.lower()
        assert current_rate == 0.30


@pytest.mark.asyncio
async def test_monitor_error_rate_prometheus_failure():
    """Test monitoring handles Prometheus failures gracefully."""
    with patch("aegis.agent.agents.rollback_agent.PrometheusClient") as mock_prom:
        mock_client = AsyncMock()
        mock_client.query_error_rate.side_effect = Exception("Prometheus unavailable")
        mock_prom.return_value = mock_client

        current_rate, should_rollback, reason = await monitor_error_rate(
            namespace="default",
            resource_name="test-app",
            baseline_error_rate=0.02,
            monitoring_window_minutes=1,
        )

        # Should not rollback on monitoring failure
        assert should_rollback is False
        assert current_rate == 0.0


@pytest.mark.asyncio
async def test_execute_rollback_success():
    """Test rollback execution applies snapshot successfully."""
    snapshot = {
        "deployment": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "test-deploy",
                "namespace": "default",
            },
            "spec": {
                "replicas": 2,
                "selector": {"matchLabels": {"app": "test"}},
                "template": {
                    "metadata": {"labels": {"app": "test"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "app",
                                "image": "nginx:1.20",
                            }
                        ]
                    },
                },
            },
        }
    }

    with patch("aegis.agent.agents.rollback_agent.kubernetes_config.load_config"):
        with patch("aegis.agent.agents.rollback_agent.client.AppsV1Api") as mock_apps:
            mock_api = MagicMock()
            mock_apps.return_value = mock_api

            success, message = await execute_rollback(snapshot, "default")

            assert success is True
            assert "rolled back successfully" in message.lower()

            # Verify patch was called
            mock_api.patch_namespaced_deployment.assert_called_once()
            call_args = mock_api.patch_namespaced_deployment.call_args
            assert call_args[1]["name"] == "test-deploy"
            assert call_args[1]["namespace"] == "default"


@pytest.mark.asyncio
async def test_execute_rollback_api_failure():
    """Test rollback handles Kubernetes API failures."""
    snapshot = {
        "deployment": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deploy", "namespace": "default"},
            "spec": {},
        }
    }

    with patch("aegis.agent.agents.rollback_agent.kubernetes_config.load_config"):
        with patch("aegis.agent.agents.rollback_agent.client.AppsV1Api") as mock_apps:
            mock_api = MagicMock()
            mock_api.patch_namespaced_deployment.side_effect = client.ApiException(
                status=500, reason="Internal Server Error"
            )
            mock_apps.return_value = mock_api

            success, message = await execute_rollback(snapshot, "default")

            assert success is False
            assert "failed" in message.lower()


@pytest.mark.asyncio
async def test_rollback_agent_no_metadata():
    """Test rollback agent handles missing rollback metadata."""
    state: IncidentState = {
        "incident_id": "test-123",
        "namespace": "default",
        "resource_name": "test-app",
        "resource_type": "Deployment",
        # No rollback_metadata
    }

    config = RunnableConfig()

    result = await rollback_agent(state, config)

    # Should skip rollback and return to END
    assert result.goto == "END"
    assert result.update.get("error") is None


@pytest.mark.asyncio
async def test_rollback_agent_triggers_rollback():
    """Test rollback agent triggers rollback on error spike."""
    state: IncidentState = {
        "incident_id": "test-123",
        "namespace": "default",
        "resource_name": "test-app",
        "resource_type": "Deployment",
        "rollback_metadata": {
            "pre_deployment_snapshot": {
                "deployment": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "test-app", "namespace": "default"},
                    "spec": {"replicas": 2},
                }
            },
            "baseline_error_rate": 0.05,
        },
    }

    config = RunnableConfig()

    with patch("aegis.agent.agents.rollback_agent.monitor_error_rate") as mock_monitor:
        # Simulate error spike
        mock_monitor.return_value = (0.30, True, "Error rate spike: 500% increase")

        with patch("aegis.agent.agents.rollback_agent.execute_rollback") as mock_execute:
            mock_execute.return_value = (True, "Rollback successful")

            result = await rollback_agent(state, config)

            assert result.goto == "END"
            assert "ROLLBACK EXECUTED" in result.update.get("error", "")

            # Verify rollback metadata updated
            rollback_meta = result.update["rollback_metadata"]
            assert rollback_meta["rollback_triggered"] is True
            assert "error rate spike" in rollback_meta["rollback_reason"].lower()
            assert rollback_meta["rollback_timestamp"] is not None


@pytest.mark.asyncio
async def test_rollback_agent_stable_deployment():
    """Test rollback agent does not rollback stable deployment."""
    state: IncidentState = {
        "incident_id": "test-123",
        "namespace": "default",
        "resource_name": "test-app",
        "resource_type": "Deployment",
        "rollback_metadata": {
            "pre_deployment_snapshot": {},
            "baseline_error_rate": 0.02,
        },
    }

    config = RunnableConfig()

    with patch("aegis.agent.agents.rollback_agent.monitor_error_rate") as mock_monitor:
        # Simulate stable metrics
        mock_monitor.return_value = (0.03, False, "")

        result = await rollback_agent(state, config)

        assert result.goto == "END"
        assert result.update.get("error") is None


@pytest.mark.asyncio
async def test_rollback_agent_disabled():
    """Test rollback agent respects ROLLBACK_ENABLED setting."""
    state: IncidentState = {
        "incident_id": "test-123",
        "namespace": "default",
        "resource_name": "test-app",
        "resource_type": "Deployment",
        "rollback_metadata": {
            "pre_deployment_snapshot": {},
            "baseline_error_rate": 0.02,
        },
    }

    config = RunnableConfig()

    with patch("aegis.agent.agents.rollback_agent.ROLLBACK_ENABLED", False):
        result = await rollback_agent(state, config)

        assert result.goto == "END"
        assert result.update.get("error") is None
