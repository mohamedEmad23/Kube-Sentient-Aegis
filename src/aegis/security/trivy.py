"""Trivy vulnerability scanning integration.

This module provides a thin async wrapper around the Trivy CLI and a small
parser to convert Trivy JSON into a pass/fail decision suitable for use in
shadow verification gating.

Design goals:
- Fail closed when SECURITY_TRIVY_ENABLED=true and Trivy is unavailable
- Keep output structured for storage in ShadowEnvironment.test_results
- Avoid hard dependency on Trivy in unit tests (parse JSON separately)
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

# Trivy can take a while on first run (DB download).
DEFAULT_TRIVY_TIMEOUT_SECONDS = 180


def _normalize_severity_list(severity_csv: str) -> list[str]:
    """Normalize 'HIGH,CRITICAL' -> ['CRITICAL', 'HIGH'] (unique, sorted)."""
    parts = [p.strip().upper() for p in severity_csv.split(",") if p.strip()]
    # Keep deterministic ordering (use Trivy's known severities order-ish via sort)
    return sorted(set(parts))


@dataclass(frozen=True)
class TrivyScanResult:
    """Structured result of a Trivy scan."""

    passed: bool
    severity_counts: dict[str, int]
    vulnerabilities: int
    error: str | None = None

    @staticmethod
    def from_trivy_json(
        raw: dict[str, Any],
        *,
        fail_on: set[str],
    ) -> TrivyScanResult:
        """Parse Trivy JSON output into counts and pass/fail.

        Trivy image JSON output shape (simplified):
        {
          "Results": [
            {
              "Target": "...",
              "Vulnerabilities": [{"Severity": "HIGH", ...}, ...]
            }
          ]
        }
        """
        counts: dict[str, int] = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "UNKNOWN": 0,
        }

        vulns = 0
        for result in raw.get("Results", []) or []:
            for vuln in result.get("Vulnerabilities", []) or []:
                sev = (vuln.get("Severity") or "UNKNOWN").upper()
                counts[sev] = counts.get(sev, 0) + 1
                vulns += 1

        failed = any(counts.get(sev, 0) > 0 for sev in fail_on)
        return TrivyScanResult(
            passed=not failed,
            severity_counts=counts,
            vulnerabilities=vulns,
            error=None,
        )


class TrivyScanner:
    """Async wrapper around the Trivy CLI."""

    def __init__(self) -> None:
        self._trivy_path = shutil.which("trivy")

    async def scan_image(
        self,
        image: str,
        *,
        timeout_seconds: int | None = None,
        severity_csv: str | None = None,
        fail_on_csv: str | None = None,
    ) -> dict[str, Any]:
        """Scan a container image and return a structured result dict.

        The returned dict is safe to store in `ShadowEnvironment.test_results`.
        """
        timeout = timeout_seconds or DEFAULT_TRIVY_TIMEOUT_SECONDS

        # Severity knobs:
        # - severity_csv controls what Trivy includes in JSON (filter)
        # - fail_on_csv controls which severities should fail the gate
        effective_severity_csv = severity_csv or settings.security.trivy_severity
        effective_fail_on_csv = fail_on_csv or settings.security.trivy_severity

        severities = _normalize_severity_list(effective_severity_csv)
        fail_on = set(_normalize_severity_list(effective_fail_on_csv))

        if not self._trivy_path:
            msg = "Trivy binary not found in PATH"
            log.error("trivy_unavailable", image=image)
            return {
                "passed": False,
                "error": msg,
                "severity_counts": {},
                "vulnerabilities": 0,
            }

        cmd: list[str] = [
            self._trivy_path,
            "image",
            "--quiet",
            "--format",
            "json",
            "--severity",
            ",".join(severities),
            image,
        ]

        log.info(
            "trivy_scan_started",
            image=image,
            severities=severities,
            timeout_seconds=timeout,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                msg = f"Trivy scan timed out after {timeout}s"
                log.warning("trivy_timeout", image=image, timeout_seconds=timeout)
                return {
                    "passed": False,
                    "error": msg,
                    "severity_counts": {},
                    "vulnerabilities": 0,
                }

            if not stdout:
                msg = (stderr or b"").decode(errors="replace").strip() or "Trivy returned no output"
                log.error("trivy_no_output", image=image, exit_code=proc.returncode, error=msg)
                return {
                    "passed": False,
                    "error": msg,
                    "severity_counts": {},
                    "vulnerabilities": 0,
                }

            raw = json.loads(stdout.decode())
            result = TrivyScanResult.from_trivy_json(raw, fail_on=fail_on)

            log.info(
                "trivy_scan_completed",
                image=image,
                passed=result.passed,
                vulnerabilities=result.vulnerabilities,
                severity_counts=result.severity_counts,
            )

        except json.JSONDecodeError as e:
            msg = f"Failed to parse Trivy JSON: {e}"
            log.exception("trivy_json_parse_error", image=image)
            return {
                "passed": False,
                "error": msg,
                "severity_counts": {},
                "vulnerabilities": 0,
            }

        except OSError as e:
            msg = f"Trivy execution error: {e}"
            log.exception("trivy_execution_error", image=image)
            return {
                "passed": False,
                "error": msg,
                "severity_counts": {},
                "vulnerabilities": 0,
            }
        else:
            # Keep full raw output for debugging/auditing (can be large; acceptable for MVP).
            return {
                "passed": result.passed,
                "severity_counts": result.severity_counts,
                "vulnerabilities": result.vulnerabilities,
                "error": result.error,
                "raw": raw,
            }


__all__ = ["TrivyScanResult", "TrivyScanner"]
