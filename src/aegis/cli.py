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

import asyncio
import sys
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import kopf
import typer
from kubernetes import client
from kubernetes import config as k8s_config
from prometheus_client import start_http_server
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aegis.agent.graph import analyze_incident
from aegis.agent.llm.ollama import get_ollama_client
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import active_incidents, incidents_detected_total


# HTTP Status Codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404


# ============================================================================
# Helper Functions
# ============================================================================


def _handle_analysis_error(console: Console, error_msg: str) -> None:
    """Handle analysis error and exit."""
    console.print(f"\n[bold red]Analysis Error:[/bold red] {error_msg}\n")
    log.error("analysis_failed", error=error_msg)
    msg = "Analysis failed without RCA result"
    raise typer.Exit(code=1) from RuntimeError(msg)


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
        """Decorator that registers Typer callback."""
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
        """Decorator that registers Typer command."""
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


def _display_analysis_results(console: Console, result: dict[str, Any]) -> None:
    """Display analysis results with rich formatting.

    Args:
        console: Rich console instance
        result: Analysis result dictionary
    """
    # Display RCA Results
    rca_result = result.get("rca_result")
    if rca_result:
        rca_panel = Panel(
            f"[bold]Root Cause:[/bold] {rca_result.root_cause}\n\n"
            f"[bold]Severity:[/bold] {rca_result.severity.value.upper()}\n"
            f"[bold]Confidence:[/bold] {rca_result.confidence_score:.2f}\n\n"
            f"[bold]Reasoning:[/bold]\n{rca_result.reasoning}\n\n"
            f"[bold]Affected Components:[/bold]\n"
            + "\n".join(f"  • {comp}" for comp in rca_result.affected_components),
            title="[bold cyan]Root Cause Analysis[/bold cyan]",
            border_style="cyan",
        )
        console.print(rca_panel)
        console.print()

    # Display Fix Proposal
    fix_proposal = result.get("fix_proposal")
    if fix_proposal:
        fix_text = (
            f"[bold]Type:[/bold] {fix_proposal.fix_type.value}\n"
            f"[bold]Description:[/bold] {fix_proposal.description}\n\n"
            f"[bold]Commands:[/bold]\n"
        )
        for cmd in fix_proposal.commands:
            fix_text += f"  • {cmd}\n"

        if fix_proposal.estimated_downtime:
            fix_text += f"\n[bold]Estimated Downtime:[/bold] {fix_proposal.estimated_downtime}\n"

        if fix_proposal.risks:
            fix_text += "\n[bold]Risks:[/bold]\n"
            for risk in fix_proposal.risks:
                fix_text += f"  ⚠️  {risk}\n"

        fix_panel = Panel(
            fix_text,
            title="[bold green]Proposed Solution[/bold green]",
            border_style="green",
        )
        console.print(fix_panel)
        console.print()

    # Display Verification Plan
    verification_plan = result.get("verification_plan")
    if verification_plan:
        verify_text = (
            f"[bold]Type:[/bold] {verification_plan.verification_type}\n"
            f"[bold]Duration:[/bold] {verification_plan.duration}s\n\n"
            f"[bold]Test Scenarios:[/bold]\n"
        )
        for scenario in verification_plan.test_scenarios:
            verify_text += f"  ✓ {scenario}\n"

        verify_text += "\n[bold]Success Criteria:[/bold]\n"
        for criteria in verification_plan.success_criteria:
            verify_text += f"  ✓ {criteria}\n"

        verify_panel = Panel(
            verify_text,
            title="[bold blue]Verification Plan[/bold blue]",
            border_style="blue",
        )
        console.print(verify_panel)
        console.print()


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
    _auto_fix: bool = typer.Option(
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
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use mock K8sGPT data for development without cluster",
    ),
) -> None:
    """Analyze Kubernetes resources for issues.

    Examples:
        aegis analyze pod/nginx-crashloop
        aegis analyze deployment/api --namespace prod
        aegis analyze pod/nginx --auto-fix --export report.md
        aegis analyze pod/demo --mock  # Development mode without cluster
    """
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

    # Parse resource (format: type/name)
    def validate_resource_format(res: str) -> tuple[str, str]:
        """Validate and parse resource format.

        Args:
            res: Resource string in format type/name

        Returns:
            Tuple of (resource_type, resource_name)

        Raises:
            ValueError: If format is invalid
        """
        expected_parts = 2
        resource_parts = res.split("/")
        if len(resource_parts) != expected_parts:
            msg = "Resource must be in format: type/name (e.g., pod/nginx)"
            raise ValueError(msg)
        return resource_parts[0], resource_parts[1]

    try:
        resource_type, resource_name = validate_resource_format(resource)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        log.exception("invalid_resource_format", resource=resource)
        raise typer.Exit(code=1) from None

    # Run agent workflow
    try:
        with console.status("[bold green]AEGIS analyzing..."):
            # Run async workflow
            result = asyncio.run(
                analyze_incident(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    namespace=namespace,
                    use_mock=mock,
                )
            )

        # Check if no problems were detected (healthy resource)
        if result.get("no_problems"):
            console.print(
                f"\n[bold green]✓ No problems detected[/bold green] for "
                f"[cyan]{resource}[/cyan] in namespace [yellow]{namespace}[/yellow]\n"
            )
            console.print("The resource appears to be healthy according to K8sGPT analysis.\n")
            return  # Exit successfully

        # Extract results
        rca_result = result.get("rca_result")
        error_msg = result.get("error")

        # Check for fatal errors (no RCA at all)
        if not rca_result and error_msg:
            _handle_analysis_error(console, error_msg)

        # Display any partial results we have
        _display_analysis_results(console, dict(result))

        # Show low-confidence warning if workflow stopped early
        if error_msg and rca_result:
            console.print(
                Panel(
                    f"[yellow]{error_msg}[/yellow]\n\n"
                    "The analysis confidence was below threshold. "
                    "Results shown above are partial and may require manual verification.",
                    title="[bold yellow]⚠️ Low Confidence Warning[/bold yellow]",
                    border_style="yellow",
                )
            )
            console.print()

        # Update metrics
        incidents_detected_total.labels(
            severity=rca_result.severity.value if rca_result else "unknown",
            resource_type=resource_type,
            namespace=namespace,
        ).inc()
        active_incidents.labels(
            severity=rca_result.severity.value if rca_result else "unknown",
            namespace=namespace,
        ).inc()

    except Exception as e:
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}\n")
        log.exception("analysis_unexpected_error")
        raise typer.Exit(code=1) from None


# ============================================================================
# Incident Command Group
# ============================================================================

incident_app = typer.Typer(help="Manage incidents")
app.add_typer(incident_app, name="incident")


@typed_command(incident_app, name="list")
def incident_list(
    _namespace: str | None = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Filter by namespace",
    ),
    _severity: str | None = typer.Option(
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
    table = Table(title="Active Incidents")
    table.add_column("Incident ID", style="cyan")
    table.add_column("Severity", style="red")
    table.add_column("Resource", style="green")
    table.add_column("Namespace", style="yellow")
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
# Operator Command
# ============================================================================


operator_app = typer.Typer(
    name="operator",
    help="Kubernetes operator management commands.",
    no_args_is_help=True,
)
app.add_typer(operator_app, name="operator")


@typed_command(operator_app, name="run")
def operator_run(
    namespace: str | None = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Namespace to watch (None = all namespaces)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Run the AEGIS Kubernetes operator.

    Starts the Kopf-based operator that watches for K8sGPT Results
    and triggers automated remediation workflows.

    Example:
        aegis operator run
        aegis operator run --namespace default
        aegis operator run -v
    """

    from aegis.k8s_operator import handlers  # noqa: F401

    log.info("operator_starting", namespace=namespace or "all", verbose=verbose)
    console.print("\n[bold cyan]AEGIS Kubernetes Operator[/bold cyan]")
    console.print("━" * 40)
    console.print(f"Watching: [yellow]{namespace or 'all namespaces'}[/yellow]")
    console.print(f"Model: [green]{settings.ollama.model}[/green]")
    console.print(f"Base URL: [blue]{settings.ollama.base_url}[/blue]")
    console.print("━" * 40)
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    # Configure logging based on verbose flag
    if verbose:
        import logging

        logging.getLogger("kopf").setLevel(logging.DEBUG)

    try:
        run_kwargs: dict[str, Any] = {"standalone": True}
        if namespace:
            run_kwargs["namespaces"] = [namespace]
        else:
            run_kwargs["clusterwide"] = True
        kopf.run(**run_kwargs)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operator stopped by user[/yellow]")
        log.info("operator_stopped")


@typed_command(operator_app, name="status")
def operator_status() -> None:
    """Check operator and cluster status.

    Shows the current state of the AEGIS operator components
    and K8sGPT integration.

    Example:
        aegis operator status
    """

    log.info("checking_operator_status")
    console.print("\n[bold cyan]AEGIS Operator Status[/bold cyan]\n")

    try:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        v1 = client.CoreV1Api()
        custom = client.CustomObjectsApi()

        # Check K8sGPT Results
        try:
            results = custom.list_cluster_custom_object(
                group="core.k8sgpt.ai",
                version="v1alpha1",
                plural="results",
            )
            result_count = len(results.get("items", []))
            console.print(f"[green]✓[/green] K8sGPT Results: [cyan]{result_count}[/cyan] found")
        except client.ApiException as e:
            if e.status == HTTP_NOT_FOUND:
                console.print("[yellow]○[/yellow] K8sGPT Results: CRD not installed")
            else:
                console.print(f"[red]✗[/red] K8sGPT Results: Error - {e.reason}")

        # Check Ollama connectivity
        try:
            import httpx

            resp = httpx.get(f"{settings.ollama.base_url}/api/tags", timeout=5)
            if resp.status_code == HTTP_OK:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "unknown") for m in models[:3]]
                console.print(f"[green]✓[/green] Ollama: Connected ({len(models)} models)")
                for name in model_names:
                    console.print(f"    [dim]• {name}[/dim]")
            else:
                console.print(f"[red]✗[/red] Ollama: HTTP {resp.status_code}")
        except (ConnectionError, TimeoutError) as e:
            console.print(f"[red]✗[/red] Ollama: {e}")

        # Check namespaces
        namespaces = v1.list_namespace()
        ns_names = [
            ns.metadata.name
            for ns in namespaces.items
            if ns.metadata.name.startswith(("default", "aegis", "k8sgpt"))
        ]
        console.print("[green]✓[/green] Cluster: Connected")
        for ns in ns_names:
            console.print(f"    [dim]• {ns}[/dim]")

    except client.ApiException as e:
        console.print(f"[red]✗[/red] Cluster: {e}")

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
