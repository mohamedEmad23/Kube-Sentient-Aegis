"""AEGIS Incident Detection and Remediation Handlers.

Kopf-based event handlers that detect Kubernetes resource issues
and trigger the AEGIS AI-driven remediation workflow.

This module provides:
- Pod incident detection (CrashLoopBackOff, ImagePullBackOff, OOMKilled, etc.)
- Deployment health monitoring
- Automatic triggering of RCA agent workflow
- Status annotation updates with analysis results
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import kopf
from kopf import (
    Annotations,
    Body,
    Labels,
    Logger,
    Meta,
    Patch,
    Spec,
    Status,
)

from aegis.agent.state import IncidentSeverity
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    agent_iterations_total,
    incidents_detected_total,
)


# Get structured logger for this module
log = get_logger(__name__)


# Constants for magic values
CRITICAL_REPLICAS_UNAVAILABLE_THRESHOLD = 0.5

# Track background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task[Any]] = set()


# ============================================================================
# Pod Incident Handlers
# ============================================================================


@kopf.on.create("pods", annotations={"aegis.io/monitor": kopf.PRESENT})
async def handle_pod_creation(
    *,
    spec: Spec,
    meta: Meta,
    status: Status,
    name: str | None,
    namespace: str | None,
    uid: str | None,
    labels: Labels,
    annotations: Annotations,
    body: Body,
    patch: Patch,
    logger: Logger,
    **_kwargs: Any,
) -> dict[str, Any] | None:
    """Handle new pod creation with AEGIS monitoring enabled.

    This handler is triggered when a pod is created with the annotation
    `aegis.io/monitor: "enabled"`. It initializes monitoring and checks
    for immediate issues.

    Args:
        spec: Pod specification (desired state)
        meta: Pod metadata (name, namespace, labels, annotations)
        status: Pod status (current state)
        name: Pod name
        namespace: Namespace where pod resides
        uid: Unique identifier for the pod
        labels: Pod labels
        annotations: Pod annotations
        body: Full pod resource body
        patch: Patch object to modify the pod
        logger: Kopf-provided logger with context
        **_kwargs: Additional kopf kwargs (memo, retry, etc.)

    Returns:
        dict: Status to be written to pod annotations/status
              Contains AEGIS analysis metadata

    Raises:
        kopf.TemporaryError: For transient errors that should be retried
        kopf.PermanentError: For permanent errors that should not retry
    """
    _ = (logger, spec, meta, labels, annotations, body)  # Unused but required by kopf signature
    if name is None or namespace is None or uid is None:
        return None

    log.info(
        "🤖 AEGIS monitoring enabled for pod",
        pod=name,
        namespace=namespace,
        uid=uid,
    )

    # Add AEGIS tracking annotation
    patch.metadata.annotations["aegis.io/monitored-since"] = datetime.now(UTC).isoformat()
    patch.metadata.annotations["aegis.io/version"] = settings.app_version

    # Check if pod is already in a failed state
    phase = status.get("phase", "Unknown")

    if phase in ["Failed", "Unknown"]:
        log.warning(
            "⚠️ Pod in failed state immediately after creation",
            pod=name,
            phase=phase,
        )

        # Increment Prometheus metrics
        incidents_detected_total.labels(
            severity=IncidentSeverity.HIGH.value,
            resource_type="Pod",
            namespace=namespace,
        ).inc()

        # Trigger AEGIS analysis workflow (async)
        task = asyncio.create_task(
            _analyze_pod_incident(
                resource_name=name,
                namespace=namespace,
                phase=phase,
            ),
            name=f"analyze_pod_{namespace}_{name}",
        )
        # Store reference to prevent garbage collection
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return {
        "aegis-status": "monitoring-initialized",
        "pod-phase": phase,
        "monitored-at": datetime.now(UTC).isoformat(),
    }


@kopf.on.field(
    "pods",
    field="status.phase",
    annotations={"aegis.io/monitor": kopf.PRESENT},
)
async def handle_pod_phase_change(
    *,
    old: Any | None,
    new: Any | None,
    name: str | None,
    namespace: str | None,
    status: Status,
    patch: Patch,
    logger: Logger,
    **_kwargs: Any,
) -> dict[str, Any] | None:
    """Handle pod phase transitions and detect incidents.

    This handler is triggered when the `status.phase` field of a monitored pod
    changes. It detects unhealthy states and triggers AEGIS remediation.

    Monitored phases:
    - CrashLoopBackOff (via containerStatuses)
    - ImagePullBackOff (via containerStatuses)
    - Failed
    - Unknown

    Args:
        old: Previous phase value
        new: New phase value
        name: Pod name
        namespace: Namespace
        status: Full pod status
        patch: Patch object to update pod
        logger: Kopf logger
        **kwargs: Additional kopf kwargs

    Returns:
        dict: Analysis results to store in pod status
    """
    _ = (logger, patch)
    if name is None or namespace is None:
        return None

    old_phase = str(old) if old is not None else None
    new_phase = str(new) if new is not None else None

    log.info(
        "📊 Pod phase transition detected",
        pod=name,
        old_phase=old_phase,
        new_phase=new_phase,
    )

    # Check for unhealthy phases
    unhealthy_phases = ["Failed", "Unknown"]

    if new_phase in unhealthy_phases:
        log.error(
            "❌ Unhealthy pod phase detected",
            pod=name,
            phase=new_phase,
            previous=old_phase,
        )

        # Record incident detection
        incidents_detected_total.labels(
            severity=IncidentSeverity.CRITICAL.value,
            resource_type="Pod",
            namespace=namespace,
        ).inc()

        # Trigger AEGIS analysis
        task = asyncio.create_task(
            _analyze_pod_incident(
                resource_name=name,
                namespace=namespace,
                phase=new_phase or "Unknown",
            ),
            name=f"analyze_pod_phase_{namespace}_{name}",
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        # Update patch with incident marker
        patch.metadata.annotations["aegis.io/incident-detected"] = datetime.now(UTC).isoformat()
        patch.metadata.annotations["aegis.io/incident-phase"] = new_phase or "Unknown"

        return {
            "incident-detected": True,
            "incident-phase": new_phase,
            "detection-time": datetime.now(UTC).isoformat(),
        }

    # Check container statuses for waiting states
    container_statuses = status.get("containerStatuses", [])
    for container_status in container_statuses:
        waiting = container_status.get("state", {}).get("waiting")
        if waiting:
            reason = waiting.get("reason", "Unknown")
            if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
                log.error(
                    "❌ Container waiting with error",
                    pod=name,
                    container=container_status.get("name"),
                    reason=reason,
                )

                incidents_detected_total.labels(
                    severity=IncidentSeverity.HIGH.value,
                    resource_type="Pod",
                    namespace=namespace,
                ).inc()

                # Trigger analysis
                task = asyncio.create_task(
                    _analyze_pod_incident(
                        resource_name=name,
                        namespace=namespace,
                        phase=reason,
                    ),
                    name=f"analyze_container_{namespace}_{name}_{reason}",
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

                patch.metadata.annotations["aegis.io/container-error"] = reason

                return {
                    "container-error": reason,
                    "container-name": container_status.get("name"),
                    "detection-time": datetime.now(UTC).isoformat(),
                }

    return None


# ============================================================================
# Deployment Handlers
# ============================================================================


@kopf.on.create("deployments", annotations={"aegis.io/monitor": kopf.PRESENT})
async def handle_deployment_creation(
    *,
    spec: Spec,
    meta: Meta,
    status: Status,
    name: str | None,
    namespace: str | None,
    patch: Patch,
    logger: Logger,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle new deployment creation with AEGIS monitoring.

    Initializes AEGIS monitoring for a deployment. Tracks replica health,
    rollout status, and readiness.

    Args:
        spec: Deployment specification
        meta: Deployment metadata
        status: Deployment status
        name: Deployment name
        namespace: Namespace
        patch: Patch object
        logger: Kopf logger
        **_kwargs: Additional kopf kwargs

    Returns:
        dict: Status information for deployment
    """
    _ = (logger, meta, status)  # Unused but required by kopf signature
    if name is None or namespace is None:
        return {}

    log.info(
        "🚀 AEGIS monitoring enabled for deployment",
        deployment=name,
        namespace=namespace,
    )

    desired_replicas = spec.get("replicas", 1)

    # Add monitoring annotations
    patch.metadata.annotations["aegis.io/monitored-since"] = datetime.now(UTC).isoformat()
    patch.metadata.annotations["aegis.io/desired-replicas"] = str(desired_replicas)

    return {
        "aegis-status": "monitoring-initialized",
        "desired-replicas": desired_replicas,
        "monitored-at": datetime.now(UTC).isoformat(),
    }


@kopf.on.field(
    "deployments",
    field="status.unavailableReplicas",
    annotations={"aegis.io/monitor": kopf.PRESENT},
)
async def handle_deployment_unavailable_replicas(
    *,
    old: Any | None,
    new: Any | None,
    name: str | None,
    namespace: str | None,
    status: Status,
    patch: Patch,
    logger: Logger,
    **_kwargs: Any,
) -> dict[str, Any] | None:
    """Handle changes in unavailable replicas count.

    Detects when a deployment has unavailable replicas and triggers
    AEGIS analysis to identify root cause.

    Args:
        old: Previous unavailable count
        new: New unavailable count
        name: Deployment name
        namespace: Namespace
        status: Full deployment status
        patch: Patch object
        logger: Kopf logger
        **_kwargs: Additional kopf kwargs

    Returns:
        dict: Analysis metadata if incident detected
    """
    _ = logger
    if name is None or namespace is None or not isinstance(new, int) or new <= 0:
        return None

    previous = old if isinstance(old, int) else None

    if new > 0:
        log.warning(
            "⚠️ Deployment has unavailable replicas",
            deployment=name,
            unavailable=new,
            previous=previous,
        )

        desired_replicas = int(status.get("replicas", 0) or 0)

        # If more than 50% unavailable, trigger incident analysis
        if (
            desired_replicas > 0
            and (new / desired_replicas) > CRITICAL_REPLICAS_UNAVAILABLE_THRESHOLD
        ):
            log.error(
                "❌ Critical: More than 50% replicas unavailable",
                deployment=name,
                unavailable=new,
                desired=desired_replicas,
            )

            incidents_detected_total.labels(
                severity=IncidentSeverity.CRITICAL.value,
                resource_type="Deployment",
                namespace=namespace,
            ).inc()

            # Trigger AEGIS analysis for deployment
            task = asyncio.create_task(
                _analyze_deployment_incident(
                    resource_name=name,
                    namespace=namespace,
                    unavailable=new,
                    desired=desired_replicas,
                ),
                name=f"analyze_deployment_{namespace}_{name}",
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

            patch.metadata.annotations["aegis.io/incident-detected"] = datetime.now(UTC).isoformat()

            return {
                "incident-type": "unavailable-replicas",
                "unavailable-count": new,
                "desired-count": desired_replicas,
                "detection-time": datetime.now(UTC).isoformat(),
            }

    return None


# ============================================================================
# Internal Analysis Functions
# ============================================================================


async def _analyze_pod_incident(
    resource_name: str,
    namespace: str,
    phase: str,
) -> None:
    """Internal: Enqueue pod incident for analysis via incident queue.

    This function is called internally when a pod incident is detected.
    It creates an incident state and enqueues it with priority for processing.

    Args:
        resource_name: Name of the pod
        namespace: Namespace of the pod
        phase: Current phase/error state

    Raises:
        Exception: Any exception from the queue enqueue operation
    """
    from aegis.agent.state import IncidentPriority, create_initial_state
    from aegis.incident import get_incident_queue

    log.info(
        "🔍 Enqueuing pod incident for analysis",
        pod=resource_name,
        phase=phase,
        namespace=namespace,
    )

    try:
        # Create incident state
        state = create_initial_state(
            resource_type="Pod",
            resource_name=resource_name,
            namespace=namespace,
        )

        # Assign initial priority based on phase severity
        # CrashLoopBackOff/ImagePullBackOff → P1 (high)
        # Failed/Unknown → P0 (critical)
        if phase in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
            state["priority"] = IncidentPriority.P1
        elif phase in ["Failed", "Unknown"]:
            state["priority"] = IncidentPriority.P0
        else:
            state["priority"] = IncidentPriority.P2

        # Generate unique incident ID
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        state["incident_id"] = f"inc-{timestamp}-{namespace}-{resource_name}"

        # Enqueue incident for processing
        queue = get_incident_queue()
        incident_id = await queue.enqueue(state)

        log.info(
            "✅ Incident enqueued",
            incident_id=incident_id,
            priority=state["priority"].value,
            pod=resource_name,
        )

        agent_iterations_total.labels(
            agent_name="pod_incident_detector",
            status="enqueued",
        ).inc()

    except Exception:
        log.exception(
            "❌ Failed to enqueue pod incident",
            pod=resource_name,
            phase=phase,
        )
        agent_iterations_total.labels(
            agent_name="pod_incident_detector",
            status="failed",
        ).inc()
        # Don't re-raise - we don't want to crash the operator
        # The incident will be retried on next phase change


async def _analyze_deployment_incident(
    resource_name: str,
    namespace: str,
    unavailable: int,
    desired: int,
) -> None:
    """Internal: Enqueue deployment incident for analysis via incident queue.

    Args:
        resource_name: Deployment name
        namespace: Namespace
        unavailable: Number of unavailable replicas
        desired: Desired replica count
    """
    from aegis.agent.state import IncidentPriority, create_initial_state
    from aegis.incident import get_incident_queue

    log.info(
        "🔍 Enqueuing deployment incident for analysis",
        deployment=resource_name,
        unavailable=unavailable,
        desired=desired,
        namespace=namespace,
    )

    try:
        # Create incident state
        state = create_initial_state(
            resource_type="Deployment",
            resource_name=resource_name,
            namespace=namespace,
        )

        # Assign priority based on percentage unavailable
        unavailable_pct = unavailable / desired if desired > 0 else 0

        if unavailable_pct > 0.75:  # >75% unavailable
            state["priority"] = IncidentPriority.P0  # Critical
        elif unavailable_pct > 0.5:  # >50% unavailable
            state["priority"] = IncidentPriority.P1  # High
        elif unavailable_pct > 0.25:  # >25% unavailable
            state["priority"] = IncidentPriority.P2  # Medium
        else:
            state["priority"] = IncidentPriority.P3  # Low

        # Generate unique incident ID
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        state["incident_id"] = f"inc-{timestamp}-{namespace}-{resource_name}"

        # Enqueue incident
        queue = get_incident_queue()
        incident_id = await queue.enqueue(state)

        log.info(
            "✅ Deployment incident enqueued",
            incident_id=incident_id,
            priority=state["priority"].value,
            deployment=resource_name,
            unavailable_pct=f"{unavailable_pct:.1%}",
        )

        agent_iterations_total.labels(
            agent_name="deployment_incident_detector",
            status="enqueued",
        ).inc()

    except Exception:
        log.exception(
            "❌ Failed to enqueue deployment incident",
            deployment=resource_name,
        )
        agent_iterations_total.labels(
            agent_name="deployment_incident_detector",
            status="failed",
        ).inc()
