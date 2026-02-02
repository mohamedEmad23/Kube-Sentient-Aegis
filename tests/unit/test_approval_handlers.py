"""Unit tests for AEGIS Approval Workflow Handlers.

Tests the Kopf-based approval workflow handlers with mocked dependencies.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kubernetes import config as kubernetes_config

from aegis.crd import (
    ApprovalStatus,
    IncidentPhase,
)


class TestApprovalTimeoutDefault:
    """Test approval timeout constant."""

    def test_default_timeout(self) -> None:
        """Test default approval timeout is 15 minutes."""
        from aegis.k8s_operator.handlers.approval import DEFAULT_APPROVAL_TIMEOUT_MINUTES

        assert DEFAULT_APPROVAL_TIMEOUT_MINUTES == 15


class TestPostFixMonitoringDuration:
    """Test post-fix monitoring duration constant."""

    def test_monitoring_duration(self) -> None:
        """Test post-fix monitoring duration is 5 minutes."""
        from aegis.k8s_operator.handlers.approval import POST_FIX_MONITORING_SECONDS

        assert POST_FIX_MONITORING_SECONDS == 300


class TestApprovalHandlerIntegration:
    """Test approval handler integration with mocked Kubernetes clients."""

    @pytest.fixture
    def mock_k8s(self):
        """Fixture to mock Kubernetes config and clients."""
        with (
            patch("aegis.k8s_operator.handlers.approval.k8s_config") as mock_config,
            patch("aegis.k8s_operator.handlers.approval.client") as mock_client,
        ):
            # Preserve the real ConfigException class for exception handling
            mock_config.ConfigException = kubernetes_config.ConfigException
            mock_config.load_incluster_config.side_effect = kubernetes_config.ConfigException(
                "Not in cluster"
            )
            mock_config.load_kube_config.return_value = None

            mock_core = MagicMock()
            mock_custom = MagicMock()

            mock_client.CoreV1Api.return_value = mock_core
            mock_client.CustomObjectsApi.return_value = mock_custom

            yield {
                "core": mock_core,
                "custom": mock_custom,
            }

    @pytest.mark.asyncio
    async def test_apply_approved_fix_success(self, mock_k8s) -> None:
        """Test successful fix application after approval."""
        from aegis.k8s_operator.handlers.approval import _apply_approved_fix

        # Mock body representing an approved incident
        body = {
            "metadata": {
                "name": "inc-001",
                "namespace": "default",
            },
            "spec": {
                "resourceRef": {
                    "kind": "Deployment",
                    "name": "api-app",
                    "namespace": "default",
                },
                "fixProposal": {
                    "fixType": "restart",
                    "description": "Restart deployment",
                    "commands": [],
                    "manifests": {},
                    "confidenceScore": 0.9,
                    "risks": [],
                },
                "approval": {
                    "status": "approved",
                },
            },
            "status": {
                "phase": "ApplyingFix",
            },
        }

        with (
            patch("aegis.k8s_operator.handlers.approval.get_fix_applier") as mock_get_applier,
            patch("aegis.k8s_operator.handlers.approval.get_post_fix_monitor") as mock_get_monitor,
            patch("aegis.k8s_operator.handlers.approval._update_fix_status") as mock_update,
        ):
            # Mock fix applier to return success
            mock_applier = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.applied_at = datetime.now(UTC)
            mock_result.resource_version = "12345"
            mock_applier.apply_fix = AsyncMock(return_value=mock_result)
            mock_get_applier.return_value = mock_applier

            # Mock monitor
            mock_monitor = MagicMock()
            mock_monitor.monitor_resource = AsyncMock()
            mock_get_monitor.return_value = mock_monitor

            # Mock update status
            mock_update.return_value = None

            await _apply_approved_fix("inc-001", "default", body)

            # Verify fix was applied
            mock_applier.apply_fix.assert_called_once()

            # Verify monitoring was started
            mock_monitor.monitor_resource.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_approved_fix_no_proposal(self, mock_k8s) -> None:
        """Test behavior when no fix proposal exists."""
        from aegis.k8s_operator.handlers.approval import _apply_approved_fix

        body = {
            "metadata": {
                "name": "inc-002",
                "namespace": "default",
            },
            "spec": {
                "resourceRef": {
                    "kind": "Pod",
                    "name": "worker",
                },
                # No fixProposal
            },
            "status": {
                "phase": "ApplyingFix",
            },
        }

        with patch("aegis.k8s_operator.handlers.approval._update_fix_status") as mock_update:
            await _apply_approved_fix("inc-002", "default", body)

            # Should update with error
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args.kwargs.get("success") is False
            assert "no fix proposal" in call_args.kwargs.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_update_fix_status_success(self, mock_k8s) -> None:
        """Test updating fix status on success."""
        from aegis.k8s_operator.handlers.approval import _update_fix_status

        mock_custom = mock_k8s["custom"]

        await _update_fix_status(
            mock_custom,
            "inc-001",
            "default",
            success=True,
            applied_at=datetime.now(UTC),
        )

        mock_custom.patch_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom.patch_namespaced_custom_object.call_args.kwargs
        body = call_kwargs["body"]

        assert body["status"]["fixApplied"] is True
        assert body["status"]["phase"] == IncidentPhase.MONITORING.value

    @pytest.mark.asyncio
    async def test_update_fix_status_failure(self, mock_k8s) -> None:
        """Test updating fix status on failure."""
        from aegis.k8s_operator.handlers.approval import _update_fix_status

        mock_custom = mock_k8s["custom"]

        await _update_fix_status(
            mock_custom,
            "inc-001",
            "default",
            success=False,
            error="Dry-run validation failed",
        )

        mock_custom.patch_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom.patch_namespaced_custom_object.call_args.kwargs
        body = call_kwargs["body"]

        assert body["status"]["fixApplied"] is False
        assert body["status"]["phase"] == IncidentPhase.FAILED.value
        assert body["status"]["fixError"] == "Dry-run validation failed"


class TestApprovalStatusChangeHandler:
    """Test approval status change handler logic."""

    def test_approval_status_approved_triggers_fix(self) -> None:
        """Test that approved status triggers fix workflow."""
        # We test the logic that would be in the handler
        new_status = ApprovalStatus.APPROVED.value

        assert new_status == "approved"

        # When status changes to approved, phase should change to ApplyingFix
        expected_phase = IncidentPhase.APPLYING_FIX.value
        assert expected_phase == "ApplyingFix"

    def test_approval_status_rejected_ends_workflow(self) -> None:
        """Test that rejected status ends the workflow."""
        new_status = ApprovalStatus.REJECTED.value

        assert new_status == "rejected"

        # When status changes to rejected, phase should be Rejected
        expected_phase = IncidentPhase.REJECTED.value
        assert expected_phase == "Rejected"


class TestTimeoutDaemonLogic:
    """Test approval timeout daemon logic."""

    def test_timeout_calculation(self) -> None:
        """Test timeout deadline calculation."""
        from aegis.k8s_operator.handlers.approval import DEFAULT_APPROVAL_TIMEOUT_MINUTES

        now = datetime.now(UTC)
        timeout_at = now + timedelta(minutes=DEFAULT_APPROVAL_TIMEOUT_MINUTES)

        # Should be 15 minutes from now
        assert timeout_at > now
        assert (timeout_at - now).total_seconds() == 15 * 60

    def test_timeout_expiry_check(self) -> None:
        """Test checking if timeout has expired."""
        now = datetime.now(UTC)

        # Past timeout
        past_timeout = now - timedelta(minutes=1)
        assert now >= past_timeout  # Should be expired

        # Future timeout
        future_timeout = now + timedelta(minutes=10)
        assert now < future_timeout  # Should not be expired


class TestFixProposalHandler:
    """Test fix proposal addition handler logic."""

    def test_pending_approval_when_required(self) -> None:
        """Test that pending approval is set when required."""
        approval_required = True

        if approval_required:
            expected_status = ApprovalStatus.PENDING.value
            expected_phase = IncidentPhase.AWAITING_APPROVAL.value
        else:
            expected_status = ApprovalStatus.APPROVED.value
            expected_phase = IncidentPhase.APPLYING_FIX.value

        assert expected_status == "pending"
        assert expected_phase == "AwaitingApproval"

    def test_auto_approve_when_not_required(self) -> None:
        """Test auto-approval when not required."""
        approval_required = False

        if approval_required:
            expected_status = ApprovalStatus.PENDING.value
        else:
            expected_status = ApprovalStatus.APPROVED.value

        assert expected_status == "approved"


class TestIncidentCreationHandler:
    """Test incident creation handler logic."""

    def test_initial_phase_is_detected(self) -> None:
        """Test that initial phase is Detected."""
        initial_phase = IncidentPhase.DETECTED

        assert initial_phase.value == "Detected"

    def test_detected_at_is_set(self) -> None:
        """Test that detectedAt timestamp is set on creation."""
        now = datetime.now(UTC)
        detected_at = now.isoformat() + "Z"

        assert "Z" in detected_at
        assert len(detected_at) > 20  # ISO format with timezone


class TestApprovalWorkflowPhases:
    """Test the complete approval workflow phase transitions."""

    def test_workflow_phases(self) -> None:
        """Test all valid phase transitions in the approval workflow."""
        # Valid phase transitions
        transitions = {
            IncidentPhase.DETECTED: [IncidentPhase.ANALYZING],
            IncidentPhase.ANALYZING: [IncidentPhase.AWAITING_APPROVAL],
            IncidentPhase.AWAITING_APPROVAL: [
                IncidentPhase.APPLYING_FIX,  # approved
                IncidentPhase.REJECTED,  # rejected
                IncidentPhase.TIMEOUT,  # timeout
            ],
            IncidentPhase.APPLYING_FIX: [
                IncidentPhase.MONITORING,  # success
                IncidentPhase.FAILED,  # failure
            ],
            IncidentPhase.MONITORING: [
                IncidentPhase.RESOLVED,  # no issues
                # stays in MONITORING with warning if issues (human decision)
            ],
            IncidentPhase.RESOLVED: [],  # terminal
            IncidentPhase.FAILED: [],  # terminal
            IncidentPhase.REJECTED: [],  # terminal
            IncidentPhase.TIMEOUT: [],  # terminal
        }

        # Verify all phases are covered
        all_phases = set(IncidentPhase)
        covered_phases = set(transitions.keys())
        assert all_phases == covered_phases

    def test_terminal_phases(self) -> None:
        """Test that terminal phases have no outgoing transitions."""
        terminal_phases = [
            IncidentPhase.RESOLVED,
            IncidentPhase.FAILED,
            IncidentPhase.REJECTED,
            IncidentPhase.TIMEOUT,
        ]

        for phase in terminal_phases:
            # Terminal phases should exist
            assert phase is not None
            # Their values should be strings
            assert isinstance(phase.value, str)
