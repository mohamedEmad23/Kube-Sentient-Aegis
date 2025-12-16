"""AEGIS Settings configuration.

Uses Pydantic Settings for type-safe configuration management
with support for environment variables and .env files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from aegis.version import __version__


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_LLM_",
        extra="ignore",
    )

    provider: Literal["ollama", "groq", "gemini", "openai", "together"] = Field(
        default="ollama",
        description="LLM provider to use",
    )

    # Ollama settings
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )
    ollama_model: str = Field(
        default="llama3.2:3b",
        description="Ollama model to use",
    )

    # API keys for cloud providers
    groq_api_key: SecretStr | None = Field(
        default=None,
        description="Groq API key",
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="Google Gemini API key",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key",
    )
    together_api_key: SecretStr | None = Field(
        default=None,
        description="Together AI API key",
    )

    # Model settings
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature (lower = more deterministic)",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=32768,
        description="Maximum tokens in LLM response",
    )
    timeout: int = Field(
        default=120,
        ge=1,
        description="LLM request timeout in seconds",
    )


class KubernetesSettings(BaseSettings):
    """Kubernetes configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_K8S_",
        extra="ignore",
    )

    in_cluster: bool = Field(
        default=False,
        description="Whether running inside a Kubernetes cluster",
    )
    kubeconfig: str | None = Field(
        default=None,
        description="Path to kubeconfig file (if not in-cluster)",
    )
    context: str | None = Field(
        default=None,
        description="Kubernetes context to use",
    )
    namespace: str | None = Field(
        default=None,
        description="Namespace to watch (None = all namespaces)",
    )
    excluded_namespaces: list[str] = Field(
        default_factory=lambda: [
            "kube-system",
            "kube-public",
            "kube-node-lease",
        ],
        description="Namespaces to exclude from monitoring",
    )


class ObservabilitySettings(BaseSettings):
    """Observability configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_OBSERVABILITY_",
        extra="ignore",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "console"] = Field(
        default="json",
        description="Log output format",
    )

    # Metrics
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )
    metrics_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Port for metrics endpoint",
    )

    # Tracing
    tracing_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing",
    )
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP collector endpoint",
    )


class ShadowModeSettings(BaseSettings):
    """Shadow mode configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_SHADOW_",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="Enable shadow mode (dry-run for all actions)",
    )
    verification_required: bool = Field(
        default=True,
        description="Require human verification before actions",
    )
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to auto-approve actions",
    )
    max_auto_actions_per_hour: int = Field(
        default=10,
        ge=0,
        description="Maximum auto-approved actions per hour",
    )


class Settings(BaseSettings):
    """Main AEGIS configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Application info
    version: str = Field(default=__version__)
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )

    # Feature flags
    shadow_mode_enabled: bool = Field(
        default=True,
        description="Enable shadow mode globally",
    )
    auto_remediation_enabled: bool = Field(
        default=False,
        description="Enable automatic remediation (requires shadow_mode_enabled=False)",
    )

    # Nested settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    kubernetes: KubernetesSettings = Field(default_factory=KubernetesSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    shadow: ShadowModeSettings = Field(default_factory=ShadowModeSettings)

    @field_validator("auto_remediation_enabled", mode="after")
    @classmethod
    def validate_auto_remediation(cls, v: bool, info) -> bool:
        """Ensure auto-remediation is disabled when shadow mode is on."""
        data = info.data
        if v and data.get("shadow_mode_enabled", True):
            msg = "Cannot enable auto_remediation while shadow_mode_enabled is True"
            raise ValueError(msg)
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Use this function to access settings throughout the application.
    Settings are cached after first load for performance.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()


def reload_settings() -> Settings:
    """Force reload settings (clears cache).

    Use this when you need to reload settings from environment
    or .env file, such as during testing.

    Returns:
        Settings: Fresh settings instance.
    """
    get_settings.cache_clear()
    return get_settings()
