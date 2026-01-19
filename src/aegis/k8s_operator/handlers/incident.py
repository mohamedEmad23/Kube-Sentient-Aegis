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

from aegis.agent.graph import analyze_incident
from aegis.agent.state import IncidentSeverity
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    agent_iterations_total,
    incident_analysis_duration_seconds,
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


@kopf.on.create("pods", annotations={"aegis.io/monitor": kopf.PRESENT})  # type: ignore[misc]
async def handle_pod_creation(
    spec: Spec,
    meta: Meta,
    status: Status,
    name: str,
    namespace: str,
    uid: str,
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
    _ = (spec, meta, labels, annotations, body)  # Unused but required by kopf signature

    logger.info(
        "🤖 AEGIS monitoring enabled for pod",
        pod=name,
        namespace=namespace,
        uid=uid,
    )

    # Add AEGIS tracking annotation
    patch.metadata.annotations["aegis.io/monitored-since"] = kopf.utcnow().isoformat()
    patch.metadata.annotations["aegis.io/version"] = settings.app_version

    # Check if pod is already in a failed state
    phase = status.get("phase", "Unknown")

    if phase in ["Failed", "Unknown"]:
        logger.warning(
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
                logger=logger,
            ),
            name=f"analyze_pod_{namespace}_{name}",
        )
        # Store reference to prevent garbage collection
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return {
        "aegis-status": "monitoring-initialized",
        "pod-phase": phase,
        "monitored-at": kopf.utcnow().isoformat(),
    }


@kopf.on.field(  # type: ignore[misc]
    "pods",
    field="status.phase",
    annotations={"aegis.io/monitor": kopf.PRESENT},
)
async def handle_pod_phase_change(
    old: str | None,
    new: str | None,
    name: str,
    namespace: str,
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
    logger.info(
        "📊 Pod phase transition detected",
        pod=name,
        old_phase=old,
        new_phase=new,
    )

    # Check for unhealthy phases
    unhealthy_phases = ["Failed", "Unknown"]

    if new in unhealthy_phases:
        logger.error(
            "❌ Unhealthy pod phase detected",
            pod=name,
            phase=new,
            previous=old,
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
                phase=new or "Unknown",
                logger=logger,
            ),
            name=f"analyze_pod_phase_{namespace}_{name}",
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        # Update patch with incident marker
        patch.metadata.annotations["aegis.io/incident-detected"] = kopf.utcnow().isoformat()
        patch.metadata.annotations["aegis.io/incident-phase"] = new or "Unknown"

        return {
            "incident-detected": True,
            "incident-phase": new,
            "detection-time": kopf.utcnow().isoformat(),
        }

    # Check container statuses for waiting states
    container_statuses = status.get("containerStatuses", [])
    for container_status in container_statuses:
        waiting = container_status.get("state", {}).get("waiting")
        if waiting:
            reason = waiting.get("reason", "Unknown")
            if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
                logger.error(
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
                        logger=logger,
                    ),
                    name=f"analyze_container_{namespace}_{name}_{reason}",
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

                patch.metadata.annotations["aegis.io/container-error"] = reason

                return {
                    "container-error": reason,
                    "container-name": container_status.get("name"),
                    "detection-time": kopf.utcnow().isoformat(),
                }

    return None


# ============================================================================
# Deployment Handlers
# ============================================================================


@kopf.on.create("deployments", annotations={"aegis.io/monitor": kopf.PRESENT})  # type: ignore[misc]
async def handle_deployment_creation(
    spec: Spec,
    meta: Meta,
    status: Status,
    name: str,
    namespace: str,
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
    _ = (meta, status)  # Unused but required by kopf signature

    logger.info(
        "🚀 AEGIS monitoring enabled for deployment",
        deployment=name,
        namespace=namespace,
    )

    desired_replicas = spec.get("replicas", 1)

    # Add monitoring annotations
    patch.metadata.annotations["aegis.io/monitored-since"] = kopf.utcnow().isoformat()
    patch.metadata.annotations["aegis.io/desired-replicas"] = str(desired_replicas)

    return {
        "aegis-status": "monitoring-initialized",
        "desired-replicas": desired_replicas,
        "monitored-at": kopf.utcnow().isoformat(),
    }


@kopf.on.field(  # type: ignore[misc]
    "deployments",
    field="status.unavailableReplicas",
    annotations={"aegis.io/monitor": kopf.PRESENT},
)
async def handle_deployment_unavailable_replicas(
    old: int | None,
    new: int | None,
    name: str,
    namespace: str,
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
    if new and new > 0:
        logger.warning(
            "⚠️ Deployment has unavailable replicas",
            deployment=name,
            unavailable=new,
            previous=old,
        )

        desired_replicas = status.get("replicas", 0)

        # If more than 50% unavailable, trigger incident analysis
        if (
            desired_replicas > 0
            and (new / desired_replicas) > CRITICAL_REPLICAS_UNAVAILABLE_THRESHOLD
        ):
            logger.error(
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
                    logger=logger,
                ),
                name=f"analyze_deployment_{namespace}_{name}",
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

            patch.metadata.annotations["aegis.io/incident-detected"] = kopf.utcnow().isoformat()

            return {
                "incident-type": "unavailable-replicas",
                "unavailable-count": new,
                "desired-count": desired_replicas,
                "detection-time": kopf.utcnow().isoformat(),
            }

    return None


# ============================================================================
# Internal Analysis Functions
# ============================================================================


async def _analyze_pod_incident(
    resource_name: str,
    namespace: str,
    phase: str,
    logger: Logger,
) -> None:
    """Internal: Trigger AEGIS analysis workflow for pod incident.

    This function is called internally when a pod incident is detected.
    It invokes the LangGraph agent workflow to perform RCA and generate
    remediation proposals.

    Args:
        resource_name: Name of the pod
        namespace: Namespace of the pod
        phase: Current phase/error state
        logger: Logger instance

    Raises:
        Exception: Any exception from the analysis workflow
    """
    logger.info(
        "🔍 Starting AEGIS analysis for pod incident",
        pod=resource_name,
        phase=phase,
    )

    try:
        # Track analysis duration
        with incident_analysis_duration_seconds.labels(
            agent_name="pod_incident_analyzer",
        ).time():
            # Call the existing AEGIS agent workflow
            result = await analyze_incident(
                resource_type="Pod",
                resource_name=resource_name,
                namespace=namespace,
            )

        # Extract results
        rca_result = result.get("rca_result")
        fix_proposal = result.get("fix_proposal")

        if rca_result:
            logger.info(
                "✅ RCA completed",
                pod=resource_name,
                root_cause=rca_result.root_cause,
                confidence=rca_result.confidence_score,
            )

            agent_iterations_total.labels(
                agent_name="rca_agent",
                status="success",
            ).inc()

        if fix_proposal:
            logger.info(
                "🔧 Fix proposal generated",
                pod=resource_name,
                fix_type=fix_proposal.fix_type.value,
                confidence=fix_proposal.confidence_score,
            )

    except Exception as error:
        logger.exception(
            "❌ AEGIS analysis failed",
            pod=resource_name,
            error=str(error),
        )
        agent_iterations_total.labels(
            agent_name="pod_incident_analyzer",
            status="failed",
        ).inc()
        # Don't re-raise - we don't want to crash the operator
        # The incident will be retried on next phase change


async def _analyze_deployment_incident(
    resource_name: str,
    namespace: str,
    unavailable: int,
    desired: int,
    logger: Logger,
) -> None:
    """Internal: Trigger AEGIS analysis workflow for deployment incident.

    Args:
        resource_name: Deployment name
        namespace: Namespace
        unavailable: Number of unavailable replicas
        desired: Desired replica count
        logger: Logger instance
    """
    logger.info(
        "🔍 Starting AEGIS analysis for deployment incident",
        deployment=resource_name,
        unavailable=unavailable,
        desired=desired,
    )

    try:
        with incident_analysis_duration_seconds.labels(
            agent_name="deployment_incident_analyzer",
        ).time():
            result = await analyze_incident(
                resource_type="Deployment",
                resource_name=resource_name,
                namespace=namespace,
            )

        rca_result = result.get("rca_result")
        if rca_result:
            logger.info(
                "✅ Deployment RCA completed",
                deployment=resource_name,
                root_cause=rca_result.root_cause,
                confidence=rca_result.confidence_score,
            )

    except Exception as error:
        logger.exception(
            "❌ Deployment analysis failed",
            deployment=resource_name,
            error=str(error),
        )
