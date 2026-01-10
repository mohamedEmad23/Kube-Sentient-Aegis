"""AEGIS Prometheus metrics for observability.

Provides production-ready metrics tracking using Prometheus client:
- Counter metrics for incidents, fixes, and verifications
- Gauge metrics for active operations
- Histogram metrics for operation durations
- Automatic metric initialization
"""

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

from aegis.config.settings import settings


# Create custom registry if needed, otherwise use default
registry = REGISTRY if settings.observability.prometheus_enabled else CollectorRegistry()


# ============================================================================
# Counter Metrics - Monotonically increasing values
# ============================================================================

incidents_detected_total = Counter(
    name="incidents_detected_total",
    documentation="Total number of incidents detected by AEGIS",
    labelnames=["severity", "resource_type", "namespace"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

fixes_applied_total = Counter(
    name="fixes_applied_total",
    documentation="Total number of fixes applied to production",
    labelnames=["fix_type", "namespace", "success"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

shadow_verifications_total = Counter(
    name="shadow_verifications_total",
    documentation="Total number of shadow environment verifications",
    labelnames=["result", "fix_type"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

agent_iterations_total = Counter(
    name="agent_iterations_total",
    documentation="Total number of LangGraph agent workflow iterations",
    labelnames=["agent_name", "status"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

llm_requests_total = Counter(
    name="llm_requests_total",
    documentation="Total number of LLM requests to Ollama",
    labelnames=["model", "status"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

k8sgpt_analyses_total = Counter(
    name="k8sgpt_analyses_total",
    documentation="Total number of K8sGPT analysis runs",
    labelnames=["resource_type", "problems_found"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)


# ============================================================================
# Gauge Metrics - Values that can go up or down
# ============================================================================

active_incidents = Gauge(
    name="active_incidents",
    documentation="Number of currently active incidents",
    labelnames=["severity", "namespace"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

shadow_environments_active = Gauge(
    name="shadow_environments_active",
    documentation="Number of active shadow verification environments",
    labelnames=["runtime"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

agent_workflow_in_progress = Gauge(
    name="agent_workflow_in_progress",
    documentation="Number of agent workflows currently in progress",
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)


# ============================================================================
# Histogram Metrics - Distribution of values
# ============================================================================

incident_analysis_duration_seconds = Histogram(
    name="incident_analysis_duration_seconds",
    documentation="Time taken to analyze incidents",
    labelnames=["agent_name"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

fix_application_duration_seconds = Histogram(
    name="fix_application_duration_seconds",
    documentation="Time taken to apply fixes",
    labelnames=["fix_type"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

shadow_verification_duration_seconds = Histogram(
    name="shadow_verification_duration_seconds",
    documentation="Time taken for shadow verification",
    buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

llm_request_duration_seconds = Histogram(
    name="llm_request_duration_seconds",
    documentation="LLM request duration in seconds",
    labelnames=["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)


# ============================================================================
# Initialization Functions
# ============================================================================


def initialize_metrics() -> None:
    """Initialize all metrics with default values.

    This ensures metrics exist in Prometheus even if no events have occurred yet.
    """
    # Initialize counters with zero values
    incidents_detected_total.labels(severity="high", resource_type="pod", namespace="default")
    fixes_applied_total.labels(fix_type="restart", namespace="default", success="true")
    shadow_verifications_total.labels(result="passed", fix_type="config_change")
    agent_iterations_total.labels(agent_name="rca_agent", status="completed")
    llm_requests_total.labels(model="phi3:mini", status="success")
    k8sgpt_analyses_total.labels(resource_type="pod", problems_found="0")

    # Initialize gauges to zero
    active_incidents.labels(severity="high", namespace="default").set(0)
    shadow_environments_active.labels(runtime="vcluster").set(0)
    agent_workflow_in_progress.set(0)


# Auto-initialize metrics on module import
if settings.observability.prometheus_enabled:
    initialize_metrics()


__all__ = [
    "active_incidents",
    "agent_iterations_total",
    "agent_workflow_in_progress",
    "fix_application_duration_seconds",
    "fixes_applied_total",
    "incident_analysis_duration_seconds",
    "incidents_detected_total",
    "initialize_metrics",
    "k8sgpt_analyses_total",
    "llm_request_duration_seconds",
    "llm_requests_total",
    "registry",
    "shadow_environments_active",
    "shadow_verification_duration_seconds",
    "shadow_verifications_total",
]
