"""
Docstring for aegis.config.settings
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ======================================
# ENUMS - Configuration Options
# ======================================


class Environment(str, Enum):
    """Development Environment"""

    DEV = "development"
    STAGING = "staging"
    PROD = "production"


class LogLevel(str, Enum):
    """Logging Levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMProvider(str, Enum):
    """LLM Providers"""

    OLLAMA = "ollama"


class SandBoxRuntime(str, Enum):
    """Sandbox Runtime Environments"""

    VCLUSTER = "vcluster"
    KIND = "kind"
    MINIKUBE = "minikube"
    DOCKER = "docker"


class ComputeMode(str, Enum):
    """Compute mode selection."""

    AUTO = "auto"
    GPU = "gpu"
    CPU = "cpu"


# ============================================================================
# SETTINGS MODELS - Organized by domain
# ============================================================================


class OllamaSettings(BaseSettings):
    """Ollama LLM Server Configuration"""

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_",
        case_sensitive=False,
    )

    base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server base URL",
    )

    model: str = Field(
        default="phi3:mini",
        description="Default Ollama model to use",
    )

    timeout: int = Field(
        default=300,
        description="Request timeout in seconds",
        ge=1,
    )

    max_retries: int = Field(
        default=3,
        description="Max retry attempts for failed requests",
        ge=0,
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    top_p: float = Field(
        default=0.9,
        description="Nucleus sampling parameter",
        ge=0.0,
        le=1.0,
    )
    num_ctx: int = Field(
        default=2048,
        description="Context window size",
        ge=512,
    )
    enabled: bool = Field(
        default=True,
        description="Enable Ollama as LLM provider",
    )


class KubernetesSettings(BaseSettings):
    """Kubernetes client and operator configuration."""

    model_config = SettingsConfigDict(
        env_prefix="K8S_",
        case_sensitive=False,
    )

    in_cluster: bool = Field(
        default=False,
        description="Use in-cluster authentication when running in K8s pod",
    )
    kubeconfig_path: str | None = Field(
        default=None,
        description="Path to kubeconfig file (auto-detected if not set)",
    )
    context: str | None = Field(
        default=None,
        description="Kubernetes context name",
    )
    namespace: str | None = Field(
        default=None,
        description="Default namespace for AEGIS resources (None = all namespaces)",
    )
    operator_name: str = Field(
        default="aegis-operator",
        description="Name of the operator service account",
    )
    peering_id: str = Field(
        default="aegis",
        description="Kopf peering ID for operator coordination",
    )
    api_timeout: int = Field(
        default=30,
        description="Kubernetes API call timeout in seconds",
        ge=5,
    )


class ShadowEnvironmentSettings(BaseSettings):
    """Shadow verification sandbox configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SHADOW_",
        case_sensitive=False,
    )

    enabled: bool = Field(
        default=True,
        description="Enable shadow verification workflows",
    )
    runtime: SandBoxRuntime = Field(
        default=SandBoxRuntime.VCLUSTER,
        description="Virtual cluster runtime",
    )
    namespace_prefix: str = Field(
        default="aegis-shadow-",
        description="Prefix for shadow namespace names",
    )
    auto_cleanup: bool = Field(
        default=True,
        description="Automatically delete shadow environments after verification",
    )
    cleanup_timeout: int = Field(
        default=300,
        description="Cleanup timeout in seconds",
        ge=60,
    )
    verification_timeout: int = Field(
        default=600,
        description="Max time to wait for verification to complete",
        ge=60,
    )
    storage_class: str | None = Field(
        default=None,
        description="Storage class for persistent volumes in shadow clusters",
    )
    cpu_request: str = Field(
        default="500m",
        description="CPU request for shadow cluster pods",
    )
    memory_request: str = Field(
        default="512Mi",
        description="Memory request for shadow cluster pods",
    )
    max_concurrent_shadows: int = Field(
        default=3,
        description="Max concurrent shadow environments",
        ge=1,
    )


class IncidentSettings(BaseSettings):
    """Incident workflow configuration."""

    model_config = SettingsConfigDict(
        env_prefix="INCIDENT_",
        case_sensitive=False,
    )

    auto_fix_enabled: bool = Field(
        default=False,
        description="Automatically apply fixes after approval",
    )
    approval_timeout_minutes: int = Field(
        default=15,
        description="Minutes to wait for human approval before auto-reject",
        ge=1,
    )
    post_fix_monitoring_seconds: int = Field(
        default=300,
        description="Post-fix monitoring window in seconds",
        ge=30,
    )


class SecuritySettings(BaseSettings):
    """Security scanning and exploit testing configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        case_sensitive=False,
    )

    trivy_enabled: bool = Field(
        default=True,
        description="Enable Trivy vulnerability scanning",
    )
    trivy_severity: str = Field(
        default="HIGH,CRITICAL",
        description="Comma-separated severity levels (LOW,MEDIUM,HIGH,CRITICAL)",
    )
    kubesec_enabled: bool = Field(
        default=True,
        description="Enable Kubesec manifest security scanning",
    )
    kubesec_min_score: int = Field(
        default=0,
        description="Minimum Kubesec score required to pass",
    )
    zap_enabled: bool = Field(
        default=True,
        description="Enable OWASP ZAP dynamic scanning",
    )
    zap_api_url: str = Field(
        default="http://localhost:8080",
        description="OWASP ZAP API endpoint",
    )
    falco_enabled: bool = Field(
        default=True,
        description="Enable Falco runtime security monitoring",
    )
    falco_namespace: str = Field(
        default="falco",
        description="Namespace where Falco is deployed",
    )
    falco_label_selector: str = Field(
        default="app=falco",
        description="Label selector for Falco pods",
    )
    falco_severity_threshold: str = Field(
        default="WARNING",
        description="Minimum Falco severity to consider (WARNING, ERROR, CRITICAL, etc.)",
    )
    exploit_sandbox_enabled: bool = Field(
        default=False,
        description="Enable experimental exploit proof-of-concept generation",
    )
    sandbox_timeout: int = Field(
        default=30,
        description="Exploit sandbox execution timeout in seconds",
        ge=5,
    )


class ObservabilitySettings(BaseSettings):
    """Metrics, logging, and tracing configuration."""

    model_config = SettingsConfigDict(
        env_prefix="OBS_",
        case_sensitive=False,
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging verbosity level",
    )
    log_format: str = Field(
        default="json",
        description="Log format: 'json' or 'text'",
    )

    # Prometheus metrics
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics export",
    )
    prometheus_port: int = Field(
        default=8000,
        description="Prometheus metrics server port",
        ge=1024,
        le=65535,
    )
    metrics_namespace: str = Field(
        default="aegis",
        description="Prometheus metric namespace prefix",
    )

    # OpenTelemetry tracing
    tracing_enabled: bool = Field(
        default=False,
        description="Enable distributed tracing with OpenTelemetry",
    )
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP collector endpoint (e.g., http://localhost:4317)",
    )
    tracing_sample_rate: float = Field(
        default=0.1,
        description="Fraction of traces to sample (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Structured logging targets
    loki_enabled: bool = Field(
        default=False,
        description="Enable Loki log aggregation",
    )
    loki_url: str | None = Field(
        default=None,
        description="Grafana Loki push API endpoint",
    )


class GPUSettings(BaseSettings):
    """GPU and accelerator configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GPU_",
        case_sensitive=False,
    )

    enabled: bool = Field(
        default=False,
        description="Enable GPU support",
    )
    compute_mode: ComputeMode = Field(
        default=ComputeMode.AUTO,
        description="Compute mode: auto, gpu, or cpu",
    )
    device_ids: str | None = Field(
        default=None,
        description="Comma-separated GPU device IDs (e.g., '0,1,2')",
    )
    memory_fraction: float = Field(
        default=0.8,
        description="Fraction of GPU memory to allocate (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    device_type: str = Field(
        default="cuda",
        description="GPU device type: 'cuda', 'rocm', or 'mps'",
    )


class AgentSettings(BaseSettings):
    """LangGraph agent workflow configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        case_sensitive=False,
    )

    # Model assignments for each agent
    rca_model: str = Field(
        default="phi3:mini",
        description="Model for Root Cause Analysis agent",
    )
    solution_model: str = Field(
        default="tinyllama:latest",
        description="Model for Solution Generation agent",
    )
    verifier_model: str = Field(
        default="phi3:mini",
        description="Model for Verification Planning agent",
    )

    # Workflow settings
    max_iterations: int = Field(
        default=5,
        description="Max workflow iterations to prevent infinite loops",
        ge=1,
    )
    timeout: int = Field(
        default=300,
        description="Agent workflow timeout in seconds",
        ge=30,
    )
    enable_human_approval: bool = Field(
        default=False,
        description="Require human approval before applying fixes to production",
    )
    dry_run_by_default: bool = Field(
        default=True,
        description="Run fixes in shadow environment before production apply",
    )


class LoadTestingSettings(BaseSettings):
    """Load testing configuration for shadow verification."""

    model_config = SettingsConfigDict(
        env_prefix="LOADTEST_",
        case_sensitive=False,
    )

    enabled: bool = Field(
        default=True,
        description="Enable load testing during shadow verification",
    )
    users: int = Field(
        default=10,
        description="Number of concurrent test users",
        ge=1,
    )
    spawn_rate: int = Field(
        default=2,
        description="Users to spawn per second",
        ge=1,
    )
    duration: int = Field(
        default=60,
        description="Load test duration in seconds",
        ge=10,
    )
    timeout: int = Field(
        default=10,
        description="Individual request timeout in seconds",
        ge=1,
    )
    success_threshold: float = Field(
        default=0.95,
        description="Required success rate (0.0-1.0) to pass verification",
        ge=0.0,
        le=1.0,
    )


# ============================================================================
# MAIN SETTINGS - Root configuration
# ============================================================================


class Settings(BaseSettings):
    """
    Central configuration for AEGIS application.

    All settings cascade from environment variables, then .env file,
    then Python defaults with runtime overrides possible.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow additional fields from env
    )

    # ========================================================================
    # Application Metadata
    # ========================================================================

    app_name: str = Field(
        default="AEGIS",
        description="Application name",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version",
    )
    environment: Environment = Field(
        default=Environment.DEV,
        description="Deployment environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # ========================================================================
    # Nested Settings (Domain-specific configs)
    # ========================================================================

    ollama: OllamaSettings = Field(
        default_factory=OllamaSettings,
        description="Ollama LLM configuration",
    )

    kubernetes: KubernetesSettings = Field(
        default_factory=KubernetesSettings,
        description="Kubernetes client configuration",
    )
    shadow: ShadowEnvironmentSettings = Field(
        default_factory=ShadowEnvironmentSettings,
        description="Shadow verification configuration",
    )
    incident: IncidentSettings = Field(
        default_factory=IncidentSettings,
        description="Incident workflow configuration",
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings,
        description="Security scanning configuration",
    )
    observability: ObservabilitySettings = Field(
        default_factory=ObservabilitySettings,
        description="Observability (metrics, logging, tracing)",
    )
    gpu: GPUSettings = Field(
        default_factory=GPUSettings,
        description="GPU acceleration configuration",
    )
    agent: AgentSettings = Field(
        default_factory=AgentSettings,
        description="LangGraph agent workflow configuration",
    )
    loadtest: LoadTestingSettings = Field(
        default_factory=LoadTestingSettings,
        description="Load testing for shadow verification",
    )

    # ========================================================================
    # Computed Properties
    # ========================================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PROD

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEV

    @property
    def llm_providers_enabled(self) -> list[str]:
        """List of enabled LLM providers."""
        providers = []
        if self.ollama.enabled:
            providers.append("ollama")
        return providers

    # ========================================================================
    # Validators - Custom validation logic
    # ========================================================================

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> Environment:
        """Validate and normalize environment value."""
        if isinstance(v, Environment):
            return v
        return Environment(v.lower())

    @field_validator("kubernetes", mode="before")
    @classmethod
    def setup_kubernetes_defaults(
        cls, v: dict[str, Any] | KubernetesSettings
    ) -> KubernetesSettings:
        """Auto-detect Kubernetes configuration."""
        if isinstance(v, KubernetesSettings):
            return v

        # Auto-detect in-cluster if running in pod
        if v.get("in_cluster") is None:
            v["in_cluster"] = Path.exists(Path("/var/run/secrets/kubernetes.io/serviceaccount"))

        return KubernetesSettings(**v) if isinstance(v, dict) else v


# ============================================================================
# Global Settings Instance
# ============================================================================

# Load settings on module import
settings = Settings()


if __name__ == "__main__":
    # Print current configuration (masks sensitive values)
    import json
    import sys

    config_dict: dict[str, Any] = settings.model_dump()
    # Mask sensitive fields
    for field in ["api_key", "token", "password"]:
        if field in config_dict:
            config_dict[field] = "***REDACTED***"

    sys.stdout.write(json.dumps(config_dict, indent=2, default=str) + "\n")
