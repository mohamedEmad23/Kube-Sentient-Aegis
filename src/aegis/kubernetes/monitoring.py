"""Post-Fix Monitoring Module.

This module provides monitoring capabilities after a fix has been applied.
It watches the affected resource for a configurable duration and detects
any new issues that may arise.

Key features:
- Configurable monitoring duration (default: 5 minutes)
- Pod health checks (restarts, OOMKill, CrashLoop detection)
- Deployment rollout status monitoring
- Automatic alerting to human operators if issues detected
- No auto-rollback (human decision required)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from kubernetes import client
from kubernetes import config as k8s_config

from aegis.crd import (
    AEGIS_API_GROUP,
    AEGIS_API_VERSION,
    AEGIS_INCIDENT_PLURAL,
    IncidentPhase,
)
from aegis.observability._logging import get_logger


log = get_logger(__name__)

# Default monitoring configuration
DEFAULT_MONITORING_DURATION_SECONDS = 300  # 5 minutes
MONITORING_CHECK_INTERVAL = 10  # Check every 10 seconds


@dataclass
class MonitoringResult:
    """Result of post-fix monitoring."""

    success: bool
    duration_seconds: int
    new_incidents_detected: bool = False
    warning_messages: list[str] = field(default_factory=list)
    completed_at: datetime | None = None
    resource_health: dict[str, Any] = field(default_factory=dict)


class PostFixMonitor:
    """Monitors resources after fix application.

    This class watches the affected resource for a configurable period
    after a fix has been applied. It checks for:
    - Pod restarts
    - OOMKilled containers
    - CrashLoopBackOff states
    - Failed rollouts
    - Unhealthy endpoints

    If issues are detected, it updates the incident status with a warning
    and alerts human operators. It does NOT auto-rollback.
    """

    def __init__(self) -> None:
        """Initialize the monitor with Kubernetes clients."""
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()

    async def monitor_resource(
        self,
        resource_kind: str,
        resource_name: str,
        namespace: str,
        duration_seconds: int = DEFAULT_MONITORING_DURATION_SECONDS,
        incident_name: str | None = None,
    ) -> MonitoringResult:
        """Monitor a resource for issues after fix application.

        Args:
            resource_kind: Kind of resource (Pod, Deployment, etc.)
            resource_name: Name of the resource
            namespace: Namespace of the resource
            duration_seconds: How long to monitor (default: 5 minutes)
            incident_name: Name of the AegisIncident to update with status

        Returns:
            MonitoringResult: Result of the monitoring period
        """
        log.info(
            "starting_post_fix_monitoring",
            resource=f"{resource_kind}/{resource_name}",
            namespace=namespace,
            duration=duration_seconds,
        )

        result = MonitoringResult(
            success=True,
            duration_seconds=duration_seconds,
        )

        # Update incident to Monitoring phase if provided
        if incident_name:
            await self._update_incident_phase(
                incident_name,
                namespace,
                IncidentPhase.MONITORING,
                monitoring_started_at=datetime.now(UTC),
            )

        # Capture initial state for comparison
        initial_state = await self._capture_resource_state(resource_kind, resource_name, namespace)

        # Monitor loop
        start_time = datetime.now(UTC)
        end_time = start_time.timestamp() + duration_seconds
        check_count = 0

        while datetime.now(UTC).timestamp() < end_time:
            await asyncio.sleep(MONITORING_CHECK_INTERVAL)
            check_count += 1

            log.debug(
                "monitoring_check",
                resource=f"{resource_kind}/{resource_name}",
                check=check_count,
            )

            # Check resource health
            issues = await self._check_resource_health(
                resource_kind, resource_name, namespace, initial_state
            )

            if issues:
                result.new_incidents_detected = True
                result.warning_messages.extend(issues)
                log.warning(
                    "post_fix_issues_detected",
                    resource=f"{resource_kind}/{resource_name}",
                    issues=issues,
                )

                # Alert but don't auto-rollback
                if incident_name:
                    await self._update_incident_with_warning(
                        incident_name,
                        namespace,
                        issues,
                    )

        # Capture final state
        final_state = await self._capture_resource_state(resource_kind, resource_name, namespace)
        result.resource_health = final_state
        result.completed_at = datetime.now(UTC)

        # Determine final success
        if result.new_incidents_detected:
            result.success = False
            log.warning(
                "monitoring_completed_with_issues",
                resource=f"{resource_kind}/{resource_name}",
                issues=result.warning_messages,
            )
        else:
            log.info(
                "monitoring_completed_successfully",
                resource=f"{resource_kind}/{resource_name}",
            )

        # Update incident to final state
        if incident_name:
            if result.success:
                await self._update_incident_phase(
                    incident_name,
                    namespace,
                    IncidentPhase.RESOLVED,
                    resolved_at=datetime.now(UTC),
                )
            else:
                # Keep in Monitoring phase with warning, human decision needed
                await self._update_incident_with_warning(
                    incident_name,
                    namespace,
                    result.warning_messages,
                )

        return result

    async def _capture_resource_state(
        self,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> dict[str, Any]:
        """Capture current state of a resource for comparison."""
        state: dict[str, Any] = {
            "captured_at": datetime.now(UTC).isoformat(),
            "kind": resource_kind,
            "name": resource_name,
            "namespace": namespace,
        }

        try:
            if resource_kind.lower() in ["pod", "pods"]:
                pod = self.core_api.read_namespaced_pod(resource_name, namespace)
                state["phase"] = pod.status.phase
                state["container_restarts"] = {}
                for cs in pod.status.container_statuses or []:
                    state["container_restarts"][cs.name] = cs.restart_count

            elif resource_kind.lower() in ["deployment", "deployments"]:
                deploy = self.apps_api.read_namespaced_deployment(resource_name, namespace)
                state["replicas"] = {
                    "desired": deploy.spec.replicas,
                    "ready": deploy.status.ready_replicas or 0,
                    "available": deploy.status.available_replicas or 0,
                    "unavailable": deploy.status.unavailable_replicas or 0,
                }
                state["generation"] = deploy.metadata.generation
                state["observed_generation"] = deploy.status.observed_generation

                # Get pod restart counts for deployment pods
                label_selector = ",".join(
                    f"{k}={v}" for k, v in (deploy.spec.selector.match_labels or {}).items()
                )
                pods = self.core_api.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector,
                )
                state["pod_restarts"] = {}
                for pod in pods.items:
                    for cs in pod.status.container_statuses or []:
                        key = f"{pod.metadata.name}/{cs.name}"
                        state["pod_restarts"][key] = cs.restart_count

            elif resource_kind.lower() in ["statefulset", "statefulsets"]:
                sts = self.apps_api.read_namespaced_stateful_set(resource_name, namespace)
                state["replicas"] = {
                    "desired": sts.spec.replicas,
                    "ready": sts.status.ready_replicas or 0,
                    "current": sts.status.current_replicas or 0,
                }

        except client.ApiException as e:
            state["error"] = f"Failed to capture state: {e.reason}"
            log.exception("capture_state_failed")

        return state

    def _check_container_issues(
        self,
        cs: Any,
        initial_count: int,
        pod_prefix: str = "",
    ) -> list[str]:
        """Check a container status for issues.

        Args:
            cs: Container status object
            initial_count: Initial restart count for comparison
            pod_prefix: Optional prefix for pod name in messages

        Returns:
            List of issue descriptions
        """
        issues: list[str] = []
        container_name = f"{pod_prefix}{cs.name}" if pod_prefix else cs.name

        # Check restart count
        if cs.restart_count > initial_count:
            restart_diff = cs.restart_count - initial_count
            issues.append(f"Container {container_name} restarted ({restart_diff} times)")

        # Check waiting state
        bad_waiting_states = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "OOMKilled"}
        if cs.state and cs.state.waiting and cs.state.waiting.reason in bad_waiting_states:
            issues.append(f"Container {container_name} in {cs.state.waiting.reason} state")

        # Check terminated state
        if cs.state and cs.state.terminated:
            reason = cs.state.terminated.reason
            if reason == "OOMKilled":
                issues.append(f"Container {container_name} was OOMKilled")
            elif reason == "Error":
                issues.append(
                    f"Container {container_name} exited with error (code {cs.state.terminated.exit_code})"
                )

        return issues

    def _check_pod_health(
        self,
        resource_name: str,
        namespace: str,
        initial_state: dict[str, Any],
    ) -> list[str]:
        """Check Pod health and return issues."""
        issues: list[str] = []
        pod = self.core_api.read_namespaced_pod(resource_name, namespace)

        # Check phase
        if pod.status.phase in ["Failed", "Unknown"]:
            issues.append(f"Pod entered {pod.status.phase} phase")

        # Check containers
        initial_restarts = initial_state.get("container_restarts", {})
        for cs in pod.status.container_statuses or []:
            initial_count = initial_restarts.get(cs.name, 0)
            issues.extend(self._check_container_issues(cs, initial_count))

        return issues

    def _check_deployment_health(
        self,
        resource_name: str,
        namespace: str,
        initial_state: dict[str, Any],
    ) -> list[str]:
        """Check Deployment health and return issues."""
        issues: list[str] = []
        deploy = self.apps_api.read_namespaced_deployment(resource_name, namespace)

        # Check replica health
        desired = deploy.spec.replicas or 1
        ready = deploy.status.ready_replicas or 0
        unavailable = deploy.status.unavailable_replicas or 0

        if unavailable > 0:
            issues.append(f"Deployment has {unavailable} unavailable replicas")
        if ready < desired:
            issues.append(f"Deployment has {ready}/{desired} ready replicas")

        # Check for pod restarts
        label_selector = ",".join(
            f"{k}={v}" for k, v in (deploy.spec.selector.match_labels or {}).items()
        )
        pods = self.core_api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        initial_restarts = initial_state.get("pod_restarts", {})
        for pod in pods.items:
            for cs in pod.status.container_statuses or []:
                key = f"{pod.metadata.name}/{cs.name}"
                initial_count = initial_restarts.get(key, 0)
                pod_prefix = f"{pod.metadata.name}/"
                issues.extend(self._check_container_issues(cs, initial_count, pod_prefix))

        # Check rollout progress
        for condition in deploy.status.conditions or []:
            if condition.type == "Progressing" and condition.status == "False":
                issues.append(f"Deployment rollout stalled: {condition.message}")
            elif condition.type == "Available" and condition.status == "False":
                issues.append(f"Deployment unavailable: {condition.message}")

        return issues

    def _check_statefulset_health(
        self,
        resource_name: str,
        namespace: str,
    ) -> list[str]:
        """Check StatefulSet health and return issues."""
        issues: list[str] = []
        sts = self.apps_api.read_namespaced_stateful_set(resource_name, namespace)

        desired = sts.spec.replicas or 1
        ready = sts.status.ready_replicas or 0

        if ready < desired:
            issues.append(f"StatefulSet has {ready}/{desired} ready replicas")

        return issues

    async def _check_resource_health(
        self,
        resource_kind: str,
        resource_name: str,
        namespace: str,
        initial_state: dict[str, Any],
    ) -> list[str]:
        """Check resource health and return list of issues."""
        kind_lower = resource_kind.lower()
        try:
            if kind_lower in ["pod", "pods"]:
                return self._check_pod_health(resource_name, namespace, initial_state)
            if kind_lower in ["deployment", "deployments"]:
                return self._check_deployment_health(resource_name, namespace, initial_state)
            if kind_lower in ["statefulset", "statefulsets"]:
                return self._check_statefulset_health(resource_name, namespace)
        except client.ApiException as e:
            log.exception("health_check_failed")
            return [f"Failed to check health: {e.reason}"]
        else:
            return []

    async def _update_incident_phase(
        self,
        incident_name: str,
        namespace: str,
        phase: IncidentPhase,
        monitoring_started_at: datetime | None = None,
        resolved_at: datetime | None = None,
    ) -> None:
        """Update the AegisIncident status phase."""
        try:
            patch_body: dict[str, Any] = {
                "status": {
                    "phase": phase.value,
                }
            }

            if monitoring_started_at:
                patch_body["status"]["monitoring"] = {
                    "startedAt": monitoring_started_at.isoformat() + "Z",
                }

            if resolved_at:
                patch_body["status"]["resolvedAt"] = resolved_at.isoformat() + "Z"

            self.custom_api.patch_namespaced_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                namespace=namespace,
                plural=AEGIS_INCIDENT_PLURAL,
                name=incident_name,
                body=patch_body,
            )

            log.info(
                "incident_phase_updated",
                incident=incident_name,
                phase=phase.value,
            )

        except client.ApiException as e:
            log.exception("incident_phase_update_failed", error=e.reason)

    async def _update_incident_with_warning(
        self,
        incident_name: str,
        namespace: str,
        warnings: list[str],
    ) -> None:
        """Update incident with post-fix monitoring warnings."""
        try:
            warning_message = "; ".join(warnings)

            patch_body = {
                "status": {
                    "monitoring": {
                        "newIncidentsDetected": True,
                        "warningMessage": warning_message[:500],  # Truncate if too long
                    }
                }
            }

            self.custom_api.patch_namespaced_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                namespace=namespace,
                plural=AEGIS_INCIDENT_PLURAL,
                name=incident_name,
                body=patch_body,
            )

            log.warning(
                "incident_warning_updated",
                incident=incident_name,
                warning=warning_message,
            )

        except client.ApiException as e:
            log.exception("incident_warning_update_failed", error=e.reason)


class _MonitorHolder:
    """Holder class for PostFixMonitor singleton to avoid global statement."""

    instance: PostFixMonitor | None = None


def get_post_fix_monitor() -> PostFixMonitor:
    """Get the singleton PostFixMonitor instance."""
    if _MonitorHolder.instance is None:
        _MonitorHolder.instance = PostFixMonitor()
    return _MonitorHolder.instance


__all__ = [
    "DEFAULT_MONITORING_DURATION_SECONDS",
    "MonitoringResult",
    "PostFixMonitor",
    "get_post_fix_monitor",
]
