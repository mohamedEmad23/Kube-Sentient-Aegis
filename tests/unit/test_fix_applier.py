"""Unit tests for AEGIS Fix Applier.

Tests the fix application logic with mocked Kubernetes clients.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from aegis.crd import FixProposal, FixType
from aegis.kubernetes.fix_applier import FixApplier, FixResult, get_fix_applier


class TestFixResult:
    """Test FixResult dataclass."""

    def test_fix_result_defaults(self) -> None:
        """Test default FixResult values."""
        result = FixResult(success=False)
        assert result.success is False
        assert result.dry_run_passed is False
        assert result.applied is False
        assert result.error_message is None
        assert result.applied_at is None
        assert result.rollback_info == {}

    def test_fix_result_success(self) -> None:
        """Test successful FixResult."""
        now = datetime.now(UTC)
        result = FixResult(
            success=True,
            dry_run_passed=True,
            applied=True,
            applied_at=now,
            resource_version="12345",
            rollback_info={"kind": "Deployment", "name": "test"},
        )
        assert result.success is True
        assert result.dry_run_passed is True
        assert result.resource_version == "12345"

    def test_fix_result_failure(self) -> None:
        """Test failed FixResult."""
        result = FixResult(
            success=False,
            dry_run_passed=False,
            error_message="Dry-run failed: invalid resource",
        )
        assert result.success is False
        assert result.error_message is not None


class TestFixApplier:
    """Test FixApplier class."""

    @pytest.fixture
    def mock_k8s_clients(self):
        """Fixture to mock Kubernetes clients."""
        from kubernetes.config import ConfigException

        with (
            patch("aegis.kubernetes.fix_applier.k8s_config") as mock_config,
            patch("aegis.kubernetes.fix_applier.client") as mock_client,
        ):
            # Make ConfigException a real exception so it can be caught
            mock_config.ConfigException = ConfigException
            mock_config.load_incluster_config.side_effect = ConfigException("Not in cluster")
            mock_config.load_kube_config.return_value = None

            # Create mock API clients
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
    def fix_applier(self, mock_k8s_clients):
        """Fixture to create a FixApplier with mocked clients."""
        return FixApplier()

    @pytest.mark.asyncio
    async def test_apply_restart_deployment(self, fix_applier, mock_k8s_clients) -> None:
        """Test applying restart fix to deployment."""
        mock_apps = mock_k8s_clients["apps"]

        # Mock current deployment
        mock_deployment = MagicMock()
        mock_deployment.metadata.resource_version = "1000"
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        # Mock patched deployment
        mock_updated = MagicMock()
        mock_updated.metadata.resource_version = "1001"
        mock_apps.patch_namespaced_deployment.return_value = mock_updated

        fix_proposal = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart deployment to clear issue",
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is True
        assert result.dry_run_passed is True
        assert result.applied is True
        assert result.resource_version == "1001"

        # Verify dry-run was called first
        calls = mock_apps.patch_namespaced_deployment.call_args_list
        assert len(calls) == 2  # dry-run + actual
        assert calls[0].kwargs.get("dry_run") == "All"
        assert calls[1].kwargs.get("dry_run") is None

    @pytest.mark.asyncio
    async def test_apply_restart_statefulset(self, fix_applier, mock_k8s_clients) -> None:
        """Test applying restart fix to statefulset."""
        mock_apps = mock_k8s_clients["apps"]

        mock_sts = MagicMock()
        mock_sts.metadata.resource_version = "2000"
        mock_apps.read_namespaced_stateful_set.return_value = mock_sts

        mock_updated = MagicMock()
        mock_updated.metadata.resource_version = "2001"
        mock_apps.patch_namespaced_stateful_set.return_value = mock_updated

        fix_proposal = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart statefulset",
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="StatefulSet",
            resource_name="db",
            namespace="default",
        )

        assert result.success is True
        assert result.applied is True

    @pytest.mark.asyncio
    async def test_apply_restart_unsupported_kind(self, fix_applier, mock_k8s_clients) -> None:
        """Test restart on unsupported resource kind."""
        fix_proposal = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart service",
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Service",
            resource_name="api",
            namespace="default",
        )

        assert result.success is False
        assert "not supported" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_apply_scale_deployment(self, fix_applier, mock_k8s_clients) -> None:
        """Test applying scale fix to deployment."""
        mock_apps = mock_k8s_clients["apps"]

        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 2
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        mock_updated = MagicMock()
        mock_updated.metadata.resource_version = "3001"
        mock_apps.patch_namespaced_deployment.return_value = mock_updated

        fix_proposal = FixProposal(
            fix_type=FixType.SCALE,
            description="Scale up deployment",
            commands=["kubectl scale deployment/test-app --replicas=5"],
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is True
        assert result.rollback_info.get("previous_replicas") == 2

    @pytest.mark.asyncio
    async def test_apply_scale_no_replicas_in_command(self, fix_applier, mock_k8s_clients) -> None:
        """Test scale fix with missing replicas in command."""
        fix_proposal = FixProposal(
            fix_type=FixType.SCALE,
            description="Scale deployment",
            commands=["kubectl scale deployment/test-app"],  # Missing --replicas
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is False
        assert "replica count" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_apply_patch_deployment(self, fix_applier, mock_k8s_clients) -> None:
        """Test applying JSON patch to deployment."""
        mock_apps = mock_k8s_clients["apps"]

        mock_deployment = MagicMock()
        mock_deployment.metadata.resource_version = "4000"
        mock_apps.read_namespaced_deployment.return_value = mock_deployment

        mock_updated = MagicMock()
        mock_updated.metadata.resource_version = "4001"
        mock_apps.patch_namespaced_deployment.return_value = mock_updated

        fix_proposal = FixProposal(
            fix_type=FixType.PATCH,
            description="Update deployment spec",
            patch='{"spec": {"replicas": 3}}',
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is True
        assert result.dry_run_passed is True

    @pytest.mark.asyncio
    async def test_apply_patch_invalid_json(self, fix_applier, mock_k8s_clients) -> None:
        """Test patch with invalid JSON."""
        fix_proposal = FixProposal(
            fix_type=FixType.PATCH,
            description="Invalid patch",
            patch="not valid json {{",
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is False
        assert "invalid json" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_apply_patch_no_patch_provided(self, fix_applier, mock_k8s_clients) -> None:
        """Test patch fix without patch content."""
        fix_proposal = FixProposal(
            fix_type=FixType.PATCH,
            description="Empty patch",
            patch=None,
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is False
        assert "no patch" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_dry_run_failure(self, fix_applier, mock_k8s_clients) -> None:
        """Test behavior when dry-run fails."""
        from kubernetes.client import ApiException

        mock_apps = mock_k8s_clients["apps"]
        mock_k8s_clients["client"].ApiException = ApiException

        mock_deployment = MagicMock()
        mock_apps.read_namespaced_deployment.return_value = mock_deployment
        mock_apps.patch_namespaced_deployment.side_effect = ApiException(
            status=400,
            reason="Bad Request",
        )

        fix_proposal = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart deployment",
        )

        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        assert result.success is False
        assert result.dry_run_passed is False
        assert "Bad Request" in result.error_message

    @pytest.mark.asyncio
    async def test_unsupported_fix_type(self, fix_applier, mock_k8s_clients) -> None:
        """Test behavior with unhandled fix type."""
        # Create a mock fix proposal with an unknown type
        fix_proposal = MagicMock()
        fix_proposal.fix_type = MagicMock()
        fix_proposal.fix_type.value = "unknown_type"

        # The code should handle this gracefully
        result = await fix_applier.apply_fix(
            fix_proposal=fix_proposal,
            resource_kind="Deployment",
            resource_name="test-app",
            namespace="default",
        )

        # Should hit the else branch for unsupported type
        assert result.success is False


class TestGetFixApplier:
    """Test get_fix_applier singleton."""

    def test_singleton_pattern(self) -> None:
        """Test that get_fix_applier returns singleton."""
        with (
            patch("aegis.kubernetes.fix_applier.k8s_config"),
            patch("aegis.kubernetes.fix_applier.client"),
        ):
            # Reset global
            import aegis.kubernetes.fix_applier as module

            module._fix_applier = None

            applier1 = get_fix_applier()
            applier2 = get_fix_applier()

            assert applier1 is applier2
