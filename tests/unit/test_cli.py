"""Unit tests for AEGIS CLI."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from aegis.cli import create_parser, main
from aegis.version import __version__


class TestCLIParser:
    """Tests for CLI argument parsing."""

    def test_parser_creation(self) -> None:
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "aegis"

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --version flag output."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_help_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --help flag output."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "AEGIS" in captured.out

    def test_run_command_parsing(self) -> None:
        """Test 'run' command parsing."""
        parser = create_parser()
        args = parser.parse_args(["run", "--dev", "--namespace", "test-ns"])

        assert args.command == "run"
        assert args.dev is True
        assert args.namespace == "test-ns"

    def test_diagnose_command_parsing(self) -> None:
        """Test 'diagnose' command parsing."""
        parser = create_parser()
        args = parser.parse_args(["diagnose", "--pod", "my-pod", "-n", "prod"])

        assert args.command == "diagnose"
        assert args.pod == "my-pod"
        assert args.namespace == "prod"

    def test_shadow_command_parsing(self) -> None:
        """Test 'shadow' command parsing."""
        parser = create_parser()

        # Enable
        args = parser.parse_args(["shadow", "--enable"])
        assert args.command == "shadow"
        assert args.enable is True

        # Disable
        args = parser.parse_args(["shadow", "--disable"])
        assert args.disable is True

        # Status
        args = parser.parse_args(["shadow", "--status"])
        assert args.status is True


class TestCLIMain:
    """Tests for CLI main entry point."""

    def test_no_command_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that no command shows help."""
        result = main([])

        assert result == 0
        captured = capsys.readouterr()
        assert "AEGIS" in captured.out or captured.out == ""

    def test_status_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test 'status' command."""
        result = main(["status"])

        assert result == 0
        captured = capsys.readouterr()
        assert "AEGIS" in captured.out
        assert __version__ in captured.out

    def test_diagnose_requires_target(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test 'diagnose' requires --pod or --deployment."""
        result = main(["diagnose"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Specify --pod or --deployment" in captured.out

    def test_diagnose_with_pod(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test 'diagnose' with pod target."""
        result = main(["diagnose", "--pod", "test-pod"])

        assert result == 0
        captured = capsys.readouterr()
        assert "test-pod" in captured.out

    def test_shadow_enable(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test 'shadow --enable' command."""
        result = main(["shadow", "--enable"])

        assert result == 0
        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()

    def test_shadow_disable(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test 'shadow --disable' command."""
        result = main(["shadow", "--disable"])

        assert result == 0
        captured = capsys.readouterr()
        assert "disabled" in captured.out.lower()
