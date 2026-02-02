"""Unit tests for AEGIS Incident CRD Models.

Tests the Pydantic models for AegisIncident custom resources,
including parsing, validation, and helper methods.
"""

from datetime import UTC, datetime

import pytest

from aegis.crd import (
    AEGIS_API_GROUP,
    AEGIS_API_VERSION,
    AEGIS_INCIDENT_KIND,
    AEGIS_INCIDENT_PLURAL,
    AegisIncident,
    Approval,
    ApprovalStatus,
    FixProposal,
    FixType,
    IncidentMetadata,
    IncidentPhase,
    IncidentSeverity,
    IncidentSource,
    IncidentSpec,
    IncidentStatus,
    RCAResult,
    ResourceRef,
    ShadowVerification,
)


class TestAegisIncidentConstants:
    """Test AEGIS incident CRD constants."""

    def test_api_group(self) -> None:
        """Test API group constant."""
        assert AEGIS_API_GROUP == "aegis.io"

    def test_api_version(self) -> None:
        """Test API version constant."""
        assert AEGIS_API_VERSION == "v1"

    def test_incident_kind(self) -> None:
        """Test incident kind constant."""
        assert AEGIS_INCIDENT_KIND == "Incident"

    def test_incident_plural(self) -> None:
        """Test incident plural constant."""
        assert AEGIS_INCIDENT_PLURAL == "incidents"


class TestResourceRef:
    """Test ResourceRef model."""

    def test_resource_ref_creation(self) -> None:
        """Test creating a resource reference."""
        ref = ResourceRef(kind="Pod", name="nginx", namespace="default")
        assert ref.kind == "Pod"
        assert ref.name == "nginx"
        assert ref.namespace == "default"

    def test_resource_ref_without_namespace(self) -> None:
        """Test resource ref without namespace (cluster-scoped)."""
        ref = ResourceRef(kind="Node", name="node-1")
        assert ref.kind == "Node"
        assert ref.name == "node-1"
        assert ref.namespace is None


class TestApproval:
    """Test Approval model."""

    def test_approval_defaults(self) -> None:
        """Test default approval values."""
        approval = Approval()
        assert approval.required is True
        assert approval.status == ApprovalStatus.PENDING
        assert approval.approved_by is None
        assert approval.rejected_by is None

    def test_approval_approved(self) -> None:
        """Test approved state."""
        approval = Approval(
            required=True,
            status=ApprovalStatus.APPROVED,
            approved_by="admin@example.com",
            approved_at=datetime.now(UTC),
        )
        assert approval.status == ApprovalStatus.APPROVED
        assert approval.approved_by == "admin@example.com"
        assert approval.approved_at is not None

    def test_approval_rejected(self) -> None:
        """Test rejected state."""
        approval = Approval(
            required=True,
            status=ApprovalStatus.REJECTED,
            rejected_by="security@example.com",
            rejection_reason="Fix too risky",
        )
        assert approval.status == ApprovalStatus.REJECTED
        assert approval.rejected_by == "security@example.com"
        assert approval.rejection_reason == "Fix too risky"


class TestRCAResult:
    """Test RCAResult model."""

    def test_rca_result_creation(self) -> None:
        """Test creating an RCA result."""
        rca = RCAResult(
            root_cause="OOMKilled due to memory leak",
            reasoning="Container exceeded memory limit",
            confidence_score=0.95,
            affected_components=["container/app", "pod/nginx"],
        )
        assert rca.root_cause == "OOMKilled due to memory leak"
        assert rca.confidence_score == 0.95
        assert len(rca.affected_components) == 2

    def test_rca_result_confidence_bounds(self) -> None:
        """Test confidence score bounds."""
        # Should work with valid bounds
        rca = RCAResult(confidence_score=0.0)
        assert rca.confidence_score == 0.0

        rca = RCAResult(confidence_score=1.0)
        assert rca.confidence_score == 1.0

        # Should fail with invalid bounds
        with pytest.raises(ValueError, match="less than or equal to 1"):
            RCAResult(confidence_score=1.5)

        with pytest.raises(ValueError, match="greater than or equal to 0"):
            RCAResult(confidence_score=-0.1)


class TestFixProposal:
    """Test FixProposal model."""

    def test_fix_proposal_restart(self) -> None:
        """Test restart fix proposal."""
        fix = FixProposal(
            fix_type=FixType.RESTART,
            description="Restart the pod to clear memory leak",
            commands=["kubectl rollout restart deployment/app"],
        )
        assert fix.fix_type == FixType.RESTART
        assert len(fix.commands) == 1

    def test_fix_proposal_with_manifests(self) -> None:
        """Test fix proposal with manifests."""
        fix = FixProposal(
            fix_type=FixType.RESOURCE_ADJUSTMENT,
            description="Increase memory limit",
            manifests={"deployment.yaml": "apiVersion: apps/v1\nkind: Deployment\n..."},
        )
        assert fix.fix_type == FixType.RESOURCE_ADJUSTMENT
        assert "deployment.yaml" in fix.manifests

    def test_fix_proposal_with_risks(self) -> None:
        """Test fix proposal with risks."""
        fix = FixProposal(
            fix_type=FixType.ROLLBACK,
            description="Rollback to previous version",
            risks=["May cause temporary service disruption", "Previous version may have bugs"],
            estimated_downtime="30s",
        )
        assert len(fix.risks) == 2
        assert fix.estimated_downtime == "30s"


class TestShadowVerification:
    """Test ShadowVerification model."""

    def test_shadow_verification_passed(self) -> None:
        """Test passed shadow verification."""
        shadow = ShadowVerification(
            shadow_id="shadow-abc123",
            passed=True,
            health_score=0.98,
            smoke_test_passed=True,
            load_test_passed=True,
        )
        assert shadow.passed is True
        assert shadow.health_score == 0.98

    def test_shadow_verification_failed(self) -> None:
        """Test failed shadow verification."""
        shadow = ShadowVerification(
            shadow_id="shadow-def456",
            passed=False,
            health_score=0.45,
            smoke_test_passed=True,
            load_test_passed=False,
        )
        assert shadow.passed is False
        assert shadow.load_test_passed is False


class TestIncidentSpec:
    """Test IncidentSpec model."""

    def test_incident_spec_creation(self) -> None:
        """Test creating incident spec."""
        spec = IncidentSpec(
            source=IncidentSource.K8SGPT,
            resource_ref=ResourceRef(kind="Pod", name="nginx", namespace="default"),
            errors=["CrashLoopBackOff"],
            severity=IncidentSeverity.HIGH,
        )
        assert spec.source == IncidentSource.K8SGPT
        assert spec.resource_ref.name == "nginx"
        assert spec.severity == IncidentSeverity.HIGH

    def test_incident_spec_with_rca(self) -> None:
        """Test incident spec with RCA result."""
        spec = IncidentSpec(
            resource_ref=ResourceRef(kind="Deployment", name="api", namespace="prod"),
            rca_result=RCAResult(
                root_cause="Image pull error",
                confidence_score=0.9,
            ),
        )
        assert spec.rca_result is not None
        assert spec.rca_result.root_cause == "Image pull error"


class TestIncidentStatus:
    """Test IncidentStatus model."""

    def test_incident_status_defaults(self) -> None:
        """Test default status values."""
        status = IncidentStatus()
        assert status.phase == IncidentPhase.DETECTED
        assert status.fix_applied is False
        assert status.fix_error is None

    def test_incident_status_resolved(self) -> None:
        """Test resolved status."""
        status = IncidentStatus(
            phase=IncidentPhase.RESOLVED,
            fix_applied=True,
            fix_applied_at=datetime.now(UTC),
            resolved_at=datetime.now(UTC),
        )
        assert status.phase == IncidentPhase.RESOLVED
        assert status.fix_applied is True


class TestAegisIncident:
    """Test AegisIncident model."""

    def test_aegis_incident_creation(self) -> None:
        """Test creating an AEGIS incident."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="inc-001", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx", namespace="default"),
            ),
        )
        assert incident.kind == AEGIS_INCIDENT_KIND
        assert incident.metadata.name == "inc-001"
        assert incident.status.phase == IncidentPhase.DETECTED

    def test_is_awaiting_approval(self) -> None:
        """Test is_awaiting_approval helper."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="inc-001", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx"),
                approval=Approval(status=ApprovalStatus.PENDING),
            ),
            status=IncidentStatus(phase=IncidentPhase.AWAITING_APPROVAL),
        )
        assert incident.is_awaiting_approval() is True

    def test_is_approved(self) -> None:
        """Test is_approved helper."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="inc-001", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx"),
                approval=Approval(status=ApprovalStatus.APPROVED),
            ),
        )
        assert incident.is_approved() is True
        assert incident.is_rejected() is False

    def test_is_rejected(self) -> None:
        """Test is_rejected helper."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="inc-001", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx"),
                approval=Approval(status=ApprovalStatus.REJECTED),
            ),
        )
        assert incident.is_rejected() is True
        assert incident.is_approved() is False

    def test_has_fix_proposal(self) -> None:
        """Test has_fix_proposal helper."""
        # Without fix proposal
        incident = AegisIncident(
            metadata=IncidentMetadata(name="inc-001", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx"),
            ),
        )
        assert incident.has_fix_proposal() is False

        # With fix proposal
        incident_with_fix = AegisIncident(
            metadata=IncidentMetadata(name="inc-002", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx"),
                fix_proposal=FixProposal(
                    fix_type=FixType.RESTART,
                    description="Restart the pod",
                ),
            ),
        )
        assert incident_with_fix.has_fix_proposal() is True

    def test_to_dict(self) -> None:
        """Test conversion to dict for Kubernetes API."""
        incident = AegisIncident(
            metadata=IncidentMetadata(name="inc-001", namespace="default"),
            spec=IncidentSpec(
                resource_ref=ResourceRef(kind="Pod", name="nginx", namespace="default"),
                severity=IncidentSeverity.HIGH,
            ),
        )
        data = incident.to_dict()

        assert data["apiVersion"] == "aegis.io/v1"
        assert data["kind"] == "Incident"
        assert data["metadata"]["name"] == "inc-001"
        assert data["spec"]["resourceRef"]["kind"] == "Pod"

    def test_from_kubernetes_object(self) -> None:
        """Test parsing from Kubernetes API response."""
        k8s_obj = {
            "apiVersion": "aegis.io/v1",
            "kind": "Incident",
            "metadata": {
                "name": "inc-test-001",
                "namespace": "production",
                "uid": "abc123",
                "creationTimestamp": "2026-01-15T10:30:00Z",
            },
            "spec": {
                "source": "k8sgpt",
                "resourceRef": {
                    "kind": "Deployment",
                    "name": "api-service",
                    "namespace": "production",
                },
                "errors": ["CrashLoopBackOff", "ImagePullBackOff"],
                "severity": "critical",
                "approval": {
                    "required": True,
                    "status": "pending",
                },
            },
            "status": {
                "phase": "Analyzing",
                "fixApplied": False,
            },
        }

        incident = AegisIncident.from_kubernetes_object(k8s_obj)

        assert incident.metadata.name == "inc-test-001"
        assert incident.metadata.namespace == "production"
        assert incident.metadata.uid == "abc123"
        assert incident.spec.source == IncidentSource.K8SGPT
        assert incident.spec.resource_ref.kind == "Deployment"
        assert incident.spec.resource_ref.name == "api-service"
        assert incident.spec.severity == IncidentSeverity.CRITICAL
        assert len(incident.spec.errors) == 2
        assert incident.status.phase == IncidentPhase.ANALYZING
        assert incident.status.fix_applied is False

    def test_from_kubernetes_object_with_rca_and_fix(self) -> None:
        """Test parsing with RCA result and fix proposal."""
        k8s_obj = {
            "apiVersion": "aegis.io/v1",
            "kind": "Incident",
            "metadata": {
                "name": "inc-full-001",
                "namespace": "default",
            },
            "spec": {
                "resourceRef": {
                    "kind": "Pod",
                    "name": "worker-pod",
                },
                "rcaResult": {
                    "rootCause": "OOMKilled due to memory leak",
                    "reasoning": "Container exceeded limits",
                    "confidenceScore": 0.92,
                    "affectedComponents": ["container/app"],
                },
                "fixProposal": {
                    "fixType": "resource_adjustment",
                    "description": "Increase memory limit",
                    "commands": ["kubectl set resources ..."],
                    "confidenceScore": 0.88,
                },
                "approval": {
                    "status": "approved",
                    "approvedBy": "admin",
                },
            },
            "status": {
                "phase": "ApplyingFix",
            },
        }

        incident = AegisIncident.from_kubernetes_object(k8s_obj)

        assert incident.spec.rca_result is not None
        assert incident.spec.rca_result.root_cause == "OOMKilled due to memory leak"
        assert incident.spec.rca_result.confidence_score == 0.92

        assert incident.spec.fix_proposal is not None
        assert incident.spec.fix_proposal.fix_type == FixType.RESOURCE_ADJUSTMENT
        assert len(incident.spec.fix_proposal.commands) == 1

        assert incident.spec.approval.status == ApprovalStatus.APPROVED
        assert incident.status.phase == IncidentPhase.APPLYING_FIX


class TestIncidentPhaseEnum:
    """Test IncidentPhase enum values."""

    def test_all_phases(self) -> None:
        """Test all phase values exist."""
        phases = [
            IncidentPhase.DETECTED,
            IncidentPhase.ANALYZING,
            IncidentPhase.AWAITING_APPROVAL,
            IncidentPhase.APPLYING_FIX,
            IncidentPhase.MONITORING,
            IncidentPhase.RESOLVED,
            IncidentPhase.FAILED,
            IncidentPhase.REJECTED,
            IncidentPhase.TIMEOUT,
        ]
        assert len(phases) == 9

    def test_phase_values(self) -> None:
        """Test phase string values."""
        assert IncidentPhase.DETECTED.value == "Detected"
        assert IncidentPhase.AWAITING_APPROVAL.value == "AwaitingApproval"
        assert IncidentPhase.APPLYING_FIX.value == "ApplyingFix"


class TestApprovalStatusEnum:
    """Test ApprovalStatus enum values."""

    def test_all_statuses(self) -> None:
        """Test all approval statuses exist."""
        statuses = [
            ApprovalStatus.PENDING,
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.TIMEOUT,
        ]
        assert len(statuses) == 4

    def test_status_values(self) -> None:
        """Test status string values."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"


class TestFixTypeEnum:
    """Test FixType enum values."""

    def test_all_fix_types(self) -> None:
        """Test all fix types exist."""
        fix_types = [
            FixType.CONFIG_CHANGE,
            FixType.SCALE,
            FixType.ROLLBACK,
            FixType.RESTART,
            FixType.RESOURCE_ADJUSTMENT,
            FixType.PATCH,
        ]
        assert len(fix_types) == 6
