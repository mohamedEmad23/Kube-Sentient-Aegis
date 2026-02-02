"""Unit tests for Falco runtime security integration.

Tests the async Falco alert checking without requiring actual cluster access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from aegis.security.falco import (
    PRIORITY_LEVELS,
    _extract_namespace_from_event,
    _extract_priority_from_event,
    _filter_alerts,
    _get_priority_level,
    _meets_severity_threshold,
    _parse_falco_line,
    check_falco_alerts,
)


class TestPriorityHelpers:
    """Tests for priority level helper functions."""

    def test_priority_levels_order(self):
        """Verify priority levels are in correct order."""
        assert PRIORITY_LEVELS["EMERGENCY"] == 0
        assert PRIORITY_LEVELS["ALERT"] == 1
        assert PRIORITY_LEVELS["CRITICAL"] == 2
        assert PRIORITY_LEVELS["ERROR"] == 3
        assert PRIORITY_LEVELS["WARNING"] == 4
        assert PRIORITY_LEVELS["DEBUG"] == 7

    def test_get_priority_level(self):
        """Test priority level lookup."""
        assert _get_priority_level("EMERGENCY") == 0
        assert _get_priority_level("emergency") == 0
        assert _get_priority_level("WARNING") == 4
        assert _get_priority_level("UNKNOWN") > 7

    def test_meets_severity_threshold(self):
        """Test severity threshold comparison."""
        # More severe meets threshold
        assert _meets_severity_threshold("CRITICAL", "WARNING") is True
        assert _meets_severity_threshold("ERROR", "WARNING") is True
        assert _meets_severity_threshold("WARNING", "WARNING") is True
        
        # Less severe doesn't meet threshold
        assert _meets_severity_threshold("NOTICE", "WARNING") is False
        assert _meets_severity_threshold("INFO", "WARNING") is False
        assert _meets_severity_threshold("DEBUG", "ERROR") is False


class TestEventParsing:
    """Tests for Falco event parsing functions."""

    def test_parse_falco_line_json(self):
        """Test parsing JSON Falco output."""
        line = '{"priority":"Warning","output":"Test output"}'
        result = _parse_falco_line(line)
        assert isinstance(result, dict)
        assert result["priority"] == "Warning"

    def test_parse_falco_line_invalid_json(self):
        """Test parsing non-JSON output returns raw string."""
        line = "2024-01-15 Warning: Terminal shell in container"
        result = _parse_falco_line(line)
        assert result == line

    def test_parse_falco_line_empty(self):
        """Test empty line returns empty string."""
        assert _parse_falco_line("") == ""
        assert _parse_falco_line("   ") == ""

    def test_extract_namespace_from_json_event(self):
        """Test namespace extraction from JSON event."""
        event = {"k8s": {"ns": "shadow-test"}}
        assert _extract_namespace_from_event(event) == "shadow-test"
        
        event = {"k8s": {"namespace": "shadow-test"}}
        assert _extract_namespace_from_event(event) == "shadow-test"
        
        event = {"output_fields": {"k8s.ns.name": "shadow-test"}}
        assert _extract_namespace_from_event(event) == "shadow-test"

    def test_extract_priority_from_event(self):
        """Test priority extraction from JSON event."""
        assert _extract_priority_from_event({"priority": "Warning"}) == "WARNING"
        assert _extract_priority_from_event({"Priority": "Error"}) == "ERROR"
        assert _extract_priority_from_event({}) == ""


class TestFilterAlerts:
    """Tests for alert filtering logic."""

    def test_filter_by_namespace(self):
        """Test filtering alerts by namespace."""
        lines = [
            '{"priority":"Warning","k8s":{"ns":"shadow-abc"}}',
            '{"priority":"Warning","k8s":{"ns":"other-ns"}}',
            '{"priority":"Error","k8s":{"ns":"shadow-abc"}}',
        ]
        
        alerts, summary = _filter_alerts(lines, "shadow-abc", "WARNING")
        assert len(alerts) == 2
        assert summary["warning"] == 1
        assert summary["error"] == 1

    def test_filter_by_severity(self):
        """Test filtering by severity threshold."""
        lines = [
            '{"priority":"Warning","k8s":{"ns":"test"}}',
            '{"priority":"Info","k8s":{"ns":"test"}}',
            '{"priority":"Error","k8s":{"ns":"test"}}',
        ]
        
        alerts, summary = _filter_alerts(lines, "test", "WARNING")
        # Info should be filtered out (below WARNING threshold)
        assert len(alerts) == 2

    def test_filter_empty_lines(self):
        """Test empty lines are handled."""
        lines = ["", "  ", '{"priority":"Warning","k8s":{"ns":"test"}}']
        alerts, _ = _filter_alerts(lines, "test", "WARNING")
        assert len(alerts) == 1

    def test_filter_raw_string_matching(self):
        """Test namespace matching in raw string output."""
        lines = [
            "Warning shadow-test: Terminal shell detected",
            "Warning other-ns: Some other event",
        ]
        
        alerts, _ = _filter_alerts(lines, "shadow-test", "WARNING")
        assert len(alerts) == 1


class TestCheckFalcoAlerts:
    """Tests for the main check_falco_alerts function."""

    @pytest.mark.asyncio
    async def test_falco_disabled(self):
        """Test that disabled Falco returns skipped result."""
        with patch("aegis.security.falco.settings") as mock_settings:
            mock_settings.security.falco_enabled = False
            
            result = await check_falco_alerts(
                namespace="test",
                since_timestamp=datetime.now(UTC),
            )
            
            assert result["tool"] == "falco"
            assert result["skipped"] is True
            assert "disabled" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_kubectl_not_found(self):
        """Test behavior when kubectl is not available."""
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = None
            
            result = await check_falco_alerts(
                namespace="test",
                since_timestamp=datetime.now(UTC),
            )
            
            assert result["skipped"] is True
            assert "kubectl" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_kubectl_success_no_alerts(self):
        """Test successful kubectl with no matching alerts."""
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which, \
             patch("aegis.security.falco.asyncio.create_subprocess_exec") as mock_exec:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = "/usr/bin/kubectl"
            
            # Mock subprocess
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(
                b'{"priority":"Warning","k8s":{"ns":"other-namespace"}}',
                b"",
            ))
            mock_exec.return_value = mock_proc
            
            result = await check_falco_alerts(
                namespace="shadow-test",
                since_timestamp=datetime.now(UTC),
            )
            
            assert result["passed"] is True
            assert result["skipped"] is False
            assert result["alert_count"] == 0

    @pytest.mark.asyncio
    async def test_kubectl_success_with_alerts(self):
        """Test successful kubectl with matching alerts."""
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which, \
             patch("aegis.security.falco.asyncio.create_subprocess_exec") as mock_exec:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = "/usr/bin/kubectl"
            
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(
                b'{"priority":"Critical","k8s":{"ns":"shadow-test"}}\n'
                b'{"priority":"Warning","k8s":{"ns":"shadow-test"}}',
                b"",
            ))
            mock_exec.return_value = mock_proc
            
            result = await check_falco_alerts(
                namespace="shadow-test",
                since_timestamp=datetime.now(UTC),
            )
            
            assert result["passed"] is False
            assert result["alert_count"] == 2
            assert result["summary"]["critical"] == 1
            assert result["summary"]["warning"] == 1

    @pytest.mark.asyncio
    async def test_kubectl_failure(self):
        """Test kubectl command failure returns skipped."""
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which, \
             patch("aegis.security.falco.asyncio.create_subprocess_exec") as mock_exec:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = "/usr/bin/kubectl"
            
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"No pods found"))
            mock_exec.return_value = mock_proc
            
            result = await check_falco_alerts(
                namespace="test",
                since_timestamp=datetime.now(UTC),
            )
            
            assert result["skipped"] is True
            assert "failed" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_kubectl_timeout(self):
        """Test kubectl timeout returns skipped."""
        import asyncio
        
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which, \
             patch("aegis.security.falco.asyncio.create_subprocess_exec") as mock_exec:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = "/usr/bin/kubectl"
            
            mock_proc = AsyncMock()
            mock_proc.kill = AsyncMock()
            mock_proc.wait = AsyncMock()
            mock_proc.communicate = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_exec.return_value = mock_proc
            
            result = await check_falco_alerts(
                namespace="test",
                since_timestamp=datetime.now(UTC),
                timeout_seconds=1,
            )
            
            assert result["skipped"] is True
            assert "timed out" in result["reason"].lower()


class TestIntegrationScenarios:
    """Integration-style tests for realistic scenarios."""

    @pytest.mark.asyncio
    async def test_typical_shadow_verification_no_issues(self):
        """Simulate a typical shadow verification with no Falco alerts."""
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which, \
             patch("aegis.security.falco.asyncio.create_subprocess_exec") as mock_exec:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = "/usr/bin/kubectl"
            
            # Simulate empty logs (no activity)
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc
            
            result = await check_falco_alerts(
                namespace="shadow-verify-abc123",
                since_timestamp=datetime.now(UTC),
                severity_threshold="WARNING",
            )
            
            assert result["passed"] is True
            assert result["skipped"] is False
            assert result["alert_count"] == 0

    @pytest.mark.asyncio  
    async def test_typical_shadow_verification_with_attack(self):
        """Simulate a shadow verification detecting malicious activity."""
        with patch("aegis.security.falco.settings") as mock_settings, \
             patch("aegis.security.falco.shutil.which") as mock_which, \
             patch("aegis.security.falco.asyncio.create_subprocess_exec") as mock_exec:
            mock_settings.security.falco_enabled = True
            mock_which.return_value = "/usr/bin/kubectl"
            
            # Simulate Falco detecting shell access
            falco_output = (
                '{"priority":"Warning","rule":"Terminal shell in container",'
                '"output":"shell spawned in container","k8s":{"ns":"shadow-verify-abc123"}}\n'
            )
            
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(falco_output.encode(), b""))
            mock_exec.return_value = mock_proc
            
            result = await check_falco_alerts(
                namespace="shadow-verify-abc123",
                since_timestamp=datetime.now(UTC),
            )
            
            assert result["passed"] is False
            assert result["alert_count"] == 1
            assert len(result["alerts"]) == 1
