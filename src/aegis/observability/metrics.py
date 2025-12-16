"""Prometheus metrics for AEGIS.

Exposes metrics for monitoring the operator's health and performance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

if TYPE_CHECKING:
    from prometheus_client.metrics import MetricWrapperBase


class MetricsCollector:
    """Prometheus metrics collector for AEGIS.

    Provides metrics for:
    - Incident detection and processing
    - LLM inference latency and errors
    - Shadow mode verification
    - Kubernetes API interactions
    """

    def __init__(self, namespace: str = "aegis") -> None:
        """Initialize metrics.

        Args:
            namespace: Prometheus namespace prefix for all metrics.
        """
        self.namespace = namespace

        # Info metric for version
        self.info = Info(
            f"{namespace}_build",
            "AEGIS build information",
        )

        # Incident metrics
        self.incidents_total = Counter(
            f"{namespace}_incidents_total",
            "Total number of incidents detected",
            ["severity", "type", "namespace"],
        )

        self.incidents_in_progress = Gauge(
            f"{namespace}_incidents_in_progress",
            "Number of incidents currently being processed",
            ["namespace"],
        )

        self.incident_processing_duration = Histogram(
            f"{namespace}_incident_processing_duration_seconds",
            "Time spent processing an incident",
            ["type", "outcome"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
        )

        # LLM metrics
        self.llm_requests_total = Counter(
            f"{namespace}_llm_requests_total",
            "Total LLM requests made",
            ["provider", "model", "status"],
        )

        self.llm_latency = Histogram(
            f"{namespace}_llm_latency_seconds",
            "LLM request latency",
            ["provider", "model"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )

        self.llm_tokens_total = Counter(
            f"{namespace}_llm_tokens_total",
            "Total tokens processed by LLM",
            ["provider", "model", "direction"],  # direction: input/output
        )

        # Shadow mode metrics
        self.shadow_verifications_total = Counter(
            f"{namespace}_shadow_verifications_total",
            "Total shadow mode verifications",
            ["outcome"],  # approved, rejected, pending
        )

        self.shadow_action_proposals = Counter(
            f"{namespace}_shadow_action_proposals_total",
            "Total remediation actions proposed in shadow mode",
            ["action_type"],
        )

        # Kubernetes API metrics
        self.k8s_api_requests_total = Counter(
            f"{namespace}_kubernetes_api_requests_total",
            "Total Kubernetes API requests",
            ["method", "resource", "status"],
        )

        self.k8s_api_latency = Histogram(
            f"{namespace}_kubernetes_api_latency_seconds",
            "Kubernetes API request latency",
            ["method", "resource"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
        )

        # Agent metrics
        self.agent_steps_total = Counter(
            f"{namespace}_agent_steps_total",
            "Total agent reasoning steps",
            ["agent_type", "step_type"],
        )

        self.agent_tool_calls_total = Counter(
            f"{namespace}_agent_tool_calls_total",
            "Total agent tool invocations",
            ["tool_name", "status"],
        )

    def set_build_info(
        self,
        version: str,
        commit: str = "unknown",
        build_date: str = "unknown",
    ) -> None:
        """Set build information metrics.

        Args:
            version: Application version.
            commit: Git commit hash.
            build_date: Build date.
        """
        self.info.info(
            {
                "version": version,
                "commit": commit,
                "build_date": build_date,
            }
        )

    def record_incident(
        self,
        severity: str,
        incident_type: str,
        namespace: str,
    ) -> None:
        """Record a detected incident.

        Args:
            severity: Incident severity (low, medium, high, critical).
            incident_type: Type of incident (crash_loop, oom, etc.).
            namespace: Kubernetes namespace where incident occurred.
        """
        self.incidents_total.labels(
            severity=severity,
            type=incident_type,
            namespace=namespace,
        ).inc()

    def record_llm_request(
        self,
        provider: str,
        model: str,
        status: str,
        latency_seconds: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record an LLM request.

        Args:
            provider: LLM provider name.
            model: Model name.
            status: Request status (success, error, timeout).
            latency_seconds: Request latency.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
        """
        self.llm_requests_total.labels(
            provider=provider,
            model=model,
            status=status,
        ).inc()

        self.llm_latency.labels(
            provider=provider,
            model=model,
        ).observe(latency_seconds)

        if input_tokens:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                direction="input",
            ).inc(input_tokens)

        if output_tokens:
            self.llm_tokens_total.labels(
                provider=provider,
                model=model,
                direction="output",
            ).inc(output_tokens)


# Global metrics instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector.

    Returns:
        The global MetricsCollector instance.
    """
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def start_metrics_server(port: int = 8080) -> None:
    """Start the Prometheus metrics HTTP server.

    Args:
        port: Port to serve metrics on.
    """
    start_http_server(port)
