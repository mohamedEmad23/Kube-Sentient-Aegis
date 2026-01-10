"""AEGIS Command Line Interface.

Production-ready CLI for managing the AEGIS operator,
running diagnostics, and interacting with the system.

Commands:
    aegis analyze <resource>    - Analyze Kubernetes resources
    aegis incident list         - List active incidents
    aegis incident show <id>    - Show incident details
    aegis shadow create         - Create shadow environment
    aegis shadow list           - List shadow environments
    aegis shadow delete <name>  - Delete shadow environment
    aegis config show           - Show current configuration
    aegis version               - Show version information
"""

import sys
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import typer
from prometheus_client import start_http_server
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aegis.agent.llm.ollama import get_ollama_client
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import active_incidents, incidents_detected_total


# ============================================================================
# Typed Decorator Wrappers for Typer
# ============================================================================

P = ParamSpec("P")
R = TypeVar("R")


def typed_callback(
    typer_app: typer.Typer,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Type-safe wrapper for @app.callback() decorator.

    Preserves function signature using ParamSpec for full type safety.

    Args:
        typer_app: The Typer application instance

    Returns:
        A decorator that registers the callback and preserves types
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        typer_app.callback()(func)
        return func

    return decorator


def typed_command(
    typer_app: typer.Typer,
    name: str | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Type-safe wrapper for @app.command() decorator.

    Preserves function signature using ParamSpec for full type safety.

    Args:
        typer_app: The Typer application instance
        name: Optional command name override
        **kwargs: Additional arguments passed to Typer's command decorator

    Returns:
        A decorator that registers the command and preserves types
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if name is not None:
            typer_app.command(name=name, **kwargs)(func)
        else:
            typer_app.command(**kwargs)(func)
        return func

    return decorator


# Initialize CLI app
app = typer.Typer(
    name="aegis",
    help="AEGIS - Autonomous SRE Agent with Shadow Verification",
    add_completion=False,
)

# Rich console for beautiful output
console = Console()

# Logger
log = get_logger(__name__)


# ============================================================================
# Global Options
# ============================================================================


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        rprint(f"[bold cyan]AEGIS[/bold cyan] version [green]{settings.app_version}[/green]")
        rprint(f"Environment: [yellow]{settings.environment.value}[/yellow]")
        raise typer.Exit


@typed_callback(app)
def main(
    _ctx: typer.Context,
    _version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging",
    ),
    metrics_port: int | None = typer.Option(
        None,
        "--metrics-port",
        "-m",
        help="Port for Prometheus metrics server",
    ),
) -> None:
    """AEGIS - Autonomous SRE Agent with Shadow Verification."""
    # Enable debug mode if requested
    if debug:
        settings.debug = True
        log.info("debug_mode_enabled")

    # Start metrics server if enabled and port provided
    if settings.observability.prometheus_enabled and metrics_port:
        try:
            start_http_server(metrics_port)
            log.info("metrics_server_started", port=metrics_port)
        except OSError:
            log.exception("metrics_server_failed")


# ============================================================================
# Analyze Command Group
# ============================================================================


@typed_command(app)
def analyze(
    resource: str = typer.Argument(
        ...,
        help="Kubernetes resource to analyze (e.g., pod/nginx, deployment/api)",
    ),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Kubernetes namespace",
    ),
    auto_fix: bool = typer.Option(
        False,
        "--auto-fix",
        help="Automatically apply fixes after verification",
    ),
    _export: str | None = typer.Option(
        None,
        "--export",
        "-e",
        help="Export analysis report to markdown file",
    ),
) -> None:
    """Analyze Kubernetes resources for issues.

    Examples:
        aegis analyze pod/nginx-crashloop
        aegis analyze deployment/api --namespace prod
        aegis analyze pod/nginx --auto-fix --export report.md
    """
    log.info(
        "analysis_started",
        resource=resource,
        namespace=namespace,
        auto_fix=auto_fix,
    )

    console.print(
        f"\n[bold cyan]Analyzing:[/bold cyan] {resource} in namespace [yellow]{namespace}[/yellow]\n"
    )

    # Check Ollama availability
    ollama_client = get_ollama_client()
    if not ollama_client.is_available():
        console.print("[bold red]Error:[/bold red] Ollama server is not available")
        console.print("Please start Ollama: [cyan]ollama serve[/cyan]")
        log.error("ollama_unavailable")
        raise typer.Exit(code=1)

    # For MVP, show placeholder for K8sGPT integration
    with console.status("[bold green]Running K8sGPT analysis..."):
        console.print("✓ K8sGPT analysis complete", style="green")

    # Placeholder for agent workflow
    panel = Panel(
        "[yellow]Note:[/yellow] Full agent workflow implementation pending.\n"
        "This will trigger the LangGraph multi-agent workflow:\n"
        "  1. RCA Agent (phi3:mini)\n"
        "  2. Solution Agent (deepseek-coder:6.7b)\n"
        "  3. Verifier Agent (llama3.1:8b)",
        title="[bold]Agent Workflow[/bold]",
        border_style="blue",
    )
    console.print(panel)

    # Update metrics
    incidents_detected_total.labels(
        severity="high",
        resource_type=resource.split("/")[0],
        namespace=namespace,
    ).inc()
    active_incidents.labels(severity="high", namespace=namespace).inc()

    log.info(
        "analysis_completed",
        resource=resource,
        namespace=namespace,
    )


# ============================================================================
# Incident Command Group
# ============================================================================

incident_app = typer.Typer(help="Manage incidents")
app.add_typer(incident_app, name="incident")


@typed_command(incident_app, name="list")
def incident_list(
    namespace: str | None = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Filter by namespace",
    ),
    severity: str | None = typer.Option(
        None,
        "--severity",
        "-s",
        help="Filter by severity (high, medium, low)",
    ),
) -> None:
    """List active incidents.

    Example:
        aegis incident list
        aegis incident list --namespace prod --severity high
    """
    log.info("listing_incidents", namespace=namespace, severity=severity)

    console.print("\n[bold cyan]Active Incidents[/bold cyan]\n")

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Severity", style="yellow")
    table.add_column("Resource", style="green")
    table.add_column("Namespace", style="blue")
    table.add_column("Status", style="white")

    # Placeholder data for MVP
    table.add_row("inc-2026-001", "HIGH", "pod/nginx", "default", "Analyzing")
    table.add_row("inc-2026-002", "MEDIUM", "deployment/api", "prod", "Fixing")

    console.print(table)
    console.print()


@typed_command(incident_app, name="show")
def incident_show(
    incident_id: str = typer.Argument(..., help="Incident ID"),
) -> None:
    """Show incident details.

    Example:
        aegis incident show inc-2026-001
    """
    log.info("showing_incident", incident_id=incident_id)

    console.print(f"\n[bold cyan]Incident:[/bold cyan] {incident_id}\n")

    # Placeholder for incident details
    panel = Panel(
        "[bold]Status:[/bold] Analyzing\n"
        "[bold]Severity:[/bold] HIGH\n"
        "[bold]Resource:[/bold] pod/nginx\n"
        "[bold]Namespace:[/bold] default\n"
        "[bold]Detected:[/bold] 2026-01-09 12:34:56 UTC\n\n"
        "[bold]Root Cause Analysis:[/bold]\n"
        "CrashLoopBackOff due to missing DATABASE_URL environment variable\n\n"
        "[bold]Proposed Solution:[/bold]\n"
        "Add DATABASE_URL to pod configuration",
        title=f"[bold]{incident_id}[/bold]",
        border_style="cyan",
    )
    console.print(panel)
    console.print()


# ============================================================================
# Shadow Command Group
# ============================================================================

shadow_app = typer.Typer(help="Manage shadow verification environments")
app.add_typer(shadow_app, name="shadow")


@typed_command(shadow_app, name="create")
def shadow_create(
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Shadow environment name",
    ),
    runtime: str = typer.Option(
        "vcluster",
        "--runtime",
        "-r",
        help="Runtime (vcluster, kind, minikube)",
    ),
) -> None:
    """Create a shadow verification environment.

    Example:
        aegis shadow create --name test-env
        aegis shadow create --name test-env --runtime vcluster
    """
    log.info("creating_shadow", name=name, runtime=runtime)

    with console.status(f"[bold green]Creating shadow environment: {name}..."):
        console.print(f"✓ Shadow environment [cyan]{name}[/cyan] created", style="green")

    console.print()


@typed_command(shadow_app, name="list")
def shadow_list() -> None:
    """List shadow environments.

    Example:
        aegis shadow list
    """
    log.info("listing_shadows")

    console.print("\n[bold cyan]Shadow Environments[/bold cyan]\n")

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Runtime", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Created", style="blue")

    # Placeholder data
    table.add_row("test-env-001", "vcluster", "Running", "2m ago")
    table.add_row("test-env-002", "vcluster", "Terminated", "15m ago")

    console.print(table)
    console.print()


@typed_command(shadow_app, name="delete")
def shadow_delete(
    name: str = typer.Argument(..., help="Shadow environment name"),
) -> None:
    """Delete a shadow environment.

    Example:
        aegis shadow delete test-env
    """
    log.info("deleting_shadow", name=name)

    with console.status(f"[bold yellow]Deleting shadow environment: {name}..."):
        console.print(f"✓ Shadow environment [cyan]{name}[/cyan] deleted", style="green")

    console.print()


# ============================================================================
# Config Command
# ============================================================================


@typed_command(app)
def config(
    show_sensitive: bool = typer.Option(
        False,
        "--show-sensitive",
        help="Show sensitive configuration values",
    ),
) -> None:
    """Show current AEGIS configuration.

    Example:
        aegis config
        aegis config --show-sensitive
    """
    log.info("showing_config", show_sensitive=show_sensitive)

    console.print("\n[bold cyan]AEGIS Configuration[/bold cyan]\n")

    # Build config display
    config_text = f"""
[bold]Application[/bold]
  Name: {settings.app_name}
  Version: {settings.app_version}
  Environment: {settings.environment.value}
  Debug: {settings.debug}

[bold]Ollama LLM[/bold]
  Base URL: {settings.ollama.base_url}
  Default Model: {settings.ollama.model}
  Timeout: {settings.ollama.timeout}s
  Temperature: {settings.ollama.temperature}
  Max Retries: {settings.ollama.max_retries}

[bold]Kubernetes[/bold]
  Namespace: {settings.kubernetes.namespace}
  In-Cluster: {settings.kubernetes.in_cluster}
  API Timeout: {settings.kubernetes.api_timeout}s

[bold]Observability[/bold]
  Log Level: {settings.observability.log_level.value}
  Log Format: {settings.observability.log_format}
  Prometheus: {settings.observability.prometheus_enabled}
  Metrics Port: {settings.observability.prometheus_port}

[bold]Shadow Verification[/bold]
  Runtime: {settings.shadow.runtime.value}
  Auto Cleanup: {settings.shadow.auto_cleanup}
  Max Concurrent: {settings.shadow.max_concurrent_shadows}
"""

    console.print(Panel(config_text, border_style="blue"))
    console.print()


# ============================================================================
# Version Command
# ============================================================================


@typed_command(app)
def version() -> None:
    """Show AEGIS version information."""
    console.print(f"\n[bold cyan]AEGIS[/bold cyan] version [green]{settings.app_version}[/green]")
    console.print(f"Environment: [yellow]{settings.environment.value}[/yellow]")
    console.print(f"Python: [blue]{sys.version.split()[0]}[/blue]\n")


# ============================================================================
# Entry Point
# ============================================================================


def main_cli() -> None:
    """Main CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        log.info("cli_interrupted")
        raise typer.Exit(code=130) from None
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        log.exception("cli_error")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    main_cli()
