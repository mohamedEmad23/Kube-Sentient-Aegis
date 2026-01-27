"""Test AEGIS CLI functionality."""

from aegis.cli import app


def test_cli_app_exists():
    """Test that CLI app is defined."""
    assert app is not None
    assert hasattr(app, "command")


def test_cli_commands_registered():
    """Test that CLI commands are registered."""
    # Check that commands exist
    command_names = [cmd.name for cmd in app.registered_commands]
    assert "analyze" in command_names or len(app.registered_commands) > 0
