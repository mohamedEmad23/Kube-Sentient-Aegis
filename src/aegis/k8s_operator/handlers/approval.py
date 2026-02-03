"""AEGIS Incident Approval Workflow Handlers.

Kopf-based handlers for the human-in-the-loop approval workflow.
This module provides:

1. Approval timeout daemon - Auto-rejects incidents after timeout (default: 15 minutes)
2. Approval phase watcher - Triggers fix application when approved
3. Fix result handler - Monitors post-fix health

Workflow:
  Detected → Analyzing → AwaitingApproval → (Approved/Rejected/Timeout)
                                     ↓
                                ApplyingFix → Monitoring → Resolved/Failed
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import kopf
from kubernetes import client
from kubernetes import config as k8s_config

from aegis.config.settings import settings
from aegis.crd import (
    AEGIS_API_GROUP,
    AEGIS_API_VERSION,
    AEGIS_INCIDENT_PLURAL,
    AegisIncident,
    ApprovalStatus,
    IncidentPhase,
)
from aegis.kubernetes.fix_applier import get_fix_applier
from aegis.kubernetes.monitoring import get_post_fix_monitor
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    agent_iterations_total,
)


log = get_logger(__name__)

# Default approval timeout (15 minutes)
DEFAULT_APPROVAL_TIMEOUT_MINUTES = settings.incident.approval_timeout_minutes

# Post-fix monitoring duration (5 minutes)
POST_FIX_MONITORING_SECONDS = settings.incident.post_fix_monitoring_seconds

# Track background tasks
_approval_tasks: set[asyncio.Task[Any]] = set()


def _init_k8s_clients() -> tuple[client.CoreV1Api, client.CustomObjectsApi]:
    """Initialize Kubernetes clients."""
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    return client.CoreV1Api(), client.CustomObjectsApi()


# ============================================================================
# Approval Timeout Daemon
# ============================================================================


@kopf.daemon(
    group=AEGIS_API_GROUP,
    version=AEGIS_API_VERSION,
    plural=AEGIS_INCIDENT_PLURAL,
    field="status.phase",
    value="AwaitingApproval",
)
async def approval_timeout_daemon(
    *,
    name: str | None,
    namespace: str | None,
    body: kopf.Body,
    stopped: kopf.DaemonStopped,
    **_kwargs: Any,
) -> None:
    """Daemon that monitors approval timeout and auto-rejects expired incidents.

    This daemon runs for each incident in AwaitingApproval phase.
    It checks the approval deadline and automatically rejects the
    incident if the timeout expires without human action.

    Args:
        name: Incident name
        namespace: Incident namespace
        body: Full incident body
        stopped: Daemon stop signal
        **_kwargs: Additional kopf kwargs
    """
    if name is None or namespace is None:
        return

    log.info(
        "approval_timeout_daemon_started",
        incident=name,
        namespace=namespace,
    )

    _, custom_api = _init_k8s_clients()

    # Get or set timeout deadline
    spec = body.get("spec", {})
    approval = spec.get("approval", {})
    timeout_at_str = approval.get("timeoutAt")

    if timeout_at_str:
        # Parse existing timeout
        try:
            timeout_at = datetime.fromisoformat(timeout_at_str.replace("Z", "+00:00"))
        except ValueError:
            # Invalid format, set new timeout
            timeout_at = None
    else:
        timeout_at = None

    if not timeout_at:
        # Set timeout based on config (default 15 minutes)
        timeout_minutes = approval.get("timeoutMinutes", DEFAULT_APPROVAL_TIMEOUT_MINUTES)
        timeout_at = datetime.now(UTC) + timedelta(minutes=timeout_minutes)

        # Update incident with timeout deadline
        patch_body = {
            "spec": {
                "approval": {
                    "timeoutAt": timeout_at.isoformat() + "Z",
                }
            }
        }
        try:
            custom_api.patch_namespaced_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                namespace=namespace,
                plural=AEGIS_INCIDENT_PLURAL,
                name=name,
                body=patch_body,
            )
            log.info(
                "approval_timeout_set",
                incident=name,
                timeout_at=timeout_at.isoformat(),
            )
        except client.ApiException as e:
            log.exception("approval_timeout_update_failed", error=e.reason)

    # Wait for timeout or daemon stop
    while not stopped:
        now = datetime.now(UTC)

        if now >= timeout_at:
            log.warning(
                "approval_timeout_expired",
                incident=name,
                namespace=namespace,
            )

            # Auto-reject due to timeout
            try:
                reject_patch = {
                    "spec": {
                        "approval": {
                            "status": ApprovalStatus.TIMEOUT.value,
                            "rejectedAt": now.isoformat() + "Z",
                            "rejectionReason": "Approval timeout expired without human action",
                        }
                    },
                    "status": {
                        "phase": IncidentPhase.TIMEOUT.value,
                    },
                }
                custom_api.patch_namespaced_custom_object(
                    group=AEGIS_API_GROUP,
                    version=AEGIS_API_VERSION,
                    namespace=namespace,
                    plural=AEGIS_INCIDENT_PLURAL,
                    name=name,
                    body=reject_patch,
                )

                log.info(
                    "incident_auto_rejected_timeout",
                    incident=name,
                )

                agent_iterations_total.labels(
                    agent_name="approval_daemon",
                    status="timeout",
                ).inc()

            except client.ApiException as e:
                log.exception("timeout_rejection_failed", error=e.reason)

            return  # Exit daemon

        # Check every 30 seconds
        await asyncio.sleep(30)

    log.info(
        "approval_timeout_daemon_stopped",
        incident=name,
        reason="incident_updated_or_deleted",
    )


# ============================================================================
# Approval Phase Change Handler
# ============================================================================


@kopf.on.field(
    group=AEGIS_API_GROUP,
    version=AEGIS_API_VERSION,
    plural=AEGIS_INCIDENT_PLURAL,
    field="spec.approval.status",
)
async def handle_approval_status_change(
    *,
    old: Any | None,
    new: Any | None,
    name: str | None,
    namespace: str | None,
    body: kopf.Body,
    patch: kopf.Patch,
    logger: Any,
    **_kwargs: Any,
) -> dict[str, Any] | None:
    """Handle changes to approval status.

    Triggered when spec.approval.status changes. If changed to 'approved',
    triggers the fix application workflow.

    Args:
        old: Previous approval status
        new: New approval status
        name: Incident name
        namespace: Namespace
        body: Full incident body
        patch: Patch object
        **_kwargs: Additional kopf kwargs

    Returns:
        Handler status dict or None
    """
    _ = logger
    if name is None or namespace is None:
        return None

    old_status = str(old) if old is not None else None
    new_status = str(new) if new is not None else None

    log.info(
        "approval_status_changed",
        incident=name,
        old_status=old_status,
        new_status=new_status,
    )

    if new_status == ApprovalStatus.APPROVED.value:
        log.info(
            "incident_approved",
            incident=name,
            namespace=namespace,
        )

        # Update phase to ApplyingFix
        patch.status["phase"] = IncidentPhase.APPLYING_FIX.value

        # Trigger fix application in background
        task = asyncio.create_task(
            _apply_approved_fix(name, namespace, body),
            name=f"apply_fix_{namespace}_{name}",
        )
        _approval_tasks.add(task)
        task.add_done_callback(_approval_tasks.discard)

        agent_iterations_total.labels(
            agent_name="approval_handler",
            status="approved",
        ).inc()

        return {
            "approved": True,
            "approved_at": datetime.now(UTC).isoformat(),
        }

    if new_status == ApprovalStatus.REJECTED.value:
        log.info(
            "incident_rejected",
            incident=name,
            namespace=namespace,
        )

        # Phase already updated by CLI, just log
        agent_iterations_total.labels(
            agent_name="approval_handler",
            status="rejected",
        ).inc()

        return {
            "rejected": True,
            "rejected_at": datetime.now(UTC).isoformat(),
        }

    return None


async def _apply_approved_fix(
    incident_name: str,
    namespace: str,
    body: kopf.Body,
) -> None:
    """Apply the approved fix to the target resource.

    This function:
    1. Extracts the fix proposal from the incident
    2. Applies the fix with dry-run validation
    3. Updates incident status with result
    4. Triggers post-fix monitoring

    Args:
        incident_name: Name of the incident
        namespace: Namespace of the incident
        body: Full incident body
    """
    log.info(
        "applying_approved_fix",
        incident=incident_name,
        namespace=namespace,
    )

    _, custom_api = _init_k8s_clients()
    fix_applier = get_fix_applier()

    # Parse incident
    incident = AegisIncident.from_kubernetes_object(cast(dict[str, Any], body))

    if not incident.spec.fix_proposal:
        log.error(
            "no_fix_proposal",
            incident=incident_name,
        )
        await _update_fix_status(
            custom_api,
            incident_name,
            namespace,
            success=False,
            error="No fix proposal available",
        )
        return

    # Get target resource info
    resource_ref = incident.spec.resource_ref
    fix_proposal = incident.spec.fix_proposal

    # Convert CRD FixProposal to applier FixProposal
    from aegis.crd import FixProposal as CRDFixProposalClass
    from aegis.crd import FixType

    applier_proposal = CRDFixProposalClass(
        fix_type=FixType(fix_proposal.fix_type.value),
        description=fix_proposal.description,
        commands=fix_proposal.commands,
        manifests=fix_proposal.manifests,
        patch=fix_proposal.patch,
        confidence_score=fix_proposal.confidence_score,
        risks=fix_proposal.risks,
        estimated_downtime=fix_proposal.estimated_downtime,
    )

    # Apply the fix
    result = await fix_applier.apply_fix(
        fix_proposal=applier_proposal,
        resource_kind=resource_ref.kind,
        resource_name=resource_ref.name,
        namespace=resource_ref.namespace or namespace,
    )

    if result.success:
        log.info(
            "fix_applied_successfully",
            incident=incident_name,
            resource=f"{resource_ref.kind}/{resource_ref.name}",
        )

        # Update incident with success
        await _update_fix_status(
            custom_api,
            incident_name,
            namespace,
            success=True,
            applied_at=result.applied_at,
            resource_version=result.resource_version,
        )

        agent_iterations_total.labels(
            agent_name="fix_applier",
            status="success",
        ).inc()

        # Start post-fix monitoring
        monitor = get_post_fix_monitor()
        await monitor.monitor_resource(
            resource_kind=resource_ref.kind,
            resource_name=resource_ref.name,
            namespace=resource_ref.namespace or namespace,
            duration_seconds=POST_FIX_MONITORING_SECONDS,
            incident_name=incident_name,
        )

    else:
        log.error(
            "fix_application_failed",
            incident=incident_name,
            error=result.error_message,
        )

        # Update incident with failure
        await _update_fix_status(
            custom_api,
            incident_name,
            namespace,
            success=False,
            error=result.error_message,
            dry_run_passed=result.dry_run_passed,
        )

        agent_iterations_total.labels(
            agent_name="fix_applier",
            status="failed",
        ).inc()


async def _update_fix_status(
    custom_api: client.CustomObjectsApi,
    incident_name: str,
    namespace: str,
    success: bool,
    error: str | None = None,
    applied_at: datetime | None = None,
    resource_version: str | None = None,
    dry_run_passed: bool | None = None,
) -> None:
    """Update incident status after fix application attempt."""
    patch_body: dict[str, Any] = {
        "status": {
            "fixApplied": success,
        }
    }

    # Include dry-run pass status if available
    if dry_run_passed is not None:
        patch_body["status"]["dryRunPassed"] = dry_run_passed

    # Include resource version for tracking
    if resource_version is not None:
        patch_body["status"]["resourceVersion"] = resource_version

    if success:
        patch_body["status"]["phase"] = IncidentPhase.MONITORING.value
        if applied_at:
            patch_body["status"]["fixAppliedAt"] = applied_at.isoformat() + "Z"
    else:
        patch_body["status"]["phase"] = IncidentPhase.FAILED.value
        if error:
            patch_body["status"]["fixError"] = error

    try:
        custom_api.patch_namespaced_custom_object(
            group=AEGIS_API_GROUP,
            version=AEGIS_API_VERSION,
            namespace=namespace,
            plural=AEGIS_INCIDENT_PLURAL,
            name=incident_name,
            body=patch_body,
        )
        log.info(
            "fix_status_updated",
            incident=incident_name,
            success=success,
        )
    except client.ApiException as e:
        log.exception("fix_status_update_failed", error=e.reason)


# ============================================================================
# Incident Creation Handler - Initialize Approval Fields
# ============================================================================


@kopf.on.create(
    group=AEGIS_API_GROUP,
    version=AEGIS_API_VERSION,
    plural=AEGIS_INCIDENT_PLURAL,
)
async def handle_incident_creation(
    *,
    name: str | None,
    namespace: str | None,
    body: kopf.Body,
    patch: kopf.Patch,
    logger: Any,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle new AegisIncident creation.

    Initializes tracking metadata and sets up approval workflow if
    a fix proposal is present.

    Args:
        name: Incident name
        namespace: Namespace
        body: Full incident body
        patch: Patch object
        **_kwargs: Additional kopf kwargs

    Returns:
        Handler status dict
    """
    _ = logger
    if name is None or namespace is None:
        return {"created": False}

    log.info(
        "incident_created",
        incident=name,
        namespace=namespace,
    )

    # Initialize status if not present
    if "status" not in body or not body.get("status"):
        patch.status["phase"] = IncidentPhase.DETECTED.value
        patch.status["detectedAt"] = datetime.now(UTC).isoformat() + "Z"

    return {
        "created": True,
        "created_at": datetime.now(UTC).isoformat(),
    }


# ============================================================================
# Fix Proposal Available Handler
# ============================================================================


@kopf.on.field(
    group=AEGIS_API_GROUP,
    version=AEGIS_API_VERSION,
    plural=AEGIS_INCIDENT_PLURAL,
    field="spec.fixProposal",
)
async def handle_fix_proposal_added(
    *,
    old: Any | None,
    new: Any | None,
    name: str | None,
    namespace: str | None,
    body: kopf.Body,
    patch: kopf.Patch,
    logger: Any,
    **_kwargs: Any,
) -> dict[str, Any] | None:
    """Handle when a fix proposal is added to an incident.

    When a fix proposal is added and approval is required, transitions
    the incident to AwaitingApproval phase.

    Args:
        old: Previous fix proposal (None if first time)
        new: New fix proposal
        name: Incident name
        namespace: Namespace
        body: Full incident body
        patch: Patch object
        **_kwargs: Additional kopf kwargs

    Returns:
        Handler status dict or None
    """
    _ = logger
    if name is None or namespace is None:
        return None

    if old is None and isinstance(new, dict):
        log.info(
            "fix_proposal_added",
            incident=name,
            namespace=namespace,
            fix_type=new.get("fixType"),
        )

        # Check if approval is required
        spec = body.get("spec", {})
        approval = spec.get("approval", {})
        approval_required = approval.get("required", True)

        if approval_required:
            # Set timeout and transition to AwaitingApproval
            timeout_minutes = approval.get("timeoutMinutes", DEFAULT_APPROVAL_TIMEOUT_MINUTES)
            timeout_at = datetime.now(UTC) + timedelta(minutes=timeout_minutes)

            patch.spec["approval"] = {
                "status": ApprovalStatus.PENDING.value,
                "timeoutAt": timeout_at.isoformat() + "Z",
            }
            patch.status["phase"] = IncidentPhase.AWAITING_APPROVAL.value

            log.info(
                "awaiting_approval",
                incident=name,
                timeout_at=timeout_at.isoformat(),
            )

            return {
                "awaiting_approval": True,
                "timeout_at": timeout_at.isoformat(),
            }
        # Auto-approve if approval not required
        log.info(
            "auto_approving",
            incident=name,
            reason="approval_not_required",
        )

        patch.spec["approval"] = {
            "status": ApprovalStatus.APPROVED.value,
            "approvedBy": "aegis-operator",
            "approvedAt": datetime.now(UTC).isoformat() + "Z",
        }
        patch.status["phase"] = IncidentPhase.APPLYING_FIX.value

        # Trigger fix application
        task = asyncio.create_task(
            _apply_approved_fix(name, namespace, body),
            name=f"auto_apply_fix_{namespace}_{name}",
        )
        _approval_tasks.add(task)
        task.add_done_callback(_approval_tasks.discard)

        return {"auto_approved": True}

    return None


__all__ = [
    "approval_timeout_daemon",
    "handle_approval_status_change",
    "handle_fix_proposal_added",
    "handle_incident_creation",
]
