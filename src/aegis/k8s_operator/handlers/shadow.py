<<<<<<< HEAD
"""AEGIS Shadow Verification Handlers.

Daemon and timer-based handlers for shadow environment testing
of AI-proposed remediations before production deployment.

This module provides:
- Shadow environment daemons (continuous testing)
- Periodic health check timers
- Gradual rollout coordinators
- Integration with VClusterManager (when implemented)
"""

import json
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import kopf
from kopf import DaemonStopped, Index, Logger, Patch, Spec, Status
from kubernetes import client
from kubernetes import config as k8s_config

from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    shadow_environments_active,
    shadow_verification_duration_seconds,
    shadow_verifications_total,
)


# Get structured logger
log = get_logger(__name__)


# Constants for magic values
HIGH_LOAD_THRESHOLD = 0.8
LOW_LOAD_THRESHOLD = 0.3
SHADOW_HEALTH_CHECK_INTERVAL = 10


# Persistent storage for AI proposals/results
PROPOSALS_CONFIGMAP = "aegis-shadow-proposals"
RESULTS_CONFIGMAP = "aegis-shadow-results"
CONFIGMAP_DATA_KEY = "data.json"

_core_api: client.CoreV1Api | None = None
_custom_api: client.CustomObjectsApi | None = None


def _get_core_api() -> client.CoreV1Api:
    """Get or initialize CoreV1 API client."""
    global _core_api  # noqa: PLW0603
    if _core_api is not None:
        return _core_api
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()
    _core_api = client.CoreV1Api()
    return _core_api


def _get_custom_api() -> client.CustomObjectsApi:
    """Get or initialize CustomObjects API client."""
    global _custom_api  # noqa: PLW0603
    if _custom_api is not None:
        return _custom_api
    _get_core_api()  # Ensures config is loaded
    _custom_api = client.CustomObjectsApi()
    return _custom_api


def _operator_namespace() -> str:
    return settings.kubernetes.namespace or "aegis-system"


def _load_map(name: str) -> dict[str, dict[str, Any]]:
    """Load a JSON map from a ConfigMap."""
    api = _get_core_api()
    namespace = _operator_namespace()
    try:
        cm = api.read_namespaced_config_map(name, namespace)
    except client.ApiException as exc:
        if exc.status == HTTPStatus.NOT_FOUND:
            cm = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                data={CONFIGMAP_DATA_KEY: "{}"},
            )
            try:
                api.create_namespaced_config_map(namespace, cm)
            except client.ApiException as create_exc:
                log.warning("shadow_configmap_create_failed", name=name, error=create_exc.reason)
                return {}
            return {}
        log.warning("shadow_configmap_read_failed", name=name, error=exc.reason)
        return {}

    raw = (cm.data or {}).get(CONFIGMAP_DATA_KEY, "{}")
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        log.warning("shadow_configmap_parse_failed", name=name)
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _save_map(name: str, data: dict[str, dict[str, Any]]) -> None:
    """Persist a JSON map to a ConfigMap."""
    api = _get_core_api()
    namespace = _operator_namespace()
    body = {"data": {CONFIGMAP_DATA_KEY: json.dumps(data)}}
    try:
        api.patch_namespaced_config_map(name, namespace, body)
    except client.ApiException as exc:
        if exc.status == HTTPStatus.NOT_FOUND:
            cm = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                data={CONFIGMAP_DATA_KEY: json.dumps(data)},
            )
            try:
                api.create_namespaced_config_map(namespace, cm)
            except client.ApiException as create_exc:
                log.warning("shadow_configmap_create_failed", name=name, error=create_exc.reason)
        else:
            log.warning("shadow_configmap_write_failed", name=name, error=exc.reason)


def _get_ai_proposal(key: str) -> dict[str, Any] | None:
    proposals = _load_map(PROPOSALS_CONFIGMAP)
    value = proposals.get(key)
    return value if isinstance(value, dict) else None


def _set_ai_proposal(key: str, proposal: dict[str, Any]) -> None:
    proposals = _load_map(PROPOSALS_CONFIGMAP)
    proposals[key] = proposal
    _save_map(PROPOSALS_CONFIGMAP, proposals)


def _pop_ai_proposal(key: str) -> dict[str, Any] | None:
    proposals = _load_map(PROPOSALS_CONFIGMAP)
    value = proposals.pop(key, None)
    _save_map(PROPOSALS_CONFIGMAP, proposals)
    return value if isinstance(value, dict) else None


def _set_shadow_result(key: str, result: dict[str, Any]) -> None:
    results = _load_map(RESULTS_CONFIGMAP)
    results[key] = result
    _save_map(RESULTS_CONFIGMAP, results)


def _parse_quantity(value: str | None) -> float:
    """Parse Kubernetes resource quantity into a float (base units)."""
    if not value:
        return 0.0
    try:
        from kubernetes.utils.quantity import parse_quantity
    except ImportError:
        parse_quantity = None
    if parse_quantity:
        try:
            return float(parse_quantity(value))
        except (TypeError, ValueError):
            return 0.0

    # Fallback parser (best-effort)
    suffixes = {
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "": 1.0,
        "Ki": 1024.0,
        "Mi": 1024.0**2,
        "Gi": 1024.0**3,
        "Ti": 1024.0**4,
        "Pi": 1024.0**5,
        "Ei": 1024.0**6,
        "K": 1000.0,
        "M": 1000.0**2,
        "G": 1000.0**3,
        "T": 1000.0**4,
        "P": 1000.0**5,
        "E": 1000.0**6,
    }
    for suffix, multiplier in suffixes.items():
        if value.endswith(suffix) and suffix:
            number = value[: -len(suffix)]
            try:
                return float(number) * multiplier
            except ValueError:
                return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _sum_resource_requests(spec: Spec) -> tuple[float, float]:
    """Sum CPU and memory requests for deployment containers."""
    cpu_total = 0.0
    mem_total = 0.0
    containers = (
        spec.get("template", {}).get("spec", {}).get("containers", [])
        if isinstance(spec, dict)
        else []
    )
    for container in containers:
        resources = container.get("resources", {})
        resource_requests = resources.get("requests", {}) or {}
        limits = resources.get("limits", {}) or {}
        cpu_total += _parse_quantity(resource_requests.get("cpu") or limits.get("cpu"))
        mem_total += _parse_quantity(resource_requests.get("memory") or limits.get("memory"))
    return cpu_total, mem_total


def _fetch_pod_usage(namespace: str, label_selector: str) -> tuple[float, float]:
    """Fetch total CPU/memory usage for pods matching selector."""
    api = _get_custom_api()
    metrics = api.list_namespaced_custom_object(
        group="metrics.k8s.io",
        version="v1beta1",
        namespace=namespace,
        plural="pods",
        label_selector=label_selector,
    )
    cpu_total = 0.0
    mem_total = 0.0
    for item in metrics.get("items", []):
        for container in item.get("containers", []):
            usage = container.get("usage", {})
            cpu_total += _parse_quantity(usage.get("cpu"))
            mem_total += _parse_quantity(usage.get("memory"))
    return cpu_total, mem_total


# ============================================================================
# Shadow Verification Daemon
# ============================================================================


@kopf.daemon(
    "deployments",
    annotations={"aegis.io/shadow-testing": "enabled"},
)
async def shadow_verification_daemon(
    *,
    spec: Spec,
    name: str | None,
    namespace: str | None,
    logger: Logger,
    stopped: DaemonStopped,
    patch: Patch,
    **_kwargs: Any,
) -> None:
    """Continuously test AI proposals in shadow environments.

    This daemon runs as long as the deployment exists and has shadow
    testing enabled. It monitors for AI-generated proposals and validates
    them in isolated shadow environments before production deployment.

    Workflow:
        1. Check for pending AI proposals
        2. Create shadow environment (vCluster or similar)
        3. Apply AI changes in shadow
        4. Monitor shadow health for configured duration
        5. If healthy: approve for production
        6. If unhealthy: reject and log

    Args:
        spec: Deployment specification
        name: Deployment name
        namespace: Deployment namespace
        logger: Kopf logger with context
        stopped: Signal object to check if daemon should stop
        patch: Patch object to update deployment
        **kwargs: Additional kopf kwargs (memo, retry, etc.)

    Notes:
        - This is a long-running daemon that survives pod restarts
        - Uses `stopped` signal for graceful shutdown
        - Automatically retries on temporary errors
    """
    _ = (logger, spec)  # Unused but required by kopf signature
    if not name or not namespace:
        return

    log.info(
        "🔬 Shadow verification daemon started",
        deployment=name,
        namespace=namespace,
    )

    if not settings.shadow.enabled:
        log.info(
            "shadow_verification_disabled",
            deployment=name,
            namespace=namespace,
        )
        return

    # Update metrics
    shadow_environments_active.labels(runtime=settings.shadow.runtime.value).inc()

    # Mark daemon as active in deployment annotations
    patch.metadata.annotations["aegis.io/shadow-daemon-active"] = "true"
    patch.metadata.annotations["aegis.io/shadow-daemon-started"] = datetime.now(UTC).isoformat()

    try:
        # Main daemon loop
        while not stopped:
            proposal_key = f"{namespace}/{name}"

            # Check if there are pending AI proposals
            proposal = _get_ai_proposal(proposal_key)
            if proposal:
                log.info(
                    "🧪 AI proposal detected for shadow testing",
                    deployment=name,
                    action=proposal.get("action"),
                    confidence=float(proposal.get("confidence", 0.0)),
                )

                # Track shadow verification duration
                with shadow_verification_duration_seconds.time():
                    # Execute shadow verification workflow
                    success = await _run_shadow_verification(
                        deployment_name=name,
                        namespace=namespace,
                        proposal=proposal,
                        stopped=stopped,
                    )

                # Record verification result
                if success:
                    shadow_verifications_total.labels(
                        result="passed",
                        fix_type=proposal.get("action", "unknown"),
                    ).inc()

                    log.info(
                        "✅ Shadow test PASSED - Approving for production",
                        deployment=name,
                        proposal=proposal.get("action"),
                    )

                    # Store success result
                    _set_shadow_result(
                        proposal_key,
                        {
                            "status": "passed",
                            "timestamp": datetime.now(UTC).isoformat(),
                            "proposal": proposal,
                        },
                    )

                    # Update deployment annotation with approval
                    patch.metadata.annotations["aegis.io/last-shadow-test"] = "passed"
                    patch.metadata.annotations["aegis.io/last-test-time"] = datetime.now(
                        UTC
                    ).isoformat()

                else:
                    shadow_verifications_total.labels(
                        result="failed",
                        fix_type=proposal.get("action", "unknown"),
                    ).inc()

                    log.error(
                        "❌ Shadow test FAILED - Rejecting proposal",
                        deployment=name,
                        proposal=proposal.get("action"),
                    )

                    _set_shadow_result(
                        proposal_key,
                        {
                            "status": "failed",
                            "timestamp": datetime.now(UTC).isoformat(),
                            "proposal": proposal,
                        },
                    )

                    patch.metadata.annotations["aegis.io/last-shadow-test"] = "failed"

                # Remove processed proposal
                _pop_ai_proposal(proposal_key)

            # Wait before next check (configurable interval)
            # Use stopped.wait() instead of asyncio.sleep() for graceful shutdown
            await stopped.wait(timeout=settings.shadow.verification_timeout)

    finally:
        # Cleanup on daemon exit
        log.info(
            "🛑 Shadow verification daemon stopped",
            deployment=name,
        )
        shadow_environments_active.labels(runtime=settings.shadow.runtime.value).dec()

        patch.metadata.annotations["aegis.io/shadow-daemon-active"] = "false"
        patch.metadata.annotations["aegis.io/shadow-daemon-stopped"] = datetime.now(UTC).isoformat()


# ============================================================================
# Periodic Health Check Timer
# ============================================================================


@kopf.timer(
    "deployments",
    interval=60.0,  # Check every 60 seconds
    annotations={"aegis.io/monitor": kopf.PRESENT},
)
async def periodic_health_check_timer(
    *,
    spec: Spec,
    name: str | None,
    namespace: str | None,
    status: Status,
    logger: Logger,
    pod_health_index: Index[tuple[str, str], dict[str, Any]]
    | None = None,  # Injected from index.py
    pod_by_label_index: Index[tuple[str, str, str], str] | None = None,  # Injected from index.py
    **_kwargs: Any,
) -> None:
    """Periodically check deployment health and trigger AI analysis.

    This timer runs every 60 seconds for monitored deployments.
    It checks pod health, replica status, and triggers AI analysis
    if anomalies are detected.

    Args:
        spec: Deployment specification
        name: Deployment name
        namespace: Deployment namespace
        status: Deployment status
        logger: Kopf logger
        pod_health_index: Injected index of pod health (from index.py)
        **kwargs: Additional kopf kwargs
    """
    _ = logger
    if not name or not namespace or not pod_health_index or not pod_by_label_index:
        return

    log.debug(
        "🔍 Running periodic health check",
        deployment=name,
        namespace=namespace,
    )

    # Get deployment selector to find associated pods
    selector = spec.get("selector", {}).get("matchLabels", {})

    if not selector:
        log.warning("deployment_no_selector", deployment=name)
        return

    # Find pods matching deployment selector using the label index
    matching_pods: set[str] | None = None
    for label_key, label_value in selector.items():
        names = set(pod_by_label_index.get((namespace, label_key, label_value), ()))
        matching_pods = names if matching_pods is None else matching_pods & names

    if not matching_pods:
        return

    unhealthy_pods: list[str] = []
    for (pod_ns, pod_name), health_store in pod_health_index.items():
        if pod_ns != namespace or pod_name not in matching_pods:
            continue
        if any(not entry.get("healthy", True) for entry in health_store):
            unhealthy_pods.append(pod_name)

    # Check replica health
    ready_replicas = status.get("readyReplicas", 0)
    desired_replicas = spec.get("replicas", 1)

    if ready_replicas < desired_replicas:
        log.warning(
            "⚠️ Deployment has insufficient ready replicas",
            deployment=name,
            ready=int(ready_replicas),
            desired=int(desired_replicas),
        )

    if unhealthy_pods:
        log.warning(
            "⚠️ Unhealthy pods detected in deployment",
            deployment=name,
            count=len(unhealthy_pods),
            pods=str(unhealthy_pods[:5]),
        )


# ============================================================================
# AI-Driven Scaling Timer
# ============================================================================


@kopf.timer(
    "deployments",
    interval=120.0,  # Check every 2 minutes
    annotations={"aegis.io/ai-scaling": "enabled"},
)
async def ai_driven_scaling_timer(
    *,
    spec: Spec,
    name: str | None,
    namespace: str | None,
    patch: Patch,
    logger: Logger,
    **_kwargs: Any,
) -> None:
    """AI-driven predictive scaling based on load patterns.

    This timer uses AI to predict future load and proactively scale
    deployments before resource exhaustion.

    Args:
        spec: Deployment specification
        name: Deployment name
        namespace: Deployment namespace
        patch: Patch object to update replicas
        logger: Kopf logger
        **_kwargs: Additional kopf kwargs
    """
    _ = (logger, patch)  # Unused but available for scaling implementation
    if not name or not namespace:
        return
    if not settings.shadow.enabled:
        return

    current_replicas = spec.get("replicas", 1)

    log.info(
        "📊 Running AI-driven scaling analysis",
        deployment=name,
        current_replicas=int(current_replicas),
    )

    selector = spec.get("selector", {}).get("matchLabels", {})
    if not selector:
        log.warning("ai_scaling_missing_selector", deployment=name)
        return

    predicted_load = _predict_load(name, namespace, selector, spec)
    if predicted_load is None:
        log.info(
            "ai_scaling_metrics_unavailable",
            deployment=name,
            namespace=namespace,
        )
        return

    log.info(
        "🔮 AI load prediction",
        deployment=name,
        predicted_load=predicted_load,
    )

    # Scaling logic based on predicted load
    if predicted_load > HIGH_LOAD_THRESHOLD:  # High load predicted
        new_replicas = min(current_replicas + 2, 10)  # Max 10 replicas
        if new_replicas > current_replicas:
            log.info(
                "📈 AI recommends scaling UP",
                deployment=name,
                current=int(current_replicas),
                new=int(new_replicas),
                predicted_load=predicted_load,
            )

            # Create AI proposal for shadow testing
            _set_ai_proposal(
                f"{namespace}/{name}",
                {
                    "action": "scale_up",
                    "changes": {"replicas": new_replicas},
                    "reason": f"High predicted load: {predicted_load:.2f}",
                    "confidence": 0.85,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

    elif predicted_load < LOW_LOAD_THRESHOLD:  # Low load predicted
        new_replicas = max(current_replicas - 1, 1)  # Min 1 replica
        if new_replicas < current_replicas:
            log.info(
                "📉 AI recommends scaling DOWN",
                deployment=name,
                current=int(current_replicas),
                new=int(new_replicas),
                predicted_load=predicted_load,
            )

            _set_ai_proposal(
                f"{namespace}/{name}",
                {
                    "action": "scale_down",
                    "changes": {"replicas": new_replicas},
                    "reason": f"Low predicted load: {predicted_load:.2f}",
                    "confidence": 0.80,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )


# ============================================================================
# Internal Helper Functions
# ============================================================================


async def _run_shadow_verification(
    deployment_name: str,
    namespace: str,
    proposal: dict[str, Any],
    stopped: DaemonStopped,
) -> bool:
    """Internal: Run shadow verification workflow.

    This function creates a shadow environment, applies AI changes,
    monitors health, and returns success/failure.

    Args:
        deployment_name: Name of the deployment
        namespace: Namespace
        proposal: AI proposal dict with changes
        stopped: Stopped signal for graceful cancellation

    Returns:
        bool: True if shadow test passed, False otherwise
    """
    from aegis.shadow.manager import get_shadow_manager

    log.info(
        "🔬 Creating shadow environment",
        deployment=deployment_name,
        namespace=namespace,
    )

    shadow_manager = get_shadow_manager()

    try:
        # Create shadow environment
        shadow_env = await shadow_manager.create_shadow(
            source_namespace=namespace,
            source_resource=deployment_name,
            source_resource_kind="Deployment",
        )

        if stopped:
            log.warning("shadow_test_cancelled", deployment=deployment_name)
            await shadow_manager.cleanup(shadow_env.id)
            return False

        log.info("✅ Shadow environment created", shadow_id=shadow_env.id)

        # Run verification with proposed changes
        changes = proposal.get("changes", {})
        passed = await shadow_manager.run_verification(
            shadow_id=shadow_env.id,
            changes=changes,
            duration=settings.shadow.verification_timeout,
        )

        log.info(
            "Shadow verification result",
            passed=passed,
            health_score=shadow_env.health_score,
        )

        # Cleanup
        await shadow_manager.cleanup(shadow_env.id)

    except Exception:
        log.exception("shadow_verification_error")
        return False
    else:
        return passed


def _predict_load(
    deployment_name: str,
    namespace: str,
    selector: dict[str, str],
    spec: Spec,
) -> float | None:
    """Predict load using live metrics and resource requests."""
    if not selector:
        return None

    label_selector = ",".join(f"{key}={value}" for key, value in selector.items())
    try:
        usage_cpu, usage_mem = _fetch_pod_usage(namespace, label_selector)
    except client.ApiException as exc:
        log.warning(
            "shadow_metrics_query_failed",
            deployment=deployment_name,
            namespace=namespace,
            error=exc.reason,
        )
        return None

    req_cpu, req_mem = _sum_resource_requests(spec)
    ratios: list[float] = []
    if req_cpu > 0:
        ratios.append(usage_cpu / req_cpu)
    if req_mem > 0:
        ratios.append(usage_mem / req_mem)
    if not ratios:
        log.warning(
            "shadow_metrics_missing_requests",
            deployment=deployment_name,
            namespace=namespace,
        )
        return None

    return max(ratios)
=======
"""AEGIS Shadow Verification Handlers.

Daemon and timer-based handlers for shadow environment testing
of AI-proposed remediations before production deployment.

This module provides:
- Shadow environment daemons (continuous testing)
- Periodic health check timers
- Gradual rollout coordinators
- Integration with VClusterManager (when implemented)
"""

from datetime import UTC, datetime
from typing import Any

import kopf
from kopf import DaemonStopped, Index, Logger, Patch, Spec, Status

from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    shadow_environments_active,
    shadow_verification_duration_seconds,
    shadow_verifications_total,
)


# Get structured logger
log = get_logger(__name__)


# Constants for magic values
HIGH_LOAD_THRESHOLD = 0.8
LOW_LOAD_THRESHOLD = 0.3
BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 17
HIGH_LOAD_PREDICTION = 0.85
LOW_LOAD_PREDICTION = 0.25
SHADOW_ENV_CREATION_SECONDS = 5
SHADOW_HEALTH_CHECK_INTERVAL = 10


# In-memory storage for AI proposals
# TODO: Replace with Redis or etcd for multi-instance operators
_ai_proposals: dict[str, dict[str, Any]] = {}
_shadow_results: dict[str, dict[str, Any]] = {}


# ============================================================================
# Shadow Verification Daemon
# ============================================================================


@kopf.daemon(  # type: ignore[misc]
    "deployments",
    annotations={"aegis.io/shadow-testing": "enabled"},
)
async def shadow_verification_daemon(
    spec: Spec,
    name: str,
    namespace: str,
    _logger: Logger,
    stopped: DaemonStopped,
    patch: Patch,
    **_kwargs: Any,
) -> None:
    """Continuously test AI proposals in shadow environments.

    This daemon runs as long as the deployment exists and has shadow
    testing enabled. It monitors for AI-generated proposals and validates
    them in isolated shadow environments before production deployment.

    Workflow:
        1. Check for pending AI proposals
        2. Create shadow environment (vCluster or similar)
        3. Apply AI changes in shadow
        4. Monitor shadow health for configured duration
        5. If healthy: approve for production
        6. If unhealthy: reject and log

    Args:
        spec: Deployment specification
        name: Deployment name
        namespace: Deployment namespace
        logger: Kopf logger with context
        stopped: Signal object to check if daemon should stop
        patch: Patch object to update deployment
        **kwargs: Additional kopf kwargs (memo, retry, etc.)

    Notes:
        - This is a long-running daemon that survives pod restarts
        - Uses `stopped` signal for graceful shutdown
        - Automatically retries on temporary errors
    """
    _ = spec  # Unused but required by kopf signature

    log.info(
        "🔬 Shadow verification daemon started",
        deployment=name,
        namespace=namespace,
    )

    # Update metrics
    shadow_environments_active.labels(runtime=settings.shadow.runtime.value).inc()

    # Mark daemon as active in deployment annotations
    patch.metadata.annotations["aegis.io/shadow-daemon-active"] = "true"
    patch.metadata.annotations["aegis.io/shadow-daemon-started"] = datetime.now(UTC).isoformat()

    try:
        # Main daemon loop
        while not stopped:
            proposal_key = f"{namespace}/{name}"

            # Check if there are pending AI proposals
            if proposal_key in _ai_proposals:
                proposal = _ai_proposals[proposal_key]

                log.info(
                    "🧪 AI proposal detected for shadow testing",
                    deployment=name,
                    action=proposal.get("action"),
                    confidence=float(proposal.get("confidence", 0.0)),
                )

                # Track shadow verification duration
                with shadow_verification_duration_seconds.time():
                    # Execute shadow verification workflow
                    success = await _run_shadow_verification(
                        deployment_name=name,
                        namespace=namespace,
                        proposal=proposal,
                        stopped=stopped,
                    )

                # Record verification result
                if success:
                    shadow_verifications_total.labels(
                        result="passed",
                        fix_type=proposal.get("action", "unknown"),
                    ).inc()

                    log.info(
                        "✅ Shadow test PASSED - Approving for production",
                        deployment=name,
                        proposal=proposal.get("action"),
                    )

                    # Store success result
                    _shadow_results[proposal_key] = {
                        "status": "passed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "proposal": proposal,
                    }

                    # Update deployment annotation with approval
                    patch.metadata.annotations["aegis.io/last-shadow-test"] = "passed"
                    patch.metadata.annotations["aegis.io/last-test-time"] = datetime.now(
                        UTC
                    ).isoformat()

                else:
                    shadow_verifications_total.labels(
                        result="failed",
                        fix_type=proposal.get("action", "unknown"),
                    ).inc()

                    log.error(
                        "❌ Shadow test FAILED - Rejecting proposal",
                        deployment=name,
                        proposal=proposal.get("action"),
                    )

                    _shadow_results[proposal_key] = {
                        "status": "failed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "proposal": proposal,
                    }

                    patch.metadata.annotations["aegis.io/last-shadow-test"] = "failed"

                # Remove processed proposal
                del _ai_proposals[proposal_key]

            # Wait before next check (configurable interval)
            # Use stopped.wait() instead of asyncio.sleep() for graceful shutdown
            await stopped.wait(timeout=settings.shadow.verification_timeout)

    finally:
        # Cleanup on daemon exit
        log.info(
            "🛑 Shadow verification daemon stopped",
            deployment=name,
        )
        shadow_environments_active.labels(runtime=settings.shadow.runtime.value).dec()

        patch.metadata.annotations["aegis.io/shadow-daemon-active"] = "false"
        patch.metadata.annotations["aegis.io/shadow-daemon-stopped"] = datetime.now(UTC).isoformat()


# ============================================================================
# Periodic Health Check Timer
# ============================================================================


@kopf.timer(  # type: ignore[misc]
    "deployments",
    interval=60.0,  # Check every 60 seconds
    annotations={"aegis.io/monitor": kopf.PRESENT},
)
async def periodic_health_check_timer(
    spec: Spec,
    name: str,
    namespace: str,
    status: Status,
    _logger: Logger,
    pod_health_index: Index,  # Injected from index.py
    **_kwargs: Any,
) -> None:
    """Periodically check deployment health and trigger AI analysis.

    This timer runs every 60 seconds for monitored deployments.
    It checks pod health, replica status, and triggers AI analysis
    if anomalies are detected.

    Args:
        spec: Deployment specification
        name: Deployment name
        namespace: Deployment namespace
        status: Deployment status
        logger: Kopf logger
        pod_health_index: Injected index of pod health (from index.py)
        **kwargs: Additional kopf kwargs
    """
    log.debug(
        "🔍 Running periodic health check",
        deployment=name,
        namespace=namespace,
    )

    # Get deployment selector to find associated pods
    selector = spec.get("selector", {}).get("matchLabels", {})

    if not selector:
        log.warning("deployment_no_selector", deployment=name)
        return

    # Find pods matching deployment selector using the index
    unhealthy_pods: list[str] = []

    for (pod_ns, pod_name), health_data_list in pod_health_index.items():
        if pod_ns != namespace:
            continue

        # Check if pod matches selector (simplified - real impl needs label matching)
        # For now, check if pods are in same namespace
        unhealthy_pods.extend(
            pod_name for health_data in health_data_list if not health_data.get("healthy", True)
        )

    # Check replica health
    ready_replicas = status.get("readyReplicas", 0)
    desired_replicas = spec.get("replicas", 1)

    if ready_replicas < desired_replicas:
        log.warning(
            "⚠️ Deployment has insufficient ready replicas",
            deployment=name,
            ready=int(ready_replicas),
            desired=int(desired_replicas),
        )

    if unhealthy_pods:
        log.warning(
            "⚠️ Unhealthy pods detected in deployment",
            deployment=name,
            count=len(unhealthy_pods),
            pods=str(unhealthy_pods[:5]),
        )


# ============================================================================
# AI-Driven Scaling Timer
# ============================================================================


@kopf.timer(  # type: ignore[misc]
    "deployments",
    interval=120.0,  # Check every 2 minutes
    annotations={"aegis.io/ai-scaling": "enabled"},
)
async def ai_driven_scaling_timer(
    spec: Spec,
    name: str,
    namespace: str,
    patch: Patch,
    _logger: Logger,
    **_kwargs: Any,
) -> None:
    """AI-driven predictive scaling based on load patterns.

    This timer uses AI to predict future load and proactively scale
    deployments before resource exhaustion.

    Args:
        spec: Deployment specification
        name: Deployment name
        namespace: Deployment namespace
        patch: Patch object to update replicas
        logger: Kopf logger
        **_kwargs: Additional kopf kwargs
    """
    _ = patch  # Unused but available for scaling implementation

    current_replicas = spec.get("replicas", 1)

    log.info(
        "📊 Running AI-driven scaling analysis",
        deployment=name,
        current_replicas=int(current_replicas),
    )

    # TODO: Integrate with real AI model for load prediction
    # For now, use a simple heuristic based on time
    predicted_load = _predict_load(name, namespace)

    log.info(
        "🔮 AI load prediction",
        deployment=name,
        predicted_load=predicted_load,
    )

    # Scaling logic based on predicted load
    if predicted_load > HIGH_LOAD_THRESHOLD:  # High load predicted
        new_replicas = min(current_replicas + 2, 10)  # Max 10 replicas
        if new_replicas > current_replicas:
            log.info(
                "📈 AI recommends scaling UP",
                deployment=name,
                current=int(current_replicas),
                new=int(new_replicas),
                predicted_load=predicted_load,
            )

            # Create AI proposal for shadow testing
            _ai_proposals[f"{namespace}/{name}"] = {
                "action": "scale_up",
                "changes": {"replicas": new_replicas},
                "reason": f"High predicted load: {predicted_load:.2f}",
                "confidence": 0.85,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    elif predicted_load < LOW_LOAD_THRESHOLD:  # Low load predicted
        new_replicas = max(current_replicas - 1, 1)  # Min 1 replica
        if new_replicas < current_replicas:
            log.info(
                "📉 AI recommends scaling DOWN",
                deployment=name,
                current=int(current_replicas),
                new=int(new_replicas),
                predicted_load=predicted_load,
            )

            _ai_proposals[f"{namespace}/{name}"] = {
                "action": "scale_down",
                "changes": {"replicas": new_replicas},
                "reason": f"Low predicted load: {predicted_load:.2f}",
                "confidence": 0.80,
                "timestamp": datetime.now(UTC).isoformat(),
            }


# ============================================================================
# Internal Helper Functions
# ============================================================================


async def _run_shadow_verification(
    deployment_name: str,
    namespace: str,
    proposal: dict[str, Any],
    stopped: DaemonStopped,
) -> bool:
    """Internal: Run shadow verification workflow.

    This function creates a shadow environment, applies AI changes,
    monitors health, and returns success/failure.

    Args:
        deployment_name: Name of the deployment
        namespace: Namespace
        proposal: AI proposal dict with changes
        stopped: Stopped signal for graceful cancellation

    Returns:
        bool: True if shadow test passed, False otherwise
    """
    from aegis.shadow.manager import get_shadow_manager

    log.info(
        "🔬 Creating shadow environment",
        deployment=deployment_name,
        namespace=namespace,
    )

    shadow_manager = get_shadow_manager()

    try:
        # Create shadow environment
        shadow_env = await shadow_manager.create_shadow(
            source_namespace=namespace,
            source_resource=deployment_name,
            source_resource_kind="Deployment",
        )

        if stopped:
            log.warning("shadow_test_cancelled", deployment=deployment_name)
            await shadow_manager.cleanup(shadow_env.id)
            return False

        log.info("✅ Shadow environment created", shadow_id=shadow_env.id)

        # Run verification with proposed changes
        changes = proposal.get("changes", {})
        passed = await shadow_manager.run_verification(
            shadow_id=shadow_env.id,
            changes=changes,
            duration=settings.shadow.verification_timeout,
        )

        log.info(
            "Shadow verification result",
            passed=passed,
            health_score=shadow_env.health_score,
        )

        # Cleanup
        await shadow_manager.cleanup(shadow_env.id)

    except Exception:
        log.exception("shadow_verification_error")
        return False
    else:
        return passed


def _predict_load(_deployment_name: str, _namespace: str) -> float:
    """Internal: Predict future load for a deployment.

    This is a mock implementation. Replace with real ML model.

    Args:
        _deployment_name: Deployment name (unused in heuristic)
        _namespace: Namespace (unused in heuristic)

    Returns:
        float: Predicted load (0.0 to 1.0)
    """
    # Simple heuristic based on time of day
    current_hour = datetime.now(UTC).hour

    # Business hours (9am-5pm UTC): high load
    if BUSINESS_HOURS_START <= current_hour <= BUSINESS_HOURS_END:
        return HIGH_LOAD_PREDICTION  # High load

    # Off hours: low load
    return LOW_LOAD_PREDICTION  # Low load
>>>>>>> main
