"""Unit tests for AEGIS configuration settings."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from aegis.config.settings import (
    LLMSettings,
    Settings,
    get_settings,
    reload_settings,
)


class TestSettings:
    """Tests for the main Settings class."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = Settings()

        assert settings.environment == "development"
        assert settings.shadow_mode_enabled is True
        assert settings.auto_remediation_enabled is False

    def test_settings_from_env(self) -> None:
        """Test settings loaded from environment variables."""
        with patch.dict(
            os.environ,
            {
                "AEGIS_ENVIRONMENT": "production",
                "AEGIS_SHADOW_MODE_ENABLED": "false",
            },
        ):
            settings = Settings()

            assert settings.environment == "production"
            assert settings.shadow_mode_enabled is False

    def test_auto_remediation_requires_shadow_mode_disabled(self) -> None:
        """Test that auto_remediation fails when shadow mode is enabled."""
        with pytest.raises(ValueError, match="Cannot enable auto_remediation"):
            Settings(
                shadow_mode_enabled=True,
                auto_remediation_enabled=True,
            )

    def test_auto_remediation_allowed_when_shadow_disabled(self) -> None:
        """Test that auto_remediation works when shadow mode is disabled."""
        settings = Settings(
            shadow_mode_enabled=False,
            auto_remediation_enabled=True,
        )

        assert settings.auto_remediation_enabled is True
        assert settings.shadow_mode_enabled is False


class TestLLMSettings:
    """Tests for LLM configuration settings."""

    def test_default_llm_settings(self) -> None:
        """Test default LLM settings."""
        settings = LLMSettings()

        assert settings.provider == "ollama"
        assert settings.ollama_host == "http://localhost:11434"
        assert settings.ollama_model == "llama3.2:3b"
        assert settings.temperature == 0.1
        assert settings.max_tokens == 4096

    def test_llm_settings_from_env(self) -> None:
        """Test LLM settings from environment variables."""
        with patch.dict(
            os.environ,
            {
                "AEGIS_LLM_PROVIDER": "groq",
                "AEGIS_LLM_TEMPERATURE": "0.5",
            },
        ):
            settings = LLMSettings()

            assert settings.provider == "groq"
            assert settings.temperature == 0.5

    def test_temperature_validation(self) -> None:
        """Test temperature bounds validation."""
        with pytest.raises(ValueError):
            LLMSettings(temperature=3.0)  # Above max of 2.0

        with pytest.raises(ValueError):
            LLMSettings(temperature=-0.1)  # Below min of 0.0


class TestSettingsCache:
    """Tests for settings caching behavior."""

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reload_settings_clears_cache(self) -> None:
        """Test that reload_settings clears the cache."""
        settings1 = get_settings()
        settings2 = reload_settings()

        # After reload, we get a new instance
        # (they should be equal but not the same object)
        assert settings1 is not settings2
