"""Grafana Dashboard Link Generator for RCA Enrichment.

This module generates deep links to Grafana dashboards with pre-populated
variables for pods, namespaces, and time ranges to help operators quickly
visualize metrics during incident analysis.

Grafana URL Parameters:
- var-namespace: Dashboard variable for namespace
- var-pod: Dashboard variable for pod name
- from/to: Time range in Grafana format (epoch milliseconds or relative)
- refresh: Dashboard auto-refresh interval

Usage:
    links = GrafanaLinkGenerator()
    pod_url = links.pod_dashboard("demo", "demo-api")
    print(f"View metrics: {pod_url}")
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)


class GrafanaLinkGenerator:
    """Generate deep links to Grafana dashboards with context.

    Creates URLs that open Grafana dashboards with pre-populated
    namespace, pod, and time range variables for quick access
    during incident triage.
    """

    def __init__(
        self,
        base_url: str | None = None,
        pod_dashboard_uid: str | None = None,
        deployment_dashboard_uid: str | None = None,
    ) -> None:
        """Initialize Grafana link generator.

        Args:
            base_url: Grafana server URL (default from settings)
            pod_dashboard_uid: Dashboard UID for pod metrics (default from settings)
            deployment_dashboard_uid: Dashboard UID for deployment metrics (default from settings)
        """
        self.base_url = (base_url or settings.observability.grafana_url).rstrip("/")
        self.pod_dashboard_uid = (
            pod_dashboard_uid or settings.observability.grafana_pod_dashboard_uid
        )
        self.deployment_dashboard_uid = (
            deployment_dashboard_uid or settings.observability.grafana_deployment_dashboard_uid
        )
        self._enabled = settings.observability.grafana_enabled

    def _build_dashboard_url(
        self,
        dashboard_uid: str,
        namespace: str,
        resource_name: str,
        time_from: str = "now-1h",
        time_to: str = "now",
        refresh: str = "30s",
        extra_vars: dict[str, str] | None = None,
    ) -> str:
        """Build a Grafana dashboard URL with query parameters.

        Args:
            dashboard_uid: Grafana dashboard UID
            namespace: Kubernetes namespace
            resource_name: Pod or deployment name
            time_from: Start time (Grafana format: now-1h, epoch ms)
            time_to: End time (Grafana format: now, epoch ms)
            refresh: Auto-refresh interval
            extra_vars: Additional dashboard variables

        Returns:
            Complete Grafana dashboard URL
        """
        params: dict[str, str] = {
            "var-namespace": namespace,
            "var-pod": resource_name,
            "from": time_from,
            "to": time_to,
            "refresh": refresh,
        }

        if extra_vars:
            for key, value in extra_vars.items():
                params[f"var-{key}"] = value

        query_string = urlencode(params)
        return f"{self.base_url}/d/{dashboard_uid}?{query_string}"

    def pod_dashboard(
        self,
        namespace: str,
        pod_name: str,
        time_range_minutes: int = 60,
    ) -> str | None:
        """Generate URL for pod metrics dashboard.

        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name (exact or prefix)
            time_range_minutes: How far back to show (default: 60 min)

        Returns:
            Grafana dashboard URL or None if disabled
        """
        if not self._enabled or not self.pod_dashboard_uid:
            return None

        time_from = f"now-{time_range_minutes}m"
        return self._build_dashboard_url(
            dashboard_uid=self.pod_dashboard_uid,
            namespace=namespace,
            resource_name=pod_name,
            time_from=time_from,
        )

    def deployment_dashboard(
        self,
        namespace: str,
        deployment_name: str,
        time_range_minutes: int = 60,
    ) -> str | None:
        """Generate URL for deployment metrics dashboard.

        Args:
            namespace: Kubernetes namespace
            deployment_name: Deployment name
            time_range_minutes: How far back to show (default: 60 min)

        Returns:
            Grafana dashboard URL or None if disabled
        """
        if not self._enabled or not self.deployment_dashboard_uid:
            return None

        time_from = f"now-{time_range_minutes}m"
        return self._build_dashboard_url(
            dashboard_uid=self.deployment_dashboard_uid,
            namespace=namespace,
            resource_name=deployment_name,
            time_from=time_from,
            extra_vars={"deployment": deployment_name},
        )

    def resource_dashboard(
        self,
        resource_type: str,
        resource_name: str,
        namespace: str,
        time_range_minutes: int = 60,
    ) -> str | None:
        """Generate URL for any resource type.

        Automatically selects deployment or pod dashboard based on resource type.

        Args:
            resource_type: Kubernetes resource type (Pod, Deployment, etc.)
            resource_name: Resource name
            namespace: Kubernetes namespace
            time_range_minutes: How far back to show (default: 60 min)

        Returns:
            Grafana dashboard URL or None if disabled/unavailable
        """
        resource_lower = resource_type.lower()

        if resource_lower in ("deployment", "replicaset", "statefulset", "daemonset"):
            return self.deployment_dashboard(namespace, resource_name, time_range_minutes)

        # Default to pod dashboard
        return self.pod_dashboard(namespace, resource_name, time_range_minutes)

    def incident_time_range_url(
        self,
        namespace: str,
        resource_name: str,
        incident_time: datetime,
        window_minutes: int = 30,
    ) -> str | None:
        """Generate URL centered on incident time.

        Creates a dashboard URL with time range centered on the incident
        time, useful for post-incident analysis.

        Args:
            namespace: Kubernetes namespace
            resource_name: Resource name
            incident_time: When the incident occurred
            window_minutes: Minutes before and after incident to show

        Returns:
            Grafana dashboard URL or None if disabled
        """
        if not self._enabled or not self.pod_dashboard_uid:
            return None

        start = incident_time - timedelta(minutes=window_minutes)
        end = incident_time + timedelta(minutes=window_minutes)

        # Convert to epoch milliseconds for Grafana
        time_from = str(int(start.timestamp() * 1000))
        time_to = str(int(end.timestamp() * 1000))

        return self._build_dashboard_url(
            dashboard_uid=self.pod_dashboard_uid,
            namespace=namespace,
            resource_name=resource_name,
            time_from=time_from,
            time_to=time_to,
            refresh="off",  # No refresh for historical view
        )

    async def check_health(self) -> dict[str, Any]:
        """Check Grafana server health and connectivity.

        Returns:
            Health status dict with:
            - healthy: bool
            - url: str
            - error: str | None
            - version: str | None
        """
        status: dict[str, Any] = {
            "healthy": False,
            "url": self.base_url,
            "error": None,
            "version": None,
        }

        if not self._enabled:
            status["error"] = "Grafana integration disabled"
            return status

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/health")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("database") == "ok":
                        status["healthy"] = True
                        status["version"] = data.get("version")
                else:
                    status["error"] = f"HTTP {resp.status_code}"
        except httpx.ConnectError:
            status["error"] = "Connection refused"
        except httpx.TimeoutException:
            status["error"] = "Connection timeout"
        except Exception as e:
            status["error"] = str(e)

        return status


# Module-level singleton
_grafana_links: GrafanaLinkGenerator | None = None


def get_grafana_link_generator() -> GrafanaLinkGenerator:
    """Get or create Grafana link generator singleton."""
    global _grafana_links
    if _grafana_links is None:
        _grafana_links = GrafanaLinkGenerator()
    return _grafana_links


def generate_dashboard_url(
    resource_type: str,
    resource_name: str,
    namespace: str,
    time_range_minutes: int = 60,
) -> str | None:
    """Convenience function to generate dashboard URL.

    Args:
        resource_type: Kubernetes resource type
        resource_name: Resource name
        namespace: Kubernetes namespace
        time_range_minutes: How far back to show (default: 60 min)

    Returns:
        Grafana dashboard URL or None if disabled
    """
    generator = get_grafana_link_generator()
    return generator.resource_dashboard(resource_type, resource_name, namespace, time_range_minutes)


__all__ = [
    "GrafanaLinkGenerator",
    "generate_dashboard_url",
    "get_grafana_link_generator",
]
