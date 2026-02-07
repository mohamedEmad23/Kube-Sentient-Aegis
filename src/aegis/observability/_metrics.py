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

http_requests_total = Counter(
    name="http_requests_total",
    documentation="Total HTTP requests received",
    labelnames=["method", "endpoint", "status_code"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

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

shadow_smoke_tests_total = Counter(
    name="shadow_smoke_tests_total",
    documentation="Total number of shadow smoke tests executed",
    labelnames=["result", "target"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

shadow_load_tests_total = Counter(
    name="shadow_load_tests_total",
    documentation="Total number of shadow load tests executed",
    labelnames=["result", "target"],
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
    documentation="Total number of LLM requests",
    labelnames=["model", "provider", "status"],
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

operator_errors_total = Counter(
    name="operator_errors_total",
    documentation="Total number of operator errors",
    labelnames=["component", "error_type"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

operator_reconciliations_total = Counter(
    name="operator_reconciliations_total",
    documentation="Total number of operator reconciliation attempts",
    labelnames=["resource_type", "status"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

# Enhanced Incident Response Metrics

rollbacks_total = Counter(
    name="rollbacks_total",
    documentation="Total number of automatic rollbacks executed",
    labelnames=["resource_type", "namespace", "reason"],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

shadow_retries_total = Counter(
    name="shadow_retries_total",
    documentation="Total number of shadow verification retries",
    labelnames=["outcome", "attempt"],  # outcome: success/failure, attempt: 1/2/3
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

drift_detections_total = Counter(
    name="drift_detections_total",
    documentation="Total number of drift detections between prod/shadow",
    labelnames=["severity"],  # none/low/high
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

security_blocks_total = Counter(
    name="security_blocks_total",
    documentation="Total number of deployments blocked by security scans",
    labelnames=["scan_type", "severity"],  # kubesec/trivy/falco, CRITICAL/HIGH
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

production_approvals_total = Counter(
    name="production_approvals_total",
    documentation="Total number of production approval decisions",
    labelnames=["decision", "namespace"],  # yes/no/timeout
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

incident_queue_enqueued_total = Counter(
    name="incident_queue_enqueued_total",
    documentation="Total incidents enqueued",
    labelnames=["priority"],  # p0/p1/p2/p3/p4
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

incident_queue_correlated_total = Counter(
    name="incident_queue_correlated_total",
    documentation="Total incidents deduplicated via correlation",
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)


# ============================================================================
# Gauge Metrics - Values that can go up or down
# ============================================================================

system_healthy = Gauge(
    name="system_healthy",
    documentation="AEGIS system health status (1=healthy, 0=unhealthy)",
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

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

incident_queue_depth = Gauge(
    name="incident_queue_depth",
    documentation="Current incident queue depth",
    labelnames=["priority"],  # p0/p1/p2/p3/p4
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

production_locked = Gauge(
    name="production_locked",
    documentation="Production deployment lock status (1=locked, 0=unlocked)",
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)


# ============================================================================
# Histogram Metrics - Distribution of values
# ============================================================================

http_request_duration_seconds = Histogram(
    name="http_request_duration_seconds",
    documentation="HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

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

shadow_smoke_test_duration_seconds = Histogram(
    name="shadow_smoke_test_duration_seconds",
    documentation="Time taken for shadow smoke tests",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

shadow_load_test_duration_seconds = Histogram(
    name="shadow_load_test_duration_seconds",
    documentation="Time taken for shadow load tests",
    buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

llm_request_duration_seconds = Histogram(
    name="llm_request_duration_seconds",
    documentation="LLM request duration in seconds",
    labelnames=["model", "provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

rollback_duration_seconds = Histogram(
    name="rollback_duration_seconds",
    documentation="Time taken to execute rollback",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

drift_detection_duration_seconds = Histogram(
    name="drift_detection_duration_seconds",
    documentation="Time taken for drift detection",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
    namespace=settings.observability.metrics_namespace,
)

incident_queue_processing_duration_seconds = Histogram(
    name="incident_queue_processing_duration_seconds",
    documentation="Time taken to process incidents from the priority queue",
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
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
    shadow_smoke_tests_total.labels(result="passed", target="service")
    shadow_load_tests_total.labels(result="passed", target="service")
    agent_iterations_total.labels(agent_name="rca_agent", status="completed")
    llm_requests_total.labels(model="phi3:mini", provider="ollama", status="success")
    k8sgpt_analyses_total.labels(resource_type="pod", problems_found="0")
    operator_errors_total.labels(component="operator", error_type="general")
    operator_reconciliations_total.labels(resource_type="pod", status="success")

    # Initialize gauges to starting values
    system_healthy.set(1)  # Assume healthy at start
    active_incidents.labels(severity="high", namespace="default").set(0)
    shadow_environments_active.labels(runtime=settings.shadow.runtime.value).set(0)
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
    "http_request_duration_seconds",
    "http_requests_total",
    "incident_analysis_duration_seconds",
    "incident_queue_processing_duration_seconds",
    "incidents_detected_total",
    "initialize_metrics",
    "k8sgpt_analyses_total",
    "llm_request_duration_seconds",
    "llm_requests_total",
    "operator_errors_total",
    "operator_reconciliations_total",
    "registry",
    "shadow_environments_active",
    "shadow_load_test_duration_seconds",
    "shadow_load_tests_total",
    "shadow_smoke_test_duration_seconds",
    "shadow_smoke_tests_total",
    "shadow_verification_duration_seconds",
    "shadow_verifications_total",
    "system_healthy",
]
