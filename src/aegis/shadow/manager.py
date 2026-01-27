"""Shadow Environment Manager.

Manages shadow verification environments using vCluster or similar technologies.
Provides isolated environments for testing AI-proposed remediations before
production deployment.

Features:
- Create isolated vCluster environments
- Clone resources from production
- Apply AI-proposed changes
- Monitor health metrics
- Cleanup after verification
"""

import asyncio
import copy
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

from kubernetes import client
from kubernetes.client.rest import ApiException

from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    shadow_environments_active,
    shadow_verification_duration_seconds,
    shadow_verifications_total,
)


log = get_logger(__name__)

# HTTP Status codes
HTTP_CONFLICT = 409
HTTP_NOT_FOUND = 404

# Health thresholds
SHADOW_HEALTH_PASS_THRESHOLD = 0.8  # 80% health threshold
HEALTH_THRESHOLD = SHADOW_HEALTH_PASS_THRESHOLD  # Alias for backwards compatibility
K8S_NAME_MAX_LENGTH = 63


class ShadowStatus(str, Enum):
    """Status of a shadow environment."""

    PENDING = "pending"
    CREATING = "creating"
    READY = "ready"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    CLEANING = "cleaning"
    DELETED = "deleted"
    ERROR = "error"


@dataclass
class ShadowEnvironment:
    """Represents a shadow verification environment."""

    id: str
    namespace: str
    source_namespace: str
    source_resource: str
    source_resource_kind: str
    status: ShadowStatus = ShadowStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    health_score: float = 0.0
    logs: list[str] = field(default_factory=list)
    error: str | None = None
    test_results: dict[str, Any] = field(default_factory=dict)


class ShadowManager:
    """Manager for shadow verification environments.

    Supports multiple runtime backends:
    - namespace: Simple namespace isolation (fast, limited isolation)
    - vcluster: Full virtual cluster (slower, complete isolation)
    - kind: Local kind cluster (for development)
    """

    def __init__(self) -> None:
        """Initialize shadow manager with Kubernetes clients."""
        self._environments: dict[str, ShadowEnvironment] = {}
        self._core_api = client.CoreV1Api()
        self._apps_api = client.AppsV1Api()
        self._custom_api = client.CustomObjectsApi()

        self.runtime = settings.shadow.runtime.value
        self.namespace_prefix = settings.shadow.namespace_prefix
        self.max_concurrent = settings.shadow.max_concurrent_shadows
        self.verification_timeout = settings.shadow.verification_timeout
        self._namespace_prefix = self._sanitize_name(
            self.namespace_prefix, allow_trailing_dash=True
        )

        log.info(
            "shadow_manager_initialized",
            runtime=self.runtime,
            max_concurrent=self.max_concurrent,
        )

    @property
    def active_count(self) -> int:
        """Count of active shadow environments."""
        return sum(
            1
            for env in self._environments.values()
            if env.status in (ShadowStatus.CREATING, ShadowStatus.READY, ShadowStatus.TESTING)
        )

    async def create_shadow(
        self,
        source_namespace: str,
        source_resource: str,
        source_resource_kind: str,
        shadow_id: str | None = None,
    ) -> ShadowEnvironment:
        """Create a new shadow environment.

        Args:
            source_namespace: Namespace of the source resource
            source_resource: Name of the source resource to clone
            source_resource_kind: Kind of the source resource (Pod, Deployment, etc.)
            shadow_id: Optional custom ID for the shadow environment

        Returns:
            ShadowEnvironment: Created shadow environment

        Raises:
            RuntimeError: If max concurrent shadows exceeded or creation fails
        """
        if self.active_count >= self.max_concurrent:
            msg = f"Max concurrent shadows ({self.max_concurrent}) exceeded"
            log.error(msg)
            raise RuntimeError(msg)

        # Generate shadow ID if not provided
        if not shadow_id:
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            shadow_id = f"{source_resource}-{timestamp}"

        sanitized_id = self._sanitize_name(shadow_id)
        shadow_namespace = self._build_shadow_namespace(sanitized_id)
        if sanitized_id != shadow_id:
            log.debug(
                "shadow_id_sanitized",
                original=shadow_id,
                sanitized=sanitized_id,
                namespace=shadow_namespace,
            )

        env = ShadowEnvironment(
            id=sanitized_id,
            namespace=shadow_namespace,
            source_namespace=source_namespace,
            source_resource=source_resource,
            source_resource_kind=source_resource_kind,
            status=ShadowStatus.CREATING,
        )

        self._environments[shadow_id] = env
        env.logs.append(f"Creating shadow environment: {shadow_namespace}")

        try:
            # Create namespace for shadow environment
            await self._create_namespace(shadow_namespace)
            env.logs.append(f"Namespace {shadow_namespace} created")

            # Clone the source resource
            await self._clone_resource(
                source_namespace=source_namespace,
                source_name=source_resource,
                source_kind=source_resource_kind,
                target_namespace=shadow_namespace,
            )
            env.logs.append(f"Cloned {source_resource_kind}/{source_resource}")

            env.status = ShadowStatus.READY
            log.info(
                "shadow_created",
                shadow_id=sanitized_id,
                namespace=shadow_namespace,
            )

            # Track active shadow environment
            shadow_environments_active.labels(runtime=self.runtime).inc()

        except Exception as e:
            env.status = ShadowStatus.ERROR
            env.error = str(e)
            log.exception("shadow_creation_failed")
            await self._best_effort_cleanup(env)
            raise

        return env

    async def run_verification(
        self,
        shadow_id: str,
        changes: dict[str, Any],
        duration: int | None = None,
    ) -> bool:
        """Run verification tests in shadow environment.

        Args:
            shadow_id: ID of the shadow environment
            changes: Changes to apply for testing
            duration: Verification duration in seconds (default from settings)

        Returns:
            bool: True if verification passed, False otherwise
        """
        env = self._environments.get(shadow_id)
        if not env:
            raise ValueError(f"Shadow environment {shadow_id} not found")

        if env.status != ShadowStatus.READY:
            raise RuntimeError(f"Shadow {shadow_id} not ready: {env.status}")

        env.status = ShadowStatus.TESTING
        env.logs.append("Starting verification tests")
        duration = duration or self.verification_timeout

        # Determine fix type from changes
        fix_type = "unknown"
        if "replicas" in changes:
            fix_type = "scale"
        elif "image" in changes:
            fix_type = "rollback"
        elif "env" in changes:
            fix_type = "config_change"
        elif "manifests" in changes:
            fix_type = "patch"

        try:
            # Track verification duration
            with shadow_verification_duration_seconds.time():
                # Apply changes to shadow environment
                await self._apply_changes(env, changes)
                env.logs.append(f"Applied changes: {list(changes.keys())}")

                # ----------------------------------------------------------------
                # Security gate: Trivy image scan (fail closed)
                # ----------------------------------------------------------------
                trivy_result: dict[str, Any] | None = None
                if settings.security.trivy_enabled and "image" in changes:
                    from aegis.security.trivy import TrivyScanner

                    image = str(changes["image"])
                    env.logs.append(
                        f"Running Trivy image scan (severity={settings.security.trivy_severity}): {image}"
                    )
                    trivy_result = await TrivyScanner().scan_image(
                        image,
                        severity_csv=settings.security.trivy_severity,
                        fail_on_csv=settings.security.trivy_severity,
                    )

                    if not trivy_result.get("passed", False):
                        env.status = ShadowStatus.FAILED
                        env.test_results = {
                            "passed": False,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "trivy": trivy_result,
                        }
                        env.logs.append(
                            f"Trivy failed: {trivy_result.get('severity_counts', {})} "
                            f"error={trivy_result.get('error')}"
                        )
                        log.warning(
                            "shadow_verification_blocked_by_trivy",
                            shadow_id=shadow_id,
                            image=image,
                            severity_counts=trivy_result.get("severity_counts"),
                            error=trivy_result.get("error"),
                        )
                        return False

                # Monitor health for specified duration
                health_score = await self._monitor_health(env, duration)
                env.health_score = health_score
                env.logs.append(f"Health monitoring complete: score={health_score:.2f}")

                # Evaluate results
                passed = health_score >= HEALTH_THRESHOLD
                env.status = ShadowStatus.PASSED if passed else ShadowStatus.FAILED
                env.test_results = {
                    "health_score": health_score,
                    "duration": duration,
                    "passed": passed,
                    "timestamp": datetime.now(UTC).isoformat(),
                    **({"trivy": trivy_result} if trivy_result is not None else {}),
                }

            # Track verification result
            shadow_verifications_total.labels(
                result="passed" if passed else "failed",
                fix_type=fix_type,
            ).inc()

            log.info(
                "verification_completed",
                shadow_id=shadow_id,
                passed=passed,
                health_score=health_score,
            )

        except Exception as e:
            env.status = ShadowStatus.ERROR
            env.error = str(e)
            log.exception("verification_failed", shadow_id=shadow_id)
            return False
        else:
            return passed

    async def cleanup(self, shadow_id: str) -> None:
        """Cleanup shadow environment.

        Args:
            shadow_id: ID of the shadow environment to cleanup
        """
        env = self._environments.get(shadow_id)
        if not env:
            log.warning("shadow_not_found", shadow_id=shadow_id)
            return

        env.status = ShadowStatus.CLEANING
        env.logs.append("Cleaning up shadow environment")

        try:
            # Delete namespace (cascades to all resources)
            await self._delete_namespace(env.namespace)
            env.status = ShadowStatus.DELETED
            log.info("shadow_cleaned", shadow_id=shadow_id)

            # Decrement active shadow counter
            shadow_environments_active.labels(runtime=self.runtime).dec()

        except Exception as e:
            log.exception("cleanup_failed", shadow_id=shadow_id)
            env.error = str(e)

    def get_environment(self, shadow_id: str) -> ShadowEnvironment | None:
        """Get shadow environment by ID."""
        return self._environments.get(shadow_id)

    def list_environments(self) -> list[ShadowEnvironment]:
        """List all shadow environments."""
        return list(self._environments.values())

    # ========================================================================
    # Private helpers
    # ========================================================================

    @staticmethod
    def _sanitize_name(value: str, allow_trailing_dash: bool = False) -> str:
        """Sanitize strings to valid DNS-1123 labels."""
        trailing_dash = value.endswith("-")
        sanitized = re.sub(r"[^a-z0-9-]+", "-", value.lower())
        sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
        if not sanitized:
            sanitized = "shadow"
        if allow_trailing_dash and trailing_dash:
            sanitized = f"{sanitized}-"
        return sanitized

    def _build_shadow_namespace(self, shadow_id: str) -> str:
        """Build a shadow namespace within DNS-1123 limits."""
        prefix = self._namespace_prefix
        trimmed_id = shadow_id.lstrip("-")
        max_id_len = K8S_NAME_MAX_LENGTH - len(prefix)
        if max_id_len <= 0:
            return prefix[:K8S_NAME_MAX_LENGTH].rstrip("-")
        if len(trimmed_id) > max_id_len:
            trimmed_id = trimmed_id[:max_id_len].rstrip("-")
        return f"{prefix}{trimmed_id}"

    async def _call_api(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Run blocking Kubernetes client calls in a thread."""
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _best_effort_cleanup(self, env: ShadowEnvironment) -> None:
        """Attempt cleanup after a failed shadow creation."""
        try:
            await self._delete_namespace(env.namespace)
        except ApiException:
            log.warning("shadow_cleanup_failed", shadow_id=env.id)

    async def _create_namespace(self, name: str) -> None:
        """Create namespace for shadow environment."""
        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={
                    "aegis.io/shadow": "true",
                    "aegis.io/managed-by": "aegis-operator",
                },
            )
        )

        try:
            await self._call_api(self._core_api.create_namespace, namespace)
        except ApiException as e:
            if e.status != HTTP_CONFLICT:  # Already exists is OK
                raise

    async def _delete_namespace(self, name: str) -> None:
        """Delete shadow namespace."""
        try:
            await self._call_api(self._core_api.delete_namespace, name)
        except ApiException as e:
            if e.status != HTTP_NOT_FOUND:  # Not found is OK
                raise

    async def _clone_resource(
        self,
        source_namespace: str,
        source_name: str,
        source_kind: str,
        target_namespace: str,
    ) -> None:
        """Clone a resource to the shadow namespace."""
        if source_kind.lower() == "deployment":
            # Get source deployment
            source_deployment = cast(
                client.V1Deployment,
                await self._call_api(
                    self._apps_api.read_namespaced_deployment,
                    source_name,
                    source_namespace,
                ),
            )
            deployment = copy.deepcopy(source_deployment)

            # Prepare for cloning
            if deployment.metadata is None:
                deployment.metadata = client.V1ObjectMeta()
            deployment.metadata.namespace = target_namespace
            deployment.metadata.resource_version = None
            deployment.metadata.uid = None
            deployment.metadata.creation_timestamp = None
            deployment.metadata.managed_fields = None
            deployment.metadata.owner_references = None
            deployment.metadata.finalizers = None
            deployment.metadata.generation = None

            # Add shadow label
            if not deployment.metadata.labels:
                deployment.metadata.labels = {}
            deployment.metadata.labels["aegis.io/shadow"] = "true"
            deployment.metadata.labels["aegis.io/source-namespace"] = source_namespace
            deployment.metadata.labels["aegis.io/source-name"] = source_name
            deployment.metadata.labels["aegis.io/source-kind"] = "Deployment"

            # Create in shadow namespace
            await self._call_api(
                self._apps_api.create_namespaced_deployment,
                target_namespace,
                deployment,
            )

        elif source_kind.lower() == "pod":
            # For standalone pods, create a deployment wrapper
            pod = cast(
                client.V1Pod,
                await self._call_api(
                    self._core_api.read_namespaced_pod,
                    source_name,
                    source_namespace,
                ),
            )
            pod_spec = copy.deepcopy(pod.spec)
            if pod_spec and pod_spec.restart_policy and pod_spec.restart_policy != "Always":
                pod_spec.restart_policy = "Always"

            base_labels = pod.metadata.labels if pod.metadata and pod.metadata.labels else {}
            base_labels = copy.deepcopy(base_labels)
            base_labels.setdefault("app", source_name)
            base_labels["aegis.io/shadow"] = "true"

            # Create deployment from pod spec
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(
                    name=source_name,
                    namespace=target_namespace,
                    labels={
                        **base_labels,
                        "aegis.io/source-namespace": source_namespace,
                        "aegis.io/source-name": source_name,
                        "aegis.io/source-kind": "Pod",
                    },
                ),
                spec=client.V1DeploymentSpec(
                    replicas=1,
                    selector=client.V1LabelSelector(match_labels={"app": base_labels["app"]}),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(labels=base_labels),
                        spec=pod_spec,
                    ),
                ),
            )

            await self._call_api(
                self._apps_api.create_namespaced_deployment,
                target_namespace,
                deployment,
            )

        else:
            log.warning(
                "unsupported_resource_kind",
                kind=source_kind,
                message="Only Deployment and Pod cloning supported",
            )

    async def _apply_changes(self, env: ShadowEnvironment, changes: dict[str, Any]) -> None:
        """Apply proposed changes to shadow environment."""
        if not changes:
            return

        deployment = cast(
            client.V1Deployment,
            await self._call_api(
                self._apps_api.read_namespaced_deployment,
                env.source_resource,
                env.namespace,
            ),
        )
        container_name = changes.get("container") or changes.get("container_name")
        if not container_name:
            containers = (
                deployment.spec.template.spec.containers
                if deployment.spec and deployment.spec.template and deployment.spec.template.spec
                else []
            )
            if containers:
                container_name = containers[0].name

        patch: dict[str, Any] = {"spec": {}}
        template_patch: dict[str, Any] = {"spec": {}}
        container_patch: dict[str, Any] = {}

        # Handle replica changes
        if "replicas" in changes:
            patch["spec"]["replicas"] = changes["replicas"]

        # Handle image changes
        if "image" in changes:
            if container_name:
                container_patch["name"] = container_name
                container_patch["image"] = changes["image"]
            else:
                log.warning(
                    "shadow_patch_no_container", change="image", resource=env.source_resource
                )

        # Handle environment variable changes
        if "env" in changes and isinstance(changes["env"], dict):
            env_updates = [{"name": key, "value": value} for key, value in changes["env"].items()]
            if container_name:
                container_patch["name"] = container_name
                container_patch["env"] = env_updates
            else:
                log.warning("shadow_patch_no_container", change="env", resource=env.source_resource)

        if container_patch:
            template_patch["spec"]["containers"] = [container_patch]

        if template_patch["spec"]:
            patch["spec"]["template"] = template_patch

        if not patch["spec"]:
            return

        try:
            await self._call_api(
                self._apps_api.patch_namespaced_deployment,
                env.source_resource,
                env.namespace,
                patch,
            )
        except ApiException as e:
            log.warning("shadow_patch_failed", error=str(e))

    async def _monitor_health(self, env: ShadowEnvironment, duration: int) -> float:
        """Monitor shadow environment health.

        Returns health score between 0.0 and 1.0.
        """
        check_interval = 5  # seconds
        checks = []

        elapsed = 0
        while elapsed < duration:
            score = await self._check_health(env)
            checks.append(score)
            elapsed += check_interval
            await asyncio.sleep(check_interval)

        # Average health score
        if checks:
            return sum(checks) / len(checks)
        return 0.0

    async def _check_health(self, env: ShadowEnvironment) -> float:
        """Single health check for shadow environment."""
        try:
            pods = cast(
                client.V1PodList,
                await self._call_api(self._core_api.list_namespaced_pod, env.namespace),
            )
            if not pods.items:
                return 0.0

            healthy = 0
            for pod in pods.items:
                if not pod.status:
                    continue
                if pod.status.phase != "Running":
                    continue
                ready = True
                for cs in pod.status.container_statuses or []:
                    if not cs.ready:
                        ready = False
                        break
                if ready:
                    healthy += 1

            return healthy / len(pods.items)

        except ApiException:
            return 0.0


# Module-level singleton
_shadow_manager: ShadowManager | None = None


def get_shadow_manager() -> ShadowManager:
    """Get or create shadow manager instance."""
    global _shadow_manager  # noqa: PLW0603
    if _shadow_manager is None:
        _shadow_manager = ShadowManager()
    return _shadow_manager


__all__ = [
    "ShadowEnvironment",
    "ShadowManager",
    "ShadowStatus",
    "get_shadow_manager",
]
