"""AEGIS Kubernetes Operator.

Main entry point for the Kubernetes operator that monitors and manages
AEGIS resources in the cluster using the Kopf framework.

This operator provides:
- Incident detection and remediation for Pods and Deployments
- Shadow verification of AI-proposed changes
- In-memory resource indexing for fast lookups
- Periodic health checks and AI-driven scaling
- Integration with AEGIS LangGraph agent workflow

Usage:
    # Run in development mode (single-threaded, verbose)
    python -m aegis.k8s_operator.main --dev --verbose

    # Run in production mode with specific namespace
    python -m aegis.k8s_operator.main --namespace=production

    # Run with peering for multi-instance deployment
    python -m aegis.k8s_operator.main --peering=aegis-operator-cluster
"""

import argparse
import sys
from typing import NoReturn

import kopf

from aegis.config.settings import settings

# Import handlers to register their decorators
# This must happen before kopf.run() is called
from aegis.k8s_operator import handlers  # noqa: F401
from aegis.observability._logging import configure_logging, get_logger


# Configure logging before anything else
configure_logging()
logger = get_logger(__name__)


def main(
    namespace: str | None = None,
    peering_name: str | None = None,
    liveness_port: int | None = None,
    priority: int = 0,
    dev_mode: bool = False,
) -> NoReturn:
    """Main entry point for AEGIS Kubernetes operator.

    This function configures and runs the Kopf-based operator with all
    registered handlers. It blocks indefinitely until the operator is stopped.

    Args:
        namespace: Kubernetes namespace to monitor. If None, monitors all namespaces.
        peering_name: Name for operator peering (multi-instance coordination).
                     If None, uses value from settings or generates one.
        liveness_port: Port for liveness/readiness probes. If None, uses settings.
        priority: Operator priority for peering (higher = more preferred).
        dev_mode: If True, runs in development mode (pauses other operators).

    Environment Variables:
        K8S_NAMESPACE: Override namespace
        K8S_PEERING_ID: Override peering name
        OBS_PROMETHEUS_PORT: Override liveness port
        DEBUG: Enable debug mode

    Examples:
        >>> # Run with defaults from settings
        >>> main()

        >>> # Run in specific namespace
        >>> main(namespace="production")

        >>> # Run in dev mode (for testing)
        >>> main(dev_mode=True, namespace="development")

    Raises:
        SystemExit: Never returns normally, exits with code 0 on success
    """
    # Use settings as defaults
    namespace = namespace or settings.kubernetes.namespace
    peering_name = peering_name or settings.kubernetes.peering_id or "aegis-operator"
    liveness_port = liveness_port or settings.observability.prometheus_port

    logger.info(
        "🚀 Starting AEGIS Kubernetes Operator",
        version=settings.app_version,
        namespace=namespace or "all",
        peering=peering_name,
        liveness_port=liveness_port,
        dev_mode=dev_mode,
        debug=settings.debug,
    )

    # Log configuration
    logger.info(
        "⚙️ Operator Configuration",
        llm_provider=settings.llm_providers_enabled,
        shadow_runtime=settings.shadow.runtime.value,
        auto_fix=not settings.agent.dry_run_by_default,
        max_concurrent_shadows=settings.shadow.max_concurrent_shadows,
    )

    # Configure kopf operator settings
    kopf_settings = kopf.OperatorSettings()

    # Configure logging format
    if settings.is_production or settings.observability.log_format == "json":
        kopf_settings.posting.level = "INFO"
    else:
        kopf_settings.posting.level = "DEBUG" if settings.debug else "INFO"

    # Configure peering for multi-instance coordination
    if peering_name:
        kopf_settings.peering.name = peering_name
        kopf_settings.peering.priority = priority
        logger.info(
            "🤝 Peering configured",
            peering_name=peering_name,
            priority=priority,
        )

    # Configure execution settings
    kopf_settings.execution.max_workers = settings.agent.max_iterations or 10

    # Configure watching timeouts
    kopf_settings.watching.server_timeout = settings.kubernetes.api_timeout
    kopf_settings.watching.client_timeout = settings.kubernetes.api_timeout + 10

    try:
        # Start the operator (this blocks until stopped)
        kopf.run(
            settings=kopf_settings,
            standalone=True,  # Run as standalone operator
            namespace=namespace,  # Monitor specific namespace or all
            liveness_endpoint=f"http://0.0.0.0:{liveness_port}/healthz",
            priority=priority,
            peering=peering_name,
            dev=dev_mode,  # Development mode (pauses other operators)
        )

    except KeyboardInterrupt:
        logger.info("🛑 Operator stopped by user (Ctrl+C)")
        sys.exit(0)

    except Exception as error:
        logger.exception(
            "💥 Operator crashed with unexpected error",
            error=str(error),
            error_type=type(error).__name__,
        )
        raise

    # Should never reach here (kopf.run blocks indefinitely)
    sys.exit(0)


def cli() -> NoReturn:
    """CLI entry point for aegis-operator command.

    This function is called when running:
        aegis-operator [options]

    It parses command-line arguments and starts the operator.
    For advanced configuration, use main() directly.
    """

    parser = argparse.ArgumentParser(
        description="AEGIS Kubernetes Operator - AI-driven incident remediation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in all namespaces
  aegis-operator

  # Run in specific namespace
  aegis-operator --namespace production

  # Run in development mode (verbose, single-threaded)
  aegis-operator --dev --verbose

  # Run with peering for multi-instance
  aegis-operator --peering aegis-cluster --priority 100

Environment Variables:
  K8S_NAMESPACE          - Default namespace to monitor
  K8S_PEERING_ID         - Peering name for multi-instance
  OBS_PROMETHEUS_PORT    - Port for liveness/metrics endpoint
  DEBUG                  - Enable debug logging
        """,
    )

    parser.add_argument(
        "--namespace",
        "-n",
        type=str,
        default=None,
        help="Kubernetes namespace to monitor (default: all namespaces)",
    )

    parser.add_argument(
        "--peering",
        type=str,
        default=None,
        help="Peering name for multi-instance coordination",
    )

    parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Operator priority for peering (higher = preferred)",
    )

    parser.add_argument(
        "--liveness-port",
        type=int,
        default=None,
        help="Port for liveness/readiness probes",
    )

    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode (pauses other operators)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Override debug setting if verbose flag is set
    if args.verbose:
        settings.debug = True
        configure_logging()  # Reconfigure with debug level

    # Run the operator
    main(
        namespace=args.namespace,
        peering_name=args.peering,
        liveness_port=args.liveness_port,
        priority=args.priority,
        dev_mode=args.dev,
    )


if __name__ == "__main__":
    # Allow running as: python -m aegis.k8s_operator.main
    cli()
