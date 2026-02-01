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
import base64
import copy
import re
import shlex
import shutil
import tempfile
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from aegis.agent.state import LoadTestConfig, VerificationPlan
from aegis.config.settings import SandBoxRuntime, settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import (
    shadow_environments_active,
    shadow_load_test_duration_seconds,
    shadow_load_tests_total,
    shadow_smoke_test_duration_seconds,
    shadow_smoke_tests_total,
    shadow_verification_duration_seconds,
    shadow_verifications_total,
)
from aegis.shadow.vcluster import VClusterManager


log = get_logger(__name__)

# HTTP Status codes
HTTP_CONFLICT = 409
HTTP_NOT_FOUND = 404

# Health thresholds
SHADOW_HEALTH_PASS_THRESHOLD = 0.8  # 80% health threshold
HEALTH_THRESHOLD = SHADOW_HEALTH_PASS_THRESHOLD  # Alias for backwards compatibility
K8S_NAME_MAX_LENGTH = 63
DEFAULT_HTTP_PORT = 80
VCLUSTER_KUBECONFIG_NAME = "vc-shadow-kubeconfig"
SMOKE_TEST_IMAGE = "curlimages/curl:8.5.0"
LOAD_TEST_IMAGE = "locustio/locust:2.42.6"
DEFAULT_SMOKE_PATHS = ["/health", "/ready", "/healthz", "/readyz"]
SMOKE_TEST_TIMEOUT_SECONDS = 120
JOB_POLL_INTERVAL_SECONDS = 2
CURL_CONNECT_TIMEOUT_SECONDS = 10
CURL_MAX_TIME_SECONDS = 30
JOB_ACTIVE_DEADLINE_SECONDS = 180
KUBECTL_SKIP_ARGS = {"-n", "--namespace", "--context", "--kubeconfig"}
KUBECTL_MIN_ARGS = 2
KUBECTL_SET_MIN_ARGS = 3
KUBECTL_SET_IMAGE_MIN_ARGS = 4


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
    runtime: str | None = None
    host_namespace: str | None = None
    kubeconfig_path: str | None = None


@dataclass
class ShadowClients:
    """API clients for a shadow environment."""

    api_client: client.ApiClient
    core: client.CoreV1Api
    apps: client.AppsV1Api
    batch: client.BatchV1Api
    custom: client.CustomObjectsApi


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
        self._shadow_clients: dict[str, ShadowClients] = {}

        # Host cluster client (source of truth)
        self._host_api_client = self._load_api_client(
            kubeconfig_path=settings.kubernetes.kubeconfig_path,
            context=settings.kubernetes.context,
            in_cluster=settings.kubernetes.in_cluster,
        )
        self._core_api = client.CoreV1Api(self._host_api_client)
        self._apps_api = client.AppsV1Api(self._host_api_client)
        self._custom_api = client.CustomObjectsApi(self._host_api_client)

        self.runtime = settings.shadow.runtime.value
        self.namespace_prefix = settings.shadow.namespace_prefix
        self.max_concurrent = settings.shadow.max_concurrent_shadows
        self.verification_timeout = settings.shadow.verification_timeout
        self._namespace_prefix = self._sanitize_name(
            self.namespace_prefix, allow_trailing_dash=True
        )

        repo_root = Path(__file__).resolve().parents[3]
        template_path = repo_root / "examples/shadow/vcluster-template.yaml"
        self._vcluster_manager = VClusterManager(
            template_path=template_path if template_path.exists() else None
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
        target_namespace = (
            source_namespace if self.runtime == SandBoxRuntime.VCLUSTER.value else shadow_namespace
        )
        if sanitized_id != shadow_id:
            log.debug(
                "shadow_id_sanitized",
                original=shadow_id,
                sanitized=sanitized_id,
                namespace=shadow_namespace,
            )

        env = ShadowEnvironment(
            id=sanitized_id,
            namespace=target_namespace,
            source_namespace=source_namespace,
            source_resource=source_resource,
            source_resource_kind=source_resource_kind,
            status=ShadowStatus.CREATING,
            runtime=self.runtime,
            host_namespace=shadow_namespace
            if self.runtime == SandBoxRuntime.VCLUSTER.value
            else None,
        )

        self._environments[env.id] = env
        env.logs.append(f"Creating shadow environment: {env.id}")

        if self.runtime != SandBoxRuntime.VCLUSTER.value:
            msg = (
                f"Shadow runtime '{self.runtime}' is not supported for real cluster "
                "verification. Set SHADOW_RUNTIME=vcluster."
            )
            env.status = ShadowStatus.ERROR
            env.error = msg
            log.error(msg)
            await self._best_effort_cleanup(env)
            raise RuntimeError(msg)

        if not self._vcluster_manager.is_installed():
            msg = "vcluster CLI not installed. Install vcluster to use shadow runtime."
            env.status = ShadowStatus.ERROR
            env.error = msg
            log.error(msg)
            await self._best_effort_cleanup(env)
            raise RuntimeError(msg)

        try:
            # Create host namespace for vCluster
            await self._create_namespace(shadow_namespace, core_api=self._core_api)
            env.logs.append(f"Host namespace {shadow_namespace} created")

            # Create vCluster
            await self._call_api(
                self._vcluster_manager.create,
                env.id,
                shadow_namespace,
            )
            env.logs.append("vCluster created")

            # Get vCluster kubeconfig and build shadow clients
            kubeconfig_path = await self._write_vcluster_kubeconfig(env.id, shadow_namespace)
            env.kubeconfig_path = kubeconfig_path
            shadow_clients = self._build_shadow_clients(kubeconfig_path)
            self._shadow_clients[env.id] = shadow_clients

            # Ensure target namespace exists inside shadow cluster
            await self._create_namespace(env.namespace, core_api=shadow_clients.core)
            env.logs.append(f"Shadow namespace {env.namespace} created in vCluster")

            # Clone the source resource from host to shadow
            await self._clone_resource(
                source_namespace=source_namespace,
                source_name=source_resource,
                source_kind=source_resource_kind,
                target_namespace=env.namespace,
                source_apps_api=self._apps_api,
                source_core_api=self._core_api,
                target_apps_api=shadow_clients.apps,
                target_core_api=shadow_clients.core,
            )
            env.logs.append(f"Cloned {source_resource_kind}/{source_resource} into vCluster")

            env.status = ShadowStatus.READY
            log.info(
                "shadow_created",
                shadow_id=sanitized_id,
                namespace=env.namespace,
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
        verification_plan: VerificationPlan | None = None,
    ) -> bool:
        """Run verification tests in shadow environment.

        Args:
            shadow_id: ID of the shadow environment
            changes: Changes to apply for testing
            duration: Verification duration in seconds (default from settings)
            verification_plan: Optional verification plan for smoke/load testing

        Returns:
            bool: True if verification passed, False otherwise
        """
        env = self._environments.get(shadow_id)
        if not env:
            raise ValueError(f"Shadow environment {shadow_id} not found")

        if env.status != ShadowStatus.READY:
            raise RuntimeError(f"Shadow {shadow_id} not ready: {env.status}")

        shadow_clients = self._shadow_clients.get(env.id)
        if not shadow_clients:
            raise RuntimeError(f"Shadow clients not initialized for {shadow_id}")

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
                await self._apply_changes(env, changes, apps_api=shadow_clients.apps)
                env.logs.append(f"Applied changes: {list(changes.keys())}")

                # Wait for rollout to settle before tests
                await self._wait_for_rollout(env, apps_api=shadow_clients.apps)

                # Resolve target URL + probe paths for smoke/load tests
                target_base, probe_paths = await self._resolve_service_target(
                    env,
                    apps_api=shadow_clients.apps,
                    core_api=shadow_clients.core,
                    preferred_target=verification_plan.load_test_config.target_url
                    if verification_plan and verification_plan.load_test_config
                    else None,
                )

                smoke_result = None
                if target_base:
                    smoke_result = await self._run_smoke_test(
                        env=env,
                        target_base=target_base,
                        paths=probe_paths,
                        core_api=shadow_clients.core,
                        batch_api=shadow_clients.batch,
                    )
                    env.logs.append(
                        f"Smoke test {'passed' if smoke_result['passed'] else 'failed'}"
                    )
                else:
                    env.logs.append("Smoke test skipped: no target URL resolved")

                load_result = None
                load_config = self._resolve_load_test_config(
                    verification_plan=verification_plan,
                    fallback_base=target_base,
                    fallback_paths=probe_paths,
                )
                if load_config and (smoke_result is None or smoke_result["passed"]):
                    load_result = await self._run_load_test(
                        env=env,
                        config=load_config,
                        core_api=shadow_clients.core,
                        batch_api=shadow_clients.batch,
                    )
                    env.logs.append(f"Load test {'passed' if load_result['passed'] else 'failed'}")
                elif load_config and smoke_result and not smoke_result["passed"]:
                    env.logs.append("Load test skipped: smoke test failed")

                # Monitor health for specified duration
                health_score = await self._monitor_health(
                    env,
                    duration,
                    core_api=shadow_clients.core,
                )
                env.health_score = health_score
                env.logs.append(f"Health monitoring complete: score={health_score:.2f}")

                # Evaluate results
                passed = health_score >= HEALTH_THRESHOLD
                if smoke_result is not None:
                    passed = passed and smoke_result["passed"]
                if load_result is not None:
                    passed = passed and load_result["passed"]

                env.status = ShadowStatus.PASSED if passed else ShadowStatus.FAILED
                env.test_results = {
                    "health_score": health_score,
                    "duration": duration,
                    "passed": passed,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "smoke_test": smoke_result,
                    "load_test": load_result,
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
                smoke_passed=smoke_result["passed"] if smoke_result else None,
                load_passed=load_result["passed"] if load_result else None,
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
            if env.runtime == SandBoxRuntime.VCLUSTER.value:
                await self._delete_vcluster(env)
            else:
                # Delete namespace (cascades to all resources)
                await self._delete_namespace(env.namespace)
            env.status = ShadowStatus.DELETED
            log.info("shadow_cleaned", shadow_id=shadow_id)

            # Decrement active shadow counter
            shadow_environments_active.labels(runtime=self.runtime).dec()

        except Exception as e:
            log.exception("cleanup_failed", shadow_id=shadow_id)
            env.error = str(e)
        finally:
            self._dispose_shadow_clients(env.id)

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

    def _load_api_client(
        self,
        *,
        kubeconfig_path: str | None = None,
        context: str | None = None,
        in_cluster: bool | None = None,
    ) -> client.ApiClient:
        """Load Kubernetes config into a dedicated ApiClient."""
        config_obj = client.Configuration()
        use_in_cluster = settings.kubernetes.in_cluster if in_cluster is None else in_cluster
        if use_in_cluster:
            config.load_incluster_config(client_configuration=config_obj)
            log.info("k8s_config_loaded", mode="in_cluster")
        else:
            config.load_kube_config(
                config_file=kubeconfig_path,
                context=context or settings.kubernetes.context,
                client_configuration=config_obj,
            )
            log.info(
                "k8s_config_loaded",
                mode="kubeconfig",
                context=context or settings.kubernetes.context,
            )
        return client.ApiClient(config_obj)

    def _build_shadow_clients(self, kubeconfig_path: str) -> ShadowClients:
        """Create API clients for a shadow cluster."""
        api_client = self._load_api_client(
            kubeconfig_path=kubeconfig_path,
            context=None,
            in_cluster=False,
        )
        return ShadowClients(
            api_client=api_client,
            core=client.CoreV1Api(api_client),
            apps=client.AppsV1Api(api_client),
            batch=client.BatchV1Api(api_client),
            custom=client.CustomObjectsApi(api_client),
        )

    async def _write_vcluster_kubeconfig(self, name: str, namespace: str) -> str:
        """Fetch vCluster kubeconfig and persist it to a temp file."""
        try:
            kubeconfig = await self._call_api(
                self._vcluster_manager.get_kubeconfig, name, namespace
            )
        except RuntimeError as e:
            log.warning(
                "vcluster_kubeconfig_cli_failed",
                shadow=name,
                namespace=namespace,
                error=str(e),
            )
            kubeconfig = await self._get_vcluster_kubeconfig_from_secret(namespace)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as handle:
            handle.write(kubeconfig)
            return handle.name

    async def _get_vcluster_kubeconfig_from_secret(self, namespace: str) -> str:
        """Fallback: read kubeconfig from vCluster secret in host namespace."""
        try:
            secret = cast(
                client.V1Secret,
                await self._call_api(
                    self._core_api.read_namespaced_secret,
                    VCLUSTER_KUBECONFIG_NAME,
                    namespace,
                ),
            )
        except ApiException as e:
            msg = f"Failed to read vCluster kubeconfig secret: {e}"
            log.exception("vcluster_kubeconfig_secret_read_failed", error=str(e))
            raise RuntimeError(msg) from e

        data = secret.data or {}
        for key in ("config", "kubeconfig", "kubeconfig.yaml"):
            if key in data:
                return base64.b64decode(data[key]).decode()

        raise RuntimeError("vCluster kubeconfig secret missing expected data keys")

    async def _delete_vcluster(self, env: ShadowEnvironment) -> None:
        """Delete vCluster and its host namespace."""
        if not env.host_namespace:
            raise RuntimeError("vCluster host namespace not set")

        await self._call_api(self._vcluster_manager.delete, env.id, env.host_namespace)
        await self._delete_namespace(env.host_namespace, core_api=self._core_api)

        if env.kubeconfig_path:
            try:
                Path(env.kubeconfig_path).unlink(missing_ok=True)
            except OSError:
                log.warning("shadow_kubeconfig_cleanup_failed", path=env.kubeconfig_path)

    def _dispose_shadow_clients(self, shadow_id: str) -> None:
        """Dispose of cached shadow clients."""
        clients = self._shadow_clients.pop(shadow_id, None)
        if clients:
            try:
                clients.api_client.close()
            except (OSError, RuntimeError) as exc:
                log.debug("shadow_client_close_failed", shadow_id=shadow_id, error=str(exc))

    async def _best_effort_cleanup(self, env: ShadowEnvironment) -> None:
        """Attempt cleanup after a failed shadow creation."""
        try:
            if env.runtime == SandBoxRuntime.VCLUSTER.value:
                await self._delete_vcluster(env)
            else:
                await self._delete_namespace(env.namespace)
        except ApiException:
            log.warning("shadow_cleanup_failed", shadow_id=env.id)
        finally:
            self._dispose_shadow_clients(env.id)

    async def _create_namespace(self, name: str, core_api: client.CoreV1Api | None = None) -> None:
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
            api = core_api or self._core_api
            await self._call_api(api.create_namespace, namespace)
        except ApiException as e:
            if e.status != HTTP_CONFLICT:  # Already exists is OK
                raise

    async def _delete_namespace(self, name: str, core_api: client.CoreV1Api | None = None) -> None:
        """Delete shadow namespace."""
        try:
            api = core_api or self._core_api
            await self._call_api(api.delete_namespace, name)
        except ApiException as e:
            if e.status != HTTP_NOT_FOUND:  # Not found is OK
                raise

    async def _clone_resource(
        self,
        source_namespace: str,
        source_name: str,
        source_kind: str,
        target_namespace: str,
        source_apps_api: client.AppsV1Api,
        source_core_api: client.CoreV1Api,
        target_apps_api: client.AppsV1Api,
        target_core_api: client.CoreV1Api,
    ) -> None:
        """Clone a resource to the shadow namespace."""
        if source_kind.lower() == "deployment":
            # Get source deployment
            source_deployment = cast(
                client.V1Deployment,
                await self._call_api(
                    source_apps_api.read_namespaced_deployment,
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
                target_apps_api.create_namespaced_deployment,
                target_namespace,
                deployment,
            )

            # Clone matching services into shadow namespace
            await self._clone_services_for_deployment(
                source_namespace=source_namespace,
                target_namespace=target_namespace,
                deployment=deployment,
                source_core_api=source_core_api,
                target_core_api=target_core_api,
            )

        elif source_kind.lower() == "pod":
            # For standalone pods, create a deployment wrapper
            pod = cast(
                client.V1Pod,
                await self._call_api(
                    source_core_api.read_namespaced_pod,
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
                target_apps_api.create_namespaced_deployment,
                target_namespace,
                deployment,
            )

            # Clone matching services into shadow namespace
            await self._clone_services_for_deployment(
                source_namespace=source_namespace,
                target_namespace=target_namespace,
                deployment=deployment,
                source_core_api=source_core_api,
                target_core_api=target_core_api,
            )

        else:
            log.warning(
                "unsupported_resource_kind",
                kind=source_kind,
                message="Only Deployment and Pod cloning supported",
            )

    async def _clone_services_for_deployment(
        self,
        source_namespace: str,
        target_namespace: str,
        deployment: client.V1Deployment,
        source_core_api: client.CoreV1Api,
        target_core_api: client.CoreV1Api,
    ) -> None:
        """Clone matching Services for a deployment into the shadow namespace."""
        if (
            not deployment.spec
            or not deployment.spec.template
            or not deployment.spec.template.metadata
        ):
            return

        pod_labels = deployment.spec.template.metadata.labels or {}
        services = cast(
            client.V1ServiceList,
            await self._call_api(source_core_api.list_namespaced_service, source_namespace),
        )

        for service in services.items:
            selector = service.spec.selector if service.spec else None
            if not selector or not all(pod_labels.get(k) == v for k, v in selector.items()):
                continue

            cloned = copy.deepcopy(service)
            if cloned.metadata is None:
                cloned.metadata = client.V1ObjectMeta()
            cloned.metadata.namespace = target_namespace
            cloned.metadata.resource_version = None
            cloned.metadata.uid = None
            cloned.metadata.creation_timestamp = None
            cloned.metadata.managed_fields = None
            cloned.metadata.owner_references = None
            cloned.metadata.finalizers = None
            cloned.metadata.generation = None

            if cloned.metadata.labels is None:
                cloned.metadata.labels = {}
            cloned.metadata.labels["aegis.io/shadow"] = "true"
            cloned.metadata.labels["aegis.io/source-namespace"] = source_namespace
            cloned.metadata.labels["aegis.io/source-name"] = (
                deployment.metadata.name if deployment.metadata else ""
            )

            if cloned.spec:
                cloned.spec.cluster_ip = None
                cloned.spec.cluster_ips = None
                cloned.spec.type = "ClusterIP"
                for port in cloned.spec.ports or []:
                    port.node_port = None

            try:
                await self._call_api(
                    target_core_api.create_namespaced_service,
                    target_namespace,
                    cloned,
                )
                log.info(
                    "shadow_service_cloned",
                    service=cloned.metadata.name if cloned.metadata else None,
                    shadow_namespace=target_namespace,
                )
            except ApiException as e:
                if e.status != HTTP_CONFLICT:
                    log.warning(
                        "shadow_service_clone_failed",
                        service=service.metadata.name if service.metadata else None,
                        error=str(e),
                    )

    async def _apply_changes(
        self,
        env: ShadowEnvironment,
        changes: dict[str, Any],
        apps_api: client.AppsV1Api,
    ) -> None:
        """Apply proposed changes to shadow environment."""
        if not changes:
            return

        # Apply manifest-based changes first (e.g., ConfigMaps, Secrets, Deployments)
        manifests = changes.get("manifests")
        if manifests:
            await self._apply_manifest_bundle(env, manifests)

        # Normalize kubectl command changes into structured patches
        command_changes = self._extract_command_changes(changes.get("commands", []), env)
        self._merge_command_changes(changes, command_changes)

        deployment = cast(
            client.V1Deployment,
            await self._call_api(
                apps_api.read_namespaced_deployment,
                env.source_resource,
                env.namespace,
            ),
        )
        container_name = self._resolve_container_name(deployment, changes)
        patch = self._build_deployment_patch(
            changes=changes,
            container_name=container_name,
            resource_name=env.source_resource,
        )
        if not patch:
            return

        try:
            await self._call_api(
                apps_api.patch_namespaced_deployment,
                env.source_resource,
                env.namespace,
                patch,
            )
        except ApiException as e:
            log.warning("shadow_patch_failed", error=str(e))

    @staticmethod
    def _merge_command_changes(
        changes: dict[str, Any],
        command_changes: dict[str, Any],
    ) -> None:
        """Merge parsed kubectl command changes into the change set."""
        if not command_changes:
            return
        merged_env = {**changes.get("env", {}), **command_changes.get("env", {})}
        if merged_env:
            changes["env"] = merged_env
        for key in ("replicas", "image", "container"):
            if key in command_changes and key not in changes:
                changes[key] = command_changes[key]

    @staticmethod
    def _resolve_container_name(
        deployment: client.V1Deployment,
        changes: dict[str, Any],
    ) -> str | None:
        """Pick target container name for patching."""
        container_name = changes.get("container") or changes.get("container_name")
        if isinstance(container_name, str) and container_name:
            return container_name

        containers = (
            deployment.spec.template.spec.containers
            if deployment.spec and deployment.spec.template and deployment.spec.template.spec
            else []
        )
        return containers[0].name if containers else None

    def _build_deployment_patch(
        self,
        *,
        changes: dict[str, Any],
        container_name: str | None,
        resource_name: str,
    ) -> dict[str, Any] | None:
        """Build a deployment patch for replicas, image, and env updates."""
        patch: dict[str, Any] = {"spec": {}}
        template_patch: dict[str, Any] = {"spec": {}}
        container_patch: dict[str, Any] = {}

        if "replicas" in changes:
            patch["spec"]["replicas"] = changes["replicas"]

        if "image" in changes:
            if container_name:
                container_patch["name"] = container_name
                container_patch["image"] = changes["image"]
            else:
                log.warning("shadow_patch_no_container", change="image", resource=resource_name)

        if "env" in changes and isinstance(changes["env"], dict):
            env_updates = [{"name": key, "value": value} for key, value in changes["env"].items()]
            if container_name:
                container_patch["name"] = container_name
                container_patch["env"] = env_updates
            else:
                log.warning("shadow_patch_no_container", change="env", resource=resource_name)

        if container_patch:
            template_patch["spec"]["containers"] = [container_patch]

        if template_patch["spec"]:
            patch["spec"]["template"] = template_patch

        if not patch["spec"]:
            return None
        return patch

    async def _apply_manifest_bundle(
        self,
        env: ShadowEnvironment,
        manifests: dict[str, str] | list[str] | str,
    ) -> None:
        """Apply YAML manifests to the shadow cluster using kubectl when available."""
        if not env.kubeconfig_path:
            log.warning("shadow_manifest_missing_kubeconfig", shadow_id=env.id)
            return
        kubectl_path = shutil.which("kubectl")
        if not kubectl_path:
            log.warning("shadow_manifest_kubectl_missing", shadow_id=env.id)
            return
        kubeconfig_path = env.kubeconfig_path

        if isinstance(manifests, dict):
            manifest_blob = "\n---\n".join(manifests.values())
        elif isinstance(manifests, list):
            manifest_blob = "\n---\n".join(manifests)
        else:
            manifest_blob = manifests

        if not manifest_blob.strip():
            return

        process = await asyncio.create_subprocess_exec(
            kubectl_path,
            "--kubeconfig",
            kubeconfig_path,
            "apply",
            "-f",
            "-",
            "-n",
            env.namespace,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(input=manifest_blob.encode())
        if process.returncode != 0:
            stderr_text = stderr.decode(errors="replace").strip() if stderr else ""
            log.warning(
                "shadow_manifest_apply_failed",
                shadow_id=env.id,
                stderr=stderr_text[:500],
            )
        else:
            log.info("shadow_manifest_applied", shadow_id=env.id)

    def _extract_command_changes(
        self,
        commands: Iterable[str],
        env: ShadowEnvironment,
    ) -> dict[str, Any]:
        """Extract structured changes from kubectl commands."""
        extracted: dict[str, Any] = {}
        for command in commands:
            if not command or "kubectl" not in command:
                continue

            try:
                parts = shlex.split(command)
            except ValueError:
                continue

            if not parts or parts[0] != "kubectl":
                continue

            cleaned = self._clean_kubectl_args(parts)
            if len(cleaned) < KUBECTL_MIN_ARGS:
                continue

            self._apply_kubectl_action(cleaned, env, extracted)

        return extracted

    @staticmethod
    def _clean_kubectl_args(parts: list[str]) -> list[str]:
        """Remove global kubeconfig/namespace/context args from kubectl commands."""
        cleaned: list[str] = []
        skip_next = False
        for part in parts[1:]:
            if skip_next:
                skip_next = False
                continue
            if part in KUBECTL_SKIP_ARGS:
                skip_next = True
                continue
            cleaned.append(part)
        return cleaned

    def _apply_kubectl_action(
        self,
        cleaned: list[str],
        env: ShadowEnvironment,
        extracted: dict[str, Any],
    ) -> None:
        action = cleaned[0]
        if action == "set":
            self._apply_kubectl_set(cleaned, env, extracted)
        elif action == "scale":
            self._apply_kubectl_scale(cleaned, env, extracted)

    def _apply_kubectl_set(
        self,
        cleaned: list[str],
        env: ShadowEnvironment,
        extracted: dict[str, Any],
    ) -> None:
        if len(cleaned) < KUBECTL_SET_MIN_ARGS:
            return
        subcommand = cleaned[1]
        resource_name = cleaned[2].split("/", 1)[-1]
        if resource_name != env.source_resource:
            return

        if subcommand == "env":
            self._apply_kubectl_set_env(cleaned[KUBECTL_SET_MIN_ARGS:], extracted)
        elif subcommand == "image":
            self._apply_kubectl_set_image(cleaned, extracted)

    @staticmethod
    def _apply_kubectl_set_env(env_pairs: list[str], extracted: dict[str, Any]) -> None:
        if not env_pairs:
            return
        env_updates = extracted.setdefault("env", {})
        for pair in env_pairs:
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            env_updates[key] = value

    @staticmethod
    def _apply_kubectl_set_image(cleaned: list[str], extracted: dict[str, Any]) -> None:
        if len(cleaned) < KUBECTL_SET_IMAGE_MIN_ARGS:
            return
        image_pair = cleaned[KUBECTL_SET_MIN_ARGS]
        if "=" in image_pair:
            container, image = image_pair.split("=", 1)
            extracted["image"] = image
            extracted["container"] = container

    def _apply_kubectl_scale(
        self,
        cleaned: list[str],
        env: ShadowEnvironment,
        extracted: dict[str, Any],
    ) -> None:
        if len(cleaned) < KUBECTL_MIN_ARGS:
            return
        resource_name = cleaned[1].split("/", 1)[-1]
        if resource_name != env.source_resource:
            return

        replicas = self._parse_kubectl_replicas(cleaned[KUBECTL_MIN_ARGS:])
        if replicas is not None:
            extracted["replicas"] = replicas

    @staticmethod
    def _parse_kubectl_replicas(parts: list[str]) -> int | None:
        for idx, part in enumerate(parts):
            if part.startswith("--replicas="):
                value = part.split("=", 1)[-1]
                return int(value) if value.isdigit() else None
            if part == "--replicas" and idx + 1 < len(parts):
                value = parts[idx + 1]
                return int(value) if value.isdigit() else None
        return None

    async def _wait_for_rollout(
        self,
        env: ShadowEnvironment,
        apps_api: client.AppsV1Api,
        timeout_seconds: int = 120,
    ) -> None:
        """Wait for deployment rollout to reach desired availability."""
        start = time.monotonic()
        while time.monotonic() - start < timeout_seconds:
            deployment = cast(
                client.V1Deployment,
                await self._call_api(
                    apps_api.read_namespaced_deployment,
                    env.source_resource,
                    env.namespace,
                ),
            )
            desired = deployment.spec.replicas if deployment.spec else 1
            available = deployment.status.available_replicas if deployment.status else 0
            if available >= (desired or 1):
                return
            await asyncio.sleep(5)

        log.warning("shadow_rollout_timeout", shadow_id=env.id, deployment=env.source_resource)

    async def _resolve_service_target(
        self,
        env: ShadowEnvironment,
        apps_api: client.AppsV1Api,
        core_api: client.CoreV1Api,
        preferred_target: str | None = None,
    ) -> tuple[str | None, list[str]]:
        """Resolve service base URL and probe paths for smoke/load tests."""
        if preferred_target:
            parsed = urlparse(preferred_target)
            base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else preferred_target
            path = parsed.path or "/"
            return base, [path]

        deployment = cast(
            client.V1Deployment,
            await self._call_api(
                apps_api.read_namespaced_deployment,
                env.source_resource,
                env.namespace,
            ),
        )
        pod_labels: dict[str, str] = {}
        if deployment.spec and deployment.spec.template and deployment.spec.template.metadata:
            pod_labels = deployment.spec.template.metadata.labels or {}

        services = cast(
            client.V1ServiceList,
            await self._call_api(core_api.list_namespaced_service, env.namespace),
        )

        service = None
        for candidate in services.items:
            if candidate.metadata and candidate.metadata.name == env.source_resource:
                service = candidate
                break

        if service is None:
            for candidate in services.items:
                selector = candidate.spec.selector if candidate.spec else None
                if selector and all(pod_labels.get(k) == v for k, v in selector.items()):
                    service = candidate
                    break

        if service is None or not service.spec or not service.spec.ports:
            log.warning("shadow_service_not_found", shadow_id=env.id)
            return None, DEFAULT_SMOKE_PATHS

        port = self._select_service_port(service.spec.ports)
        base_url = f"http://{service.metadata.name}.{env.namespace}.svc.cluster.local:{port}"
        probe_paths = self._extract_probe_paths(deployment)
        return base_url, probe_paths or DEFAULT_SMOKE_PATHS

    @staticmethod
    def _select_service_port(ports: list[client.V1ServicePort]) -> int:
        """Pick the most likely HTTP service port."""

        def _port_value(port: client.V1ServicePort) -> int | None:
            if port.port is None:
                return None
            return int(port.port)

        for port in ports:
            value = _port_value(port)
            if value is None:
                continue
            if port.name and "http" in port.name:
                return value
        for port in ports:
            value = _port_value(port)
            if value == DEFAULT_HTTP_PORT:
                return value
        for port in ports:
            value = _port_value(port)
            if value is not None:
                return value
        raise RuntimeError("Service ports missing values")

    @staticmethod
    def _extract_probe_paths(deployment: client.V1Deployment) -> list[str]:
        """Extract HTTP probe paths from deployment container probes."""
        paths: list[str] = []
        if not deployment.spec or not deployment.spec.template or not deployment.spec.template.spec:
            return paths
        for container in deployment.spec.template.spec.containers or []:
            for probe in (container.liveness_probe, container.readiness_probe):
                if probe and probe.http_get and probe.http_get.path:
                    path = probe.http_get.path
                    if not path.startswith("/"):
                        path = f"/{path}"
                    if path not in paths:
                        paths.append(path)
        return paths

    def _resolve_load_test_config(
        self,
        verification_plan: VerificationPlan | None,
        fallback_base: str | None,
        fallback_paths: list[str],
    ) -> LoadTestConfig | None:
        """Determine load test configuration for shadow verification."""
        if not settings.loadtest.enabled:
            return None

        if verification_plan and verification_plan.load_test_config:
            return verification_plan.load_test_config

        if not fallback_base:
            return None

        path = fallback_paths[0] if fallback_paths else "/"
        return LoadTestConfig(
            users=settings.loadtest.users,
            spawn_rate=settings.loadtest.spawn_rate,
            duration_seconds=settings.loadtest.duration,
            target_url=f"{fallback_base}{path}",
        )

    async def _run_smoke_test(
        self,
        env: ShadowEnvironment,
        target_base: str,
        paths: list[str],
        core_api: client.CoreV1Api,
        batch_api: client.BatchV1Api,
    ) -> dict[str, Any]:
        """Run smoke tests inside the shadow cluster."""
        job_name = self._build_job_name("aegis-smoke", env.id)
        smoke_paths = " ".join(paths)
        script = (
            "set -e\n"
            "for path in $SMOKE_PATHS; do\n"
            '  echo "SMOKE_CHECK ${path}"\n'
            f"  curl -fsS --connect-timeout {CURL_CONNECT_TIMEOUT_SECONDS} "
            f'--max-time {CURL_MAX_TIME_SECONDS} "${{TARGET_BASE}}${{path}}" >/dev/null\n'
            "done\n"
            'echo "SMOKE_OK"\n'
        )

        job = client.V1Job(
            metadata=client.V1ObjectMeta(
                name=job_name,
                namespace=env.namespace,
                labels={"aegis.io/test": "smoke", "aegis.io/shadow-id": env.id},
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                ttl_seconds_after_finished=300,
                active_deadline_seconds=JOB_ACTIVE_DEADLINE_SECONDS,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"aegis.io/test": "smoke"}),
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=[
                            client.V1Container(
                                name="smoke",
                                image=SMOKE_TEST_IMAGE,
                                command=["/bin/sh", "-c", script],
                                env=[
                                    client.V1EnvVar(name="TARGET_BASE", value=target_base),
                                    client.V1EnvVar(name="SMOKE_PATHS", value=smoke_paths),
                                ],
                            )
                        ],
                    ),
                ),
            ),
        )

        start = time.monotonic()
        passed = False
        logs = ""
        try:
            await self._call_api(batch_api.create_namespaced_job, env.namespace, job)
            passed = await self._wait_for_job(
                job_name, env.namespace, batch_api, SMOKE_TEST_TIMEOUT_SECONDS
            )
            logs = await self._get_job_logs(job_name, env.namespace, core_api)
        except (ApiException, RuntimeError) as exc:
            logs = f"Smoke test error: {exc}"
            log.warning("shadow_smoke_test_failed", shadow_id=env.id, error=str(exc))
        finally:
            duration = time.monotonic() - start
            shadow_smoke_test_duration_seconds.observe(duration)
            shadow_smoke_tests_total.labels(
                result="passed" if passed else "failed",
                target="service",
            ).inc()
            log.info(
                "shadow_test_evidence",
                shadow_id=env.id,
                test_type="smoke",
                passed=passed,
                target_url=target_base,
                duration_seconds=round(duration, 2),
            )

        return {
            "passed": passed,
            "target": target_base,
            "paths": paths,
            "duration": round(duration, 2),
            "job": job_name,
            "logs": logs,
        }

    async def _run_load_test(
        self,
        env: ShadowEnvironment,
        config: LoadTestConfig,
        core_api: client.CoreV1Api,
        batch_api: client.BatchV1Api,
    ) -> dict[str, Any]:
        """Run Locust-based load test inside the shadow cluster."""
        job_name = self._build_job_name("aegis-load", env.id)
        parsed = urlparse(config.target_url)
        base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else config.target_url
        path = parsed.path or "/"

        locustfile = "\n".join(
            [
                "from locust import HttpUser, task, between",
                "",
                "class AegisUser(HttpUser):",
                "    wait_time = between(0.1, 0.5)",
                "",
                "    @task",
                "    def hit(self):",
                f'        self.client.get("{path}", timeout={settings.loadtest.timeout})',
            ]
        )
        command = (
            "cat << 'PY' > /tmp/locustfile.py\n"
            f"{locustfile}\n"
            "PY\n"
            f"locust -f /tmp/locustfile.py --headless "
            f"-u {config.users} -r {config.spawn_rate} -t {config.duration_seconds}s "
            f"--host {base}\n"
        )

        job = client.V1Job(
            metadata=client.V1ObjectMeta(
                name=job_name,
                namespace=env.namespace,
                labels={"aegis.io/test": "load", "aegis.io/shadow-id": env.id},
            ),
            spec=client.V1JobSpec(
                backoff_limit=0,
                ttl_seconds_after_finished=300,
                active_deadline_seconds=config.duration_seconds + 60,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"aegis.io/test": "load"}),
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=[
                            client.V1Container(
                                name="load",
                                image=LOAD_TEST_IMAGE,
                                command=["/bin/sh", "-c", command],
                            )
                        ],
                    ),
                ),
            ),
        )

        start = time.monotonic()
        passed = False
        logs = ""
        success_rate = None
        try:
            await self._call_api(batch_api.create_namespaced_job, env.namespace, job)
            job_ok = await self._wait_for_job(
                job_name,
                env.namespace,
                batch_api,
                config.duration_seconds + 90,
            )
            logs = await self._get_job_logs(job_name, env.namespace, core_api)
            failure_rate = self._parse_locust_failure_rate(logs)
            if failure_rate is not None:
                success_rate = 1.0 - failure_rate
                passed = job_ok and success_rate >= settings.loadtest.success_threshold
            else:
                passed = job_ok
        except (ApiException, RuntimeError) as exc:
            logs = f"Load test error: {exc}"
            log.warning("shadow_load_test_failed", shadow_id=env.id, error=str(exc))
        finally:
            duration = time.monotonic() - start
            shadow_load_test_duration_seconds.observe(duration)
            shadow_load_tests_total.labels(
                result="passed" if passed else "failed",
                target="service",
            ).inc()
            log.info(
                "shadow_test_evidence",
                shadow_id=env.id,
                test_type="load",
                passed=passed,
                target_url=config.target_url,
                duration_seconds=round(duration, 2),
                success_rate=round(success_rate, 3) if success_rate is not None else None,
            )

        return {
            "passed": passed,
            "target": config.target_url,
            "duration": round(duration, 2),
            "job": job_name,
            "success_rate": success_rate,
            "logs": logs,
        }

    async def _wait_for_job(
        self,
        job_name: str,
        namespace: str,
        batch_api: client.BatchV1Api,
        timeout_seconds: int,
    ) -> bool:
        """Wait for a Kubernetes Job to complete."""
        start = time.monotonic()
        while time.monotonic() - start < timeout_seconds:
            job = cast(
                client.V1Job,
                await self._call_api(batch_api.read_namespaced_job, job_name, namespace),
            )
            status = job.status
            if status and status.succeeded and status.succeeded >= 1:
                return True
            if status and status.failed and status.failed >= 1:
                return False
            await asyncio.sleep(JOB_POLL_INTERVAL_SECONDS)
        return False

    async def _get_job_logs(
        self,
        job_name: str,
        namespace: str,
        core_api: client.CoreV1Api,
    ) -> str:
        """Fetch logs from the first pod of a job."""
        pods = cast(
            client.V1PodList,
            await self._call_api(
                core_api.list_namespaced_pod,
                namespace,
                label_selector=f"job-name={job_name}",
            ),
        )
        if not pods.items:
            return ""
        pod_name = pods.items[0].metadata.name if pods.items[0].metadata else None
        if not pod_name:
            return ""
        try:
            logs = await self._call_api(core_api.read_namespaced_pod_log, pod_name, namespace)
        except ApiException:
            return ""
        return str(logs) if logs is not None else ""

    @staticmethod
    def _parse_locust_failure_rate(logs: str) -> float | None:
        """Parse Locust failure rate from logs."""
        for line in logs.splitlines():
            if line.strip().startswith("Aggregated"):
                match = re.search(r"\((\d+\.?\d*)%\)", line)
                if match:
                    return float(match.group(1)) / 100.0
        return None

    @classmethod
    def _build_job_name(cls, prefix: str, shadow_id: str) -> str:
        """Build a DNS-safe job name within the length limit."""
        raw = f"{prefix}-{shadow_id}-{int(time.time())}"
        name = cls._sanitize_name(raw)
        return name[:K8S_NAME_MAX_LENGTH].rstrip("-")

    async def _monitor_health(
        self,
        env: ShadowEnvironment,
        duration: int,
        core_api: client.CoreV1Api,
    ) -> float:
        """Monitor shadow environment health.

        Returns health score between 0.0 and 1.0.
        """
        check_interval = 5  # seconds
        checks = []

        elapsed = 0
        while elapsed < duration:
            score = await self._check_health(env, core_api=core_api)
            checks.append(score)
            elapsed += check_interval
            await asyncio.sleep(check_interval)

        # Average health score
        if checks:
            return sum(checks) / len(checks)
        return 0.0

    async def _check_health(
        self,
        env: ShadowEnvironment,
        core_api: client.CoreV1Api,
    ) -> float:
        """Single health check for shadow environment."""
        try:
            pods = cast(
                client.V1PodList,
                await self._call_api(core_api.list_namespaced_pod, env.namespace),
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
