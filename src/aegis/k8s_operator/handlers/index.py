"""AEGIS Resource Indexing Handlers.

In-memory indexing of Kubernetes resources for fast O(1) lookups
used by AI decision-making and analysis workflows.

This module provides:
- Pod health indexing (phase, restarts, ready status)
- Deployment replica tracking
- Service endpoint monitoring
- Fast lookups without querying Kubernetes API
"""

from typing import Any

import kopf
from kopf import Index, Labels, Spec, Status

from aegis.observability._logging import get_logger


# Get structured logger
log = get_logger(__name__)


# Constants for health thresholds
MAX_ACCEPTABLE_RESTARTS = 5
HIGH_RESTARTS_WARNING_THRESHOLD = 10


# ============================================================================
# Pod Indexing
# ============================================================================


@kopf.index("pods")
def pod_health_index(
    *,
    namespace: str | None,
    name: str | None,
    status: Status,
    **_kwargs: Any,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Build in-memory index of pod health status.

    This index provides O(1) lookups for pod health information without
    querying the Kubernetes API. Used by AI agents for fast decision-making.

    Index structure:
        {
            (namespace, pod_name): {
                'phase': str,                 # Running, Failed, Pending, etc.
                'restarts': int,              # Total container restarts
                'ready': bool,                # All containers ready
                'containers': int,            # Number of containers
                'healthy': bool,              # Overall health (derived)
            }
        }

    Args:
        namespace: Pod namespace
        name: Pod name
        status: Full pod status object
        **kwargs: Additional kopf kwargs

    Returns:
        dict: Mapping of (namespace, name) to health metrics

    Example:
        >>> # In a handler or timer
        >>> def check_pod_health(pod_health_index: kopf.Index, **_):
        ...     for (ns, pod_name), health in pod_health_index.items():
        ...         if not health['healthy']:
        ...             print(f"Unhealthy pod: {ns}/{pod_name}")
    """
    if not namespace or not name:
        return {}

    # Extract phase
    phase = status.get("phase", "Unknown")

    # Count total restarts across all containers
    container_statuses = status.get("containerStatuses", [])
    total_restarts = sum(cs.get("restartCount", 0) for cs in container_statuses)

    # Check if all containers are ready
    num_containers = len(container_statuses)
    ready_containers = sum(1 for cs in container_statuses if cs.get("ready", False))
    all_ready = (num_containers > 0) and (ready_containers == num_containers)

    # Derive overall health
    # Healthy if: Running phase, low restarts, and all containers ready
    healthy = (
        phase == "Running"
        and total_restarts < MAX_ACCEPTABLE_RESTARTS  # Threshold for "acceptable" restarts
        and all_ready
    )

    health_data = {
        "phase": phase,
        "restarts": total_restarts,
        "ready": all_ready,
        "containers": num_containers,
        "healthy": healthy,
    }

    # Log significant changes
    if total_restarts > HIGH_RESTARTS_WARNING_THRESHOLD:
        log.warning(
            "pod_high_restarts",
            namespace=namespace,
            pod=name,
            restarts=total_restarts,
        )

    return {(namespace, name): health_data}


@kopf.index("pods")
def pod_by_label_index(
    *,
    labels: Labels | None,
    name: str | None,
    namespace: str | None,
    **_kwargs: Any,
) -> dict[tuple[str, str, str], str]:
    """Index pods by their labels for fast label-based lookups.

    Allows querying pods by label key-value pairs in O(1) time.

    Index structure:
        {
            (namespace, label_key, label_value): pod_name
        }

    Args:
        labels: Pod labels dict
        name: Pod name
        namespace: Pod namespace
        **kwargs: Additional kopf kwargs

    Returns:
        dict: Mapping of (namespace, label_key, label_value) to pod name

    Example:
        >>> # Find all pods with app=nginx in namespace=production
        >>> for key, pod_names in pod_by_label_index.items():
        ...     ns, label_key, label_value = key
        ...     if ns == "production" and label_key == "app" and label_value == "nginx":
        ...         print(f"Found: {pod_names}")
    """
    if not labels or not name or not namespace:
        return {}

    result = {}
    for label_key, label_value in labels.items():
        # Create index entry for each label
        result[(namespace, label_key, label_value)] = name

    return result


# ============================================================================
# Deployment Indexing
# ============================================================================


@kopf.index("deployments")
def deployment_replica_index(
    *,
    namespace: str | None,
    name: str | None,
    spec: Spec,
    status: Status,
    **_kwargs: Any,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Index deployment replica status for fast health checks.

    Tracks desired vs actual replica counts to detect scaling issues.

    Index structure:
        {
            (namespace, deployment_name): {
                'desired': int,
                'ready': int,
                'available': int,
                'unavailable': int,
                'updated': int,
                'healthy': bool,
            }
        }

    Args:
        namespace: Deployment namespace
        name: Deployment name
        spec: Deployment specification
        status: Deployment status
        **kwargs: Additional kopf kwargs

    Returns:
        dict: Mapping of (namespace, name) to replica metrics
    """
    if not namespace or not name:
        return {}

    desired = spec.get("replicas", 1)
    ready = status.get("readyReplicas", 0)
    available = status.get("availableReplicas", 0)
    unavailable = status.get("unavailableReplicas", 0)
    updated = status.get("updatedReplicas", 0)

    # Deployment is healthy if:
    # - Ready replicas == desired replicas
    # - No unavailable replicas
    # - All replicas are updated (for rollouts)
    healthy = ready == desired and unavailable == 0 and updated == desired

    replica_data = {
        "desired": desired,
        "ready": ready,
        "available": available,
        "unavailable": unavailable,
        "updated": updated,
        "healthy": healthy,
    }

    if not healthy:
        log.info(
            "deployment_unhealthy",
            namespace=namespace,
            deployment=name,
            desired=desired,
            ready=ready,
            unavailable=unavailable,
        )

    return {(namespace, name): replica_data}


# ============================================================================
# Service Indexing
# ============================================================================


@kopf.index("services")
def service_endpoint_index(
    *,
    namespace: str | None,
    name: str | None,
    spec: Spec,
    **_kwargs: Any,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Index service selector and type information.

    Helps identify services without endpoints by correlating
    selectors with pod labels.

    Index structure:
        {
            (namespace, service_name): {
                'selector': dict,
                'type': str,
                'ports': list,
            }
        }

    Args:
        namespace: Service namespace
        name: Service name
        spec: Service specification
        **kwargs: Additional kopf kwargs

    Returns:
        dict: Mapping of (namespace, name) to service info
    """
    if not namespace or not name:
        return {}

    selector = spec.get("selector", {})
    service_type = spec.get("type", "ClusterIP")
    ports = spec.get("ports", [])

    service_data = {
        "selector": selector,
        "type": service_type,
        "ports": [
            {
                "name": p.get("name"),
                "port": p.get("port"),
                "targetPort": p.get("targetPort"),
                "protocol": p.get("protocol", "TCP"),
            }
            for p in ports
        ],
    }

    return {(namespace, name): service_data}


# ============================================================================
# Node Indexing (for resource availability)
# ============================================================================


@kopf.index("nodes")
def node_resource_index(
    *,
    name: str | None,
    status: Status,
    **_kwargs: Any,
) -> dict[str, dict[str, Any]]:
    """Index node resource capacity and availability.

    Used by AI agents to make informed scaling decisions.

    Index structure:
        {
            node_name: {
                'capacity': {'cpu': str, 'memory': str},
                'allocatable': {'cpu': str, 'memory': str},
                'conditions': dict,
                'ready': bool,
            }
        }

    Args:
        name: Node name
        status: Node status
        **kwargs: Additional kopf kwargs

    Returns:
        dict: Mapping of node_name to resource info
    """
    if not name:
        return {}

    capacity = status.get("capacity", {})
    allocatable = status.get("allocatable", {})
    conditions = status.get("conditions", [])

    # Check if node is ready
    ready = False
    for condition in conditions:
        if condition.get("type") == "Ready":
            ready = condition.get("status") == "True"
            break

    node_data = {
        "capacity": {
            "cpu": capacity.get("cpu", "0"),
            "memory": capacity.get("memory", "0"),
            "pods": capacity.get("pods", "0"),
        },
        "allocatable": {
            "cpu": allocatable.get("cpu", "0"),
            "memory": allocatable.get("memory", "0"),
            "pods": allocatable.get("pods", "0"),
        },
        "conditions": {
            cond.get("type", "Unknown"): cond.get("status", "Unknown") for cond in conditions
        },
        "ready": ready,
    }

    if not ready:
        log.warning("node_not_ready", node=name)

    return {name: node_data}


# ============================================================================
# Probe Handlers (Expose Index Stats)
# ============================================================================


@kopf.on.probe()
def pod_count_probe(
    *,
    pod_health_index: Index[Any, Any] | None = None,
    **_kwargs: Any,
) -> int:
    """Liveness probe: Return total number of indexed pods.

    Used by Prometheus/health checks to verify operator is functioning.

    Args:
        pod_health_index: The pod health index
        **kwargs: Additional kopf kwargs

    Returns:
        int: Number of pods currently indexed
    """
    return len(pod_health_index) if pod_health_index else 0


@kopf.on.probe()
def unhealthy_pod_count_probe(
    *,
    pod_health_index: Index[Any, Any] | None = None,
    **_kwargs: Any,
) -> int:
    """Liveness probe: Return count of unhealthy pods.

    Args:
        pod_health_index: The pod health index
        **_kwargs: Additional kopf kwargs

    Returns:
        int: Number of unhealthy pods
    """
    if not pod_health_index:
        return 0

    return sum(
        1
        for store in pod_health_index.values()
        for health in store
        if not health.get("healthy", True)
    )


@kopf.on.probe()
def deployment_count_probe(
    *,
    deployment_replica_index: Index[Any, Any] | None = None,
    **_kwargs: Any,
) -> int:
    """Liveness probe: Return total number of indexed deployments.

    Args:
        deployment_replica_index: The deployment replica index
        **kwargs: Additional kopf kwargs

    Returns:
        int: Number of deployments currently indexed
    """
    return len(deployment_replica_index) if deployment_replica_index else 0
