"""Test AEGIS settings and configuration."""

from aegis.config.settings import (
    Environment,
    LogLevel,
    OllamaSettings,
    Settings,
    ShadowEnvironmentSettings,
)


def test_settings_default() -> None:
    """Test that settings load with defaults."""
    settings = Settings()
    assert settings.environment in (Environment.DEV, Environment.STAGING, Environment.PROD)
    assert settings.observability.log_level in (
        LogLevel.DEBUG,
        LogLevel.INFO,
        LogLevel.WARNING,
        LogLevel.ERROR,
        LogLevel.CRITICAL,
    )


def test_ollama_settings() -> None:
    """Test Ollama configuration."""
    ollama = OllamaSettings()
    assert ollama.base_url.startswith("http")
    assert ollama.timeout > 0
    assert ollama.max_retries >= 0


def test_shadow_settings() -> None:
    """Test shadow environment configuration."""
    shadow = ShadowEnvironmentSettings()
    assert shadow.namespace_prefix == "aegis-shadow-"
    assert shadow.max_concurrent_shadows > 0
    assert shadow.verification_timeout > 0


def test_settings_validation() -> None:
    """Test settings validation."""
    # Should not raise when valid
    settings = Settings()
    assert settings is not None
    assert settings.app_name == "AEGIS"
