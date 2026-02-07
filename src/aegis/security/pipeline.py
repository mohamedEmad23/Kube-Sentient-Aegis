"""Security scanning pipeline for shadow verification.

This module orchestrates all security scans during shadow verification:
1. Kubesec - Static manifest analysis (BEFORE deployment)
2. Trivy - Container image vulnerability scanning (AFTER deployment)
3. Falco - Runtime behavior monitoring (DURING verification)

Integration point: Called by ShadowManager.run_verification()
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import yaml
from kubernetes import client

from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.security.falco import FalcoMonitor
from aegis.security.kubesec import KubesecScanner
from aegis.security.trivy import TrivyScanner


log = get_logger(__name__)


@dataclass
class SecurityScanResults:
    """Aggregated results from all security scans."""

    passed: bool
    kubesec: dict[str, Any] | None = None
    trivy: dict[str, Any] | None = None
    falco: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for storage in ShadowEnvironment.test_results."""
        return {
            "passed": self.passed,
            "kubesec": self.kubesec,
            "trivy": self.trivy,
            "falco": self.falco,
            "errors": self.errors,
        }


class SecurityPipeline:
    """Orchestrates security scans for shadow verification.

    Usage:
        pipeline = SecurityPipeline()

        # Before applying changes - scan the proposed manifests
        kubesec_result = await pipeline.scan_manifests(manifests)

        # After deploying to shadow - scan container images
        trivy_result = await pipeline.scan_images(images)

        # After verification - check runtime alerts
        falco_result = await pipeline.check_runtime_alerts(namespace, core_api)

        # Or run all applicable scans
        results = await pipeline.run_full_scan(
            manifests=manifests,
            images=images,
            namespace=namespace,
            core_api=core_api,
        )
    """

    def __init__(self) -> None:
        self._kubesec = KubesecScanner()
        self._trivy = TrivyScanner()
        self._falco = FalcoMonitor()
        if not any(
            [
                settings.security.trivy_enabled,
                settings.security.kubesec_enabled,
                settings.security.zap_enabled,
                settings.security.falco_enabled,
            ]
        ):
            log.warning(
                "security_scans_disabled_demo_mode",
                reminder="TEMPORARY DEMO MODE - re-enable security scans after the demo.",
            )

    async def scan_manifests(
        self,
        manifests: dict[str, str] | list[str] | str,
    ) -> dict[str, Any]:
        """Scan Kubernetes manifests with Kubesec.

        Args:
            manifests: YAML manifests to scan. Can be:
                - dict mapping filename to YAML content
                - list of YAML strings
                - single YAML string

        Returns:
            Aggregated scan result with passed status
        """
        if not settings.security.kubesec_enabled:
            log.info("kubesec_disabled_skipping")
            return {"passed": True, "skipped": True, "results": []}

        # Normalize input
        if isinstance(manifests, str):
            manifest_list = [manifests]
        elif isinstance(manifests, dict):
            manifest_list = list(manifests.values())
        else:
            manifest_list = list(manifests)

        results: list[dict[str, Any]] = []
        all_passed = True

        for manifest_yaml in manifest_list:
            if not manifest_yaml.strip():
                continue

            result = await self._kubesec.scan_manifest(manifest_yaml)
            results.append(result)

            if not result.get("passed", False):
                all_passed = False
                log.warning(
                    "kubesec_scan_failed",
                    score=result.get("score"),
                    critical_issues=result.get("critical_issues"),
                )

        return {
            "passed": all_passed,
            "results": results,
            "total_scanned": len(results),
            "failed_count": sum(1 for r in results if not r.get("passed", False)),
        }

    async def scan_images(
        self,
        images: list[str] | str,
    ) -> dict[str, Any]:
        """Scan container images with Trivy.

        Args:
            images: Container image(s) to scan

        Returns:
            Aggregated scan result with passed status
        """
        if not settings.security.trivy_enabled:
            log.info("trivy_disabled_skipping")
            return {"passed": True, "skipped": True, "results": []}

        # Normalize input
        image_list = [images] if isinstance(images, str) else list(images)

        # Deduplicate images
        image_list = list(set(image_list))

        results: list[dict[str, Any]] = []
        all_passed = True

        # Scan images concurrently (but limit concurrency)
        semaphore = asyncio.Semaphore(3)

        async def scan_one(image: str) -> dict[str, Any]:
            async with semaphore:
                return await self._trivy.scan_image(image)

        scan_tasks = [scan_one(img) for img in image_list]
        scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)

        for image, result in zip(image_list, scan_results, strict=False):
            if isinstance(result, BaseException):
                results.append(
                    {
                        "image": image,
                        "passed": False,
                        "error": str(result),
                    }
                )
                all_passed = False
            else:
                result["image"] = image
                results.append(result)
                if not result.get("passed", False):
                    all_passed = False
                    log.warning(
                        "trivy_scan_failed",
                        image=image,
                        vulnerabilities=result.get("vulnerabilities"),
                        severity_counts=result.get("severity_counts"),
                    )

        return {
            "passed": all_passed,
            "results": results,
            "total_scanned": len(results),
            "failed_count": sum(1 for r in results if not r.get("passed", False)),
        }

    async def check_runtime_alerts(
        self,
        namespace: str,
        core_api: client.CoreV1Api,
        *,
        since_minutes: int = 10,
    ) -> dict[str, Any]:
        """Check Falco runtime alerts for the namespace.

        Args:
            namespace: Shadow namespace to check
            core_api: Kubernetes API client for the shadow cluster
            since_minutes: Look back window

        Returns:
            Analysis result with passed status
        """
        return await self._falco.analyze_alerts(
            namespace,
            core_api=core_api,
            since_minutes=since_minutes,
        )

    async def run_full_scan(
        self,
        *,
        manifests: dict[str, str] | list[str] | str | None = None,
        images: list[str] | None = None,
        namespace: str | None = None,
        core_api: client.CoreV1Api | None = None,
    ) -> SecurityScanResults:
        """Run all applicable security scans.

        Args:
            manifests: YAML manifests to scan with Kubesec
            images: Container images to scan with Trivy
            namespace: Namespace to check Falco alerts
            core_api: Kubernetes API client for Falco

        Returns:
            SecurityScanResults with aggregated results
        """
        results = SecurityScanResults(passed=True)

        # Kubesec - manifest scanning
        if manifests:
            try:
                results.kubesec = await self.scan_manifests(manifests)
                if not results.kubesec.get("passed", True):
                    results.passed = False
            except Exception as e:
                log.exception("kubesec_pipeline_error")
                results.errors.append(f"Kubesec error: {e}")
                results.passed = False

        # Trivy - image scanning
        if images:
            try:
                results.trivy = await self.scan_images(images)
                if not results.trivy.get("passed", True):
                    results.passed = False
            except Exception as e:
                log.exception("trivy_pipeline_error")
                results.errors.append(f"Trivy error: {e}")
                results.passed = False

        # Falco - runtime alerts
        if namespace and core_api:
            try:
                results.falco = await self.check_runtime_alerts(namespace, core_api)
                if not results.falco.get("passed", True):
                    results.passed = False
            except Exception as e:
                log.exception("falco_pipeline_error")
                results.errors.append(f"Falco error: {e}")
                # Don't fail on Falco errors (may not be installed)

        log.info(
            "security_pipeline_completed",
            passed=results.passed,
            kubesec_passed=results.kubesec.get("passed") if results.kubesec else None,
            trivy_passed=results.trivy.get("passed") if results.trivy else None,
            falco_passed=results.falco.get("passed") if results.falco else None,
        )

        return results


def extract_images_from_manifests(manifests: list[str] | str) -> list[str]:
    """Extract container images from Kubernetes YAML manifests.

    Args:
        manifests: YAML manifest(s) to parse

    Returns:
        List of unique container image references
    """
    manifest_list = [manifests] if isinstance(manifests, str) else list(manifests)

    images: set[str] = set()

    for manifest_yaml in manifest_list:
        try:
            for doc in yaml.safe_load_all(manifest_yaml):
                if not doc:
                    continue
                _extract_images_recursive(doc, images)
        except yaml.YAMLError as e:
            log.warning("yaml_parse_error_extracting_images", error=str(e))

    return list(images)


def _extract_images_recursive(obj: Any, images: set[str]) -> None:
    """Recursively extract image references from a parsed YAML object."""
    if isinstance(obj, dict):
        # Check for container specs
        if "image" in obj and isinstance(obj["image"], str):
            images.add(obj["image"])

        # Recurse into nested objects
        for value in obj.values():
            _extract_images_recursive(value, images)

    elif isinstance(obj, list):
        for item in obj:
            _extract_images_recursive(item, images)


__all__ = [
    "SecurityPipeline",
    "SecurityScanResults",
    "extract_images_from_manifests",
]
