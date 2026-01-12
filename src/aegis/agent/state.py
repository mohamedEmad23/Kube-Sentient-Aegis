"""LangGraph state schemas for AEGIS agent workflow.

Defines typed state structures for the multi-agent incident analysis workflow:
- IncidentState: Main workflow state passed between agents
- K8sGPTAnalysis: Structured K8sGPT output
- RCAResult: Root Cause Analysis output
- FixProposal: Solution generation output
- VerificationPlan: Shadow verification planning output
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ============================================================================
# Enums - Agent States & Severities
# ============================================================================


class AgentNode(str, Enum):
    """Agent nodes in the LangGraph workflow."""

    RCA = "rca_agent"
    SOLUTION = "solution_agent"
    VERIFIER = "verifier_agent"
    END = "END"


class IncidentSeverity(str, Enum):
    """Incident severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FixType(str, Enum):
    """Types of fixes that can be applied."""

    CONFIG_CHANGE = "config_change"
    RESTART = "restart"
    SCALE = "scale"
    ROLLBACK = "rollback"
    PATCH = "patch"
    MANUAL = "manual"


# ============================================================================
# Pydantic Models - Structured Agent Outputs
# ============================================================================


class K8sGPTError(BaseModel):
    """Single error from K8sGPT analysis."""

    text: str = Field(description="Error description")
    kubernetes_doc: str | None = Field(
        default=None,
        description="Link to Kubernetes documentation",
    )
    sensitive: list[dict[str, str]] | None = Field(
        default=None,
        description="Sensitive data detected (anonymized)",
    )


class K8sGPTResult(BaseModel):
    """Result for a single Kubernetes resource from K8sGPT."""

    kind: str = Field(description="Resource type (Pod, Deployment, etc.)")
    name: str = Field(description="Resource name")
    namespace: str | None = Field(default=None, description="Resource namespace")
    error: list[K8sGPTError] = Field(description="List of errors detected")
    parent_object: str | None = Field(default=None, description="Parent resource if applicable")


class K8sGPTAnalysis(BaseModel):
    """Complete K8sGPT analysis output."""

    status: str = Field(description="Analysis status (OK, Error)")
    problems: int = Field(description="Number of problems detected")
    results: list[K8sGPTResult] = Field(description="Analysis results per resource")
    errors: list[str] | None = Field(default=None, description="Analysis errors")


class RCAResult(BaseModel):
    """Root Cause Analysis output from RCA agent."""

    root_cause: str = Field(description="Primary root cause identified")
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Additional factors contributing to the incident",
    )
    severity: IncidentSeverity = Field(description="Assessed incident severity")
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the analysis (0.0-1.0)",
    )
    reasoning: str = Field(description="Detailed reasoning for the analysis")
    affected_components: list[str] = Field(
        default_factory=list,
        description="List of affected system components",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FixProposal(BaseModel):
    """Solution proposal from Solution agent."""

    fix_type: FixType = Field(description="Type of fix proposed")
    description: str = Field(description="Human-readable fix description")
    commands: list[str] = Field(
        default_factory=list,
        description="kubectl commands to execute",
    )
    manifests: dict[str, str] = Field(
        default_factory=dict,
        description="YAML manifests to apply (filename: content)",
    )
    rollback_commands: list[str] = Field(
        default_factory=list,
        description="Commands to rollback if fix fails",
    )
    estimated_downtime: str | None = Field(
        default=None,
        description="Estimated downtime (e.g., '5 minutes', 'zero-downtime')",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Potential risks of applying this fix",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Prerequisites before applying fix",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the proposed solution",
    )


class VerificationPlan(BaseModel):
    """Verification plan from Verifier agent."""

    verification_type: Literal["shadow", "canary", "blue-green", "manual"] = Field(
        description="Type of verification to perform"
    )
    test_scenarios: list[str] = Field(
        description="Test scenarios to execute in shadow environment",
    )
    success_criteria: list[str] = Field(
        description="Criteria for successful verification",
    )
    duration: int = Field(
        ge=60,
        description="Expected verification duration in seconds",
    )
    load_test_config: dict[str, Any] | None = Field(
        default=None,
        description="Locust load test configuration",
    )
    security_checks: list[str] = Field(
        default_factory=list,
        description="Security checks to perform (Trivy, ZAP)",
    )
    rollback_on_failure: bool = Field(
        default=True,
        description="Automatically rollback if verification fails",
    )
    approval_required: bool = Field(
        default=False,
        description="Require human approval before production",
    )


# ============================================================================
# TypedDict - LangGraph State
# ============================================================================


class IncidentState(TypedDict):
    """Shared state across all agents in the LangGraph workflow.

    This state is passed between agents and updated via Command objects.
    Uses Annotated for automatic message aggregation via add_messages reducer.
    """

    # ========== Input Context ==========
    resource_type: str  # Pod, Deployment, Service, etc.
    resource_name: str  # Name of the resource
    namespace: str  # Kubernetes namespace

    # ========== K8sGPT Analysis ==========
    k8sgpt_raw: dict[str, Any] | None  # Raw K8sGPT JSON output
    k8sgpt_analysis: K8sGPTAnalysis | None  # Parsed K8sGPT analysis

    # ========== Kubernetes Context ==========
    kubectl_logs: str | None  # Pod logs from kubectl
    kubectl_describe: str | None  # kubectl describe output
    kubectl_events: str | None  # Recent events for the resource

    # ========== Agent Outputs ==========
    rca_result: RCAResult | None  # Root Cause Analysis
    fix_proposal: FixProposal | None  # Proposed solution
    verification_plan: VerificationPlan | None  # Verification strategy

    # ========== Workflow State ==========
    current_agent: AgentNode  # Current agent in workflow
    error: str | None  # Error message if workflow fails
    completed_at: datetime | None  # Workflow completion timestamp

    # ========== Agent Communication ==========
    # Messages aggregated across agents using add_messages reducer
    messages: Annotated[list[AnyMessage], add_messages]

    # ========== Optional: Shadow Verification Results ==========
    shadow_env_id: str | None  # Shadow environment identifier
    shadow_test_passed: bool | None  # Shadow verification result
    shadow_logs: str | None  # Shadow environment logs


# ============================================================================
# Helper Functions
# ============================================================================


def create_initial_state(
    resource_type: str,
    resource_name: str,
    namespace: str = "default",
) -> IncidentState:
    """Create initial incident state for workflow.

    Args:
        resource_type: Type of Kubernetes resource (Pod, Deployment, etc.)
        resource_name: Name of the resource
        namespace: Kubernetes namespace (default: "default")

    Returns:
        IncidentState: Initial state with basic context

    Example:
        >>> state = create_initial_state("Pod", "nginx-crashloop")
        >>> graph.invoke(state, config={"thread_id": "inc-001"})
    """
    return IncidentState(
        resource_type=resource_type,
        resource_name=resource_name,
        namespace=namespace,
        k8sgpt_raw=None,
        k8sgpt_analysis=None,
        kubectl_logs=None,
        kubectl_describe=None,
        kubectl_events=None,
        rca_result=None,
        fix_proposal=None,
        verification_plan=None,
        current_agent=AgentNode.RCA,
        error=None,
        completed_at=None,
        messages=[],
        shadow_env_id=None,
        shadow_test_passed=None,
        shadow_logs=None,
    )


__all__ = [
    "AgentNode",
    "FixProposal",
    "FixType",
    "IncidentSeverity",
    "IncidentState",
    "K8sGPTAnalysis",
    "K8sGPTError",
    "K8sGPTResult",
    "RCAResult",
    "VerificationPlan",
    "create_initial_state",
]
