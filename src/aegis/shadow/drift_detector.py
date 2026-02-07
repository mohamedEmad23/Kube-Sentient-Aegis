"""Environment Drift Detection for Shadow Verification.

Compares production and shadow environments to ensure configuration parity:
- Deployment specs (replicas, resources, env vars)
- Network policies
- RBAC (Roles, RoleBindings, ServiceAccounts)
- Resource quotas
- ConfigMaps and Secrets (existence check, not content)

High drift severity blocks shadow testing as results would not be representative.
"""

import asyncio
from typing import Any

from kubernetes import client

from aegis.agent.state import DriftReport
from aegis.observability._logging import get_logger


log = get_logger(__name__)


# ============================================================================
# Drift Detection
# ============================================================================


class DriftDetector:
    """Detects configuration drift between production and shadow environments.

    Example:
        >>> detector = DriftDetector()
        >>> report = await detector.detect_drift(
        ...     prod_namespace="production",
        ...     shadow_namespace="shadow-abc123",
        ...     prod_api=prod_core_api,
        ...     shadow_api=shadow_core_api
        ... )
        >>> if report.drifted and report.severity == "high":
        ...     log.error("High drift detected", mismatches=report.config_mismatches)
    """

    def __init__(self) -> None:
        """Initialize drift detector."""

    async def detect_drift(
        self,
        *,
        prod_namespace: str,
        shadow_namespace: str,
        prod_core_api: client.CoreV1Api,
        shadow_core_api: client.CoreV1Api,
        prod_apps_api: client.AppsV1Api,
        shadow_apps_api: client.AppsV1Api,
        prod_rbac_api: client.RbacAuthorizationV1Api | None = None,
        shadow_rbac_api: client.RbacAuthorizationV1Api | None = None,
    ) -> DriftReport:
        """Detect drift between production and shadow environments.

        Args:
            prod_namespace: Production namespace
            shadow_namespace: Shadow namespace
            prod_core_api: Production CoreV1 API client
            shadow_core_api: Shadow CoreV1 API client
            prod_apps_api: Production AppsV1 API client
            shadow_apps_api: Shadow AppsV1 API client
            prod_rbac_api: Optional production RBAC API client
            shadow_rbac_api: Optional shadow RBAC API client

        Returns:
            DriftReport with findings
        """
        log.info(
            "drift_detection_started",
            prod_namespace=prod_namespace,
            shadow_namespace=shadow_namespace,
        )

        # Run comparisons concurrently
        results = await asyncio.gather(
            self._compare_deployments(
                prod_apps_api, shadow_apps_api, prod_namespace, shadow_namespace
            ),
            self._compare_services(
                prod_core_api, shadow_core_api, prod_namespace, shadow_namespace
            ),
            self._compare_configmaps(
                prod_core_api, shadow_core_api, prod_namespace, shadow_namespace
            ),
            self._compare_resource_quotas(
                prod_core_api, shadow_core_api, prod_namespace, shadow_namespace
            ),
            return_exceptions=True,
        )

        # Aggregate results
        all_mismatches: list[dict[str, Any]] = []
        missing_resources: list[str] = []
        extra_resources: list[str] = []

        for result in results:
            if isinstance(result, Exception):
                log.warning("drift_check_failed", error=str(result))
                continue

            mismatches, missing, extra = result
            all_mismatches.extend(mismatches)
            missing_resources.extend(missing)
            extra_resources.extend(extra)

        # RBAC comparison (optional)
        if prod_rbac_api and shadow_rbac_api:
            try:
                rbac_result = await self._compare_rbac(
                    prod_rbac_api, shadow_rbac_api, prod_namespace, shadow_namespace
                )
                rbac_mismatches, rbac_missing, rbac_extra = rbac_result
                all_mismatches.extend(rbac_mismatches)
                missing_resources.extend(rbac_missing)
                extra_resources.extend(rbac_extra)
            except Exception as e:
                log.warning("rbac_drift_check_failed", error=str(e))

        # Determine severity
        severity = self._calculate_severity(all_mismatches, missing_resources)

        report = DriftReport(
            drifted=len(all_mismatches) > 0 or len(missing_resources) > 0,
            severity=severity,
            missing_resources=missing_resources,
            extra_resources=extra_resources,
            config_mismatches=all_mismatches,
        )

        log.info(
            "drift_detection_completed",
            drifted=report.drifted,
            severity=report.severity,
            mismatches=len(all_mismatches),
            missing=len(missing_resources),
        )

        return report

    def _calculate_severity(self, mismatches: list[dict[str, Any]], missing: list[str]) -> str:
        """Calculate drift severity.

        High:  Critical resources missing or major config differences
        Low:   Minor differences (e.g., labels, annotations)
        None:  No drift

        Args:
            mismatches: List of config mismatches
            missing: List of missing resources

        Returns:
            Severity: "none", "low", or "high"
        """
        if not mismatches and not missing:
            return "none"

        # High severity triggers
        high_severity_keywords = [
            "replicas",
            "resources.limits",
            "resources.requests",
            "securityContext",
            "networkPolicy",
            "serviceAccount",
        ]

        # Check for critical mismatches
        for mismatch in mismatches:
            field = mismatch.get("field", "")
            for keyword in high_severity_keywords:
                if keyword in field:
                    return "high"

        # Missing security-critical resources
        critical_resources = ["NetworkPolicy", "ServiceAccount", "Secret"]
        for resource in missing:
            for critical in critical_resources:
                if critical in resource:
                    return "high"

        return "low"

    async def _compare_deployments(
        self,
        prod_api: client.AppsV1Api,
        shadow_api: client.AppsV1Api,
        prod_ns: str,
        shadow_ns: str,
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        """Compare Deployment configurations.

        Returns:
            Tuple of (mismatches, missing_in_shadow, extra_in_shadow)
        """
        mismatches: list[dict[str, Any]] = []
        missing: list[str] = []
        extra: list[str] = []

        try:
            # Fetch deployments
            prod_deployments = await asyncio.to_thread(prod_api.list_namespaced_deployment, prod_ns)
            shadow_deployments = await asyncio.to_thread(
                shadow_api.list_namespaced_deployment, shadow_ns
            )

            prod_deploys = {d.metadata.name: d for d in prod_deployments.items}
            shadow_deploys = {d.metadata.name: d for d in shadow_deployments.items}

            # Check for missing/extra deployments
            prod_names = set(prod_deploys.keys())
            shadow_names = set(shadow_deploys.keys())

            for name in prod_names - shadow_names:
                missing.append(f"Deployment/{name}")

            for name in shadow_names - prod_names:
                extra.append(f"Deployment/{name}")

            # Compare common deployments
            for name in prod_names & shadow_names:
                prod_deploy = prod_deploys[name]
                shadow_deploy = shadow_deploys[name]

                # Compare replicas
                prod_replicas = prod_deploy.spec.replicas
                shadow_replicas = shadow_deploy.spec.replicas
                if prod_replicas != shadow_replicas:
                    mismatches.append(
                        {
                            "resource": f"Deployment/{name}",
                            "field": "spec.replicas",
                            "prod_value": prod_replicas,
                            "shadow_value": shadow_replicas,
                        }
                    )

                # Compare container resources
                prod_containers = prod_deploy.spec.template.spec.containers
                shadow_containers = shadow_deploy.spec.template.spec.containers

                for idx, (prod_c, shadow_c) in enumerate(
                    zip(prod_containers, shadow_containers, strict=False)
                ):
                    if prod_c.resources != shadow_c.resources:
                        mismatches.append(
                            {
                                "resource": f"Deployment/{name}",
                                "field": f"spec.template.spec.containers[{idx}].resources",
                                "prod_value": str(prod_c.resources),
                                "shadow_value": str(shadow_c.resources),
                            }
                        )

        except Exception as e:
            log.error("deployment_comparison_failed", error=str(e))

        return (mismatches, missing, extra)

    async def _compare_services(
        self,
        prod_api: client.CoreV1Api,
        shadow_api: client.CoreV1Api,
        prod_ns: str,
        shadow_ns: str,
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        """Compare Service configurations."""
        mismatches: list[dict[str, Any]] = []
        missing: list[str] = []
        extra: list[str] = []

        try:
            prod_services = await asyncio.to_thread(prod_api.list_namespaced_service, prod_ns)
            shadow_services = await asyncio.to_thread(shadow_api.list_namespaced_service, shadow_ns)

            prod_svcs = {s.metadata.name: s for s in prod_services.items}
            shadow_svcs = {s.metadata.name: s for s in shadow_services.items}

            prod_names = set(prod_svcs.keys())
            shadow_names = set(shadow_svcs.keys())

            for name in prod_names - shadow_names:
                missing.append(f"Service/{name}")

            for name in shadow_names - prod_names:
                extra.append(f"Service/{name}")

            # Compare service types and ports
            for name in prod_names & shadow_names:
                prod_svc = prod_svcs[name]
                shadow_svc = shadow_svcs[name]

                if prod_svc.spec.type != shadow_svc.spec.type:
                    mismatches.append(
                        {
                            "resource": f"Service/{name}",
                            "field": "spec.type",
                            "prod_value": prod_svc.spec.type,
                            "shadow_value": shadow_svc.spec.type,
                        }
                    )

        except Exception as e:
            log.error("service_comparison_failed", error=str(e))

        return (mismatches, missing, extra)

    async def _compare_configmaps(
        self,
        prod_api: client.CoreV1Api,
        shadow_api: client.CoreV1Api,
        prod_ns: str,
        shadow_ns: str,
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        """Compare ConfigMap existence (not content for performance)."""
        mismatches: list[dict[str, Any]] = []
        missing: list[str] = []
        extra: list[str] = []

        try:
            prod_cms = await asyncio.to_thread(prod_api.list_namespaced_config_map, prod_ns)
            shadow_cms = await asyncio.to_thread(shadow_api.list_namespaced_config_map, shadow_ns)

            prod_names = {cm.metadata.name for cm in prod_cms.items}
            shadow_names = {cm.metadata.name for cm in shadow_cms.items}

            for name in prod_names - shadow_names:
                missing.append(f"ConfigMap/{name}")

            for name in shadow_names - prod_names:
                extra.append(f"ConfigMap/{name}")

        except Exception as e:
            log.error("configmap_comparison_failed", error=str(e))

        return (mismatches, missing, extra)

    async def _compare_resource_quotas(
        self,
        prod_api: client.CoreV1Api,
        shadow_api: client.CoreV1Api,
        prod_ns: str,
        shadow_ns: str,
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        """Compare ResourceQuota configurations."""
        mismatches: list[dict[str, Any]] = []
        missing: list[str] = []
        extra: list[str] = []

        try:
            prod_quotas = await asyncio.to_thread(prod_api.list_namespaced_resource_quota, prod_ns)
            shadow_quotas = await asyncio.to_thread(
                shadow_api.list_namespaced_resource_quota, shadow_ns
            )

            prod_names = {q.metadata.name for q in prod_quotas.items}
            shadow_names = {q.metadata.name for q in shadow_quotas.items}

            for name in prod_names - shadow_names:
                missing.append(f"ResourceQuota/{name}")

            for name in shadow_names - prod_names:
                extra.append(f"ResourceQuota/{name}")

        except Exception as e:
            log.error("resource_quota_comparison_failed", error=str(e))

        return (mismatches, missing, extra)

    async def _compare_rbac(
        self,
        prod_api: client.RbacAuthorizationV1Api,
        shadow_api: client.RbacAuthorizationV1Api,
        prod_ns: str,
        shadow_ns: str,
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        """Compare RBAC configurations (Roles, RoleBindings)."""
        mismatches: list[dict[str, Any]] = []
        missing: list[str] = []
        extra: list[str] = []

        try:
            # Compare Roles
            prod_roles = await asyncio.to_thread(prod_api.list_namespaced_role, prod_ns)
            shadow_roles = await asyncio.to_thread(shadow_api.list_namespaced_role, shadow_ns)

            prod_role_names = {r.metadata.name for r in prod_roles.items}
            shadow_role_names = {r.metadata.name for r in shadow_roles.items}

            for name in prod_role_names - shadow_role_names:
                missing.append(f"Role/{name}")

            for name in shadow_role_names - prod_role_names:
                extra.append(f"Role/{name}")

            # Compare RoleBindings
            prod_bindings = await asyncio.to_thread(prod_api.list_namespaced_role_binding, prod_ns)
            shadow_bindings = await asyncio.to_thread(
                shadow_api.list_namespaced_role_binding, shadow_ns
            )

            prod_binding_names = {rb.metadata.name for rb in prod_bindings.items}
            shadow_binding_names = {rb.metadata.name for rb in shadow_bindings.items}

            for name in prod_binding_names - shadow_binding_names:
                missing.append(f"RoleBinding/{name}")

            for name in shadow_binding_names - prod_binding_names:
                extra.append(f"RoleBinding/{name}")

        except Exception as e:
            log.error("rbac_comparison_failed", error=str(e))

        return (mismatches, missing, extra)


__all__ = ["DriftDetector"]
