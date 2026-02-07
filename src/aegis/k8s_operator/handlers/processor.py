"""Incident queue processor daemon.

This module provides the background daemon that continuously processes
incidents from the priority queue and routes them through the AEGIS workflow.
"""

import asyncio
from typing import Any

import kopf

from aegis.agent.graph import analyze_incident
from aegis.agent.state import IncidentPriority, IncidentState
from aegis.incident import get_incident_queue
from aegis.observability._logging import get_logger
from aegis.observability._metrics import incident_queue_processing_duration_seconds


log = get_logger(__name__)

# Track background tasks
_processor_task: asyncio.Task[Any] | None = None


@kopf.on.startup()
async def start_incident_processor(**_kwargs: Any) -> None:
    """Kopf startup handler to launch the incident queue processor daemon.

    This handler is called when the operator starts up, before any resource
    events are processed. It launches the incident queue processor as a
    background task that runs for the lifetime of the operator.
    """
    global _processor_task

    log.info("🚀 Starting incident queue processor daemon")

    try:
        # Launch processor as background task
        _processor_task = asyncio.create_task(
            process_incident_queue(),
            name="incident_queue_processor",
        )

        log.info(
            "✅ Incident queue processor started",
            task_name=_processor_task.get_name(),
        )

    except Exception:
        log.exception("❌ Failed to start incident queue processor")
        raise


@kopf.on.cleanup()
async def stop_incident_processor(**_kwargs: Any) -> None:
    """Kopf cleanup handler to stop the incident queue processor.

    This handler is called when the operator is shutting down.
    """
    global _processor_task

    if _processor_task and not _processor_task.done():
        log.info("🛑 Stopping incident queue processor")
        _processor_task.cancel()

        try:
            await _processor_task
        except asyncio.CancelledError:
            log.info("✅ Incident queue processor stopped")


async def process_incident_queue() -> None:
    """Main daemon to continuously process incidents from the queue.

    This function runs in a background task and:
    1. Dequeues highest priority incidents (P0 → P1 → P2 → P3 → P4)
    2. Checks production lock status (P0 incidents lock production)
    3. Routes incidents through the AEGIS LangGraph workflow
    4. Updates incident state with final results

    The processor respects production locks - if production is locked,
    it requeues the incident and waits before trying again.
    """
    queue = get_incident_queue()

    log.info("🚀 Starting incident queue processor daemon")

    while True:
        try:
            # Dequeue highest priority incident (blocks if empty, timeout 30s)
            incident = await queue.dequeue(timeout=30.0)

            if not incident:
                # Queue empty - sleep and retry
                await asyncio.sleep(5)
                continue

            incident_id = incident.get("incident_id", "unknown")
            priority = incident.get("priority")
            resource_type = incident.get("resource_type")
            resource_name = incident.get("resource_name")
            namespace = incident.get("namespace", "default")

            log.info(
                "📨 Dequeued incident for processing",
                incident_id=incident_id,
                priority=priority.value if priority else "unknown",
                resource=f"{resource_type}/{resource_name}",
            )

            # Check production lock
            locked, reason = queue.is_production_locked()

            if locked:
                log.warning(
                    "🔒 Production locked - requeueing incident",
                    incident_id=incident_id,
                    lock_reason=reason,
                )

                # Requeue the incident
                await queue.enqueue(incident)
                await asyncio.sleep(10)  # Wait before next dequeue
                continue

            # Process incident through AEGIS workflow
            with incident_queue_processing_duration_seconds.time():
                result = await _process_single_incident(incident)

            # Update priority if RCA refined it
            if result and result.get("rca_result"):
                rca_result = result["rca_result"]
                severity = rca_result.severity
                refined_priority = IncidentPriority.from_severity(severity)

                # If incident was upgraded to P0, lock production
                if refined_priority == IncidentPriority.P0 and priority != IncidentPriority.P0:
                    queue.lock_production(f"P0 incident detected: {incident_id}")
                    log.error(
                        "🔴 P0 incident detected - locking production deployments",
                        incident_id=incident_id,
                        severity=severity.value,
                    )

            log.info(
                "✅ Incident processing completed",
                incident_id=incident_id,
                final_agent=result.get("current_agent") if result else None,
            )

        except asyncio.CancelledError:
            log.info("🛑 Incident queue processor shutting down")
            raise

        except Exception:
            log.exception("❌ Error processing incident queue")
            await asyncio.sleep(5)  # Backoff on error


async def _process_single_incident(incident: IncidentState) -> IncidentState | None:
    """Process a single incident through the AEGIS workflow.

    Args:
        incident: Incident state to process

    Returns:
        Final incident state after workflow completion, or None if error
    """
    resource_type = incident.get("resource_type")
    resource_name = incident.get("resource_name")
    namespace = incident.get("namespace", "default")
    incident_id = incident.get("incident_id", "unknown")

    if not resource_type or not resource_name:
        log.error(
            "Invalid incident - missing required fields",
            incident_id=incident_id,
            has_resource_type=bool(resource_type),
            has_resource_name=bool(resource_name),
        )
        return None

    try:
        # Run through AEGIS workflow (RCA → Solution → Verifier → Approval → Deployment → Rollback Monitor)
        result = await analyze_incident(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )

        return result

    except Exception:
        log.exception(
            "Failed to process incident",
            incident_id=incident_id,
            resource=f"{resource_type}/{resource_name}",
        )
        return None


__all__ = ["process_incident_queue"]
