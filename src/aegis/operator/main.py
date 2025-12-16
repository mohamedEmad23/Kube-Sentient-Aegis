"""AEGIS Kubernetes Operator main entry point.

This module contains the Kopf-based operator that watches for
Kubernetes events and triggers the AEGIS incident response workflow.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import TYPE_CHECKING, Any

import kopf
import structlog

from aegis.config.settings import get_settings
from aegis.observability.logging import configure_logging

if TYPE_CHECKING:
    from collections.abc import MutableMapping

# Configure structured logging
configure_logging()
logger = structlog.get_logger(__name__)


@kopf.on.startup()
async def startup_handler(
    settings: kopf.OperatorSettings, **_kwargs: Any
) -> None:
    """Configure the operator on startup."""
    app_settings = get_settings()

    # Configure Kopf settings
    settings.posting.level = logging.WARNING
    settings.watching.server_timeout = 300
    settings.watching.client_timeout = 300
    settings.batching.batch_window = 1.0

    # Log startup
    logger.info(
        "aegis_operator_starting",
        version=app_settings.version,
        environment=app_settings.environment,
        shadow_mode=app_settings.shadow_mode_enabled,
    )


@kopf.on.cleanup()
async def cleanup_handler(**_kwargs: Any) -> None:
    """Clean up resources when the operator is shutting down."""
    logger.info("aegis_operator_shutting_down")


# ============================================================================
# Pod Event Handlers
# ============================================================================


@kopf.on.event("", "v1", "pods")
async def pod_event_handler(
    event: MutableMapping[str, Any],
    body: kopf.Body,
    meta: kopf.Meta,
    spec: kopf.Spec,
    status: kopf.Status,
    **_kwargs: Any,
) -> None:
    """Handle pod events for incident detection."""
    event_type = event.get("type", "UNKNOWN")
    pod_name = meta.get("name", "unknown")
    namespace = meta.get("namespace", "default")

    # Skip if pod is in a system namespace
    if namespace in ("kube-system", "kube-public", "kube-node-lease"):
        return

    # Check for pod failures
    pod_phase = status.get("phase", "Unknown")
    container_statuses = status.get("containerStatuses", [])

    # Detect crash loops
    for container_status in container_statuses:
        restart_count = container_status.get("restartCount", 0)
        waiting = container_status.get("waiting", {})
        waiting_reason = waiting.get("reason", "")

        if restart_count >= 3 or waiting_reason in (
            "CrashLoopBackOff",
            "ImagePullBackOff",
            "ErrImagePull",
        ):
            logger.warning(
                "pod_failure_detected",
                pod=pod_name,
                namespace=namespace,
                phase=pod_phase,
                restart_count=restart_count,
                reason=waiting_reason,
            )

            # Trigger incident analysis
            await _trigger_incident_analysis(
                resource_type="pod",
                resource_name=pod_name,
                namespace=namespace,
                reason=waiting_reason or f"RestartCount={restart_count}",
            )


@kopf.on.event("", "v1", "events")
async def k8s_event_handler(
    event: MutableMapping[str, Any],
    body: kopf.Body,
    **_kwargs: Any,
) -> None:
    """Handle Kubernetes events for incident detection."""
    event_type = body.get("type", "Normal")
    reason = body.get("reason", "")
    message = body.get("message", "")
    involved_object = body.get("involvedObject", {})

    # Only process Warning events
    if event_type != "Warning":
        return

    # Skip system namespaces
    namespace = involved_object.get("namespace", "default")
    if namespace in ("kube-system", "kube-public", "kube-node-lease"):
        return

    # Log the warning event
    logger.info(
        "kubernetes_warning_event",
        reason=reason,
        message=message[:200],
        kind=involved_object.get("kind"),
        name=involved_object.get("name"),
        namespace=namespace,
    )


# ============================================================================
# Custom Resource Handlers (AegisIncident CRD)
# ============================================================================


@kopf.on.create("aegis.io", "v1alpha1", "incidents")
async def incident_created(
    body: kopf.Body,
    meta: kopf.Meta,
    spec: kopf.Spec,
    status: kopf.Status,
    patch: kopf.Patch,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle AegisIncident creation."""
    incident_name = meta.get("name", "unknown")
    namespace = meta.get("namespace", "default")

    logger.info(
        "incident_created",
        name=incident_name,
        namespace=namespace,
        severity=spec.get("severity", "unknown"),
    )

    # Update status to indicate processing
    patch.status["phase"] = "Analyzing"
    patch.status["startedAt"] = kopf.datetime_now_iso()

    return {"phase": "Analyzing", "message": "Incident analysis started"}


@kopf.on.update("aegis.io", "v1alpha1", "incidents")
async def incident_updated(
    body: kopf.Body,
    meta: kopf.Meta,
    spec: kopf.Spec,
    old: kopf.Body,
    new: kopf.Body,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle AegisIncident updates."""
    incident_name = meta.get("name", "unknown")

    logger.info(
        "incident_updated",
        name=incident_name,
    )

    return {"message": "Incident updated"}


@kopf.on.delete("aegis.io", "v1alpha1", "incidents")
async def incident_deleted(
    body: kopf.Body,
    meta: kopf.Meta,
    **_kwargs: Any,
) -> None:
    """Handle AegisIncident deletion."""
    incident_name = meta.get("name", "unknown")

    logger.info(
        "incident_deleted",
        name=incident_name,
    )


# ============================================================================
# Helper Functions
# ============================================================================


async def _trigger_incident_analysis(
    resource_type: str,
    resource_name: str,
    namespace: str,
    reason: str,
) -> None:
    """Trigger the incident analysis workflow."""
    settings = get_settings()

    logger.info(
        "triggering_incident_analysis",
        resource_type=resource_type,
        resource_name=resource_name,
        namespace=namespace,
        reason=reason,
        shadow_mode=settings.shadow_mode_enabled,
    )

    # TODO: Integrate with the agent module for actual analysis
    # For now, just log the incident
    if settings.shadow_mode_enabled:
        logger.info(
            "shadow_mode_active",
            message="Would analyze incident but shadow mode is enabled",
        )


# ============================================================================
# Main Entry Point
# ============================================================================


def run(
    dev_mode: bool = False,
    namespace: str | None = None,
) -> int:
    """Run the AEGIS operator."""
    settings = get_settings()

    logger.info(
        "starting_aegis_operator",
        dev_mode=dev_mode,
        namespace=namespace or "all",
        environment=settings.environment,
    )

    try:
        # Build kopf arguments
        kopf_args = ["run", __file__]

        if dev_mode:
            kopf_args.append("--dev")
            kopf_args.append("--verbose")

        if namespace:
            kopf_args.extend(["--namespace", namespace])

        # Run kopf
        kopf.cli.main(kopf_args)
        return 0

    except KeyboardInterrupt:
        logger.info("operator_interrupted")
        return 0
    except Exception as e:
        logger.exception("operator_failed", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(run(dev_mode="--dev" in sys.argv))
