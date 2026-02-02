"""Unit tests for AEGIS Post-Fix Monitoring.

Tests the post-fix monitoring logic with mocked Kubernetes clients.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from aegis.kubernetes.monitoring import (
    DEFAULT_MONITORING_DURATION_SECONDS,
    MonitoringResult,
    PostFixMonitor,
    get_post_fix_monitor,
)


class TestMonitoringResult:
    """Test MonitoringResult dataclass."""

    def test_monitoring_result_defaults(self) -> None:
        """Test default MonitoringResult values."""
        result = MonitoringResult(success=True, duration_seconds=300)
        assert result.success is True
        assert result.duration_seconds == 300
        assert result.new_incidents_detected is False
        assert result.warning_messages == []
        assert result.completed_at is None
        assert result.resource_health == {}

    def test_monitoring_result_with_issues(self) -> None:
        """Test MonitoringResult with detected issues."""
        result = MonitoringResult(
            success=False,
            duration_seconds=300,
            new_incidents_detected=True,
            warning_messages=[
                "Container app restarted 3 times",
                "Pod entered CrashLoopBackOff",
            ],
            completed_at=datetime.now(UTC),
        )
        assert result.success is False
        assert result.new_incidents_detected is True
        assert len(result.warning_messages) == 2


class TestDefaultMonitoringDuration:
    """Test monitoring duration constant."""

    def test_default_duration(self) -> None:
        """Test default monitoring duration is 5 minutes."""
        assert DEFAULT_MONITORING_DURATION_SECONDS == 300


class TestPostFixMonitor:
    """Test PostFixMonitor class."""

    @pytest.fixture
    def mock_k8s_clients(self):
        """Fixture to mock Kubernetes clients."""
        with (
            patch("aegis.kubernetes.monitoring.k8s_config") as mock_config,
            patch("aegis.kubernetes.monitoring.client") as mock_client,
        ):
            mock_config.load_incluster_config.side_effect = Exception("Not in cluster")
            mock_config.load_kube_config.return_value = None

            mock_core = MagicMock()
            mock_apps = MagicMock()
            mock_custom = MagicMock()

            mock_client.CoreV1Api.return_value = mock_core
            mock_client.AppsV1Api.return_value = mock_apps
            mock_client.CustomObjectsApi.return_value = mock_custom

            yield {
                "core": mock_core,
                "apps": mock_apps,
                "custom": mock_custom,
                "client": mock_client,
            }

    @pytest.fixture
    def monitor(self, mock_k8s_clients):
        """Fixture to create PostFixMonitor with mocked clients."""
        return PostFixMonitor()

    @pytest.mark.asyncio
    async def test_capture_pod_state(self, monitor, mock_k8s_clients) -> None:
        """Test capturing pod state."""
        mock_core = mock_k8s_clients["core"]

        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_pod.status.container_statuses = [
            MagicMock(name="app", restart_count=5),
            MagicMock(name="sidecar", restart_count=0),
        ]
        mock_core.read_namespaced_pod.return_value = mock_pod

        state = await monitor._capture_resource_state("Pod", "nginx", "default")

        assert state["kind"] == "Pod"
        assert state["name"] == "nginx"
        assert state["phase"] == "Running"
        assert state["container_restarts"]["app"] == 5
        assert state["container_restarts"]["sidecar"] == 0

    @pytest.mark.asyncio
    async def test_capture_deployment_state(self, monitor, mock_k8s_clients) -> None:
        """Test capturing deployment state."""
        mock_apps = mock_k8s_clients["apps"]
        mock_core = mock_k8s_clients["core"]

        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 3
        mock_deployment.status.ready_replicas = 3
        mock_deployment.status.available_replicas = 3
        mock_deployment.status.unavailable_replicas = 0
        mock_deployment.metadata.generation = 5
        mock_deployment.status.observed_generation = 5
        mock_deployment.spec.selector.match_labels = {"app": "nginx"}
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        # Mock pods for deployment
        mock_pod = MagicMock()
        mock_pod.metadata.name = "nginx-pod-1"
        mock_pod.status.container_statuses = [
            MagicMock(name="app", restart_count=2),
        ]
        mock_core.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        state = await monitor._capture_resource_state("Deployment", "nginx", "default")

        assert state["kind"] == "Deployment"
        assert state["replicas"]["desired"] == 3
        assert state["replicas"]["ready"] == 3
        assert state["replicas"]["unavailable"] == 0

    @pytest.mark.asyncio
    async def test_check_pod_health_no_issues(self, monitor, mock_k8s_clients) -> None:
        """Test health check when pod is healthy."""
        mock_core = mock_k8s_clients["core"]

        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_cs = MagicMock()
        mock_cs.name = "app"
        mock_cs.restart_count = 3  # Same as initial
        mock_cs.state = MagicMock()
        mock_cs.state.waiting = None
        mock_cs.state.terminated = None
        mock_pod.status.container_statuses = [mock_cs]
        mock_core.read_namespaced_pod.return_value = mock_pod

        initial_state = {
            "container_restarts": {"app": 3},
        }

        issues = await monitor._check_resource_health("Pod", "nginx", "default", initial_state)

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_check_pod_health_restart_detected(self, monitor, mock_k8s_clients) -> None:
        """Test health check when pod has restarted."""
        mock_core = mock_k8s_clients["core"]

        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_cs = MagicMock()
        mock_cs.name = "app"
        mock_cs.restart_count = 6  # Increased from 3
        mock_cs.state = MagicMock()
        mock_cs.state.waiting = None
        mock_cs.state.terminated = None
        mock_pod.status.container_statuses = [mock_cs]
        mock_core.read_namespaced_pod.return_value = mock_pod

        initial_state = {
            "container_restarts": {"app": 3},
        }

        issues = await monitor._check_resource_health("Pod", "nginx", "default", initial_state)

        assert len(issues) == 1
        assert "restarted" in issues[0].lower()
        assert "3 times" in issues[0]

    @pytest.mark.asyncio
    async def test_check_pod_health_crashloop_detected(self, monitor, mock_k8s_clients) -> None:
        """Test health check detects CrashLoopBackOff."""
        mock_core = mock_k8s_clients["core"]

        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_cs = MagicMock()
        mock_cs.name = "app"
        mock_cs.restart_count = 3
        mock_cs.state = MagicMock()
        mock_cs.state.waiting = MagicMock()
        mock_cs.state.waiting.reason = "CrashLoopBackOff"
        mock_cs.state.terminated = None
        mock_pod.status.container_statuses = [mock_cs]
        mock_core.read_namespaced_pod.return_value = mock_pod

        initial_state = {"container_restarts": {"app": 3}}

        issues = await monitor._check_resource_health("Pod", "nginx", "default", initial_state)

        assert len(issues) == 1
        assert "CrashLoopBackOff" in issues[0]

    @pytest.mark.asyncio
    async def test_check_pod_health_oomkilled_detected(self, monitor, mock_k8s_clients) -> None:
        """Test health check detects OOMKilled."""
        mock_core = mock_k8s_clients["core"]

        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_cs = MagicMock()
        mock_cs.name = "app"
        mock_cs.restart_count = 3
        mock_cs.state = MagicMock()
        mock_cs.state.waiting = None
        mock_cs.state.terminated = MagicMock()
        mock_cs.state.terminated.reason = "OOMKilled"
        mock_cs.state.terminated.exit_code = 137
        mock_pod.status.container_statuses = [mock_cs]
        mock_core.read_namespaced_pod.return_value = mock_pod

        initial_state = {"container_restarts": {"app": 3}}

        issues = await monitor._check_resource_health("Pod", "nginx", "default", initial_state)

        assert len(issues) == 1
        assert "OOMKilled" in issues[0]

    @pytest.mark.asyncio
    async def test_check_deployment_health_unavailable_replicas(
        self, monitor, mock_k8s_clients
    ) -> None:
        """Test health check detects unavailable replicas."""
        mock_apps = mock_k8s_clients["apps"]
        mock_core = mock_k8s_clients["core"]

        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 3
        mock_deployment.status.ready_replicas = 1
        mock_deployment.status.unavailable_replicas = 2
        mock_deployment.spec.selector.match_labels = {"app": "api"}
        mock_deployment.status.conditions = []
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        mock_core.list_namespaced_pod.return_value = MagicMock(items=[])

        initial_state = {"pod_restarts": {}}

        issues = await monitor._check_resource_health("Deployment", "api", "default", initial_state)

        assert len(issues) >= 1
        assert any("unavailable" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_update_incident_phase(self, monitor, mock_k8s_clients) -> None:
        """Test updating incident phase."""
        mock_custom = mock_k8s_clients["custom"]

        await monitor._update_incident_phase(
            "inc-001",
            "default",
            MagicMock(value="Monitoring"),
        )

        mock_custom.patch_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom.patch_namespaced_custom_object.call_args.kwargs
        assert call_kwargs["name"] == "inc-001"
        assert call_kwargs["namespace"] == "default"

    @pytest.mark.asyncio
    async def test_update_incident_with_warning(self, monitor, mock_k8s_clients) -> None:
        """Test updating incident with warning."""
        mock_custom = mock_k8s_clients["custom"]

        await monitor._update_incident_with_warning(
            "inc-001",
            "default",
            ["Container restarted", "OOMKilled detected"],
        )

        mock_custom.patch_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom.patch_namespaced_custom_object.call_args.kwargs
        body = call_kwargs["body"]
        assert body["status"]["monitoring"]["newIncidentsDetected"] is True
        assert "Container restarted" in body["status"]["monitoring"]["warningMessage"]


class TestGetPostFixMonitor:
    """Test get_post_fix_monitor singleton."""

    def test_singleton_pattern(self) -> None:
        """Test that get_post_fix_monitor returns singleton."""
        with (
            patch("aegis.kubernetes.monitoring.k8s_config"),
            patch("aegis.kubernetes.monitoring.client"),
        ):
            # Reset global
            import aegis.kubernetes.monitoring as module

            module._monitor = None

            monitor1 = get_post_fix_monitor()
            monitor2 = get_post_fix_monitor()

            assert monitor1 is monitor2
