"""Prometheus query client for RCA agent enrichment.

Provides async API for querying Prometheus metrics to enrich Root Cause Analysis:
- CPU/memory usage for pods and containers
- Restart counts and availability metrics
- Custom application metrics

This module queries FROM Prometheus (unlike _metrics.py which exports TO Prometheus).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)


@dataclass
class PrometheusMetrics:
    """Structured metrics result for RCA enrichment."""

    cpu_usage_cores: float | None = None
    memory_usage_bytes: int | None = None
    memory_limit_bytes: int | None = None
    memory_utilization_pct: float | None = None
    restart_count: int | None = None
    pod_phase: str | None = None
    container_ready: bool | None = None
    request_rate_per_sec: float | None = None
    error_rate_pct: float | None = None
    latency_p99_ms: float | None = None
    query_timestamp: datetime | None = None
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for state storage."""
        return {
            "cpu_usage_cores": self.cpu_usage_cores,
            "memory_usage_bytes": self.memory_usage_bytes,
            "memory_limit_bytes": self.memory_limit_bytes,
            "memory_utilization_pct": self.memory_utilization_pct,
            "restart_count": self.restart_count,
            "pod_phase": self.pod_phase,
            "container_ready": self.container_ready,
            "request_rate_per_sec": self.request_rate_per_sec,
            "error_rate_pct": self.error_rate_pct,
            "latency_p99_ms": self.latency_p99_ms,
            "query_timestamp": self.query_timestamp.isoformat() if self.query_timestamp else None,
            "errors": self.errors,
        }

    def to_summary_text(self) -> str:
        """Generate human-readable summary for LLM context."""
        lines = ["Prometheus Metrics Summary:"]

        if self.cpu_usage_cores is not None:
            lines.append(f"  • CPU Usage: {self.cpu_usage_cores:.3f} cores")

        if self.memory_usage_bytes is not None:
            mem_mb = self.memory_usage_bytes / (1024 * 1024)
            lines.append(f"  • Memory Usage: {mem_mb:.1f} MB")
            if self.memory_utilization_pct is not None:
                lines.append(f"  • Memory Utilization: {self.memory_utilization_pct:.1f}%")

        if self.restart_count is not None:
            lines.append(f"  • Restart Count: {self.restart_count}")
            if self.restart_count > 3:
                lines.append("    ⚠️ HIGH RESTART COUNT - indicates instability")

        if self.pod_phase is not None:
            lines.append(f"  • Pod Phase: {self.pod_phase}")

        if self.container_ready is not None:
            ready_str = "Ready" if self.container_ready else "NOT Ready"
            lines.append(f"  • Container Status: {ready_str}")

        if self.request_rate_per_sec is not None:
            lines.append(f"  • Request Rate: {self.request_rate_per_sec:.2f} req/s")

        if self.error_rate_pct is not None:
            lines.append(f"  • Error Rate: {self.error_rate_pct:.2f}%")
            if self.error_rate_pct > 5.0:
                lines.append("    ⚠️ HIGH ERROR RATE - check application logs")

        if self.latency_p99_ms is not None:
            lines.append(f"  • P99 Latency: {self.latency_p99_ms:.1f} ms")

        if self.errors:
            lines.append("  • Query Errors:")
            for err in self.errors[:3]:
                lines.append(f"    - {err}")

        return "\n".join(lines) if len(lines) > 1 else "No Prometheus metrics available"


class PrometheusClient:
    """Async client for querying Prometheus metrics."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        """Initialize Prometheus client.

        Args:
            base_url: Prometheus server URL (default from settings)
            timeout: Query timeout in seconds (default from settings)
        """
        self.base_url = (base_url or settings.observability.prometheus_url).rstrip("/")
        self.timeout = timeout or settings.observability.prometheus_query_timeout

    async def query(self, promql: str) -> dict[str, Any]:
        """Execute an instant PromQL query.

        Args:
            promql: PromQL query string

        Returns:
            Raw Prometheus API response

        Raises:
            httpx.HTTPError: On HTTP errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/query",
                params={"query": promql},
            )
            resp.raise_for_status()
            return resp.json()

    async def query_range(
        self,
        promql: str,
        start: datetime | None = None,
        end: datetime | None = None,
        step: str = "1m",
    ) -> dict[str, Any]:
        """Execute a range PromQL query.

        Args:
            promql: PromQL query string
            start: Start time (default: 15 minutes ago)
            end: End time (default: now)
            step: Query step (default: 1m)

        Returns:
            Raw Prometheus API response
        """
        end = end or datetime.now(UTC)
        start = start or (end - timedelta(minutes=15))

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": promql,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "step": step,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def _extract_scalar(self, result: dict[str, Any]) -> float | None:
        """Extract single scalar value from Prometheus result."""
        try:
            data = result.get("data", {})
            results = data.get("result", [])
            if not results:
                return None
            # Get the most recent value
            value = results[0].get("value", [])
            if len(value) >= 2:
                return float(value[1])
        except (KeyError, IndexError, ValueError, TypeError):
            pass
        return None

    def _extract_string(self, result: dict[str, Any]) -> str | None:
        """Extract string value from Prometheus result."""
        try:
            data = result.get("data", {})
            results = data.get("result", [])
            if not results:
                return None
            metric = results[0].get("metric", {})
            # Common label names
            for key in ("phase", "status", "state"):
                if key in metric:
                    return str(metric[key])
            value = results[0].get("value", [])
            if len(value) >= 2:
                return str(value[1])
        except (KeyError, IndexError, TypeError):
            pass
        return None

    async def get_pod_metrics(
        self,
        namespace: str,
        pod_name: str,
        container: str | None = None,
    ) -> PrometheusMetrics:
        """Get comprehensive metrics for a pod.

        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name (can be partial - uses regex match)
            container: Optional container name filter

        Returns:
            PrometheusMetrics: Structured metrics data
        """
        metrics = PrometheusMetrics(query_timestamp=datetime.now(UTC), errors=[])

        # Build pod selector - support both exact and prefix matching
        pod_selector = f'pod=~"{pod_name}.*"' if not pod_name.endswith("$") else f'pod="{pod_name}"'
        container_selector = f', container="{container}"' if container else ""
        ns_filter = f'namespace="{namespace}"'

        queries = {
            "cpu": f"sum(rate(container_cpu_usage_seconds_total{{{ns_filter}, {pod_selector}{container_selector}}}[5m]))",
            "memory": f"sum(container_memory_usage_bytes{{{ns_filter}, {pod_selector}{container_selector}}})",
            "memory_limit": f"sum(container_spec_memory_limit_bytes{{{ns_filter}, {pod_selector}{container_selector}}})",
            "restarts": f"sum(kube_pod_container_status_restarts_total{{{ns_filter}, {pod_selector}}})",
            "ready": f"min(kube_pod_container_status_ready{{{ns_filter}, {pod_selector}}})",
            "phase": f'kube_pod_status_phase{{{ns_filter}, pod=~"{pod_name}.*", phase!=""}}',
        }

        for name, promql in queries.items():
            try:
                result = await self.query(promql)

                if name == "cpu":
                    metrics.cpu_usage_cores = self._extract_scalar(result)
                elif name == "memory":
                    metrics.memory_usage_bytes = int(self._extract_scalar(result) or 0) or None
                elif name == "memory_limit":
                    limit = self._extract_scalar(result)
                    if limit and limit > 0:
                        metrics.memory_limit_bytes = int(limit)
                elif name == "restarts":
                    restarts = self._extract_scalar(result)
                    if restarts is not None:
                        metrics.restart_count = int(restarts)
                elif name == "ready":
                    ready_val = self._extract_scalar(result)
                    metrics.container_ready = ready_val == 1.0 if ready_val is not None else None
                elif name == "phase":
                    phase = self._extract_string(result)
                    if phase:
                        metrics.pod_phase = phase

            except httpx.HTTPError as e:
                log.debug("prometheus_query_failed", query=name, error=str(e))
                if metrics.errors is not None:
                    metrics.errors.append(f"{name}: {e}")
            except Exception as e:
                log.debug("prometheus_query_error", query=name, error=str(e))
                if metrics.errors is not None:
                    metrics.errors.append(f"{name}: {e}")

        # Calculate memory utilization
        if metrics.memory_usage_bytes and metrics.memory_limit_bytes:
            metrics.memory_utilization_pct = (
                metrics.memory_usage_bytes / metrics.memory_limit_bytes
            ) * 100

        return metrics

    async def get_service_metrics(
        self,
        namespace: str,
        service_name: str,
    ) -> PrometheusMetrics:
        """Get traffic/latency metrics for a service.

        Args:
            namespace: Kubernetes namespace
            service_name: Service or deployment name

        Returns:
            PrometheusMetrics: Structured metrics data
        """
        metrics = PrometheusMetrics(query_timestamp=datetime.now(UTC), errors=[])

        # Common label patterns for services
        job_selector = f'job=~".*{service_name}.*"'
        service_selector = f'service=~".*{service_name}.*"'

        queries = {
            "request_rate": f"sum(rate(http_requests_total{{{job_selector}}}[5m])) or sum(rate(http_server_requests_seconds_count{{{job_selector}}}[5m]))",
            "error_rate": f'sum(rate(http_requests_total{{{job_selector}, status=~"5.."}}[5m])) / sum(rate(http_requests_total{{{job_selector}}}[5m])) * 100',
            "latency_p99": f"histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{{{job_selector}}}[5m])) by (le)) * 1000",
        }

        for name, promql in queries.items():
            try:
                result = await self.query(promql)
                value = self._extract_scalar(result)

                if name == "request_rate" and value is not None:
                    metrics.request_rate_per_sec = value
                elif name == "error_rate" and value is not None:
                    metrics.error_rate_pct = value
                elif name == "latency_p99" and value is not None:
                    metrics.latency_p99_ms = value

            except httpx.HTTPError as e:
                log.debug("prometheus_service_query_failed", query=name, error=str(e))
            except Exception as e:
                log.debug("prometheus_service_query_error", query=name, error=str(e))

        return metrics

    async def check_connectivity(self) -> bool:
        """Check if Prometheus is reachable.

        Returns:
            True if Prometheus responds to health check
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/-/healthy")
                return resp.status_code == 200
        except Exception:
            return False


async def fetch_prometheus_metrics(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> PrometheusMetrics | None:
    """High-level function to fetch Prometheus metrics for RCA enrichment.

    Args:
        resource_type: Kubernetes resource type (Pod, Deployment, etc.)
        resource_name: Resource name
        namespace: Kubernetes namespace

    Returns:
        PrometheusMetrics if successful, None if disabled or unavailable
    """
    if not settings.observability.prometheus_query_enabled:
        log.info("prometheus_query_disabled")
        return None

    client = PrometheusClient()

    # Check connectivity first
    if not await client.check_connectivity():
        log.warning("prometheus_not_reachable", url=client.base_url)
        return None

    try:
        # Get pod metrics
        pod_metrics = await client.get_pod_metrics(namespace, resource_name)

        # If it's a service/deployment, also get traffic metrics
        if resource_type.lower() in ("deployment", "service", "replicaset"):
            service_metrics = await client.get_service_metrics(namespace, resource_name)
            # Merge service metrics into pod metrics
            pod_metrics.request_rate_per_sec = service_metrics.request_rate_per_sec
            pod_metrics.error_rate_pct = service_metrics.error_rate_pct
            pod_metrics.latency_p99_ms = service_metrics.latency_p99_ms

        log.info(
            "prometheus_metrics_fetched",
            resource=f"{resource_type}/{resource_name}",
            namespace=namespace,
            cpu=pod_metrics.cpu_usage_cores,
            memory_mb=pod_metrics.memory_usage_bytes / 1024 / 1024
            if pod_metrics.memory_usage_bytes
            else None,
            restarts=pod_metrics.restart_count,
        )

        return pod_metrics

    except Exception as e:
        log.exception("prometheus_fetch_error", error=str(e))
        return None


# Module-level client cache
_prometheus_client: PrometheusClient | None = None


def get_prometheus_client() -> PrometheusClient:
    """Get or create Prometheus client instance."""
    global _prometheus_client
    if _prometheus_client is None:
        _prometheus_client = PrometheusClient()
    return _prometheus_client


__all__ = [
    "PrometheusClient",
    "PrometheusMetrics",
    "fetch_prometheus_metrics",
    "get_prometheus_client",
]
