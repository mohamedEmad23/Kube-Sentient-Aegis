"""Kubesec Kubernetes manifest security scanning integration.

This module provides an async wrapper around the Kubesec CLI for scanning
Kubernetes YAML manifests (Deployments, StatefulSets, DaemonSets, Pods).

Design goals:
- Fail closed when SECURITY_KUBESEC_ENABLED=true and Kubesec is unavailable
- Keep output structured for storage in verification results
- Score-based pass/fail (default threshold: 0)
"""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass
from typing import Any

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)

DEFAULT_KUBESEC_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class KubesecScanResult:
    """Structured result of a Kubesec scan."""

    passed: bool
    score: int
    critical_issues: list[str]
    advise: list[str]
    resource_kind: str | None = None
    error: str | None = None

    @staticmethod
    def from_kubesec_json(
        raw: dict[str, Any],
        *,
        min_score: int,
    ) -> KubesecScanResult:
        """Parse Kubesec JSON output into structured result.

        Kubesec output shape:
        {
          "object": "Deployment/name.namespace",
          "valid": true,
          "score": -30,
          "scoring": {
            "critical": [{"selector": "...", "reason": "...", "points": -30}],
            "advise": [{"selector": "...", "reason": "...", "points": 3}]
          }
        }
        """
        score = raw.get("score", 0)
        passed = score >= min_score

        scoring = raw.get("scoring", {})

        # Extract critical issues (negative points)
        critical = scoring.get("critical", [])
        critical_issues = [item.get("reason", "Unknown issue") for item in critical]

        # Extract improvement suggestions
        advise_list = scoring.get("advise", [])
        advise = [item.get("reason", "Unknown advice") for item in advise_list]

        # Extract resource type
        obj = raw.get("object", "")
        resource_kind = obj.split("/")[0] if "/" in obj else None

        return KubesecScanResult(
            passed=passed,
            score=score,
            critical_issues=critical_issues,
            advise=advise,
            resource_kind=resource_kind,
            error=None,
        )


class KubesecScanner:
    """Async wrapper around the Kubesec CLI."""

    def __init__(self) -> None:
        self._kubesec_path = shutil.which("kubesec")

    async def scan_manifest(
        self,
        manifest_yaml: str,
        *,
        timeout_seconds: int | None = None,
        min_score: int | None = None,
    ) -> dict[str, Any]:
        """Scan a Kubernetes manifest YAML and return a structured result dict.

        The returned dict is safe to store in verification results.

        Args:
            manifest_yaml: YAML string of a single Kubernetes resource
            timeout_seconds: Scan timeout (default: 30s)
            min_score: Minimum acceptable score (default: 0)

        Returns:
            Dict with keys: passed, score, critical_issues, advise, error
        """
        timeout = timeout_seconds or DEFAULT_KUBESEC_TIMEOUT_SECONDS
        effective_min_score = (
            min_score if min_score is not None else settings.security.kubesec_min_score
        )

        if not self._kubesec_path:
            msg = "Kubesec binary not found in PATH"
            log.error("kubesec_unavailable")
            return {
                "passed": False,
                "error": msg,
                "score": 0,
                "critical_issues": [],
                "advise": [],
            }

        cmd: list[str] = [
            self._kubesec_path,
            "scan",
            "-",  # Read from stdin
        ]

        log.info(
            "kubesec_scan_started",
            min_score=effective_min_score,
            timeout_seconds=timeout,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=manifest_yaml.encode()),
                    timeout=timeout,
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                msg = f"Kubesec scan timed out after {timeout}s"
                log.warning("kubesec_timeout", timeout_seconds=timeout)
                return {
                    "passed": False,
                    "error": msg,
                    "score": 0,
                    "critical_issues": [],
                    "advise": [],
                }

            if not stdout:
                msg = (stderr or b"").decode(
                    errors="replace"
                ).strip() or "Kubesec returned no output"
                log.error("kubesec_no_output", exit_code=proc.returncode, error=msg)
                return {
                    "passed": False,
                    "error": msg,
                    "score": 0,
                    "critical_issues": [],
                    "advise": [],
                }

            raw_list = json.loads(stdout.decode())

            # Kubesec returns a list, take first result
            if not raw_list or not isinstance(raw_list, list):
                msg = "Kubesec returned empty or invalid result"
                log.error("kubesec_invalid_output")
                return {
                    "passed": False,
                    "error": msg,
                    "score": 0,
                    "critical_issues": [],
                    "advise": [],
                }

            raw = raw_list[0]

            # Check for errors in output
            if not raw.get("valid", False):
                msg = raw.get("message", "Invalid manifest")
                log.error("kubesec_invalid_manifest", message=msg)
                return {
                    "passed": False,
                    "error": msg,
                    "score": 0,
                    "critical_issues": [],
                    "advise": [],
                }

            result = KubesecScanResult.from_kubesec_json(raw, min_score=effective_min_score)

            log.info(
                "kubesec_scan_completed",
                passed=result.passed,
                score=result.score,
                critical_issues_count=len(result.critical_issues),
                resource_kind=result.resource_kind,
            )

        except json.JSONDecodeError as e:
            msg = f"Failed to parse Kubesec JSON: {e}"
            log.exception("kubesec_json_parse_error")
            return {
                "passed": False,
                "error": msg,
                "score": 0,
                "critical_issues": [],
                "advise": [],
            }

        except OSError as e:
            msg = f"Kubesec execution error: {e}"
            log.exception("kubesec_execution_error")
            return {
                "passed": False,
                "error": msg,
                "score": 0,
                "critical_issues": [],
                "advise": [],
            }
        else:
            return {
                "passed": result.passed,
                "score": result.score,
                "critical_issues": result.critical_issues,
                "advise": result.advise,
                "resource_kind": result.resource_kind,
                "error": result.error,
                "raw": raw,
            }


__all__ = ["KubesecScanResult", "KubesecScanner"]
