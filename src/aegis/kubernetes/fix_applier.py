"""Kubernetes Fix Applier with Dry-Run Validation.

This module provides the core fix application logic for AEGIS remediation.
It supports multiple fix types and always validates with dry-run before
actually applying changes to the cluster.

Supported fix types:
- config_change: Update ConfigMaps, Secrets, or resource specs
- scale: Adjust replica counts for Deployments/StatefulSets
- rollback: Rollback to a previous revision
- restart: Trigger rolling restart via annotation
- resource_adjustment: Update resource requests/limits
- patch: Apply arbitrary JSON patches

All fixes are validated with server-side dry-run before application.
"""

import contextlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, assert_never

from kubernetes import client
from kubernetes import config as k8s_config

from aegis.crd import FixProposal, FixType
from aegis.observability._logging import get_logger


log = get_logger(__name__)

# HTTP Status Codes
HTTP_CONFLICT = 409

# Minimum revision count for rollback availability
MIN_REVISIONS_FOR_ROLLBACK = 2


@dataclass
class FixResult:
    """Result of a fix application attempt."""

    success: bool
    dry_run_passed: bool = False
    applied: bool = False
    error_message: str | None = None
    applied_at: datetime | None = None
    resource_version: str | None = None
    rollback_info: dict[str, Any] = field(default_factory=dict)


class FixApplier:
    """Applies fixes to Kubernetes resources with dry-run validation.

    This class implements the fix application logic for AEGIS remediation.
    All fixes go through a two-phase process:
    1. Dry-run validation to ensure the fix is valid
    2. Actual application if dry-run succeeds

    Attributes:
        core_api: Kubernetes CoreV1Api client
        apps_api: Kubernetes AppsV1Api client
        custom_api: Kubernetes CustomObjectsApi client
    """

    def __init__(self) -> None:
        """Initialize the FixApplier with Kubernetes clients."""
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()

    async def apply_fix(
        self,
        fix_proposal: FixProposal,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply a fix proposal to a Kubernetes resource.

        Args:
            fix_proposal: The fix proposal to apply
            resource_kind: Kind of the target resource (e.g., "Pod", "Deployment")
            resource_name: Name of the target resource
            namespace: Namespace of the target resource

        Returns:
            FixResult: Result of the fix application
        """
        log.info(
            "applying_fix",
            fix_type=fix_proposal.fix_type.value,
            resource=f"{resource_kind}/{resource_name}",
            namespace=namespace,
        )

        result = FixResult(success=False)

        try:
            # Route to appropriate handler based on fix type
            if fix_proposal.fix_type == FixType.RESTART:
                result = await self._apply_restart(resource_kind, resource_name, namespace)
            elif fix_proposal.fix_type == FixType.SCALE:
                result = await self._apply_scale(
                    fix_proposal, resource_kind, resource_name, namespace
                )
            elif fix_proposal.fix_type == FixType.ROLLBACK:
                result = await self._apply_rollback(resource_kind, resource_name, namespace)
            elif fix_proposal.fix_type == FixType.RESOURCE_ADJUSTMENT:
                result = await self._apply_resource_adjustment(
                    fix_proposal, resource_kind, resource_name, namespace
                )
            elif fix_proposal.fix_type == FixType.CONFIG_CHANGE:
                result = await self._apply_config_change(
                    fix_proposal, resource_kind, resource_name, namespace
                )
            elif fix_proposal.fix_type == FixType.PATCH:
                result = await self._apply_patch(
                    fix_proposal, resource_kind, resource_name, namespace
                )
            else:
                # All FixType values handled above; this branch is for type safety
                assert_never(fix_proposal.fix_type)

        except client.ApiException as e:
            result.error_message = f"Kubernetes API error: {e.reason}"
            log.exception("fix_application_failed", error=e.reason)
        except Exception as e:
            result.error_message = f"Unexpected error: {e!s}"
            log.exception("fix_application_error")

        return result

    async def _apply_restart(
        self,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply a rolling restart by updating the pod template annotation.

        This triggers a rolling restart without changing the actual configuration.
        """
        result = FixResult(success=False)

        restart_annotation = "aegis.io/restartedAt"
        restart_time = datetime.now(UTC).isoformat()

        if resource_kind.lower() in ["deployment", "deployments"]:
            # Get current deployment for rollback info
            current = self.apps_api.read_namespaced_deployment(resource_name, namespace)
            result.rollback_info = {
                "kind": "Deployment",
                "name": resource_name,
                "namespace": namespace,
                "previous_version": current.metadata.resource_version,
            }

            # Build patch
            patch_body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                restart_annotation: restart_time,
                            }
                        }
                    }
                }
            }

            # Dry-run first
            try:
                self.apps_api.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
                log.info("restart_dry_run_passed", deployment=resource_name)
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                log.exception("restart_dry_run_failed", error=e.reason)
                return result

            # Apply actual patch
            updated = self.apps_api.patch_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version
            log.info("restart_applied", deployment=resource_name)

        elif resource_kind.lower() in ["statefulset", "statefulsets"]:
            current = self.apps_api.read_namespaced_stateful_set(resource_name, namespace)
            result.rollback_info = {
                "kind": "StatefulSet",
                "name": resource_name,
                "namespace": namespace,
                "previous_version": current.metadata.resource_version,
            }

            patch_body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                restart_annotation: restart_time,
                            }
                        }
                    }
                }
            }

            # Dry-run
            try:
                self.apps_api.patch_namespaced_stateful_set(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            # Apply
            updated = self.apps_api.patch_namespaced_stateful_set(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version

        elif resource_kind.lower() in ["daemonset", "daemonsets"]:
            current = self.apps_api.read_namespaced_daemon_set(resource_name, namespace)
            result.rollback_info = {
                "kind": "DaemonSet",
                "name": resource_name,
                "namespace": namespace,
                "previous_version": current.metadata.resource_version,
            }

            patch_body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                restart_annotation: restart_time,
                            }
                        }
                    }
                }
            }

            try:
                self.apps_api.patch_namespaced_daemon_set(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            updated = self.apps_api.patch_namespaced_daemon_set(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version

        else:
            result.error_message = f"Restart not supported for {resource_kind}"

        return result

    async def _apply_scale(
        self,
        fix_proposal: FixProposal,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply a scaling operation."""
        result = FixResult(success=False)

        # Extract target replicas from commands or patch
        target_replicas = None
        for cmd in fix_proposal.commands:
            if "replicas=" in cmd:
                with contextlib.suppress(IndexError, ValueError):
                    target_replicas = int(cmd.split("replicas=")[1].split()[0])

        if target_replicas is None:
            result.error_message = "Could not determine target replica count from fix proposal"
            return result

        if resource_kind.lower() in ["deployment", "deployments"]:
            current = self.apps_api.read_namespaced_deployment(resource_name, namespace)
            result.rollback_info = {
                "kind": "Deployment",
                "name": resource_name,
                "namespace": namespace,
                "previous_replicas": current.spec.replicas,
            }

            patch_body = {"spec": {"replicas": target_replicas}}

            # Dry-run
            try:
                self.apps_api.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            # Apply
            updated = self.apps_api.patch_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version
            log.info("scale_applied", deployment=resource_name, replicas=target_replicas)

        elif resource_kind.lower() in ["statefulset", "statefulsets"]:
            current = self.apps_api.read_namespaced_stateful_set(resource_name, namespace)
            result.rollback_info = {
                "kind": "StatefulSet",
                "name": resource_name,
                "namespace": namespace,
                "previous_replicas": current.spec.replicas,
            }

            patch_body = {"spec": {"replicas": target_replicas}}

            try:
                self.apps_api.patch_namespaced_stateful_set(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            updated = self.apps_api.patch_namespaced_stateful_set(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version

        else:
            result.error_message = f"Scale not supported for {resource_kind}"

        return result

    async def _apply_rollback(
        self,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply a rollback to previous revision."""
        result = FixResult(success=False)

        if resource_kind.lower() not in ["deployment", "deployments"]:
            result.error_message = f"Rollback not supported for {resource_kind}"
            return result

        # Get deployment history
        deployment = self.apps_api.read_namespaced_deployment(resource_name, namespace)
        result.rollback_info = {
            "kind": "Deployment",
            "name": resource_name,
            "namespace": namespace,
            "current_revision": deployment.metadata.annotations.get(
                "deployment.kubernetes.io/revision", "unknown"
            ),
        }

        # Get ReplicaSets to find previous revision
        label_selector = ",".join(
            f"{k}={v}" for k, v in (deployment.spec.selector.match_labels or {}).items()
        )
        replica_sets = self.apps_api.list_namespaced_replica_set(
            namespace=namespace,
            label_selector=label_selector,
        )

        # Sort by revision number
        revisions = []
        for rs in replica_sets.items:
            revision_str = rs.metadata.annotations.get("deployment.kubernetes.io/revision", "0")
            try:
                revision = int(revision_str)
                revisions.append((revision, rs))
            except ValueError:
                continue

        revisions.sort(key=lambda x: x[0], reverse=True)

        if len(revisions) < MIN_REVISIONS_FOR_ROLLBACK:
            result.error_message = "No previous revision available for rollback"
            return result

        # Get the previous revision's template
        previous_rs = revisions[1][1]
        previous_template = previous_rs.spec.template

        # Create rollback patch
        patch_body = {
            "spec": {
                "template": {
                    "spec": previous_template.spec.to_dict(),
                }
            }
        }

        # Dry-run
        try:
            self.apps_api.patch_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
                dry_run="All",
            )
            result.dry_run_passed = True
        except client.ApiException as e:
            result.error_message = f"Dry-run failed: {e.reason}"
            return result

        # Apply rollback
        updated = self.apps_api.patch_namespaced_deployment(
            name=resource_name,
            namespace=namespace,
            body=patch_body,
        )
        result.success = True
        result.applied = True
        result.applied_at = datetime.now(UTC)
        result.resource_version = updated.metadata.resource_version
        result.rollback_info["rolled_back_to"] = revisions[1][0]
        log.info(
            "rollback_applied",
            deployment=resource_name,
            from_revision=revisions[0][0],
            to_revision=revisions[1][0],
        )

        return result

    async def _apply_resource_adjustment(
        self,
        fix_proposal: FixProposal,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply resource requests/limits adjustments."""
        result = FixResult(success=False)

        # Parse resource changes from commands
        # Expected format: kubectl set resources deployment/name -c container --limits=cpu=500m,memory=512Mi
        resources_patch: dict[str, Any] = {}
        for cmd in fix_proposal.commands:
            if "--limits=" in cmd:
                limits_str = cmd.split("--limits=")[1].split()[0]
                limits = {}
                for item in limits_str.split(","):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        limits[k] = v
                resources_patch["limits"] = limits
            if "--requests=" in cmd:
                requests_str = cmd.split("--requests=")[1].split()[0]
                requests = {}
                for item in requests_str.split(","):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        requests[k] = v
                resources_patch["requests"] = requests

        if not resources_patch:
            result.error_message = "Could not parse resource adjustments from fix proposal"
            return result

        if resource_kind.lower() in ["deployment", "deployments"]:
            current = self.apps_api.read_namespaced_deployment(resource_name, namespace)
            containers = current.spec.template.spec.containers
            if not containers:
                result.error_message = "Deployment has no containers"
                return result

            result.rollback_info = {
                "kind": "Deployment",
                "name": resource_name,
                "namespace": namespace,
                "previous_resources": {
                    c.name: c.resources.to_dict() if c.resources else {} for c in containers
                },
            }

            # Update first container's resources
            patch_body = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": containers[0].name,
                                    "resources": resources_patch,
                                }
                            ]
                        }
                    }
                }
            }

            # Dry-run
            try:
                self.apps_api.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            # Apply
            updated = self.apps_api.patch_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version
            log.info("resource_adjustment_applied", deployment=resource_name)

        else:
            result.error_message = f"Resource adjustment not supported for {resource_kind}"

        return result

    async def _apply_config_change(
        self,
        fix_proposal: FixProposal,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply configuration changes (ConfigMaps, environment variables, etc.)."""
        result = FixResult(success=False)

        # Check if we have manifests to apply
        if fix_proposal.manifests:
            for manifest_name, manifest_content in fix_proposal.manifests.items():
                try:
                    import yaml

                    manifest = yaml.safe_load(manifest_content)
                    manifest_kind = manifest.get("kind", "")
                    manifest_meta = manifest.get("metadata", {})
                    manifest_ns = manifest_meta.get("namespace", namespace)

                    if manifest_kind == "ConfigMap":
                        # Dry-run
                        try:
                            self.core_api.patch_namespaced_config_map(
                                name=manifest_meta.get("name"),
                                namespace=manifest_ns,
                                body=manifest,
                                dry_run="All",
                            )
                            result.dry_run_passed = True
                        except client.ApiException as e:
                            if e.status == HTTP_CONFLICT:
                                # ConfigMap doesn't exist, create it
                                self.core_api.create_namespaced_config_map(
                                    namespace=manifest_ns,
                                    body=manifest,
                                    dry_run="All",
                                )
                                result.dry_run_passed = True
                            else:
                                result.error_message = f"Dry-run failed: {e.reason}"
                                return result

                        # Apply
                        try:
                            self.core_api.patch_namespaced_config_map(
                                name=manifest_meta.get("name"),
                                namespace=manifest_ns,
                                body=manifest,
                            )
                        except client.ApiException as e:
                            if e.status == HTTP_CONFLICT:
                                self.core_api.create_namespaced_config_map(
                                    namespace=manifest_ns,
                                    body=manifest,
                                )
                            else:
                                raise

                        result.success = True
                        result.applied = True
                        result.applied_at = datetime.now(UTC)
                        log.info("config_map_applied", name=manifest_name)

                except (client.ApiException, KeyError, TypeError, yaml.YAMLError) as e:
                    result.error_message = f"Failed to apply manifest {manifest_name}: {e}"
                    return result

        elif fix_proposal.patch:
            # Apply JSON patch directly
            result = await self._apply_patch(fix_proposal, resource_kind, resource_name, namespace)

        else:
            result.error_message = "No manifests or patch in config_change fix proposal"

        return result

    async def _apply_patch(
        self,
        fix_proposal: FixProposal,
        resource_kind: str,
        resource_name: str,
        namespace: str,
    ) -> FixResult:
        """Apply a JSON patch to a resource."""
        result = FixResult(success=False)

        if not fix_proposal.patch:
            result.error_message = "No patch provided"
            return result

        try:
            patch_body = json.loads(fix_proposal.patch)
        except json.JSONDecodeError as e:
            result.error_message = f"Invalid JSON patch: {e}"
            return result

        if resource_kind.lower() in ["deployment", "deployments"]:
            current = self.apps_api.read_namespaced_deployment(resource_name, namespace)
            result.rollback_info = {
                "kind": "Deployment",
                "name": resource_name,
                "namespace": namespace,
                "previous_version": current.metadata.resource_version,
            }

            # Dry-run
            try:
                self.apps_api.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            # Apply
            updated = self.apps_api.patch_namespaced_deployment(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version

        elif resource_kind.lower() in ["pod", "pods"]:
            current = self.core_api.read_namespaced_pod(resource_name, namespace)
            result.rollback_info = {
                "kind": "Pod",
                "name": resource_name,
                "namespace": namespace,
                "previous_version": current.metadata.resource_version,
            }

            try:
                self.core_api.patch_namespaced_pod(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            updated = self.core_api.patch_namespaced_pod(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version

        elif resource_kind.lower() in ["configmap", "configmaps"]:
            current = self.core_api.read_namespaced_config_map(resource_name, namespace)
            result.rollback_info = {
                "kind": "ConfigMap",
                "name": resource_name,
                "namespace": namespace,
                "previous_data": current.data,
            }

            try:
                self.core_api.patch_namespaced_config_map(
                    name=resource_name,
                    namespace=namespace,
                    body=patch_body,
                    dry_run="All",
                )
                result.dry_run_passed = True
            except client.ApiException as e:
                result.error_message = f"Dry-run failed: {e.reason}"
                return result

            updated = self.core_api.patch_namespaced_config_map(
                name=resource_name,
                namespace=namespace,
                body=patch_body,
            )
            result.success = True
            result.applied = True
            result.applied_at = datetime.now(UTC)
            result.resource_version = updated.metadata.resource_version

        else:
            result.error_message = f"Patch not supported for {resource_kind}"

        return result


class _FixApplierHolder:
    """Holder class for FixApplier singleton to avoid global statement."""

    instance: FixApplier | None = None


def get_fix_applier() -> FixApplier:
    """Get the singleton FixApplier instance."""
    if _FixApplierHolder.instance is None:
        _FixApplierHolder.instance = FixApplier()
    return _FixApplierHolder.instance


__all__ = [
    "FixApplier",
    "FixResult",
    "get_fix_applier",
]
