"""OWASP ZAP baseline scanning via Docker.

Runs zap-baseline.py in owasp/zap2docker-stable: temp dir mounted as /zap/wrk,
JSON report read back. No ZAP daemon or API client. Designed for WSL/Docker.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)

ZAP_IMAGE = "owasp/zap2docker-stable"
REPORT_FILENAME = "report.json"
ZAP_WRK = "/zap/wrk"


def _normalize_alerts(raw_report: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and normalize alerts from ZAP Traditional JSON report.

    Expects structure: site[].alerts[] with name, riskdesc/riskcode, confidence,
    desc, solution, instances (or similar).
    """
    alerts_out: list[dict[str, Any]] = []
    sites = raw_report.get("site") or []
    if not isinstance(sites, list):
        return alerts_out
    for site in sites:
        if not isinstance(site, dict):
            continue
        for alert in site.get("alerts") or []:
            if not isinstance(alert, dict):
                continue
            risk = (
                str(alert.get("riskdesc") or alert.get("riskcode") or "")
            ).strip()
            if not risk and "riskcode" in alert:
                rc = alert["riskcode"]
                risk = {"3": "High", "2": "Medium", "1": "Low", "0": "Informational"}.get(
                    str(rc), str(rc)
                )
            urls: list[str] = []
            for inst in alert.get("instances") or []:
                if isinstance(inst, dict) and inst.get("uri"):
                    urls.append(str(inst["uri"]))
            alerts_out.append({
                "name": str(alert.get("name") or alert.get("alert") or ""),
                "risk": risk or "Unknown",
                "confidence": str(alert.get("confidence") or ""),
                "description": str(alert.get("desc") or ""),
                "solution": str(alert.get("solution") or ""),
                "urls": urls[:10],
            })
    return alerts_out


def _alert_summary(alerts: list[dict[str, Any]]) -> dict[str, int]:
    """Build summary counts by risk (high, medium, low, info)."""
    summary: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for a in alerts:
        r = (a.get("risk") or "").lower()
        if "high" in r:
            summary["high"] += 1
        elif "medium" in r:
            summary["medium"] += 1
        elif "low" in r:
            summary["low"] += 1
        else:
            summary["info"] += 1
    return summary


async def zap_baseline_scan(
    target_url: str,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run ZAP baseline scan via Docker (zap-baseline.py), return raw dict + simple summary.

    Uses: docker run --rm --network host -v <tmpdir>:/zap/wrk owasp/zap2docker-stable
          zap-baseline.py -t <TARGET_URL> -J /zap/wrk/report.json -m <minutes>

    - ZAP exit code non-zero when it finds issues; we do NOT treat that as failure.
    - Only treat as failure if Docker fails to run or JSON report is missing/unreadable.
    - If docker not in PATH or settings.security.zap_enabled is False, return skipped.

    Returns:
        dict with: target_url, tool, timeout_seconds, alerts (normalized list),
                   summary {high, medium, low, info}, raw_report (full JSON).
        Or: {skipped: True, reason: "..."}.
    """
    try:
        zap_enabled = getattr(settings.security, "zap_enabled", True)
    except Exception:  # noqa: BLE001
        zap_enabled = True
    if not zap_enabled:
        log.warning("zap_scan_skipped", reason="zap_enabled is False", target_url=target_url)
        return {"skipped": True, "reason": "ZAP scanning is disabled (settings.security.zap_enabled)"}

    docker_path = shutil.which("docker")
    if not docker_path:
        log.warning("zap_scan_skipped", reason="Docker not in PATH", target_url=target_url)
        return {"skipped": True, "reason": "Docker not found in PATH"}

    minutes = max(1, timeout_seconds // 60)
    report_path = f"{ZAP_WRK}/{REPORT_FILENAME}"

    log.info(
        "zap_baseline_scan_started",
        target_url=target_url,
        timeout_seconds=timeout_seconds,
        minutes=minutes,
    )

    with tempfile.TemporaryDirectory(prefix="aegis_zap_") as tmpdir:
        host_dir = Path(tmpdir).resolve()
        # Use .as_posix() so on WSL we pass a path Docker can use when engine is Linux
        mount_src = host_dir.as_posix()

        cmd: list[str] = [
            docker_path,
            "run",
            "--rm",
            "--network", "host",
            "-v", f"{mount_src}:{ZAP_WRK}",
            ZAP_IMAGE,
            "zap-baseline.py",
            "-t", target_url,
            "-J", report_path,
            "-m", str(minutes),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds + 60
            )
        except asyncio.TimeoutError:
            log.warning("zap_baseline_scan_timeout", target_url=target_url)
            return {
                "target_url": target_url,
                "tool": "zap",
                "timeout_seconds": timeout_seconds,
                "alerts": [],
                "summary": {"high": 0, "medium": 0, "low": 0, "info": 0},
                "raw_report": {},
                "error": "ZAP Docker run timed out",
            }
        except OSError as e:
            log.exception("zap_baseline_scan_docker_error", target_url=target_url, error=str(e))
            return {
                "target_url": target_url,
                "tool": "zap",
                "timeout_seconds": timeout_seconds,
                "alerts": [],
                "summary": {"high": 0, "medium": 0, "low": 0, "info": 0},
                "raw_report": {},
                "error": f"Docker execution failed: {e}",
            }

        # ZAP returns non-zero when it finds issues; we ignore exit code for "failure"
        # Only fail if we cannot read the report
        local_report = host_dir / REPORT_FILENAME
        if not local_report.exists():
            err = (stderr or b"").decode(errors="replace").strip()
            log.warning(
                "zap_baseline_scan_no_report",
                target_url=target_url,
                exit_code=proc.returncode,
                stderr=err[:500],
            )
            return {
                "target_url": target_url,
                "tool": "zap",
                "timeout_seconds": timeout_seconds,
                "alerts": [],
                "summary": {"high": 0, "medium": 0, "low": 0, "info": 0},
                "raw_report": {},
                "error": "ZAP did not produce report.json (missing or unreadable)",
                "docker_exit_code": proc.returncode,
            }

        try:
            raw_report = json.loads(local_report.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.exception("zap_baseline_scan_json_error", target_url=target_url)
            return {
                "target_url": target_url,
                "tool": "zap",
                "timeout_seconds": timeout_seconds,
                "alerts": [],
                "summary": {"high": 0, "medium": 0, "low": 0, "info": 0},
                "raw_report": {},
                "error": f"Report JSON invalid: {e}",
            }

    alerts = _normalize_alerts(raw_report)
    summary = _alert_summary(alerts)

    log.info(
        "zap_baseline_scan_completed",
        target_url=target_url,
        alerts_count=len(alerts),
        summary=summary,
    )

    return {
        "target_url": target_url,
        "tool": "zap",
        "timeout_seconds": timeout_seconds,
        "alerts": alerts,
        "summary": summary,
        "raw_report": raw_report,
    }


__all__ = ["zap_baseline_scan"]
