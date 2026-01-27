"""Test GPU configuration utilities."""

from aegis.config.settings import settings


def test_gpu_settings_exist():
    """Test that GPU settings are accessible."""
    assert hasattr(settings, "agent")
    assert hasattr(settings.agent, "rca_model")
    assert hasattr(settings.agent, "solution_model")
    assert hasattr(settings.agent, "verifier_model")


def test_model_names_valid():
    """Test that model names are valid strings."""
    assert isinstance(settings.agent.rca_model, str)
    assert len(settings.agent.rca_model) > 0
    assert isinstance(settings.agent.solution_model, str)
    assert len(settings.agent.solution_model) > 0
