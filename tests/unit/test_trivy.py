"""Unit tests for Trivy vulnerability scanning integration.

Tests TrivyScanResult parsing (no Trivy binary required) and TrivyScanner
behavior with mocks. One optional integration test runs a real scan if
Trivy is in PATH.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aegis.security.trivy import TrivyScanResult, TrivyScanner


# =============================================================================
# TrivyScanResult.from_trivy_json (no Trivy binary needed)
# =============================================================================


def test_from_trivy_json_empty_results_passes() -> None:
    """Empty or no Results -> passed when fail_on includes CRITICAL/HIGH."""
    raw = {"Results": []}
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"CRITICAL", "HIGH"})
    assert r.passed is True
    assert r.vulnerabilities == 0
    assert r.severity_counts == {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}


def test_from_trivy_json_none_results_passes() -> None:
    """Missing Results -> treated as empty."""
    raw = {}
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"CRITICAL", "HIGH"})
    assert r.passed is True
    assert r.vulnerabilities == 0


def test_from_trivy_json_critical_fails() -> None:
    """CRITICAL vuln and fail_on CRITICAL -> failed."""
    raw = {
        "Results": [
            {
                "Target": "python:3.12-slim",
                "Vulnerabilities": [
                    {"Severity": "CRITICAL", "VulnerabilityID": "CVE-2024-X"},
                ],
            },
        ],
    }
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"CRITICAL", "HIGH"})
    assert r.passed is False
    assert r.vulnerabilities == 1
    assert r.severity_counts.get("CRITICAL", 0) == 1


def test_from_trivy_json_high_fails() -> None:
    """HIGH vuln and fail_on HIGH -> failed."""
    raw = {
        "Results": [
            {
                "Target": "nginx:latest",
                "Vulnerabilities": [
                    {"Severity": "HIGH", "VulnerabilityID": "CVE-2024-Y"},
                ],
            },
        ],
    }
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"CRITICAL", "HIGH"})
    assert r.passed is False
    assert r.severity_counts.get("HIGH", 0) == 1


def test_from_trivy_json_low_only_passes() -> None:
    """Only LOW vulns and fail_on CRITICAL,HIGH -> passed."""
    raw = {
        "Results": [
            {
                "Target": "alpine:3.18",
                "Vulnerabilities": [
                    {"Severity": "LOW", "VulnerabilityID": "CVE-2024-Z"},
                ],
            },
        ],
    }
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"CRITICAL", "HIGH"})
    assert r.passed is True
    assert r.vulnerabilities == 1
    assert r.severity_counts.get("LOW", 0) == 1


def test_from_trivy_json_unknown_severity_counted() -> None:
    """Unknown severity is counted and does not fail if not in fail_on."""
    raw = {
        "Results": [
            {
                "Target": "img",
                "Vulnerabilities": [{"Severity": "UNKNOWN", "VulnerabilityID": "X"}],
            },
        ],
    }
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"CRITICAL", "HIGH"})
    assert r.passed is True
    assert r.severity_counts.get("UNKNOWN", 0) == 1


def test_from_trivy_json_multiple_results_aggregated() -> None:
    """Multiple Results entries are aggregated."""
    raw = {
        "Results": [
            {"Target": "a", "Vulnerabilities": [{"Severity": "HIGH"}]},
            {"Target": "b", "Vulnerabilities": [{"Severity": "HIGH"}]},
        ],
    }
    r = TrivyScanResult.from_trivy_json(raw, fail_on={"HIGH"})
    assert r.passed is False
    assert r.vulnerabilities == 2
    assert r.severity_counts.get("HIGH", 0) == 2


# =============================================================================
# TrivyScanner – Trivy not in PATH
# =============================================================================


def test_trivy_scanner_missing_binary_returns_fail_dict() -> None:
    """When Trivy is not in PATH, scan_image returns fail dict (sync check via run)."""
    with patch("aegis.security.trivy.shutil.which", return_value=None):
        scanner = TrivyScanner()
        # Scanner was created with no trivy path; run scan_image
        # We need async – run via asyncio
        async def run() -> dict:
            return await scanner.scan_image("nginx:latest")

        result = asyncio.run(run())
    assert result["passed"] is False
    assert "error" in result
    assert "Trivy" in result["error"] or "trivy" in result["error"].lower()
    assert result.get("vulnerabilities", 0) == 0


# =============================================================================
# TrivyScanner – Mocked subprocess (Trivy in PATH, subprocess mocked)
# =============================================================================


@pytest.mark.asyncio
async def test_trivy_scanner_scan_image_success_mocked() -> None:
    """scan_image with mocked subprocess returning valid JSON -> structured result."""
    fake_json = {
        "Results": [
            {
                "Target": "alpine:3.18",
                "Vulnerabilities": [],
            },
        ],
    }
    stdout_bytes = json.dumps(fake_json).encode()

    async def fake_communicate() -> tuple[bytes, bytes]:
        return (stdout_bytes, b"")

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.communicate = fake_communicate
    fake_proc.wait = AsyncMock(return_value=0)
    fake_proc.kill = MagicMock()

    with (
        patch("aegis.security.trivy.shutil.which", return_value="/usr/bin/trivy"),
        patch(
            "aegis.security.trivy.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=fake_proc,
        ),
    ):
        scanner = TrivyScanner()
        result = await scanner.scan_image("alpine:3.18", timeout_seconds=5)

    assert result["passed"] is True
    assert result.get("vulnerabilities") == 0
    assert "severity_counts" in result


@pytest.mark.asyncio
async def test_trivy_scanner_scan_image_fail_mocked() -> None:
    """scan_image with mocked subprocess returning CRITICAL vulns -> passed False."""
    fake_json = {
        "Results": [
            {
                "Target": "nginx:latest",
                "Vulnerabilities": [{"Severity": "CRITICAL", "VulnerabilityID": "CVE-X"}],
            },
        ],
    }
    stdout_bytes = json.dumps(fake_json).encode()

    async def fake_communicate() -> tuple[bytes, bytes]:
        return (stdout_bytes, b"")

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.communicate = fake_communicate
    fake_proc.wait = AsyncMock(return_value=0)
    fake_proc.kill = MagicMock()

    with (
        patch("aegis.security.trivy.shutil.which", return_value="/usr/bin/trivy"),
        patch(
            "aegis.security.trivy.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=fake_proc,
        ),
    ):
        scanner = TrivyScanner()
        result = await scanner.scan_image(
            "nginx:latest",
            timeout_seconds=5,
            fail_on_csv="CRITICAL,HIGH",
        )

    assert result["passed"] is False
    assert result.get("vulnerabilities") == 1
    assert result.get("severity_counts", {}).get("CRITICAL", 0) == 1


# =============================================================================
# Integration: real Trivy (skip if not in PATH)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("trivy"), reason="Trivy not in PATH")
async def test_trivy_scanner_scan_image_integration_alpine() -> None:
    """Run a real Trivy scan on a small image when Trivy is installed (e.g. in WSL)."""
    scanner = TrivyScanner()
    result = await scanner.scan_image(
        "alpine:3.18",
        timeout_seconds=120,
        severity_csv="CRITICAL,HIGH",
        fail_on_csv="CRITICAL,HIGH",
    )
    assert "passed" in result
    assert "vulnerabilities" in result
    assert "severity_counts" in result
    # Alpine 3.18 is generally clean; we only require structure
    assert isinstance(result["severity_counts"], dict)
