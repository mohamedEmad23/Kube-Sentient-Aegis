"""Falco runtime security monitoring integration.

This module provides an async wrapper for querying Falco alerts from the cluster.
Falco runs as a DaemonSet and monitors syscalls; AEGIS queries its logs to detect
suspicious runtime activity in shadow environments.

Design goals:
- Fail-open when Falco is unavailable (skip check, don't block verification)
- Fail verification only when actual alerts are detected in the shadow namespace
- Keep output structured for storage in ShadowEnvironment.test_results
- Avoid hard dependency on Falco in unit tests (parse logic is separate)
"""

from __future__ import annotations

import asyncio
import json
import math
import shutil
from datetime import UTC, datetime, timezone
from typing import Any

from aegis.config.settings import settings
from aegis.observability._logging import get_logger


log = get_logger(__name__)

# Default timeout for kubectl logs command
DEFAULT_FALCO_TIMEOUT_SECONDS = 30

# Falco priority levels in order (highest to lowest)
FALCO_PRIORITY_ORDER = [
    "EMERGENCY",
    "ALERT",
    "CRITICAL",
    "ERROR",
    "WARNING",
    "NOTICE",
    "INFO",
    "DEBUG",
]

# Map priority strings to numeric values for comparison
PRIORITY_LEVELS = {p: i for i, p in enumerate(FALCO_PRIORITY_ORDER)}


def _get_priority_level(priority: str) -> int:
    """Get numeric priority level (lower = more severe)."""
    return PRIORITY_LEVELS.get(priority.upper(), len(FALCO_PRIORITY_ORDER))


def _meets_severity_threshold(priority: str, threshold: str) -> bool:
    """Check if priority meets or exceeds threshold (more severe = lower number)."""
    return _get_priority_level(priority) <= _get_priority_level(threshold)


def _extract_namespace_from_event(event: dict[str, Any] | str) -> str | None:
    """Extract namespace from a Falco event (JSON dict or raw string)."""
    if isinstance(event, dict):
        # Try common Falco JSON fields
        # Falco JSON output can have various structures
        k8s = event.get("k8s", {})
        if isinstance(k8s, dict):
            ns = k8s.get("ns") or k8s.get("namespace")
            if ns:
                return str(ns)
        
        # Try output_fields
        output_fields = event.get("output_fields", {})
        if isinstance(output_fields, dict):
            ns = output_fields.get("k8s.ns.name") or output_fields.get("container.namespace")
            if ns:
                return str(ns)
        
        # Check in output string
        output = event.get("output", "")
        if output:
            return None  # Will fall through to string matching below
        
        return None
    return None


def _extract_priority_from_event(event: dict[str, Any] | str) -> str:
    """Extract priority from a Falco event."""
    if isinstance(event, dict):
        priority = event.get("priority") or event.get("Priority") or ""
        return str(priority).upper()
    return ""


def _parse_falco_line(line: str) -> dict[str, Any] | str:
    """Parse a single line of Falco output.
    
    Returns dict if JSON, raw string otherwise.
    """
    line = line.strip()
    if not line:
        return ""
    
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return line


def _filter_alerts(
    lines: list[str],
    namespace: str,
    severity_threshold: str,
) -> tuple[list[dict[str, Any] | str], dict[str, int]]:
    """Filter Falco alerts by namespace and severity.
    
    Returns:
        Tuple of (filtered_alerts, summary_counts)
    """
    filtered: list[dict[str, Any] | str] = []
    summary: dict[str, int] = {
        "critical": 0,
        "error": 0,
        "warning": 0,
        "other": 0,
    }
    
    for line in lines:
        parsed = _parse_falco_line(line)
        if not parsed:
            continue
        
        # Check if event relates to our namespace
        matches_namespace = False
        
        if isinstance(parsed, dict):
            event_ns = _extract_namespace_from_event(parsed)
            if event_ns and event_ns == namespace:
                matches_namespace = True
            else:
                # Also check output string for namespace
                output = str(parsed.get("output", ""))
                if namespace in output:
                    matches_namespace = True
        else:
            # Raw string: substring match
            if namespace in str(parsed):
                matches_namespace = True
        
        if not matches_namespace:
            continue
        
        # Check severity threshold
        priority = ""
        if isinstance(parsed, dict):
            priority = _extract_priority_from_event(parsed)
        else:
            # Try to extract from common patterns like "Warning" or "Critical"
            for p in FALCO_PRIORITY_ORDER:
                if p.lower() in str(parsed).lower():
                    priority = p
                    break
        
        if priority and not _meets_severity_threshold(priority, severity_threshold):
            continue
        
        # Count by category
        priority_upper = priority.upper() if priority else "OTHER"
        if priority_upper in ("EMERGENCY", "ALERT", "CRITICAL"):
            summary["critical"] += 1
        elif priority_upper == "ERROR":
            summary["error"] += 1
        elif priority_upper == "WARNING":
            summary["warning"] += 1
        else:
            summary["other"] += 1
        
        filtered.append(parsed)
    
    return filtered, summary


async def check_falco_alerts(
    namespace: str,
    since_timestamp: datetime,
    severity_threshold: str = "WARNING",
    timeout_seconds: int = DEFAULT_FALCO_TIMEOUT_SECONDS,
    falco_namespace: str = "falco",
    label_selector: str = "app=falco",
    fallback_since_minutes: int = 10,
) -> dict[str, Any]:
    """Query Falco alerts from cluster logs.
    
    Queries Falco DaemonSet logs for alerts that occurred after since_timestamp
    and filters them to the specified namespace.
    
    Args:
        namespace: Shadow namespace to filter alerts for
        since_timestamp: Only consider alerts after this time
        severity_threshold: Minimum severity to consider (WARNING, ERROR, CRITICAL, etc.)
        timeout_seconds: Timeout for kubectl command
        falco_namespace: Namespace where Falco is deployed
        label_selector: Label selector for Falco pods
        fallback_since_minutes: Fallback time window if timestamp calculation fails
    
    Returns:
        Dict with:
        - tool: "falco"
        - passed: bool (False if alerts found, True otherwise)
        - skipped: bool (True if check was skipped)
        - reason: str | None (reason for skip or failure)
        - namespace_filter: str (shadow namespace filtered)
        - falco_namespace: str
        - label_selector: str
        - since_timestamp: str (ISO format)
        - since_minutes: int (computed minutes for --since flag)
        - severity_threshold: str
        - alert_count: int
        - summary: dict (counts by severity category)
        - alerts: list (filtered alerts)
        - raw_lines_count: int
        - stderr: str | None
    """
    result: dict[str, Any] = {
        "tool": "falco",
        "passed": True,
        "skipped": False,
        "reason": None,
        "namespace_filter": namespace,
        "falco_namespace": falco_namespace,
        "label_selector": label_selector,
        "since_timestamp": since_timestamp.isoformat() if since_timestamp else None,
        "since_minutes": 0,
        "severity_threshold": severity_threshold,
        "alert_count": 0,
        "summary": {"critical": 0, "error": 0, "warning": 0, "other": 0},
        "alerts": [],
        "raw_lines_count": 0,
        "stderr": None,
    }
    
    # Check if Falco is enabled
    if not settings.security.falco_enabled:
        result["skipped"] = True
        result["reason"] = "Falco is disabled (settings.security.falco_enabled=False)"
        log.info("falco_check_skipped", reason=result["reason"])
        return result
    
    # Check if kubectl is available
    kubectl_path = shutil.which("kubectl")
    if not kubectl_path:
        result["skipped"] = True
        result["reason"] = "kubectl not found in PATH"
        log.warning("falco_check_skipped", reason=result["reason"])
        return result
    
    # Compute --since duration in minutes
    now = datetime.now(UTC)
    if since_timestamp.tzinfo is None:
        since_timestamp = since_timestamp.replace(tzinfo=UTC)
    
    delta = now - since_timestamp
    since_minutes = max(1, min(int(math.ceil(delta.total_seconds() / 60)), fallback_since_minutes))
    result["since_minutes"] = since_minutes
    
    # Build kubectl logs command
    # Using --since=Nm format which is widely supported
    cmd: list[str] = [
        kubectl_path,
        "logs",
        "-n", falco_namespace,
        "-l", label_selector,
        f"--since={since_minutes}m",
        "--timestamps=false",
    ]
    
    log.info(
        "falco_check_started",
        namespace=namespace,
        falco_namespace=falco_namespace,
        label_selector=label_selector,
        since_minutes=since_minutes,
        severity_threshold=severity_threshold,
    )
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            result["skipped"] = True
            result["reason"] = f"kubectl logs timed out after {timeout_seconds}s"
            log.warning("falco_check_timeout", timeout_seconds=timeout_seconds)
            return result
        
        stderr_text = stderr.decode(errors="replace").strip() if stderr else None
        result["stderr"] = stderr_text
        
        # Check if command failed
        if proc.returncode != 0:
            # Non-zero exit could mean no Falco pods or other issues
            result["skipped"] = True
            result["reason"] = f"kubectl logs failed (exit={proc.returncode}): {stderr_text or 'unknown error'}"
            log.warning(
                "falco_check_kubectl_failed",
                returncode=proc.returncode,
                stderr=stderr_text,
            )
            return result
        
        # Parse stdout
        stdout_text = stdout.decode(errors="replace") if stdout else ""
        lines = stdout_text.strip().split("\n") if stdout_text.strip() else []
        result["raw_lines_count"] = len(lines)
        
        if not lines or (len(lines) == 1 and not lines[0].strip()):
            # No logs - Falco might not have any output yet
            log.info(
                "falco_check_no_logs",
                namespace=namespace,
                since_minutes=since_minutes,
            )
            return result
        
        # Filter alerts by namespace and severity
        filtered_alerts, summary = _filter_alerts(lines, namespace, severity_threshold)
        
        result["alerts"] = filtered_alerts
        result["alert_count"] = len(filtered_alerts)
        result["summary"] = summary
        
        # Determine pass/fail
        if filtered_alerts:
            result["passed"] = False
            result["reason"] = f"Found {len(filtered_alerts)} Falco alert(s) in namespace {namespace}"
            log.warning(
                "falco_alerts_detected",
                namespace=namespace,
                alert_count=len(filtered_alerts),
                summary=summary,
            )
        else:
            log.info(
                "falco_check_passed",
                namespace=namespace,
                raw_lines_count=len(lines),
                filtered_count=0,
            )
        
        return result
    
    except OSError as e:
        result["skipped"] = True
        result["reason"] = f"Failed to execute kubectl: {e}"
        log.exception("falco_check_execution_error", error=str(e))
        return result


__all__ = ["check_falco_alerts"]
