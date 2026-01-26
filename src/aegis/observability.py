"""
AEGIS Observability Module - Structured Logging + Prometheus Metrics
=====================================================================

Drop-in replacement for your current logging. Production-ready with:
- JSON structured logs for Loki ingestion
- Prometheus metrics with histogram/counter/gauge support
- Contextual logging with trace IDs
- Zero configuration needed - works out of the box

Usage:
    from aegis.observability import get_logger, metrics

    logger = get_logger(__name__)
    logger.info("event", user_id=123, action="deploy")

    with metrics.track_duration("incident_analysis"):
        # Your code here
        pass
"""

import logging
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime

import structlog
from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


# ==================== STRUCTURED LOGGING ====================


def add_timestamp(_logger, _method_name, event_dict):
    """Add ISO8601 timestamp to all log entries."""
    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def add_log_level(_logger, method_name, event_dict):
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def add_logger_name(logger, _method_name, event_dict):
    """Add logger name to event dict."""
    if logger:
        event_dict["logger"] = logger.name
    return event_dict


def setup_logging(level: str = "INFO", json_logs: bool = True, dev_mode: bool = False) -> None:
    """
    Configure structured logging for AEGIS application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON for Loki. If False, pretty print for dev
        dev_mode: If True, use colored console output

    Example:
        # In your main.py or __init__.py
        from aegis.observability import setup_logging
        setup_logging(level="INFO", json_logs=True)
    """
    processors = [
        structlog.stdlib.filter_by_level,
        add_log_level,
        add_logger_name,
        add_timestamp,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs and not dev_mode:
        # Production: JSON logs for Loki
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Pretty colored output
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging as well
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger

    Example:
        logger = get_logger(__name__)
        logger.info("incident_detected",
                    incident_id="inc-123",
                    severity="critical",
                    namespace="production")
    """
    return structlog.get_logger(name)


# ==================== PROMETHEUS METRICS ====================


class AEGISMetrics:
    """
    Centralized Prometheus metrics for AEGIS application.

    All metrics follow naming conventions:
    - aegis_<component>_<metric>_<unit>
    - Labels for high-cardinality dimensions (namespace, pod, etc.)
    """

    def __init__(self, registry: CollectorRegistry | None = None):
        """Initialize metrics with optional custom registry."""
        self.registry = registry or REGISTRY

        # ============ HTTP/API Metrics ============
        self.http_requests_total = Counter(
            "aegis_http_requests_total",
            "Total HTTP requests received",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "aegis_http_request_duration_seconds",
            "HTTP request latency in seconds",
            ["method", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # ============ Incident Detection Metrics ============
        self.incidents_detected_total = Counter(
            "aegis_incidents_detected_total",
            "Total incidents detected by AEGIS",
            ["severity", "namespace", "incident_type"],
            registry=self.registry,
        )

        self.incidents_resolved_total = Counter(
            "aegis_incidents_resolved_total",
            "Total incidents successfully resolved",
            ["severity", "namespace", "resolution_type"],
            registry=self.registry,
        )

        self.incident_resolution_duration_seconds = Histogram(
            "aegis_incident_resolution_duration_seconds",
            "Time taken to resolve incidents in seconds",
            ["severity", "incident_type"],
            buckets=(10, 30, 60, 120, 300, 600, 1800, 3600),
            registry=self.registry,
        )

        # ============ LLM Inference Metrics ============
        self.llm_requests_total = Counter(
            "aegis_llm_requests_total",
            "Total LLM inference requests",
            ["model", "provider", "status"],
            registry=self.registry,
        )

        self.llm_inference_duration_seconds = Histogram(
            "aegis_llm_inference_duration_seconds",
            "LLM inference latency in seconds",
            ["model", "provider"],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry,
        )

        self.llm_tokens_processed_total = Counter(
            "aegis_llm_tokens_processed_total",
            "Total tokens processed by LLM",
            ["model", "token_type"],
            registry=self.registry,
        )

        # ============ Shadow Verification Metrics ============
        self.shadow_clusters_active = Gauge(
            "aegis_shadow_clusters_active",
            "Number of active shadow verification clusters",
            registry=self.registry,
        )

        self.shadow_verification_duration_seconds = Histogram(
            "aegis_shadow_verification_duration_seconds",
            "Shadow verification test duration in seconds",
            ["result"],
            buckets=(30, 60, 120, 300, 600),
            registry=self.registry,
        )

        self.shadow_tests_total = Counter(
            "aegis_shadow_tests_total",
            "Total shadow verification tests executed",
            ["result", "test_type"],
            registry=self.registry,
        )

        # ============ Kubernetes Operator Metrics ============
        self.operator_reconciliations_total = Counter(
            "aegis_operator_reconciliations_total",
            "Total Kopf operator reconciliations",
            ["resource_type", "namespace", "status"],
            registry=self.registry,
        )

        self.operator_errors_total = Counter(
            "aegis_operator_errors_total",
            "Total operator errors",
            ["error_type", "component"],
            registry=self.registry,
        )

        # ============ System Health Metrics ============
        self.system_healthy = Gauge(
            "aegis_system_healthy",
            "AEGIS system health status (1=healthy, 0=unhealthy)",
            registry=self.registry,
        )

        self.active_connections = Gauge(
            "aegis_active_connections",
            "Number of active connections",
            ["connection_type"],
            registry=self.registry,
        )

        # Initialize system as healthy
        self.system_healthy.set(1)

    @contextmanager
    def track_duration(self, operation: str, **labels):
        """
        Context manager to track operation duration.

        Args:
            operation: Operation name (incident_analysis, llm_inference, etc.)
            **labels: Additional labels for the metric

        Example:
            with metrics.track_duration("incident_analysis", severity="critical"):
                analyze_incident()
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time

            # Record to appropriate histogram based on operation
            if operation == "llm_inference" and "model" in labels:
                self.llm_inference_duration_seconds.labels(
                    model=labels.get("model", "unknown"),
                    provider=labels.get("provider", "ollama"),
                ).observe(duration)

            elif operation == "incident_resolution" and "severity" in labels:
                self.incident_resolution_duration_seconds.labels(
                    severity=labels.get("severity", "unknown"),
                    incident_type=labels.get("incident_type", "unknown"),
                ).observe(duration)

            elif operation == "shadow_verification":
                self.shadow_verification_duration_seconds.labels(
                    result=labels.get("result", "unknown"),
                ).observe(duration)

    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus text format.

        Returns:
            Metrics in Prometheus exposition format

        Example:
            # In your Flask/FastAPI app:
            @app.get("/metrics")
            def metrics_endpoint():
                return Response(
                    metrics.export_metrics(),
                    media_type="text/plain; charset=utf-8"
                )
        """
        return generate_latest(self.registry)


# ==================== GLOBAL INSTANCES ====================

# Global metrics instance - import this in your application
metrics = AEGISMetrics()


# ==================== DECORATOR HELPERS ====================


def track_llm_request(model: str, provider: str = "ollama"):
    """
    Decorator to track LLM request metrics.

    Example:
        @track_llm_request(model="llama3.1:8b", provider="ollama")
        def call_llm(prompt: str) -> str:
            return ollama.generate(prompt)
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                return func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time

                metrics.llm_requests_total.labels(
                    model=model,
                    provider=provider,
                    status=status,
                ).inc()

                metrics.llm_inference_duration_seconds.labels(
                    model=model,
                    provider=provider,
                ).observe(duration)

        return wrapper

    return decorator


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Setup logging
    setup_logging(level="INFO", json_logs=False, dev_mode=True)

    logger = get_logger(__name__)

    # Example structured logs
    logger.info("aegis_started", version="1.0.0", environment="production")

    logger.info(
        "incident_detected",
        incident_id="inc-123",
        severity="critical",
        namespace="production",
        pod="web-server-abc",
        error_count=5,
    )

    # Example metrics tracking
    metrics.incidents_detected_total.labels(
        severity="critical",
        namespace="production",
        incident_type="pod_crash",
    ).inc()

    # Track operation duration
    with metrics.track_duration(
        "incident_resolution", severity="critical", incident_type="pod_crash"
    ):
        time.sleep(2)  # Simulate work
        logger.info("incident_resolved", incident_id="inc-123")

    metrics.incidents_resolved_total.labels(
        severity="critical",
        namespace="production",
        resolution_type="automated",
    ).inc()

    # Export metrics
    logger.info(
        "metrics_export",
        metrics=metrics.export_metrics().decode(),
    )
