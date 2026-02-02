"""Pydantic models for AEGIS Incident Custom Resource.

AEGIS Incidents track detected issues, RCA results, fix proposals,
and human-in-the-loop approval workflow.

API Group: aegis.io
API Version: v1
Kind: Incident
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# AEGIS CRD Constants
AEGIS_API_GROUP = "aegis.io"
AEGIS_API_VERSION = "v1"
AEGIS_INCIDENT_PLURAL = "incidents"
AEGIS_INCIDENT_KIND = "Incident"


class IncidentSource(str, Enum):
    """Source of incident detection."""

    K8SGPT = "k8sgpt"
    AEGIS_MONITOR = "aegis-monitor"
    MANUAL = "manual"


class IncidentSeverity(str, Enum):
    """Severity level of an incident."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ApprovalStatus(str, Enum):
    """Approval workflow status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class IncidentPhase(str, Enum):
    """Incident lifecycle phase."""

    DETECTED = "Detected"
    ANALYZING = "Analyzing"
    AWAITING_APPROVAL = "AwaitingApproval"
    APPLYING_FIX = "ApplyingFix"
    MONITORING = "Monitoring"
    RESOLVED = "Resolved"
    FAILED = "Failed"
    REJECTED = "Rejected"
    TIMEOUT = "Timeout"


class FixType(str, Enum):
    """Type of fix to apply."""

    CONFIG_CHANGE = "config_change"
    SCALE = "scale"
    ROLLBACK = "rollback"
    RESTART = "restart"
    RESOURCE_ADJUSTMENT = "resource_adjustment"
    PATCH = "patch"


class ResourceRef(BaseModel):
    """Reference to a Kubernetes resource."""

    kind: str = Field(description="Kind of the affected resource")
    name: str = Field(description="Name of the affected resource")
    namespace: str | None = Field(default=None, description="Namespace of the resource")


class RCAResult(BaseModel):
    """Root cause analysis result."""

    root_cause: str = Field(default="", alias="rootCause", description="Identified root cause")
    reasoning: str = Field(default="", description="Explanation of the analysis")
    confidence_score: float = Field(
        default=0.0,
        alias="confidenceScore",
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)",
    )
    affected_components: list[str] = Field(
        default_factory=list,
        alias="affectedComponents",
        description="List of affected components",
    )
    analysis_steps: list[str] = Field(
        default_factory=list, alias="analysisSteps", description="Steps taken during analysis"
    )

    class Config:
        populate_by_name = True


class FixProposal(BaseModel):
    """Proposed fix for an incident."""

    fix_type: FixType = Field(alias="fixType", description="Type of fix")
    description: str = Field(default="", description="Human-readable description")
    commands: list[str] = Field(
        default_factory=list, description="kubectl commands to apply the fix"
    )
    manifests: dict[str, str] = Field(
        default_factory=dict, description="YAML manifests to apply (name -> content)"
    )
    patch: str | None = Field(default=None, description="JSON patch to apply")
    confidence_score: float = Field(
        default=0.0,
        alias="confidenceScore",
        ge=0.0,
        le=1.0,
        description="Confidence score for the fix",
    )
    risks: list[str] = Field(
        default_factory=list, description="Potential risks of applying the fix"
    )
    estimated_downtime: str | None = Field(
        default=None, alias="estimatedDowntime", description="Estimated downtime"
    )

    class Config:
        populate_by_name = True


class ShadowVerification(BaseModel):
    """Shadow environment verification result."""

    shadow_id: str | None = Field(default=None, alias="shadowId")
    passed: bool | None = Field(default=None)
    health_score: float | None = Field(default=None, alias="healthScore")
    smoke_test_passed: bool | None = Field(default=None, alias="smokeTestPassed")
    load_test_passed: bool | None = Field(default=None, alias="loadTestPassed")
    logs: str | None = Field(default=None, description="Truncated verification logs")
    verified_at: datetime | None = Field(default=None, alias="verifiedAt")

    class Config:
        populate_by_name = True


class Approval(BaseModel):
    """Human-in-the-loop approval fields."""

    required: bool = Field(default=True, description="Whether human approval is required")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Approval status")
    approved_by: str | None = Field(default=None, alias="approvedBy")
    approved_at: datetime | None = Field(default=None, alias="approvedAt")
    rejected_by: str | None = Field(default=None, alias="rejectedBy")
    rejected_at: datetime | None = Field(default=None, alias="rejectedAt")
    rejection_reason: str | None = Field(default=None, alias="rejectionReason")
    timeout_at: datetime | None = Field(default=None, alias="timeoutAt")
    comment: str | None = Field(default=None, description="Approval/rejection comment")

    class Config:
        populate_by_name = True


class MonitoringStatus(BaseModel):
    """Post-fix monitoring status."""

    started_at: datetime | None = Field(default=None, alias="startedAt")
    duration: int | None = Field(default=None, description="Duration in seconds")
    new_incidents_detected: bool = Field(default=False, alias="newIncidentsDetected")
    warning_message: str | None = Field(default=None, alias="warningMessage")

    class Config:
        populate_by_name = True


class IncidentCondition(BaseModel):
    """Condition representing incident state."""

    type: str
    status: str  # "True", "False", "Unknown"
    last_transition_time: datetime | None = Field(default=None, alias="lastTransitionTime")
    reason: str | None = Field(default=None)
    message: str | None = Field(default=None)

    class Config:
        populate_by_name = True


class IncidentSpec(BaseModel):
    """Specification for AEGIS Incident CRD."""

    source: IncidentSource = Field(default=IncidentSource.K8SGPT)
    resource_ref: ResourceRef = Field(alias="resourceRef")
    errors: list[str] = Field(default_factory=list)
    k8sgpt_analysis: str | None = Field(default=None, alias="k8sgptAnalysis")
    severity: IncidentSeverity = Field(default=IncidentSeverity.MEDIUM)
    rca_result: RCAResult | None = Field(default=None, alias="rcaResult")
    fix_proposal: FixProposal | None = Field(default=None, alias="fixProposal")
    shadow_verification: ShadowVerification | None = Field(default=None, alias="shadowVerification")
    approval: Approval = Field(default_factory=Approval)

    class Config:
        populate_by_name = True


class IncidentStatus(BaseModel):
    """Status of an AEGIS Incident."""

    phase: IncidentPhase = Field(default=IncidentPhase.DETECTED)
    fix_applied: bool = Field(default=False, alias="fixApplied")
    fix_applied_at: datetime | None = Field(default=None, alias="fixAppliedAt")
    fix_error: str | None = Field(default=None, alias="fixError")
    monitoring: MonitoringStatus | None = Field(default=None)
    detected_at: datetime | None = Field(default=None, alias="detectedAt")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    conditions: list[IncidentCondition] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class IncidentMetadata(BaseModel):
    """Metadata for AEGIS Incident CRD."""

    name: str
    namespace: str = Field(default="default")
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    creation_timestamp: datetime | None = Field(default=None, alias="creationTimestamp")
    uid: str | None = Field(default=None)

    class Config:
        populate_by_name = True


class AegisIncident(BaseModel):
    """AEGIS Incident Custom Resource Definition.

    This is the main model representing an AEGIS incident with
    full RCA, fix proposal, and approval workflow.
    """

    api_version: str = Field(default=f"{AEGIS_API_GROUP}/{AEGIS_API_VERSION}", alias="apiVersion")
    kind: str = Field(default=AEGIS_INCIDENT_KIND)
    metadata: IncidentMetadata
    spec: IncidentSpec
    status: IncidentStatus = Field(default_factory=IncidentStatus)

    class Config:
        populate_by_name = True

    def is_awaiting_approval(self) -> bool:
        """Check if incident is waiting for human approval."""
        return (
            self.spec.approval.status == ApprovalStatus.PENDING
            and self.status.phase == IncidentPhase.AWAITING_APPROVAL
        )

    def is_approved(self) -> bool:
        """Check if incident has been approved."""
        return self.spec.approval.status == ApprovalStatus.APPROVED

    def is_rejected(self) -> bool:
        """Check if incident has been rejected."""
        return self.spec.approval.status == ApprovalStatus.REJECTED

    def has_fix_proposal(self) -> bool:
        """Check if incident has a fix proposal."""
        return self.spec.fix_proposal is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Kubernetes API dict format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_kubernetes_object(cls, obj: dict[str, Any]) -> "AegisIncident":
        """Create AegisIncident from raw Kubernetes API response."""
        metadata_dict = obj.get("metadata", {})
        metadata = IncidentMetadata(
            name=metadata_dict.get("name", ""),
            namespace=metadata_dict.get("namespace", "default"),
            labels=metadata_dict.get("labels", {}),
            annotations=metadata_dict.get("annotations", {}),
            uid=metadata_dict.get("uid"),
        )
        if "creationTimestamp" in metadata_dict:
            metadata.creation_timestamp = metadata_dict["creationTimestamp"]

        spec_data = obj.get("spec", {})
        resource_ref_data = spec_data.get("resourceRef", {})

        spec = IncidentSpec(
            source=spec_data.get("source", "k8sgpt"),
            resource_ref=ResourceRef(
                kind=resource_ref_data.get("kind", ""),
                name=resource_ref_data.get("name", ""),
                namespace=resource_ref_data.get("namespace"),
            ),
            errors=spec_data.get("errors", []),
            k8sgpt_analysis=spec_data.get("k8sgptAnalysis"),
            severity=spec_data.get("severity", "medium"),
        )

        # Parse RCA result if present
        if "rcaResult" in spec_data:
            spec.rca_result = RCAResult(**spec_data["rcaResult"])

        # Parse fix proposal if present
        if "fixProposal" in spec_data:
            spec.fix_proposal = FixProposal(**spec_data["fixProposal"])

        # Parse shadow verification if present
        if "shadowVerification" in spec_data:
            spec.shadow_verification = ShadowVerification(**spec_data["shadowVerification"])

        # Parse approval if present
        if "approval" in spec_data:
            spec.approval = Approval(**spec_data["approval"])

        # Parse status
        status_data = obj.get("status", {})
        status = IncidentStatus(
            phase=status_data.get("phase", "Detected"),
            fix_applied=status_data.get("fixApplied", False),
        )
        if "fixAppliedAt" in status_data:
            status.fix_applied_at = status_data["fixAppliedAt"]
        if "fixError" in status_data:
            status.fix_error = status_data["fixError"]
        if "monitoring" in status_data:
            status.monitoring = MonitoringStatus(**status_data["monitoring"])

        return cls(
            kind=obj.get("kind", AEGIS_INCIDENT_KIND),
            metadata=metadata,
            spec=spec,
            status=status,
        )


__all__ = [
    "AEGIS_API_GROUP",
    "AEGIS_API_VERSION",
    "AEGIS_INCIDENT_KIND",
    "AEGIS_INCIDENT_PLURAL",
    "AegisIncident",
    "Approval",
    "ApprovalStatus",
    "FixProposal",
    "FixType",
    "IncidentCondition",
    "IncidentMetadata",
    "IncidentPhase",
    "IncidentSeverity",
    "IncidentSource",
    "IncidentSpec",
    "IncidentStatus",
    "MonitoringStatus",
    "RCAResult",
    "ResourceRef",
    "ShadowVerification",
]
