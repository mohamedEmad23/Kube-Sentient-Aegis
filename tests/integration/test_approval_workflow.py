"""Integration tests for AEGIS Approval Workflow.

These tests verify the complete approval workflow from detection to resolution.
They use mocked Kubernetes clients for isolation.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from aegis.crd import (
    AegisIncident,
    Approval,
    ApprovalStatus,
    FixProposal,
    FixType,
    IncidentMetadata,
    IncidentPhase,
    IncidentSeverity,
    IncidentSpec,
    IncidentStatus,
    RCAResult,
    ResourceRef,
)


class TestApprovalWorkflowIntegration:
    """Integration tests for the complete approval workflow."""

    @pytest.fixture
    def sample_incident_data(self) -> dict:
        """Create sample incident data for testing."""
        return {
            "apiVersion": "aegis.io/v1",
            "kind": "Incident",
            "metadata": {
                "name": "inc-integration-001",
                "namespace": "default",
                "uid": "test-uid-123",
                "creationTimestamp": datetime.now(UTC).isoformat() + "Z",
            },
            "spec": {
                "source": "k8sgpt",
                "resourceRef": {
                    "kind": "Deployment",
                    "name": "api-server",
                    "namespace": "default",
                },
                "errors": ["CrashLoopBackOff"],
                "severity": "high",
                "rcaResult": {
                    "rootCause": "Memory exhaustion due to connection leak",
                    "reasoning": "Container exceeded memory limits repeatedly",
                    "confidenceScore": 0.92,
                    "affectedComponents": ["container/api", "pod/api-server-abc123"],
                },
                "fixProposal": {
                    "fixType": "resource_adjustment",
                    "description": "Increase memory limit to 1Gi",
                    "commands": ["kubectl set resources deployment/api-server --limits=memory=1Gi"],
                    "confidenceScore": 0.88,
                    "risks": ["May increase cluster resource usage"],
                },
                "approval": {
                    "required": True,
                    "status": "pending",
                },
            },
            "status": {
                "phase": "AwaitingApproval",
            },
        }

    def test_parse_incident_from_k8s_object(self, sample_incident_data) -> None:
        """Test parsing a complete incident from Kubernetes API response."""
        incident = AegisIncident.from_kubernetes_object(sample_incident_data)

        assert incident.metadata.name == "inc-integration-001"
        assert incident.spec.severity == IncidentSeverity.HIGH
        assert incident.spec.rca_result is not None
        assert incident.spec.rca_result.confidence_score == 0.92
        assert incident.spec.fix_proposal is not None
        assert incident.spec.fix_proposal.fix_type == FixType.RESOURCE_ADJUSTMENT
        assert incident.status.phase == IncidentPhase.AWAITING_APPROVAL

    def test_incident_approval_state_transitions(self) -> None:
        """Test that incident transitions correctly through approval states."""
        # Create incident in detected state
        incident = AegisIncident(
            metadata=IncidentMetadata(name="test-inc", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="test-pod"),
                severity=IncidentSeverity.HIGH,
            ),
            status=IncidentStatus(phase=IncidentPhase.DETECTED),
        )

        assert incident.status.phase == IncidentPhase.DETECTED
        assert not incident.is_awaiting_approval()

        # Add fix proposal and move to awaiting approval
        incident.spec.fix_proposal = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart the pod",
        )
        incident.status.phase = IncidentPhase.AWAITING_APPROVAL
        incident.spec.approval.status = ApprovalStatus.PENDING

        assert incident.is_awaiting_approval()
        assert incident.has_fix_proposal()

        # Approve the fix
        incident.spec.approval.status = ApprovalStatus.APPROVED
        incident.spec.approval.approved_by = "admin@example.com"
        incident.status.phase = IncidentPhase.APPLYING_FIX

        assert incident.is_approved()
        assert not incident.is_awaiting_approval()

    def test_incident_rejection_flow(self) -> None:
        """Test that incident rejection flow works correctly."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="test-inc", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Deployment", name="api"),
                fix_proposal=FixProposal(
                    fix_type=FixType.ROLLBACK,
                    description="Rollback to previous version",
                    risks=["Service disruption"],
                ),
                approval=Approval(
                    required=True,
                    status=ApprovalStatus.PENDING,
                ),
            ),
            status=IncidentStatus(phase=IncidentPhase.AWAITING_APPROVAL),
        )

        # Reject the fix
        incident.spec.approval.status = ApprovalStatus.REJECTED
        incident.spec.approval.rejected_by = "security@example.com"
        incident.spec.approval.rejection_reason = "Too risky for production"
        incident.status.phase = IncidentPhase.REJECTED

        assert incident.is_rejected()
        assert not incident.is_approved()
        assert incident.status.phase == IncidentPhase.REJECTED

    def test_incident_timeout_flow(self) -> None:
        """Test that incident timeout flow works correctly."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="test-inc", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="worker"),
                fix_proposal=FixProposal(fix_type=FixType.RESTART),
                approval=Approval(
                    required=True,
                    status=ApprovalStatus.PENDING,
                    timeout_at=datetime.now(UTC) - timedelta(minutes=1),
                ),
            ),
            status=IncidentStatus(phase=IncidentPhase.AWAITING_APPROVAL),
        )

        # Simulate timeout
        incident.spec.approval.status = ApprovalStatus.TIMEOUT
        incident.status.phase = IncidentPhase.TIMEOUT

        assert incident.spec.approval.status == ApprovalStatus.TIMEOUT
        assert incident.status.phase == IncidentPhase.TIMEOUT

    def test_complete_workflow_to_resolution(self) -> None:
        """Test complete workflow from detection to resolution."""
        # 1. Create incident (detected)
        incident = AegisIncident(
            metadata=IncidentMetadata(name="full-flow", namespace="production"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(
                    kind="Deployment",
                    name="api-service",
                    namespace="production",
                ),
                severity=IncidentSeverity.CRITICAL,
                errors=["ImagePullBackOff"],
            ),
            status=IncidentStatus(
                phase=IncidentPhase.DETECTED,
                detected_at=datetime.now(UTC),
            ),
        )

        assert incident.status.phase == IncidentPhase.DETECTED

        # 2. Add RCA result (analyzing)
        incident.status.phase = IncidentPhase.ANALYZING
        incident.spec.rca_result = RCAResult(
            root_cause="Image tag 'v1.2.3' does not exist",
            reasoning="Container image pull failed",
            confidence_score=0.95,
        )

        assert incident.status.phase == IncidentPhase.ANALYZING
        assert incident.spec.rca_result is not None

        # 3. Add fix proposal and await approval
        incident.spec.fix_proposal = FixProposal(
            fix_type=FixType.PATCH,
            description="Update image tag to 'v1.2.2'",
            patch='{"spec": {"template": {"spec": {"containers": [{"name": "api", "image": "api:v1.2.2"}]}}}}',
            confidence_score=0.9,
        )
        incident.spec.approval.status = ApprovalStatus.PENDING
        incident.status.phase = IncidentPhase.AWAITING_APPROVAL

        assert incident.is_awaiting_approval()

        # 4. Approve and apply fix
        incident.spec.approval.status = ApprovalStatus.APPROVED
        incident.spec.approval.approved_by = "oncall@example.com"
        incident.spec.approval.approved_at = datetime.now(UTC)
        incident.status.phase = IncidentPhase.APPLYING_FIX

        assert incident.is_approved()

        # 5. Fix applied, enter monitoring
        incident.status.fix_applied = True
        incident.status.fix_applied_at = datetime.now(UTC)
        incident.status.phase = IncidentPhase.MONITORING

        assert incident.status.fix_applied

        # 6. Monitoring complete, resolved
        incident.status.resolved_at = datetime.now(UTC)
        incident.status.phase = IncidentPhase.RESOLVED

        assert incident.status.phase == IncidentPhase.RESOLVED
        assert incident.status.resolved_at is not None


class TestIncidentSerialization:
    """Test incident serialization for Kubernetes API."""

    def test_incident_to_dict_for_api(self) -> None:
        """Test converting incident to dict for Kubernetes API."""
        incident = AegisIncident(
            metadata=IncidentMetadata(
                name="test-123",
                namespace="prod",
                labels={"app": "api"},
            ),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="api-pod", namespace="prod"),
                severity=IncidentSeverity.HIGH,
                rca_result=RCAResult(
                    root_cause="Test root cause",
                    confidence_score=0.85,
                ),
            ),
        )

        data = incident.to_dict()

        assert data["apiVersion"] == "aegis.io/v1"
        assert data["kind"] == "Incident"
        assert data["metadata"]["name"] == "test-123"
        assert data["spec"]["severity"] == "high"
        assert data["spec"]["rcaResult"]["rootCause"] == "Test root cause"
        assert data["spec"]["rcaResult"]["confidenceScore"] == 0.85

    def test_round_trip_serialization(self) -> None:
        """Test that an incident survives round-trip serialization."""
        original = AegisIncident(
            metadata=IncidentMetadata(name="round-trip", namespace="test"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Deployment", name="app"),
                severity=IncidentSeverity.MEDIUM,
                fix_proposal=FixProposal(
                    fix_type=FixType.SCALE,
                    description="Scale up",
                    commands=["kubectl scale --replicas=5"],
                ),
                approval=Approval(
                    status=ApprovalStatus.APPROVED,
                    approved_by="user",
                ),
            ),
            status=IncidentStatus(
                phase=IncidentPhase.MONITORING,
                fix_applied=True,
            ),
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = AegisIncident.from_kubernetes_object(data)

        # Verify critical fields survive
        assert restored.metadata.name == original.metadata.name
        assert restored.spec.severity == original.spec.severity
        assert restored.spec.fix_proposal is not None
        assert restored.spec.fix_proposal.fix_type == FixType.SCALE
        assert restored.status.phase == IncidentPhase.MONITORING
        assert restored.status.fix_applied is True


class TestApprovalWithFixApplier:
    """Integration tests combining approval handlers with fix applier."""

    @pytest.fixture
    def mock_clients(self):
        """Create mocked Kubernetes clients."""
        with (
            patch("aegis.kubernetes.fix_applier.k8s_config") as config,
            patch("aegis.kubernetes.fix_applier.client") as client_mod,
        ):
            config.load_incluster_config.side_effect = Exception()
            config.load_kube_config.return_value = None

            mock_apps = MagicMock()
            mock_core = MagicMock()

            client_mod.AppsV1Api.return_value = mock_apps
            client_mod.CoreV1Api.return_value = mock_core
            client_mod.ApiException = Exception

            yield {"apps": mock_apps, "core": mock_core}

    @pytest.mark.asyncio
    async def test_fix_applier_restart_integration(self, mock_clients) -> None:
        """Test fix applier restart with full incident context."""
        from aegis.kubernetes.fix_applier import FixApplier

        mock_apps = mock_clients["apps"]

        # Mock deployment read
        mock_deployment = MagicMock()
        mock_deployment.metadata.resource_version = "1000"
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        # Mock deployment patch
        mock_updated = MagicMock()
        mock_updated.metadata.resource_version = "1001"
        mock_apps.patch_namespaced_deployment.return_value = mock_updated

        applier = FixApplier()

        fix_proposal = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart deployment",
        )

        result = await applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="api-server",
            namespace="production",
        )

        assert result.success is True
        assert result.dry_run_passed is True
        assert result.applied is True
        assert result.resource_version == "1001"


class TestMonitoringIntegration:
    """Integration tests for post-fix monitoring."""

    @pytest.fixture
    def mock_k8s(self):
        """Create mocked Kubernetes clients for monitoring."""
        with (
            patch("aegis.kubernetes.monitoring.k8s_config") as config,
            patch("aegis.kubernetes.monitoring.client") as client_mod,
        ):
            config.load_incluster_config.side_effect = Exception()
            config.load_kube_config.return_value = None

            mock_apps = MagicMock()
            mock_core = MagicMock()
            mock_custom = MagicMock()

            client_mod.AppsV1Api.return_value = mock_apps
            client_mod.CoreV1Api.return_value = mock_core
            client_mod.CustomObjectsApi.return_value = mock_custom

            yield {
                "apps": mock_apps,
                "core": mock_core,
                "custom": mock_custom,
            }

    @pytest.mark.asyncio
    async def test_monitor_healthy_deployment(self, mock_k8s) -> None:
        """Test monitoring a healthy deployment."""
        from aegis.kubernetes.monitoring import PostFixMonitor

        mock_apps = mock_k8s["apps"]
        mock_core = mock_k8s["core"]

        # Mock healthy deployment
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 3
        mock_deployment.status.ready_replicas = 3
        mock_deployment.status.available_replicas = 3
        mock_deployment.status.unavailable_replicas = 0
        mock_deployment.metadata.generation = 5
        mock_deployment.status.observed_generation = 5
        mock_deployment.spec.selector.match_labels = {"app": "api"}
        mock_deployment.status.conditions = []
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        # Mock healthy pods
        mock_pod = MagicMock()
        mock_pod.metadata.name = "api-pod-1"
        mock_cs = MagicMock()
        mock_cs.name = "app"
        mock_cs.restart_count = 0
        mock_cs.state = MagicMock()
        mock_cs.state.waiting = None
        mock_cs.state.terminated = None
        mock_pod.status.container_statuses = [mock_cs]
        mock_core.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        monitor = PostFixMonitor()

        # Capture initial state
        initial = await monitor._capture_resource_state("Deployment", "api", "default")

        assert initial["kind"] == "Deployment"
        assert initial["replicas"]["ready"] == 3
        assert initial["replicas"]["unavailable"] == 0

        # Check health (should be healthy)
        issues = await monitor._check_resource_health("Deployment", "api", "default", initial)

        assert len(issues) == 0
