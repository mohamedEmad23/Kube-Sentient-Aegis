"""Unit tests for OWASP ZAP baseline scanning.

Tests _normalize_alerts, _alert_summary, and zap_baseline_scan with mocks.
One optional integration test runs a real Docker ZAP scan if Docker is available.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aegis.security.zap import (
    _alert_summary,
    _normalize_alerts,
    zap_baseline_scan,
)


# Minimal ZAP Traditional JSON for parser tests
MINIMAL_ZAP_REPORT = {
    "site": [
        {
            "@name": "http://localhost:8080",
            "alerts": [
                {
                    "name": "X-Frame-Options Header Not Set",
                    "alert": "X-Frame-Options Header Not Set",
                    "riskcode": "1",
                    "riskdesc": "Low (Medium)",
                    "confidence": "2",
                    "desc": "Description.",
                    "solution": "Solution.",
                    "instances": [{"uri": "http://localhost:8080/"}],
                },
                {
                    "name": "XSS",
                    "riskcode": "3",
                    "confidence": "2",
                    "desc": "XSS desc",
                    "solution": "XSS fix",
                    "instances": [{"uri": "http://localhost:8080/page"}],
                },
            ],
        },
    ],
}


# =============================================================================
# _normalize_alerts (no Docker needed)
# =============================================================================


def test_normalize_alerts_empty_site() -> None:
    """Empty or missing site -> empty list."""
    assert _normalize_alerts({}) == []
    assert _normalize_alerts({"site": []}) == []


def test_normalize_alerts_uses_riskcode() -> None:
    """riskcode 3 -> High, 2 -> Medium, 1 -> Low, 0 -> Informational."""
    raw = {
        "site": [{
            "alerts": [
                {"name": "A", "riskcode": "3", "desc": "", "solution": ""},
                {"name": "B", "riskcode": "1", "desc": "", "solution": ""},
            ],
        }],
    }
    out = _normalize_alerts(raw)
    assert len(out) == 2
    assert out[0]["risk"] == "High"
    assert out[1]["risk"] == "Low"


def test_normalize_alerts_riskdesc_used() -> None:
    """riskdesc is used when present."""
    raw = {
        "site": [{
            "alerts": [{"name": "A", "riskdesc": "High (Medium)", "desc": "", "solution": ""}],
        }],
    }
    out = _normalize_alerts(raw)
    assert out[0]["risk"] == "High (Medium)"


def test_normalize_alerts_extracts_urls() -> None:
    """instances[].uri -> urls, capped at 10."""
    raw = {
        "site": [{
            "alerts": [{
                "name": "A",
                "riskcode": "0",
                "desc": "",
                "solution": "",
                "instances": [{"uri": "http://a"}, {"uri": "http://b"}],
            }],
        }],
    }
    out = _normalize_alerts(raw)
    assert out[0]["urls"] == ["http://a", "http://b"]


def test_normalize_alerts_name_from_alert() -> None:
    """Uses 'alert' field when 'name' missing."""
    raw = {
        "site": [{
            "alerts": [{"alert": "Fallback Name", "riskcode": "0", "desc": "", "solution": ""}],
        }],
    }
    out = _normalize_alerts(raw)
    assert out[0]["name"] == "Fallback Name"


# =============================================================================
# _alert_summary
# =============================================================================


def test_alert_summary_counts_by_risk() -> None:
    """Summary counts high/medium/low/info from risk string."""
    alerts = [
        {"risk": "High"},
        {"risk": "High"},
        {"risk": "Medium"},
        {"risk": "Low"},
        {"risk": "Informational"},
    ]
    s = _alert_summary(alerts)
    assert s["high"] == 2
    assert s["medium"] == 1
    assert s["low"] == 1
    assert s["info"] == 1


def test_alert_summary_unknown_goes_to_info() -> None:
    """Unknown risk -> info bucket."""
    assert _alert_summary([{"risk": "Unknown"}])["info"] == 1


# =============================================================================
# zap_baseline_scan – skip conditions
# =============================================================================


@pytest.mark.asyncio
async def test_zap_baseline_scan_skipped_when_docker_missing() -> None:
    """Docker not in PATH -> skipped."""
    with patch("aegis.security.zap.shutil.which", return_value=None):
        result = await zap_baseline_scan("http://127.0.0.1:8080", timeout_seconds=10)
    assert result.get("skipped") is True
    assert "Docker" in result.get("reason", "")


@pytest.mark.asyncio
async def test_zap_baseline_scan_skipped_when_zap_disabled() -> None:
    """settings.security.zap_enabled False -> skipped."""
    mock_settings = MagicMock()
    mock_settings.security.zap_enabled = False
    with (
        patch("aegis.security.zap.shutil.which", return_value="/usr/bin/docker"),
        patch("aegis.security.zap.settings", mock_settings),
    ):
        result = await zap_baseline_scan("http://127.0.0.1:8080", timeout_seconds=10)
    assert result.get("skipped") is True
    assert "disabled" in result.get("reason", "").lower()


# =============================================================================
# zap_baseline_scan – success with mocked Docker
# =============================================================================


@pytest.mark.asyncio
async def test_zap_baseline_scan_success_mocked() -> None:
    """When Docker runs and writes report.json, we get alerts + summary."""
    report_json = json.dumps(MINIMAL_ZAP_REPORT)

    async def fake_create_subprocess_exec(*args: object, **kwargs: object) -> MagicMock:
        cmd = list(args)
        for i, a in enumerate(cmd):
            if a == "-v" and i + 1 < len(cmd):
                mount = str(cmd[i + 1])
                host_path = mount.split(":")[0]
                (Path(host_path) / "report.json").write_text(report_json, encoding="utf-8")
                break
        proc = MagicMock()
        proc.communicate = AsyncMock(return_value=(b"", b""))
        proc.returncode = 0
        return proc

    with (
        patch("aegis.security.zap.shutil.which", return_value="/usr/bin/docker"),
        patch(
            "aegis.security.zap.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=fake_create_subprocess_exec),
        ),
    ):
        result = await zap_baseline_scan("http://127.0.0.1:8080", timeout_seconds=10)

    assert result.get("skipped") is None
    assert result.get("target_url") == "http://127.0.0.1:8080"
    assert result.get("tool") == "zap"
    assert "alerts" in result
    assert "summary" in result
    assert "raw_report" in result
    assert len(result["alerts"]) >= 2
    assert result["summary"]["high"] >= 1
    assert result["summary"]["low"] >= 1


# =============================================================================
# Integration: real Docker ZAP (skip if Docker or image unavailable)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("docker"), reason="Docker not in PATH")
async def test_zap_baseline_scan_integration_localhost() -> None:
    """Run real ZAP against http://127.0.0.1:8080 when Docker is available.

    Start a trivial HTTP server on 8080 first, or accept skip/fail if nothing
    is listening. This test is best run in WSL with Docker and optionally
    a target (e.g. python -m http.server 8080 in another terminal).
    """
    result = await zap_baseline_scan("http://127.0.0.1:8080", timeout_seconds=120)
    if result.get("skipped"):
        pytest.skip(result.get("reason", "ZAP skipped"))
    assert "target_url" in result
    assert result["target_url"] == "http://127.0.0.1:8080"
    assert "alerts" in result
    assert "summary" in result
    assert isinstance(result["summary"], dict)
    assert "high" in result["summary"] and "medium" in result["summary"]
