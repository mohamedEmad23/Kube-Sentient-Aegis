"""Rollback Agent - Automated Production Rollback.

Monitors production deployments post-fix and automatically rolls back
if degradation is detected (error rate spike, pod crashes).

Workflow:
1. Capture pre-deployment snapshot (Deployment, ConfigMaps, Services)
2. Deploy fix to production
3. Monitor metrics for degradation window (default: 5 minutes)
4. If error rate increases >20%, trigger automatic rollback
5. Restore pre-deployment snapshot
6. Verify rollback success

Integration: Called after production deployment in the LangGraph workflow.
"""

import asyncio
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from kubernetes import client
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from aegis.agent.state import IncidentState
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability.prometheus_client import PrometheusClient


log = get_logger(__name__)


# ============================================================================
# Rollback Configuration
# ============================================================================

ROLLBACK_ERROR_RATE_THRESHOLD = float(
    getattr(settings.observability, "rollback_error_rate_threshold", 0.20)
)  # 20% increase
ROLLBACK_MONITORING_WINDOW_MINUTES = int(
    getattr(settings.observability, "rollback_monitoring_window_minutes", 5)
)
ROLLBACK_ENABLED = getattr(settings.observability, "rollback_enabled", True)


# ============================================================================
# Snapshot Capture
# ============================================================================


async def capture_pre_deployment_snapshot(
    namespace: str,
    resource_name: str,
    resource_type: str,
    *,
    core_api: client.CoreV1Api | None = None,
    apps_api: client.AppsV1Api | None = None,
) -> dict[str, Any]:
    """Capture current state of production resources for rollback.

    Args:
        namespace: Kubernetes namespace
        resource_name: Resource name (Deployment, Pod, etc.)
        resource_type: Resource type
        core_api: Optional CoreV1 API client
        apps_api: Optional AppsV1 API client

    Returns:
        Snapshot dict with YAML manifests keyed by resource type/name
    """
    if core_api is None:
        core_api = client.CoreV1Api()
    if apps_api is None:
        apps_api = client.AppsV1Api()

    snapshot: dict[str, Any] = {
        "namespace": namespace,
        "resource_name": resource_name,
        "resource_type": resource_type,
        "captured_at": datetime.now(UTC).isoformat(),
        "manifests": {},
    }

    try:
        # Capture Deployment
        if resource_type.lower() in ["deployment", "deploy"]:
            deployment = await asyncio.to_thread(
                apps_api.read_namespaced_deployment, resource_name, namespace
            )
            # Convert to dict and remove server-managed fields
            deployment_dict = client.ApiClient().sanitize_for_serialization(deployment)
            _clean_metadata(deployment_dict)

            snapshot["manifests"][f"Deployment-{resource_name}"] = yaml.dump(
                deployment_dict, default_flow_style=False
            )

        # Capture associated ConfigMaps (heuristic: same name or app label)
        try:
            configmaps = await asyncio.to_thread(core_api.list_namespaced_config_map, namespace)
            for cm in configmaps.items:
                cm_name = cm.metadata.name
                if cm_name.startswith(resource_name):
                    cm_dict = client.ApiClient().sanitize_for_serialization(cm)
                    _clean_metadata(cm_dict)
                    snapshot["manifests"][f"ConfigMap-{cm_name}"] = yaml.dump(
                        cm_dict, default_flow_style=False
                    )
        except Exception as cm_error:
            log.warning("configmap_snapshot_failed", error=str(cm_error))

        # Capture associated Service
        try:
            service = await asyncio.to_thread(
                core_api.read_namespaced_service, resource_name, namespace
            )
            service_dict = client.ApiClient().sanitize_for_serialization(service)
            _clean_metadata(service_dict)
            snapshot["manifests"][f"Service-{resource_name}"] = yaml.dump(
                service_dict, default_flow_style=False
            )
        except client.ApiException:
            # Service might not exist
            pass

        log.info(
            "snapshot_captured",
            namespace=namespace,
            resource=f"{resource_type}/{resource_name}",
            manifest_count=len(snapshot["manifests"]),
        )

    except Exception as e:
        log.error(
            "snapshot_capture_failed",
            namespace=namespace,
            resource=resource_name,
            error=str(e),
        )
        snapshot["error"] = str(e)

    return snapshot


def _clean_metadata(resource_dict: dict[str, Any]) -> None:
    """Remove server-managed metadata fields for clean reapplication.

    Args:
        resource_dict: Resource dictionary to clean (modified in-place)
    """
    metadata = resource_dict.get("metadata", {})

    # Remove server-generated fields
    for field in [
        "uid",
        "resourceVersion",
        "generation",
        "creationTimestamp",
        "managedFields",
        "selfLink",
    ]:
        metadata.pop(field, None)

    # Clean status section
    resource_dict.pop("status", None)


# ============================================================================
# Metric Monitoring
# ============================================================================


async def monitor_error_rate(
    namespace: str,
    resource_name: str,
    baseline_error_rate: float,
    monitoring_window_minutes: int,
    *,
    prometheus_client: PrometheusClient | None = None,
) -> tuple[float, bool, str]:
    """Monitor error rate and determine if rollback is needed.

    Args:
        namespace: Kubernetes namespace
        resource_name: Resource name
        baseline_error_rate: Error rate before deployment (0.0-1.0)
        monitoring_window_minutes: How long to monitor
        prometheus_client: Optional Prometheus client

    Returns:
        Tuple of (current_error_rate, should_rollback, reason)
    """
    if prometheus_client is None:
        prometheus_client = PrometheusClient()

    # Wait for deployment to stabilize
    await asyncio.sleep(30)  # 30 second grace period

    # Monitor in intervals
    intervals = monitoring_window_minutes * 2  # Check every 30s

    for i in range(intervals):
        try:
            # Query HTTP error rate (5xx responses)
            error_rate_query = f"""
            sum(rate(http_requests_total{{
                namespace="{namespace}",
                deployment="{resource_name}",
                status=~"5.."
            }}[1m])) /
            sum(rate(http_requests_total{{
                namespace="{namespace}",
                deployment="{resource_name}"
            }}[1m]))
            """

            result = await asyncio.to_thread(prometheus_client.query, error_rate_query)
            current_error_rate = prometheus_client._extract_scalar(result) or 0.0

            # Check for spike
            if current_error_rate > baseline_error_rate * (1 + ROLLBACK_ERROR_RATE_THRESHOLD):
                reason = (
                    f"Error rate spiked from {baseline_error_rate:.2%} to "
                    f"{current_error_rate:.2%} (>{ROLLBACK_ERROR_RATE_THRESHOLD:.0%} increase)"
                )
                log.warning(
                    "rollback_triggered_error_rate",
                    namespace=namespace,
                    resource=resource_name,
                    baseline=baseline_error_rate,
                    current=current_error_rate,
                )
                return (current_error_rate, True, reason)

            # Check pod restart rate
            restart_query = f"""
            sum(kube_pod_container_status_restarts_total{{
                namespace="{namespace}",
                pod=~"{resource_name}-.*"
            }})
            """
            restart_result = await asyncio.to_thread(prometheus_client.query, restart_query)
            current_restarts = int(prometheus_client._extract_scalar(restart_result) or 0)

            # If restarts increasing rapidly, rollback
            if i > 0 and current_restarts > 5:
                reason = f"Excessive pod restarts detected: {current_restarts}"
                log.warning(
                    "rollback_triggered_restarts",
                    namespace=namespace,
                    resource=resource_name,
                    restarts=current_restarts,
                )
                return (current_error_rate, True, reason)

        except Exception as e:
            log.warning("metric_monitoring_failed", error=str(e))
            # Continue monitoring despite errors

        # Wait before next check
        if i < intervals - 1:
            await asyncio.sleep(30)

    # Monitoring window passed without issues
    log.info(
        "rollback_monitoring_passed",
        namespace=namespace,
        resource=resource_name,
        window_minutes=monitoring_window_minutes,
    )
    return (0.0, False, "No degradation detected")


# ============================================================================
# Rollback Execution
# ============================================================================


async def execute_rollback(
    snapshot: dict[str, Any],
    namespace: str,
) -> tuple[bool, str]:
    """Execute rollback by applying pre-deployment snapshot.

    Args:
        snapshot: Pre-deployment snapshot from capture_pre_deployment_snapshot
        namespace: Kubernetes namespace

    Returns:
        Tuple of (success, message)
    """
    if not shutil.which("kubectl"):
        return (False, "kubectl not found in PATH")

    manifests = snapshot.get("manifests", {})
    if not manifests:
        return (False, "No manifests in snapshot")

    # Write manifests to temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        for name, yaml_content in manifests.items():
            manifest_file = tmppath / f"{name}.yaml"
            manifest_file.write_text(yaml_content)

        # Apply all manifests
        try:
            process = await asyncio.create_subprocess_exec(
                "kubectl",
                "apply",
                "-f",
                str(tmppath),
                "-n",
                namespace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                log.error("rollback_failed", error=error_msg)
                return (False, f"kubectl apply failed: {error_msg}")

            log.info("rollback_executed", namespace=namespace, applied=len(manifests))

            # Verify rollback (wait for pods to be Running)
            await asyncio.sleep(10)

            verify_cmd = await asyncio.create_subprocess_exec(
                "kubectl",
                "get",
                "pods",
                "-n",
                namespace,
                "-o",
                "jsonpath={.items[*].status.phase}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            verify_stdout, _ = await verify_cmd.communicate()
            phases = verify_stdout.decode().split()

            if all(phase == "Running" for phase in phases):
                return (True, f"Rollback successful, {len(manifests)} manifests restored")
            return (True, f"Rollback applied, but pods not all Running: {phases}")

        except Exception as e:
            log.error("rollback_execution_failed", error=str(e))
            return (False, str(e))


# ============================================================================
# Rollback Agent (LangGraph Node)
# ============================================================================


async def rollback_agent(
    state: IncidentState,
    config: RunnableConfig,
) -> Command[str]:
    """Rollback agent - monitors production and triggers rollback if needed.

    Args:
        state: Current incident state (after production deployment)
        config: LangGraph runtime config

    Returns:
        Command routing to END with rollback results
    """
    log.info("rollback_agent_started", incident_id=state.get("incident_id"))

    if not ROLLBACK_ENABLED:
        log.info("rollback_monitoring_disabled")
        return Command(goto="END", update={"error": None})

    # Extract rollback metadata
    rollback_meta_dict = state.get("rollback_metadata")
    if not rollback_meta_dict:
        log.warning("no_rollback_metadata", skipping=True)
        return Command(goto="END", update={"error": None})

    # Reconstruct RollbackMetadata
    snapshot = rollback_meta_dict.get("pre_deployment_snapshot", {})
    baseline_error_rate = rollback_meta_dict.get("baseline_error_rate", 0.0)

    namespace = state["namespace"]
    resource_name = state["resource_name"]

    # Monitor for degradation
    current_rate, should_rollback, reason = await monitor_error_rate(
        namespace=namespace,
        resource_name=resource_name,
        baseline_error_rate=baseline_error_rate,
        monitoring_window_minutes=ROLLBACK_MONITORING_WINDOW_MINUTES,
    )

    if should_rollback:
        log.warning(
            "rollback_initiating",
            incident_id=state.get("incident_id"),
            reason=reason,
        )

        # Execute rollback
        success, message = await execute_rollback(snapshot, namespace)

        # Update state
        rollback_meta_dict["rollback_triggered"] = True
        rollback_meta_dict["rollback_reason"] = reason
        rollback_meta_dict["rollback_timestamp"] = datetime.now(UTC).isoformat()

        if success:
            log.info("rollback_successful", message=message)
            return Command(
                goto="END",
                update={
                    "rollback_metadata": rollback_meta_dict,
                    "error": f"ROLLBACK EXECUTED: {reason}. {message}",
                },
            )
        log.error("rollback_failed", message=message)
        return Command(
            goto="END",
            update={
                "rollback_metadata": rollback_meta_dict,
                "error": f"ROLLBACK FAILED: {message}",
            },
        )
    # No rollback needed
    log.info("rollback_not_needed", reason=reason)
    return Command(goto="END", update={"error": None})


__all__ = [
    "capture_pre_deployment_snapshot",
    "execute_rollback",
    "monitor_error_rate",
    "rollback_agent",
]
