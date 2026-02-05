"""AEGIS Command Line Interface.

Production-ready CLI for managing the AEGIS operator,
running diagnostics, and interacting with the system.

Commands:
    aegis analyze <resource>    - Analyze Kubernetes resources
    aegis incident list         - List active incidents
    aegis incident show <id>    - Show incident details
    aegis shadow create         - Create shadow environment
    aegis shadow list           - List shadow environments
    aegis shadow status <id>    - Show shadow environment status
    aegis shadow wait <id>      - Wait for shadow environment readiness
    aegis shadow delete <name>  - Delete shadow environment
    aegis shadow verify         - Verify a shadow environment
    aegis config show           - Show current configuration
    aegis version               - Show version information
"""

import asyncio
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

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
from aegis.agent.llm.router import provider_is_available
from aegis.agent.state import (
    FixProposal,
    IncidentState,
    RCAResult,
    VerificationPlan,
)
from aegis.agent.state import (
    FixProposal as AgentFixProposal,
)
from aegis.config.settings import settings
from aegis.crd import FixProposal as CRDFixProposal
from aegis.crd import FixType as CRDFixType
from aegis.kubernetes.fix_applier import FixResult, get_fix_applier
from aegis.observability._logging import get_logger
from aegis.observability._metrics import active_incidents, incidents_detected_total
from aegis.shadow.manager import get_shadow_manager


if TYPE_CHECKING:
    from aegis.shadow.manager import ShadowEnvironment


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


def _display_analysis_results(console: Console, result: IncidentState) -> None:
    """Display analysis results with rich formatting.

    Args:
        console: Rich console instance
        result: Analysis result dictionary

    """
    # Display Observability Data (Prometheus metrics + Grafana dashboard)
    prometheus_metrics = result.get("prometheus_metrics")
    grafana_url = result.get("grafana_dashboard_url")

    if prometheus_metrics or grafana_url:
        obs_text = ""

        if prometheus_metrics:
            obs_text += "[bold]Prometheus Metrics:[/bold]\n"
            cpu = prometheus_metrics.get("cpu_usage")
            memory = prometheus_metrics.get("memory_usage")
            restarts = prometheus_metrics.get("restarts")
            latency = prometheus_metrics.get("p99_latency")
            error_rate = prometheus_metrics.get("error_rate")
            ready_pods = prometheus_metrics.get("ready_pods")
            total_pods = prometheus_metrics.get("total_pods")

            if cpu is not None:
                obs_text += f"  • CPU Usage: [cyan]{cpu:.2f}%[/cyan]\n"
            if memory is not None:
                obs_text += f"  • Memory Usage: [cyan]{memory:.2f} MB[/cyan]\n"
            if restarts is not None:
                color = "red" if restarts > 5 else "yellow" if restarts > 0 else "green"
                obs_text += f"  • Container Restarts: [{color}]{restarts}[/{color}]\n"
            if latency is not None:
                color = "red" if latency > 1000 else "yellow" if latency > 500 else "green"
                obs_text += f"  • P99 Latency: [{color}]{latency:.0f}ms[/{color}]\n"
            if error_rate is not None:
                color = "red" if error_rate > 5 else "yellow" if error_rate > 1 else "green"
                obs_text += f"  • Error Rate: [{color}]{error_rate:.2f}%[/{color}]\n"
            if ready_pods is not None and total_pods is not None:
                color = "green" if ready_pods == total_pods else "yellow"
                obs_text += f"  • Ready Pods: [{color}]{ready_pods}/{total_pods}[/{color}]\n"

            obs_text += "\n"

        if grafana_url:
            obs_text += (
                f"[bold]Grafana Dashboard:[/bold]\n  🔗 [link={grafana_url}]{grafana_url}[/link]\n"
            )

        obs_panel = Panel(
            obs_text.strip(),
            title="[bold magenta]Observability Data[/bold magenta]",
            border_style="magenta",
        )
        console.print(obs_panel)
        console.print()

    # Display RCA Results
    rca_result = result.get("rca_result")
    if rca_result:
        analysis_steps = rca_result.analysis_steps or []
        evidence_summary = rca_result.evidence_summary or []
        steps_text = (
            "\n".join(f"  {idx}. {step}" for idx, step in enumerate(analysis_steps, start=1))
            if analysis_steps
            else "  • (not provided)"
        )
        evidence_text = (
            "\n".join(f"  • {item}" for item in evidence_summary)
            if evidence_summary
            else "  • (not provided)"
        )
        decision_rationale = rca_result.decision_rationale or "(not provided)"

        rca_panel = Panel(
            f"[bold]Root Cause:[/bold] {rca_result.root_cause}\n\n"
            f"[bold]Severity:[/bold] {rca_result.severity.value.upper()}\n"
            f"[bold]Confidence:[/bold] {rca_result.confidence_score:.2f}\n\n"
            f"[bold]Step-by-Step Analysis:[/bold]\n{steps_text}\n\n"
            f"[bold]Evidence Summary:[/bold]\n{evidence_text}\n\n"
            f"[bold]Decision Rationale:[/bold]\n{decision_rationale}\n\n"
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
            f"[bold]Step-by-Step Analysis:[/bold]\n"
            + (
                "\n".join(
                    f"  {idx}. {step}"
                    for idx, step in enumerate(fix_proposal.analysis_steps, start=1)
                )
                if fix_proposal.analysis_steps
                else "  • (not provided)"
            )
            + "\n\n"
            f"[bold]Decision Rationale:[/bold]\n"
            f"{fix_proposal.decision_rationale or '(not provided)'}\n\n"
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
            f"[bold]Step-by-Step Analysis:[/bold]\n"
            + (
                "\n".join(
                    f"  {idx}. {step}"
                    for idx, step in enumerate(verification_plan.analysis_steps, start=1)
                )
                if verification_plan.analysis_steps
                else "  • (not provided)"
            )
            + "\n\n"
            f"[bold]Decision Rationale:[/bold]\n"
            f"{verification_plan.decision_rationale or '(not provided)'}\n\n"
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


def _build_shadow_changes(fix_proposal: FixProposal) -> dict[str, Any]:
    """Convert a fix proposal into shadow verification changes."""
    changes: dict[str, Any] = {}
    if fix_proposal.manifests:
        changes["manifests"] = fix_proposal.manifests
    if fix_proposal.commands:
        changes["commands"] = fix_proposal.commands
    return changes


def _run_shadow_verification(
    *,
    console: Console,
    resource_type: str,
    resource_name: str,
    namespace: str,
    fix_proposal: FixProposal,
    verification_plan: VerificationPlan,
) -> tuple[str | None, bool | None, str | None, dict[str, Any] | None]:
    """Execute shadow verification and return (shadow_id, passed, logs, security_results)."""
    shadow_manager = get_shadow_manager()
    # Explicit mappings for multi-word Kubernetes resource kinds
    # to ensure correct CamelCase formatting (e.g., DaemonSet, not Daemonset)
    resource_kind_map = {
        "pod": "Pod",
        "deployment": "Deployment",
        "statefulset": "StatefulSet",
        "daemonset": "DaemonSet",
        "replicaset": "ReplicaSet",
        "cronjob": "CronJob",
        "configmap": "ConfigMap",
        "persistentvolumeclaim": "PersistentVolumeClaim",
        "persistentvolume": "PersistentVolume",
        "serviceaccount": "ServiceAccount",
        "horizontalpodautoscaler": "HorizontalPodAutoscaler",
        "poddisruptionbudget": "PodDisruptionBudget",
        "networkpolicy": "NetworkPolicy",
        "resourcequota": "ResourceQuota",
        "limitrange": "LimitRange",
        "clusterrole": "ClusterRole",
        "clusterrolebinding": "ClusterRoleBinding",
        "rolebinding": "RoleBinding",
        "ingress": "Ingress",
        "service": "Service",
        "job": "Job",
        "node": "Node",
        "namespace": "Namespace",
    }
    resource_kind = resource_kind_map.get(
        resource_type.lower(),
        # Fallback: capitalize first letter only for unknown types
        resource_type.capitalize(),
    )

    changes = _build_shadow_changes(fix_proposal)
    if not changes:
        console.print(
            "[yellow]No actionable changes found for shadow verification. Skipping.[/yellow]",
        )
        return None, None, None, None

    async def _execute() -> tuple[str | None, bool | None, str | None, dict[str, Any] | None]:
        shadow_env = await shadow_manager.create_shadow(
            source_namespace=namespace,
            source_resource=resource_name,
            source_resource_kind=resource_kind,
        )
        shadow_id = shadow_env.id
        passed = None
        logs = None
        security_results = None
        try:
            passed = await shadow_manager.run_verification(
                shadow_id=shadow_env.id,
                changes=changes,
                duration=verification_plan.duration,
                verification_plan=verification_plan,
            )
            env = shadow_manager.get_environment(shadow_env.id)
            if env:
                if env.logs:
                    logs = "\n".join(env.logs)
                # Capture security scan results from shadow environment
                if env.test_results:
                    security_results = env.test_results.get("security")
        finally:
            # Ensure cleanup always runs even if verification/log fetch fails
            if settings.shadow.auto_cleanup:
                await shadow_manager.cleanup(shadow_env.id)
        return shadow_id, passed, logs, security_results

    with console.status("[bold blue]Running shadow verification..."):
        try:
            shadow_id, passed, logs, security_results = asyncio.run(_execute())
        except Exception as e:  # pragma: no cover - runtime path
            log.exception("shadow_verification_failed_cli")
            console.print(f"[bold red]Shadow verification failed:[/bold red] {e}\n")
            return None, False, None, None

    return shadow_id, passed, logs, security_results


def _ensure_llm_available(console: Console) -> None:
    """Ensure configured LLM providers are available or exit."""
    providers = {
        "rca_agent": settings.agent.rca_provider,
        "solution_agent": settings.agent.solution_provider,
        "verifier_agent": settings.agent.verifier_provider,
    }

    missing: list[tuple[str, str]] = []
    for agent_name, provider in providers.items():
        provider_value = provider.value if hasattr(provider, "value") else str(provider)
        if not provider_is_available(provider_value):
            missing.append((agent_name, provider_value))

    if not missing:
        return

    ollama_available = provider_is_available("ollama")
    missing_non_ollama = [item for item in missing if item[1] != "ollama"]

    if missing_non_ollama and ollama_available:
        missing_agents = ", ".join(f"{agent}({provider})" for agent, provider in missing_non_ollama)
        console.print(
            "[bold yellow]Warning:[/bold yellow] "
            "Primary LLM providers are unavailable. Falling back to Ollama for: "
            f"{missing_agents}"
        )
        log.warning("llm_fallback_enabled", missing=missing_non_ollama)
        return

    console.print("[bold red]Error:[/bold red] Required LLM providers are not available.")
    if not ollama_available:
        console.print("Ollama fallback is not available. Start Ollama: [cyan]ollama serve[/cyan]")
    log.error("llm_unavailable", missing=missing)
    raise typer.Exit(code=1)


def _validate_resource_format(res: str) -> tuple[str, str]:
    """Validate and parse resource format."""
    expected_parts = 2
    resource_parts = res.split("/")
    if len(resource_parts) != expected_parts:
        msg = "Resource must be in format: type/name (e.g., pod/nginx)"
        raise ValueError(msg)
    return resource_parts[0], resource_parts[1]


def _parse_resource_or_exit(console: Console, resource: str) -> tuple[str, str]:
    """Parse resource or exit with a user-friendly error."""
    try:
        return _validate_resource_format(resource)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        log.exception("invalid_resource_format", resource=resource)
        raise typer.Exit(code=1) from None


def _run_analysis_workflow(
    console: Console,
    *,
    resource_type: str,
    resource_name: str,
    namespace: str,
    use_mock: bool,
) -> IncidentState:
    """Run the async analysis workflow and return the result."""
    with console.status("[bold green]AEGIS analyzing..."):
        return asyncio.run(
            analyze_incident(
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
                use_mock=use_mock,
            ),
        )


def _show_low_confidence_warning(console: Console, error_msg: str) -> None:
    """Display a low-confidence warning panel."""
    console.print(
        Panel(
            f"[yellow]{error_msg}[/yellow]\n\n"
            "The analysis confidence was below threshold. "
            "Results shown above are partial and may require manual verification.",
            title="[bold yellow]⚠️ Low Confidence Warning[/bold yellow]",
            border_style="yellow",
        ),
    )
    console.print()


def _maybe_run_shadow_verification(
    *,
    console: Console,
    result: IncidentState,
    verify: bool | None,
    mock: bool,
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> None:
    """Run shadow verification when eligible and update result."""
    verification_plan = result.get("verification_plan")
    fix_proposal = result.get("fix_proposal")
    run_verification = verify if verify is not None else settings.agent.dry_run_by_default
    if (
        run_verification
        and settings.shadow.enabled
        and not mock
        and verification_plan
        and fix_proposal
        and verification_plan.verification_type == "shadow"
    ):
        shadow_id, passed, logs, security_results = _run_shadow_verification(
            console=console,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            fix_proposal=fix_proposal,
            verification_plan=verification_plan,
        )
        result["shadow_env_id"] = shadow_id
        result["shadow_test_passed"] = passed
        result["shadow_logs"] = logs
        result["shadow_security_results"] = security_results

        # Handle skipped verification (no actionable changes)
        if passed is None:
            console.print(
                Panel(
                    "[bold]Status:[/bold] SKIPPED\n"
                    "No actionable changes were available for shadow verification.",
                    title="[bold magenta]Shadow Verification[/bold magenta]",
                    border_style="yellow",
                ),
            )
            console.print()
        else:
            status = "[bold green]PASSED[/bold green]" if passed else "[bold red]FAILED[/bold red]"
            details = f"[bold]Shadow ID:[/bold] {shadow_id}\n[bold]Result:[/bold] {status}"

            # Add security scan results if available
            if security_results:
                details += "\n\n[bold cyan]Security Scan Results:[/bold cyan]"
                sec_overall = (
                    "[green]PASSED[/green]"
                    if security_results.get("passed", True)
                    else "[red]FAILED[/red]"
                )
                details += f"\n  Overall: {sec_overall}"

                # Kubesec results
                kubesec = security_results.get("kubesec")
                if kubesec and not kubesec.get("skipped"):
                    ks_status = (
                        "[green]✓[/green]" if kubesec.get("passed", True) else "[red]✗[/red]"
                    )
                    details += f"\n  Kubesec: {ks_status} (score: {kubesec.get('score', 'N/A')})"
                    if kubesec.get("critical_issues"):
                        for issue in kubesec["critical_issues"][:2]:
                            details += (
                                f"\n    [red]• {issue[:60]}...[/red]"
                                if len(issue) > 60
                                else f"\n    [red]• {issue}[/red]"
                            )

                # Trivy results
                trivy = security_results.get("trivy")
                if trivy and not trivy.get("skipped"):
                    tr_status = "[green]✓[/green]" if trivy.get("passed", True) else "[red]✗[/red]"
                    counts = trivy.get("severity_counts", {})
                    vuln_summary = f"CRIT:{counts.get('CRITICAL', 0)} HIGH:{counts.get('HIGH', 0)}"
                    details += f"\n  Trivy: {tr_status} ({vuln_summary})"

                # Falco results
                falco = security_results.get("falco")
                if falco and not falco.get("skipped"):
                    fa_status = "[green]✓[/green]" if falco.get("passed", True) else "[red]✗[/red]"
                    alert_count = falco.get("alert_count", 0)
                    details += f"\n  Falco: {fa_status} ({alert_count} runtime alerts)"

            if logs:
                tail = "\n".join(logs.splitlines()[-6:])
                details += f"\n\n[bold]Evidence Logs:[/bold]\n{tail}"

            console.print(
                Panel(
                    details,
                    title="[bold magenta]Shadow Verification[/bold magenta]",
                    border_style="magenta",
                ),
            )
            console.print()
    elif run_verification and mock:
        console.print("[yellow]Shadow verification skipped in mock mode.[/yellow]\n")


def _update_incident_metrics(
    *,
    rca_result: Any | None,
    resource_type: str,
    namespace: str,
) -> None:
    """Update Prometheus incident metrics."""
    severity = rca_result.severity.value if rca_result else "unknown"
    incidents_detected_total.labels(
        severity=severity,
        resource_type=resource_type,
        namespace=namespace,
    ).inc()
    active_incidents.labels(severity=severity, namespace=namespace).inc()


def _generate_abort_report(
    *,
    resource_type: str,
    resource_name: str,
    namespace: str,
    rca_result: RCAResult | None,
    fix_proposal: FixProposal | None,
    shadow_id: str | None,
    shadow_passed: bool | None,
    shadow_logs: str | None,
) -> dict[str, Any]:
    """Generate a comprehensive abort report when user declines fix application.

    Args:
        resource_type: Kind of the Kubernetes resource
        resource_name: Name of the resource
        namespace: Namespace of the resource
        rca_result: Root cause analysis result
        fix_proposal: Proposed fix
        shadow_id: Shadow environment ID
        shadow_passed: Whether shadow verification passed
        shadow_logs: Shadow environment logs

    Returns:
        Report dictionary with complete analysis details

    """
    report: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "decision": "aborted",
        "reason": "User declined to apply fix to production cluster",
        "resource": {
            "kind": resource_type,
            "name": resource_name,
            "namespace": namespace,
        },
    }

    if rca_result:
        report["analysis"] = {
            "root_cause": rca_result.root_cause,
            "severity": rca_result.severity.value,
            "confidence": rca_result.confidence_score,
            "reasoning": rca_result.reasoning,
            "affected_components": rca_result.affected_components,
            "analysis_steps": rca_result.analysis_steps,
            "evidence_summary": rca_result.evidence_summary,
        }

    if fix_proposal:
        report["proposed_fix"] = {
            "fix_type": fix_proposal.fix_type.value,
            "description": fix_proposal.description,
            "commands": fix_proposal.commands,
            "risks": fix_proposal.risks,
            "rollback_commands": fix_proposal.rollback_commands,
            "estimated_downtime": fix_proposal.estimated_downtime,
        }

    report["shadow_verification"] = {
        "shadow_id": shadow_id,
        "passed": shadow_passed,
        "logs_excerpt": shadow_logs[-2000:] if shadow_logs else None,
    }

    report["recommendation"] = (
        "Review the proposed fix and rerun with --auto-fix when ready to apply. "
        "Alternatively, apply the fix manually using the commands provided above."
    )

    return report


def _display_abort_report(console: Console, report: dict[str, Any]) -> None:
    """Display the abort report in a formatted panel."""
    report_text = "[bold]Decision:[/bold] ABORTED\n"
    report_text += f"[bold]Timestamp:[/bold] {report['timestamp']}\n"
    report_text += f"[bold]Reason:[/bold] {report['reason']}\n\n"

    resource = report.get("resource", {})
    report_text += f"[bold]Resource:[/bold] {resource.get('kind')}/{resource.get('name')}\n"
    report_text += f"[bold]Namespace:[/bold] {resource.get('namespace')}\n\n"

    analysis = report.get("analysis", {})
    if analysis:
        report_text += "[bold]Root Cause Analysis:[/bold]\n"
        report_text += f"  • Root Cause: {analysis.get('root_cause', 'N/A')}\n"
        report_text += f"  • Severity: {analysis.get('severity', 'N/A')}\n"
        report_text += f"  • Confidence: {analysis.get('confidence', 0):.0%}\n\n"

    fix = report.get("proposed_fix", {})
    if fix:
        report_text += "[bold]Proposed Fix (NOT applied):[/bold]\n"
        report_text += f"  • Type: {fix.get('fix_type', 'N/A')}\n"
        report_text += f"  • Description: {fix.get('description', 'N/A')}\n"
        if fix.get("commands"):
            report_text += "  • Commands:\n"
            for cmd in fix["commands"][:3]:
                report_text += f"      [dim]{cmd}[/dim]\n"

    shadow = report.get("shadow_verification", {})
    if shadow.get("shadow_id"):
        report_text += "\n[bold]Shadow Verification:[/bold]\n"
        report_text += f"  • ID: {shadow.get('shadow_id')}\n"
        passed = shadow.get("passed")
        status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
        report_text += f"  • Result: {status}\n"

    report_text += f"\n[bold]Recommendation:[/bold]\n{report.get('recommendation', '')}"

    console.print(
        Panel(
            report_text,
            title="[bold yellow]Abort Report[/bold yellow]",
            border_style="yellow",
        ),
    )
    console.print()


def _convert_fix_proposal_to_crd(
    agent_fix: AgentFixProposal,
) -> CRDFixProposal:
    """Convert agent FixProposal to CRD FixProposal for fix_applier.

    Args:
        agent_fix: FixProposal from aegis.agent.state

    Returns:
        CRDFixProposal: FixProposal for aegis.crd/fix_applier

    """
    # Convert FixType enum by value (both are str enums with same values)
    crd_fix_type = CRDFixType(agent_fix.fix_type.value)

    return CRDFixProposal(
        fix_type=crd_fix_type,
        description=agent_fix.description,
        commands=agent_fix.commands,
        manifests=agent_fix.manifests,
        patch=None,  # Agent FixProposal doesn't have patch field
        confidence_score=agent_fix.confidence_score,
        risks=agent_fix.risks,
        estimated_downtime=agent_fix.estimated_downtime,
    )


async def _apply_fix_to_production(
    *,
    console: Console,
    fix_proposal: FixProposal,
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> FixResult:
    """Apply the verified fix to the production cluster.

    Args:
        console: Rich console for output
        fix_proposal: The fix proposal to apply
        resource_type: Kind of the target resource
        resource_name: Name of the target resource
        namespace: Namespace of the target resource

    Returns:
        FixResult with application status

    """
    fix_applier = get_fix_applier()

    console.print("\n[bold cyan]Applying fix to production cluster...[/bold cyan]\n")

    # Convert from agent FixProposal to CRD FixProposal
    crd_fix_proposal = _convert_fix_proposal_to_crd(fix_proposal)

    return await fix_applier.apply_fix(
        fix_proposal=crd_fix_proposal,
        resource_kind=resource_type.capitalize(),
        resource_name=resource_name,
        namespace=namespace,
    )


def _display_fix_result(console: Console, result: FixResult) -> None:
    """Display the fix application result."""
    if result.success:
        details = "[bold green]✓ Fix Applied Successfully[/bold green]\n\n"
        details += (
            f"[bold]Dry-run Validation:[/bold] {'Passed' if result.dry_run_passed else 'Skipped'}\n"
        )
        details += f"[bold]Applied:[/bold] {'Yes' if result.applied else 'No'}\n"
        if result.applied_at:
            details += f"[bold]Applied At:[/bold] {result.applied_at.isoformat()}\n"
        if result.resource_version:
            details += f"[bold]Resource Version:[/bold] {result.resource_version}\n"
        if result.rollback_info:
            details += "\n[bold]Rollback Information:[/bold]\n"
            for key, value in result.rollback_info.items():
                details += f"  • {key}: {value}\n"

        console.print(
            Panel(
                details,
                title="[bold green]Fix Applied[/bold green]",
                border_style="green",
            ),
        )
    else:
        details = "[bold red]✗ Fix Application Failed[/bold red]\n\n"
        details += f"[bold]Error:[/bold] {result.error_message or 'Unknown error'}\n"
        details += f"[bold]Dry-run Passed:[/bold] {result.dry_run_passed}\n"

        console.print(
            Panel(
                details,
                title="[bold red]Fix Failed[/bold red]",
                border_style="red",
            ),
        )
    console.print()


def _prompt_apply_fix_to_cluster(
    *,
    console: Console,
    result: IncidentState,
    resource_type: str,
    resource_name: str,
    namespace: str,
    auto_fix: bool,
) -> None:
    """Prompt user to apply fix to production cluster after successful shadow verification.

    Args:
        console: Rich console for output
        result: The analysis result with shadow verification status
        resource_type: Kind of the Kubernetes resource
        resource_name: Name of the resource
        namespace: Namespace of the resource
        auto_fix: If True, skip prompt and apply automatically

    """
    shadow_passed = result.get("shadow_test_passed")
    fix_proposal = result.get("fix_proposal")
    rca_result = result.get("rca_result")

    # Only proceed if shadow verification passed and we have a fix
    if not shadow_passed or not fix_proposal:
        return

    console.print()
    console.print("[bold green]" + "━" * 60 + "[/bold green]")
    console.print("[bold green]✓ SHADOW VERIFICATION PASSED[/bold green]")
    console.print("[bold green]" + "━" * 60 + "[/bold green]")
    console.print()
    console.print(
        "The proposed fix has been verified in an isolated vCluster environment.",
    )
    console.print(
        f"Resource: [cyan]{resource_type}/{resource_name}[/cyan] in namespace [yellow]{namespace}[/yellow]",
    )
    console.print()

    # Display security scan results from shadow verification
    shadow_security = result.get("shadow_security_results")
    if shadow_security:
        security_text = "[bold]Security Scan Results:[/bold]\n"

        # Kubesec
        kubesec = shadow_security.get("kubesec")
        if kubesec:
            status = "✅ Passed" if kubesec.get("passed") else "❌ Failed"
            score = kubesec.get("score", "N/A")
            security_text += f"  • [bold]Kubesec:[/bold] {status} (score: {score})\n"
            critical = kubesec.get("critical_issues", [])
            if critical:
                for issue in critical[:3]:
                    security_text += f"    ⚠️  {issue}\n"

        # Trivy
        trivy = shadow_security.get("trivy")
        if trivy:
            status = "✅ Passed" if trivy.get("passed") else "❌ Failed"
            vuln_count = trivy.get("vulnerabilities", 0)
            severity = trivy.get("severity_counts", {})
            security_text += f"  • [bold]Trivy:[/bold] {status} ({vuln_count} vulnerabilities)\n"
            if severity:
                crit = severity.get("CRITICAL", 0)
                high = severity.get("HIGH", 0)
                if crit > 0 or high > 0:
                    security_text += (
                        f"    [red]CRITICAL: {crit}[/red], [yellow]HIGH: {high}[/yellow]\n"
                    )

        # Falco
        falco = shadow_security.get("falco")
        if falco:
            if falco.get("skipped"):
                security_text += "  • [bold]Falco:[/bold] [dim]Skipped (not available)[/dim]\n"
            else:
                status = "✅ Passed" if falco.get("passed") else "❌ Failed"
                alert_count = falco.get("alert_count", 0)
                security_text += (
                    f"  • [bold]Falco:[/bold] {status} ({alert_count} runtime alerts)\n"
                )

        overall = "✅ All Passed" if shadow_security.get("passed") else "⚠️  Issues Found"
        security_text += f"\n[bold]Overall Security Status:[/bold] {overall}"

        security_panel = Panel(
            security_text,
            title="[bold magenta]🔒 Security Scan Results[/bold magenta]",
            border_style="magenta",
        )
        console.print(security_panel)
        console.print()

    # Display observability data for informed decision
    prometheus_metrics = result.get("prometheus_metrics")
    grafana_url = result.get("grafana_dashboard_url")
    if prometheus_metrics or grafana_url:
        obs_text = ""
        if prometheus_metrics:
            cpu = prometheus_metrics.get("cpu_usage")
            memory = prometheus_metrics.get("memory_usage")
            restarts = prometheus_metrics.get("restarts")
            if cpu is not None:
                obs_text += f"  • CPU: [cyan]{cpu:.1f}%[/cyan]  "
            if memory is not None:
                obs_text += f"  • Memory: [cyan]{memory:.1f}MB[/cyan]  "
            if restarts is not None:
                color = "red" if restarts > 5 else "yellow" if restarts > 0 else "green"
                obs_text += f"  • Restarts: [{color}]{restarts}[/{color}]"
            obs_text += "\n"
        if grafana_url:
            obs_text += f"\n  🔗 Dashboard: [link={grafana_url}]{grafana_url}[/link]"

        if obs_text.strip():
            obs_panel = Panel(
                obs_text.strip(),
                title="[bold blue]📊 Current Metrics[/bold blue]",
                border_style="blue",
            )
            console.print(obs_panel)
            console.print()

    # Show fix summary before prompting
    fix_summary_panel = Panel(
        f"[bold]Type:[/bold] {fix_proposal.fix_type.value}\n"
        f"[bold]Description:[/bold] {fix_proposal.description}\n\n"
        f"[bold]Commands:[/bold]\n"
        + "\n".join(f"  • {cmd}" for cmd in (fix_proposal.commands or [])[:5])
        + (
            "\n  • [dim]...[/dim]"
            if fix_proposal.commands and len(fix_proposal.commands) > 5
            else ""
        )
        + (
            "\n\n[bold yellow]Risks:[/bold yellow]\n"
            + "\n".join(f"  ⚠️  {r}" for r in fix_proposal.risks)
            if fix_proposal.risks
            else ""
        ),
        title="[bold]Fix Summary[/bold]",
        border_style="white",
    )
    console.print(fix_summary_panel)
    console.print()

    # Auto-fix mode or prompt user
    if auto_fix:
        apply_fix = True
        console.print(
            "[bold yellow]╔════════════════════════════════════════════════════════════╗[/bold yellow]",
        )
        console.print(
            "[bold yellow]║  AUTO-FIX MODE: Applying fix automatically...              ║[/bold yellow]",
        )
        console.print(
            "[bold yellow]╚════════════════════════════════════════════════════════════╝[/bold yellow]",
        )
        console.print()
    else:
        # Interactive confirmation prompt with prominent visual
        console.print(
            "[bold cyan]╔════════════════════════════════════════════════════════════╗[/bold cyan]",
        )
        console.print(
            "[bold cyan]║              🛡️  HUMAN APPROVAL REQUIRED  🛡️               ║[/bold cyan]",
        )
        console.print(
            "[bold cyan]╚════════════════════════════════════════════════════════════╝[/bold cyan]",
        )
        console.print()
        console.print("[bold]This action will apply the fix to your PRODUCTION cluster.[/bold]")
        console.print("[dim]The fix has been verified in shadow environment.[/dim]")
        console.print()

        apply_fix = typer.confirm(
            "🔐 Apply this fix to the PRODUCTION cluster? (yes/no)",
            default=False,
        )

    if apply_fix:
        # Apply the fix to production
        try:
            fix_result = asyncio.run(
                _apply_fix_to_production(
                    console=console,
                    fix_proposal=fix_proposal,
                    resource_type=resource_type,
                    resource_name=resource_name,
                    namespace=namespace,
                ),
            )
            _display_fix_result(console, fix_result)

            if fix_result.success:
                log.info(
                    "fix_applied_to_production",
                    resource=f"{resource_type}/{resource_name}",
                    namespace=namespace,
                    fix_type=fix_proposal.fix_type.value,
                )
            else:
                log.error(
                    "fix_application_failed",
                    resource=f"{resource_type}/{resource_name}",
                    error=fix_result.error_message,
                )
        except Exception as e:
            console.print(f"\n[bold red]Error applying fix:[/bold red] {e}\n")
            log.exception("fix_application_error")
    else:
        # User declined - generate and display abort report
        console.print("\n[yellow]Fix application cancelled by user.[/yellow]\n")

        report = _generate_abort_report(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            rca_result=rca_result,
            fix_proposal=fix_proposal,
            shadow_id=result.get("shadow_env_id"),
            shadow_passed=shadow_passed,
            shadow_logs=result.get("shadow_logs"),
        )

        _display_abort_report(console, report)

        log.info(
            "fix_application_aborted",
            resource=f"{resource_type}/{resource_name}",
            namespace=namespace,
        )


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
        settings.incident.auto_fix_enabled,
        "--auto-fix",
        help="Automatically apply fixes after verification",
    ),
    _export: str | None = typer.Option(
        None,
        "--export",
        "-e",
        help="Export analysis report to markdown file",
    ),
    verify: bool | None = typer.Option(
        None,
        "--verify/--no-verify",
        help="Run shadow verification automatically when a plan is available",
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
        aegis analyze deployment/demo-api -n production --verify
        aegis analyze pod/demo --mock  # Development mode without cluster

    """
    console.print(
        f"\n[bold cyan]Analyzing:[/bold cyan] {resource} in namespace [yellow]{namespace}[/yellow]\n",
    )

    # Check LLM availability
    _ensure_llm_available(console)

    # Parse resource (format: type/name)
    resource_type, resource_name = _parse_resource_or_exit(console, resource)

    # Run agent workflow
    try:
        result = _run_analysis_workflow(
            console,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            use_mock=mock,
        )

        # Check if no problems were detected (healthy resource)
        if result.get("no_problems"):
            console.print(
                f"\n[bold green]✓ No problems detected[/bold green] for "
                f"[cyan]{resource}[/cyan] in namespace [yellow]{namespace}[/yellow]\n",
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
        _display_analysis_results(console, result)

        # Show low-confidence warning if workflow stopped early
        if error_msg and rca_result:
            _show_low_confidence_warning(console, error_msg)

        # Optionally run shadow verification
        _maybe_run_shadow_verification(
            console=console,
            result=result,
            verify=verify,
            mock=mock,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )

        # Prompt user to apply fix to production if shadow verification passed
        _prompt_apply_fix_to_cluster(
            console=console,
            result=result,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            auto_fix=_auto_fix,
        )

        # Update metrics
        _update_incident_metrics(
            rca_result=rca_result,
            resource_type=resource_type,
            namespace=namespace,
        )

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
    namespace: str | None = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Filter by namespace (omit to list all namespaces)",
    ),
    severity: str | None = typer.Option(
        None,
        "--severity",
        "-s",
        help="Filter by severity (critical, high, medium, low)",
    ),
    all_namespaces: bool = typer.Option(
        False,
        "--all-namespaces",
        "-A",
        help="List incidents across all namespaces",
    ),
) -> None:
    """List active incidents.

    Queries the Kubernetes API for AegisIncident custom resources
    and displays them in a table format.

    Example:
        aegis incident list
        aegis incident list --namespace prod --severity high
        aegis incident list --all-namespaces

    """
    from aegis.crd import (
        AEGIS_API_GROUP,
        AEGIS_API_VERSION,
        AEGIS_INCIDENT_PLURAL,
        AegisIncident,
    )

    try:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        custom = client.CustomObjectsApi()

        # Fetch incidents from Kubernetes API
        if all_namespaces or namespace is None:
            # Cluster-wide listing
            response = custom.list_cluster_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                plural=AEGIS_INCIDENT_PLURAL,
            )
        else:
            # Namespace-scoped listing
            response = custom.list_namespaced_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                namespace=namespace,
                plural=AEGIS_INCIDENT_PLURAL,
            )

        items = response.get("items", [])

        # Parse and filter incidents
        incidents: list[AegisIncident] = []
        for item in items:
            try:
                incident = AegisIncident.from_kubernetes_object(cast("dict[str, Any]", item))
                # Apply severity filter if specified
                if severity and incident.spec.severity.value.lower() != severity.lower():
                    continue
                incidents.append(incident)
            except (TypeError, KeyError, ValueError) as e:
                log.warning("incident_parse_failed", error=str(e))
                continue

        # Create and populate table
        table = Table(title="Active Incidents")
        table.add_column("Incident ID", style="cyan")
        table.add_column("Severity", style="red")
        table.add_column("Resource", style="green")
        table.add_column("Namespace", style="yellow")
        table.add_column("Phase", style="white")
        table.add_column("Approval", style="blue")

        if not incidents:
            console.print(table)
            console.print("[dim]No incidents found[/dim]\n")
            return

        for incident in incidents:
            # Color-code severity
            severity_val = incident.spec.severity.value.upper()
            severity_color = _get_severity_color(incident.spec.severity.value)
            severity_display = f"[{severity_color}]{severity_val}[/{severity_color}]"

            # Color-code phase
            phase_val = incident.status.phase.value
            phase_color = _get_phase_color(phase_val)
            phase_display = f"[{phase_color}]{phase_val}[/{phase_color}]"

            # Resource reference
            resource_ref = incident.spec.resource_ref
            resource_display = f"{resource_ref.kind.lower()}/{resource_ref.name}"

            # Approval status
            approval_status = incident.spec.approval.status.value

            table.add_row(
                incident.metadata.name,
                severity_display,
                resource_display,
                incident.metadata.namespace,
                phase_display,
                approval_status,
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(incidents)} incident(s)[/dim]\n")

    except client.ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            console.print(
                "[bold yellow]Warning:[/bold yellow] AegisIncident CRD not installed. "
                "Install with: kubectl apply -f deploy/helm/aegis/crds/",
            )
        else:
            console.print(f"[bold red]Error:[/bold red] {e.reason}")
        raise typer.Exit(code=1) from None
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        log.exception("incident_list_failed")
        raise typer.Exit(code=1) from None


def _get_severity_color(severity: str) -> str:
    """Get Rich color for severity level."""
    return {
        "critical": "red bold",
        "high": "red",
        "medium": "yellow",
        "low": "green",
    }.get(severity, "white")


def _get_phase_color(phase: str) -> str:
    """Get Rich color for incident phase."""
    return {
        "Detected": "cyan",
        "Analyzing": "blue",
        "AwaitingApproval": "yellow bold",
        "ApplyingFix": "magenta",
        "Monitoring": "blue",
        "Resolved": "green bold",
        "Failed": "red bold",
        "Rejected": "red",
        "Timeout": "yellow",
    }.get(phase, "white")


def _build_incident_details(incident: Any, namespace: str) -> str:
    """Build incident details string for display."""
    from aegis.crd import AegisIncident

    if not isinstance(incident, AegisIncident):
        return str(incident)

    resource_ref = incident.spec.resource_ref
    severity_color = _get_severity_color(incident.spec.severity.value)
    phase_color = _get_phase_color(incident.status.phase.value)

    details = (
        f"[bold]Phase:[/bold] [{phase_color}]{incident.status.phase.value}[/{phase_color}]\n"
        f"[bold]Severity:[/bold] [{severity_color}]{incident.spec.severity.value.upper()}[/{severity_color}]\n"
        f"[bold]Resource:[/bold] {resource_ref.kind}/{resource_ref.name}\n"
        f"[bold]Namespace:[/bold] {resource_ref.namespace or namespace}\n"
        f"[bold]Source:[/bold] {incident.spec.source.value}\n"
    )

    if incident.metadata.creation_timestamp:
        details += f"[bold]Detected:[/bold] {incident.metadata.creation_timestamp}\n"

    details += _build_approval_section(incident.spec.approval)
    details += _build_rca_section(incident.spec.rca_result)
    details += _build_fix_proposal_section(incident.spec.fix_proposal)
    details += _build_shadow_section(incident.spec.shadow_verification)
    details += _build_fix_status_section(incident.status)

    return details


def _build_approval_section(approval: Any) -> str:
    """Build approval section of incident details."""
    section = f"\n[bold]Approval Required:[/bold] {approval.required}\n"
    section += f"[bold]Approval Status:[/bold] {approval.status.value}\n"
    if approval.approved_by:
        section += f"[bold]Approved By:[/bold] {approval.approved_by}\n"
    if approval.rejected_by:
        section += f"[bold]Rejected By:[/bold] {approval.rejected_by}\n"
    if approval.rejection_reason:
        section += f"[bold]Rejection Reason:[/bold] {approval.rejection_reason}\n"
    if approval.timeout_at:
        section += f"[bold]Timeout At:[/bold] {approval.timeout_at}\n"
    return section


def _build_rca_section(rca_result: Any | None) -> str:
    """Build RCA section of incident details."""
    if not rca_result:
        return ""
    section = "\n[bold]Root Cause Analysis:[/bold]\n"
    section += f"  {rca_result.root_cause}\n"
    section += f"  Confidence: {rca_result.confidence_score:.0%}\n"
    return section


def _build_fix_proposal_section(fix_proposal: Any | None) -> str:
    """Build fix proposal section of incident details."""
    if not fix_proposal:
        return ""
    section = "\n[bold]Proposed Solution:[/bold]\n"
    section += f"  Type: {fix_proposal.fix_type.value}\n"
    section += f"  {fix_proposal.description}\n"
    if fix_proposal.commands:
        section += "  Commands:\n"
        for cmd in fix_proposal.commands[:3]:
            section += f"    • {cmd}\n"
    return section


def _build_shadow_section(shadow: Any | None) -> str:
    """Build shadow verification section of incident details."""
    if not shadow:
        return ""
    section = "\n[bold]Shadow Verification:[/bold]\n"
    if shadow.shadow_id:
        section += f"  Shadow ID: {shadow.shadow_id}\n"
    if shadow.passed is not None:
        status = "[green]PASSED[/green]" if shadow.passed else "[red]FAILED[/red]"
        section += f"  Status: {status}\n"
    if shadow.health_score is not None:
        section += f"  Health Score: {shadow.health_score:.0%}\n"
    return section


def _build_fix_status_section(status: Any) -> str:
    """Build fix status section of incident details."""
    section = ""
    if status.fix_applied:
        section += "\n[bold green]✓ Fix Applied[/bold green]"
        if status.fix_applied_at:
            section += f" at {status.fix_applied_at}"
        section += "\n"
    if status.fix_error:
        section += f"\n[bold red]Fix Error:[/bold red] {status.fix_error}\n"
    return section


@typed_command(incident_app, name="show")
def incident_show(
    incident_id: str = typer.Argument(..., help="Incident ID"),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Namespace of the incident",
    ),
) -> None:
    """Show incident details.

    Example:
        aegis incident show inc-2026-001
        aegis incident show inc-2026-001 -n production

    """
    from aegis.crd import (
        AEGIS_API_GROUP,
        AEGIS_API_VERSION,
        AEGIS_INCIDENT_PLURAL,
        AegisIncident,
    )

    try:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        custom = client.CustomObjectsApi()

        obj = custom.get_namespaced_custom_object(
            group=AEGIS_API_GROUP,
            version=AEGIS_API_VERSION,
            namespace=namespace,
            plural=AEGIS_INCIDENT_PLURAL,
            name=incident_id,
        )
        incident = AegisIncident.from_kubernetes_object(cast("dict[str, Any]", obj))
        details = _build_incident_details(incident, namespace)

        panel = Panel(
            details,
            title=f"[bold]{incident_id}[/bold]",
            border_style="cyan",
        )
        console.print(panel)

    except client.ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            console.print(
                f"[bold red]Error:[/bold red] Incident '{incident_id}' not found in namespace '{namespace}'",
            )
        else:
            console.print(f"[bold red]Error:[/bold red] {e.reason}")
        raise typer.Exit(code=1) from None
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        log.exception("incident_show_failed")
        raise typer.Exit(code=1) from None

    console.print()


def _validate_incident_for_approval(incident: Any, phase_enum: Any) -> int | None:
    """Validate incident state for approval. Returns exit code or None to continue."""
    if incident.status.phase != phase_enum.AWAITING_APPROVAL:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Incident is in phase "
            f"'{incident.status.phase.value}', not 'AwaitingApproval'",
        )
        if incident.status.phase in [phase_enum.RESOLVED, phase_enum.REJECTED]:
            console.print("[dim]This incident has already been resolved/rejected.[/dim]")
            return 0

    if not incident.has_fix_proposal():
        console.print("[bold red]Error:[/bold red] Incident has no fix proposal to approve")
        return 1

    return None


def _validate_incident_for_rejection(incident: Any, phase_enum: Any) -> int | None:
    """Validate incident state for rejection. Returns exit code or None to continue."""
    if incident.status.phase not in [
        phase_enum.AWAITING_APPROVAL,
        phase_enum.DETECTED,
        phase_enum.ANALYZING,
    ]:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Incident is in phase "
            f"'{incident.status.phase.value}'",
        )
        if incident.status.phase in [phase_enum.RESOLVED, phase_enum.REJECTED]:
            console.print("[dim]This incident has already been resolved/rejected.[/dim]")
            return 0
    return None


@typed_command(incident_app, name="approve")
def incident_approve(
    incident_id: str = typer.Argument(..., help="Incident ID to approve"),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Namespace of the incident",
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="Approving user (defaults to current kubectl user)",
    ),
    comment: str = typer.Option(
        None,
        "--comment",
        "-c",
        help="Approval comment",
    ),
) -> None:
    """Approve fix for an incident.

    Approves the proposed fix for an incident, triggering the operator
    to apply the fix to the target resource. The fix is first validated
    with a dry-run before being applied.

    Examples:
        aegis incident approve inc-2026-001
        aegis incident approve inc-2026-001 -n production
        aegis incident approve inc-2026-001 --user sre-lead --comment "Verified fix"

    """
    from aegis.crd import (
        AEGIS_API_GROUP,
        AEGIS_API_VERSION,
        AEGIS_INCIDENT_PLURAL,
        AegisIncident,
        ApprovalStatus,
        IncidentPhase,
    )

    log.info("approving_incident", incident_id=incident_id, namespace=namespace, user=user)

    # Initialize Kubernetes config
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    custom = client.CustomObjectsApi()

    # Fetch current incident
    try:
        obj = custom.get_namespaced_custom_object(
            group=AEGIS_API_GROUP,
            version=AEGIS_API_VERSION,
            namespace=namespace,
            plural=AEGIS_INCIDENT_PLURAL,
            name=incident_id,
        )
        incident = AegisIncident.from_kubernetes_object(cast("dict[str, Any]", obj))
    except client.ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            console.print(f"[bold red]Error:[/bold red] Incident '{incident_id}' not found")
        else:
            console.print(f"[bold red]Error:[/bold red] {e.reason}")
        raise typer.Exit(code=1) from None

    # Validate state - outside try block to avoid TRY301
    exit_code = _validate_incident_for_approval(incident, IncidentPhase)
    if exit_code is not None:
        raise typer.Exit(code=exit_code)

    try:
        # Determine approving user
        approving_user = user
        if not approving_user:
            # Try to get current kubectl user
            try:
                _, active_context = k8s_config.list_kube_config_contexts()
                approving_user = active_context.get("context", {}).get("user", "unknown")
            except (k8s_config.ConfigException, OSError, KeyError):
                approving_user = "cli-user"

        # Build patch
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        approval_data: dict[str, Any] = {
            "status": ApprovalStatus.APPROVED.value,
            "approvedBy": approving_user,
            "approvedAt": now,
        }
        if comment:
            approval_data["comment"] = comment
        patch_body: dict[str, Any] = {
            "spec": {
                "approval": approval_data,
            },
            "status": {
                "phase": IncidentPhase.APPLYING_FIX.value,
            },
        }

        # Apply patch
        with console.status(f"[bold green]Approving incident {incident_id}..."):
            custom.patch_namespaced_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                namespace=namespace,
                plural=AEGIS_INCIDENT_PLURAL,
                name=incident_id,
                body=patch_body,
            )

        console.print(
            f"\n[green]✓[/green] Incident [cyan]{incident_id}[/cyan] approved by [yellow]{approving_user}[/yellow]",
        )
        console.print("  The operator will now apply the fix with dry-run validation.")
        console.print("  Use [cyan]aegis incident show[/cyan] to monitor progress.")

    except client.ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            console.print(f"[bold red]Error:[/bold red] Incident '{incident_id}' not found")
        else:
            console.print(f"[bold red]Error:[/bold red] {e.reason}")
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        log.exception("incident_approve_failed")
        raise typer.Exit(code=1) from None

    console.print()


@typed_command(incident_app, name="reject")
def incident_reject(
    incident_id: str = typer.Argument(..., help="Incident ID to reject"),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Namespace of the incident",
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="Rejecting user (defaults to current kubectl user)",
    ),
    reason: str = typer.Option(
        None,
        "--reason",
        "-r",
        help="Rejection reason (required)",
    ),
) -> None:
    """Reject fix for an incident.

    Rejects the proposed fix for an incident. A reason should be provided
    to document why the fix was declined.

    Examples:
        aegis incident reject inc-2026-001 --reason "Fix too risky for production"
        aegis incident reject inc-2026-001 -n prod -r "Need to investigate further"

    """
    from aegis.crd import (
        AEGIS_API_GROUP,
        AEGIS_API_VERSION,
        AEGIS_INCIDENT_PLURAL,
        AegisIncident,
        ApprovalStatus,
        IncidentPhase,
    )

    log.info("rejecting_incident", incident_id=incident_id, namespace=namespace, user=user)

    # Validate reason is provided
    if not reason:
        console.print("[bold red]Error:[/bold red] Rejection reason is required (--reason)")
        raise typer.Exit(code=1)

    # Initialize Kubernetes config
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    custom = client.CustomObjectsApi()

    # Fetch current incident
    try:
        obj = custom.get_namespaced_custom_object(
            group=AEGIS_API_GROUP,
            version=AEGIS_API_VERSION,
            namespace=namespace,
            plural=AEGIS_INCIDENT_PLURAL,
            name=incident_id,
        )
        incident = AegisIncident.from_kubernetes_object(cast("dict[str, Any]", obj))
    except client.ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            console.print(f"[bold red]Error:[/bold red] Incident '{incident_id}' not found")
        else:
            console.print(f"[bold red]Error:[/bold red] {e.reason}")
        raise typer.Exit(code=1) from None

    # Validate state - outside try block to avoid TRY301
    exit_code = _validate_incident_for_rejection(incident, IncidentPhase)
    if exit_code is not None:
        raise typer.Exit(code=exit_code)

    try:
        # Determine rejecting user
        rejecting_user = user
        if not rejecting_user:
            try:
                _, active_context = k8s_config.list_kube_config_contexts()
                rejecting_user = active_context.get("context", {}).get("user", "unknown")
            except (k8s_config.ConfigException, OSError, KeyError):
                rejecting_user = "cli-user"

        # Build patch
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        patch_body = {
            "spec": {
                "approval": {
                    "status": ApprovalStatus.REJECTED.value,
                    "rejectedBy": rejecting_user,
                    "rejectedAt": now,
                    "rejectionReason": reason,
                },
            },
            "status": {
                "phase": IncidentPhase.REJECTED.value,
            },
        }

        # Apply patch
        with console.status(f"[bold yellow]Rejecting incident {incident_id}..."):
            custom.patch_namespaced_custom_object(
                group=AEGIS_API_GROUP,
                version=AEGIS_API_VERSION,
                namespace=namespace,
                plural=AEGIS_INCIDENT_PLURAL,
                name=incident_id,
                body=patch_body,
            )

        console.print(
            f"\n[yellow]✗[/yellow] Incident [cyan]{incident_id}[/cyan] rejected by [yellow]{rejecting_user}[/yellow]",
        )
        console.print(f"  Reason: {reason}")

    except client.ApiException as e:
        if e.status == HTTP_NOT_FOUND:
            console.print(f"[bold red]Error:[/bold red] Incident '{incident_id}' not found")
        else:
            console.print(f"[bold red]Error:[/bold red] {e.reason}")
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        log.exception("incident_reject_failed")
        raise typer.Exit(code=1) from None

    console.print()


# ============================================================================
# Shadow Command Group
# ============================================================================

shadow_app = typer.Typer(help="Manage shadow verification environments")
app.add_typer(shadow_app, name="shadow")


# Time constants for human-readable formatting
_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60
_HOURS_PER_DAY = 24
_RESOURCE_REF_PARTS = 2


def _format_time_ago(dt: "datetime") -> str:
    """Format datetime as human-readable 'X ago' string."""
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds}s ago"
    minutes = seconds // _SECONDS_PER_MINUTE
    if minutes < _MINUTES_PER_HOUR:
        return f"{minutes}m ago"
    hours = minutes // _MINUTES_PER_HOUR
    if hours < _HOURS_PER_DAY:
        return f"{hours}h ago"
    days = hours // _HOURS_PER_DAY
    return f"{days}d ago"


def _parse_resource_ref(value: str) -> tuple[str, str]:
    """Parse kind/name resource reference."""
    if "/" not in value:
        if not value.strip():
            console.print(
                "[bold red]Error:[/bold red] Resource name cannot be empty",
            )
            raise typer.Exit(code=1)
        return "deployment", value

    parts = value.split("/")
    if len(parts) != _RESOURCE_REF_PARTS or not parts[0] or not parts[1]:
        console.print(
            "[bold red]Error:[/bold red] Resource must be in format: kind/name "
            "(e.g., deployment/nginx, pod/worker)",
        )
        raise typer.Exit(code=1)
    return parts[0], parts[1]


def _shadow_log_path(shadow_id: str) -> Path:
    """Resolve log path for background shadow operations."""
    try:
        base = Path.home() / ".aegis" / "shadow"
    except RuntimeError:
        base = Path(tempfile.gettempdir()) / "aegis-shadow"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{shadow_id}.log"


def _spawn_shadow_create(
    source_resource: str,
    namespace: str,
    shadow_id: str,
) -> Path:
    """Spawn a background process to create the shadow environment."""
    import subprocess

    log_path = _shadow_log_path(shadow_id)
    cmd = [
        sys.executable,
        "-m",
        "aegis.cli",
        "shadow",
        "create",
        source_resource,
        "--namespace",
        namespace,
        "--id",
        shadow_id,
        "--wait",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as handle:
        subprocess.Popen(
            cmd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return log_path


@typed_command(shadow_app, name="create")
def shadow_create(
    source_resource: str = typer.Argument(
        ...,
        help="Source resource to clone (kind/name, defaults to deployment/<name>)",
    ),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Source resource namespace",
    ),
    shadow_id: str | None = typer.Option(
        None,
        "--id",
        help="Custom shadow environment ID (auto-generated if omitted)",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Block until shadow environment is ready",
    ),
) -> None:
    """Create a shadow verification environment.

    Creates an isolated vCluster-based shadow environment by cloning
    the specified source resource from the production cluster.

    Examples:
        aegis shadow create deployment/nginx
        aegis shadow create deployment/api -n production --wait
        aegis shadow create pod/worker --id my-test-env

    """
    resource_kind, resource_name = _parse_resource_ref(source_resource)

    if not settings.shadow.enabled:
        console.print("[bold red]Error:[/bold red] Shadow verification is disabled")
        raise typer.Exit(code=1)

    if not shadow_id:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        shadow_id = f"{resource_name}-{timestamp}"

    from aegis.shadow.manager import ShadowManager

    sanitized_id = ShadowManager._sanitize_name(shadow_id)
    if sanitized_id != shadow_id:
        console.print(
            f"[yellow]Note:[/yellow] Shadow ID sanitized to [cyan]{sanitized_id}[/cyan]",
        )
        shadow_id = sanitized_id
    log.info(
        "creating_shadow",
        resource_kind=resource_kind,
        resource_name=resource_name,
        namespace=namespace,
        shadow_id=shadow_id,
        wait=wait,
    )

    shadow_manager = get_shadow_manager()

    async def _create() -> "ShadowEnvironment":
        from aegis.shadow.manager import ShadowEnvironment

        env: ShadowEnvironment = await shadow_manager.create_shadow(
            source_namespace=namespace,
            source_resource=resource_name,
            source_resource_kind=resource_kind.capitalize(),
            shadow_id=shadow_id,
        )
        return env

    if wait:
        with console.status(f"[bold green]Creating shadow environment for {source_resource}..."):
            try:
                env = asyncio.run(_create())
                console.print(
                    f"\n[green]✓[/green] Shadow environment [cyan]{env.id}[/cyan] created",
                )
                console.print(f"  Namespace: [yellow]{env.namespace}[/yellow]")
                console.print(f"  Status: [green]{env.status.value}[/green]")
                if env.kubeconfig_path:
                    console.print(f"  Kubeconfig: [blue]{env.kubeconfig_path}[/blue]")
            except RuntimeError as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")
                log.exception("shadow_create_failed")
                raise typer.Exit(code=1) from None
    else:
        # Async mode: spawn background creator and return immediately
        console.print(
            f"[bold cyan]Starting shadow environment creation for {source_resource}...[/bold cyan]"
        )
        try:
            log_path = _spawn_shadow_create(source_resource, namespace, shadow_id)
            console.print(
                f"[green]✓[/green] Shadow creation started for [cyan]{shadow_id}[/cyan]",
            )
            console.print(f"  Logs: [dim]{log_path}[/dim]")
            console.print(f"\nTrack progress: [cyan]aegis shadow status {shadow_id}[/cyan]")
            console.print(f"Wait for readiness: [cyan]aegis shadow wait {shadow_id}[/cyan]")
        except RuntimeError as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            log.exception("shadow_create_failed")
            raise typer.Exit(code=1) from None

    console.print()


@typed_command(shadow_app, name="list")
def shadow_list() -> None:
    """List shadow environments.

    Shows all shadow environments managed by AEGIS, including their
    current status, runtime, and creation time.

    Example:
        aegis shadow list

    """
    log.info("listing_shadows")

    shadow_manager = get_shadow_manager()
    environments = shadow_manager.list_environments()

    console.print("\n[bold cyan]Shadow Environments[/bold cyan]\n")

    if not environments:
        console.print("[dim]No shadow environments found[/dim]\n")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Source", style="white")
    table.add_column("Namespace", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Health", style="blue")
    table.add_column("Created", style="dim")

    for env in environments:
        # Color-code status
        status_style = {
            "ready": "green",
            "creating": "yellow",
            "testing": "cyan",
            "passed": "green bold",
            "failed": "red",
            "error": "red bold",
            "deleted": "dim",
            "cleaning": "yellow",
            "pending": "dim",
        }.get(env.status.value, "white")

        health_display = f"{env.health_score:.0%}" if env.health_score > 0 else "-"

        source_display = f"{env.source_resource_kind}/{env.source_resource}"
        created_display = _format_time_ago(env.created_at)

        table.add_row(
            env.id,
            source_display,
            env.namespace,
            f"[{status_style}]{env.status.value}[/{status_style}]",
            health_display,
            created_display,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(environments)} environment(s)[/dim]\n")


@typed_command(shadow_app, name="status")
def shadow_status(
    shadow_id: str = typer.Argument(..., help="Shadow environment ID"),
) -> None:
    """Show status for a shadow environment."""
    log.info("shadow_status", shadow_id=shadow_id)

    shadow_manager = get_shadow_manager()
    env = shadow_manager.get_environment(shadow_id)

    if not env:
        console.print(f"[bold red]Error:[/bold red] Shadow environment '{shadow_id}' not found")
        raise typer.Exit(code=1)

    console.print("\n[bold cyan]Shadow Status[/bold cyan]\n")
    console.print(f"ID: [cyan]{env.id}[/cyan]")
    console.print(f"Status: [green]{env.status.value}[/green]")
    console.print(f"Source: [white]{env.source_resource_kind}/{env.source_resource}[/white]")
    console.print(f"Namespace: [yellow]{env.namespace}[/yellow]")
    if env.host_namespace:
        console.print(f"Host Namespace: [yellow]{env.host_namespace}[/yellow]")
    if env.runtime:
        console.print(f"Runtime: [blue]{env.runtime}[/blue]")
    console.print(f"Created: [dim]{_format_time_ago(env.created_at)}[/dim]")
    if env.health_score > 0:
        console.print(f"Health Score: [cyan]{env.health_score:.0%}[/cyan]")
    console.print()


@typed_command(shadow_app, name="wait")
def shadow_wait(
    shadow_id: str = typer.Argument(..., help="Shadow environment ID"),
    timeout: int = typer.Option(
        settings.shadow.verification_timeout,
        "--timeout",
        "-t",
        help="Timeout in seconds to wait for readiness",
    ),
    poll_interval: float = typer.Option(
        3.0,
        "--poll",
        "-p",
        help="Polling interval in seconds",
    ),
) -> None:
    """Wait for a shadow environment to become ready."""
    log.info("shadow_wait", shadow_id=shadow_id, timeout=timeout)

    shadow_manager = get_shadow_manager()

    async def _wait() -> "ShadowEnvironment":
        from aegis.shadow.manager import ShadowEnvironment

        env: ShadowEnvironment = await shadow_manager.wait_for_ready(
            shadow_id=shadow_id,
            timeout_seconds=timeout,
            poll_interval=poll_interval,
        )
        return env

    with console.status(f"[bold blue]Waiting for {shadow_id} to be ready..."):
        try:
            env = asyncio.run(_wait())
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            log.exception("shadow_wait_failed")
            raise typer.Exit(code=1) from None

    console.print(f"\n[green]✓[/green] Shadow environment [cyan]{env.id}[/cyan] is ready")
    console.print(f"  Namespace: [yellow]{env.namespace}[/yellow]")
    console.print(f"  Status: [green]{env.status.value}[/green]")
    if env.kubeconfig_path:
        console.print(f"  Kubeconfig: [blue]{env.kubeconfig_path}[/blue]")
    console.print()


@typed_command(shadow_app, name="delete")
def shadow_delete(
    shadow_id: str = typer.Argument(..., help="Shadow environment ID"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force deletion without confirmation",
    ),
) -> None:
    """Delete a shadow environment.

    Cleans up the vCluster and associated resources for the specified
    shadow environment.

    Examples:
        aegis shadow delete my-test-env
        aegis shadow delete my-test-env --force

    """
    log.info("deleting_shadow", shadow_id=shadow_id)

    shadow_manager = get_shadow_manager()
    env = shadow_manager.get_environment(shadow_id)

    if not env:
        console.print(f"[bold red]Error:[/bold red] Shadow environment '{shadow_id}' not found")
        raise typer.Exit(code=1)

    if not force:
        console.print(f"Shadow environment: [cyan]{shadow_id}[/cyan]")
        console.print(f"  Source: {env.source_resource_kind}/{env.source_resource}")
        console.print(f"  Status: {env.status.value}")
        confirm = typer.confirm("\nAre you sure you want to delete this shadow environment?")
        if not confirm:
            console.print("[yellow]Deletion cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _delete() -> None:
        await shadow_manager.cleanup(shadow_id)

    with console.status(f"[bold yellow]Deleting shadow environment: {shadow_id}..."):
        try:
            asyncio.run(_delete())
            console.print(f"\n[green]✓[/green] Shadow environment [cyan]{shadow_id}[/cyan] deleted")
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            log.exception("shadow_delete_failed")
            raise typer.Exit(code=1) from None

    console.print()


@typed_command(shadow_app, name="verify")
def shadow_verify(
    shadow_id: str | None = typer.Argument(None, help="Shadow environment ID"),
    duration: int = typer.Option(
        30,
        "--duration",
        "-d",
        help="Verification duration in seconds",
    ),
    ephemeral: bool = typer.Option(
        False,
        "--ephemeral",
        help="Create a temporary shadow environment for verification",
    ),
    app: str | None = typer.Option(
        None,
        "--app",
        help="Source resource to clone (kind/name, defaults to deployment/<name>)",
    ),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Source resource namespace for ephemeral verification",
    ),
) -> None:
    """Run verification tests on a shadow environment.

    Applies pending changes and monitors health, smoke tests,
    and load tests in the shadow environment.

    Examples:
        aegis shadow verify my-test-env
        aegis shadow verify my-test-env --duration 60

    """
    if ephemeral:
        if not app:
            console.print(
                "[bold red]Error:[/bold red] --app is required when using --ephemeral",
            )
            raise typer.Exit(code=1)
        resource_kind, resource_name = _parse_resource_ref(app)
        log.info(
            "verifying_shadow_ephemeral",
            resource_kind=resource_kind,
            resource_name=resource_name,
            namespace=namespace,
            duration=duration,
        )
    else:
        if not shadow_id:
            console.print("[bold red]Error:[/bold red] Shadow environment ID required")
            raise typer.Exit(code=1)
        log.info("verifying_shadow", shadow_id=shadow_id, duration=duration)

    shadow_manager = get_shadow_manager()

    async def _verify() -> bool:
        if ephemeral:
            env = await shadow_manager.create_shadow(
                source_namespace=namespace,
                source_resource=resource_name,
                source_resource_kind=resource_kind.capitalize(),
            )
            try:
                return await shadow_manager.run_verification(
                    shadow_id=env.id,
                    changes={},  # No changes for manual verify
                    duration=duration,
                )
            finally:
                await shadow_manager.cleanup(env.id)
        return await shadow_manager.run_verification(
            shadow_id=shadow_id or "",
            changes={},  # No changes for manual verify
            duration=duration,
        )

    target_label = shadow_id or (f"{resource_kind}/{resource_name}" if ephemeral else "")
    with console.status(f"[bold blue]Running verification on {target_label} for {duration}s..."):
        try:
            passed = asyncio.run(_verify())
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            log.exception("shadow_verify_failed")
            raise typer.Exit(code=1) from None

    # Refresh env to get updated status
    env = shadow_manager.get_environment(shadow_id) if shadow_id else None

    if passed:
        console.print("\n[bold green]✓ Verification PASSED[/bold green]")
    else:
        console.print("\n[bold red]✗ Verification FAILED[/bold red]")

    if env:
        console.print(f"  Health Score: [cyan]{env.health_score:.0%}[/cyan]")
        if env.test_results:
            smoke = env.test_results.get("smoke_test")
            load = env.test_results.get("load_test")
            if smoke:
                smoke_status = "[green]passed[/green]" if smoke["passed"] else "[red]failed[/red]"
                console.print(f"  Smoke Test: {smoke_status}")
            if load:
                load_status = "[green]passed[/green]" if load["passed"] else "[red]failed[/red]"
                console.print(f"  Load Test: {load_status}")

        if env.logs:
            console.print("\n[bold]Verification Logs:[/bold]")
            for log_entry in env.logs[-5:]:
                console.print(f"  [dim]•[/dim] {log_entry}")

    console.print()
    raise typer.Exit(code=0 if passed else 1)


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

[bold]LLM Providers[/bold]
  RCA: {settings.agent.rca_provider.value} ({settings.agent.rca_model}) fallback={settings.agent.rca_fallback_model}
  Solution: {settings.agent.solution_provider.value} ({settings.agent.solution_model}) fallback={settings.agent.solution_fallback_model}
  Verifier: {settings.agent.verifier_provider.value} ({settings.agent.verifier_model}) fallback={settings.agent.verifier_fallback_model}

[bold]Groq[/bold]
  Enabled: {settings.groq.enabled}
  Model: {settings.groq.model}
  API Key: {"set" if settings.groq.api_key else "missing"}
  Base URL: {settings.groq.base_url}

[bold]Gemini[/bold]
  Enabled: {settings.gemini.enabled}
  Model: {settings.gemini.model}
  API Key: {"set" if settings.gemini.api_key else "missing"}
  Base URL: {settings.gemini.base_url}

[bold]Ollama[/bold]
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
# Queue Command Group
# ============================================================================

queue_app = typer.Typer(help="Manage incident queue")
app.add_typer(queue_app, name="queue")


@typed_command(queue_app, name="status")
def queue_status() -> None:
    """Show current incident queue status.

    Displays queue depth by priority, production lock status,
    and summary statistics.

    Example:
        aegis queue status

    """
    log.info("checking_queue_status")

    try:
        from aegis.incident import get_incident_queue
    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to import incident queue: {e}")
        raise typer.Exit(code=1) from None

    queue = get_incident_queue()

    console.print("\n[bold cyan]Incident Queue Status[/bold cyan]\n")

    # Production lock status
    locked, reason = queue.is_production_locked()
    if locked:
        console.print(f"[red]🔒 PRODUCTION LOCKED[/red]: {reason}\n")
    else:
        console.print("[green]🔓 Production unlocked[/green]\n")

    # Queue depth by priority
    table = Table(title="Queue Depth by Priority", show_header=True, header_style="bold magenta")
    table.add_column("Priority", style="cyan", justify="left")
    table.add_column("Depth", justify="right", style="yellow")
    table.add_column("Description", style="dim")

    priority_descriptions = {
        "p0": "Critical - Locks production",
        "p1": "High - Immediate attention",
        "p2": "Medium - Process soon",
        "p3": "Low - Process when available",
        "p4": "Info - Background processing",
    }

    # Get metrics
    metrics = queue.get_metrics()
    depth_by_priority = metrics.get("depth_by_priority", {})

    total_depth = 0
    for priority in ["p0", "p1", "p2", "p3", "p4"]:
        depth = depth_by_priority.get(priority, 0)
        total_depth += depth
        desc = priority_descriptions.get(priority, "")

        style_color = "red bold" if priority == "p0" else "yellow" if priority == "p1" else "white"
        priority_display = f"[{style_color}]{priority.upper()}[/{style_color}]"

        table.add_row(priority_display, str(depth), desc)

    console.print(table)

    # Summary statistics
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Total in Queue: [yellow]{total_depth}[/yellow]")
    console.print("  Processing Enabled: [green]Yes[/green]")
    console.print()


@typed_command(queue_app, name="unlock")
def queue_unlock(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force unlock without confirmation",
    ),
) -> None:
    """Unlock production deployments.

    Manually unlocks production when locked by a P0 incident.
    Use with caution - only unlock if you're certain the blocking
    incident has been resolved.

    Example:
        aegis queue unlock
        aegis queue unlock --force

    """
    log.info("unlocking_production", force=force)

    try:
        from aegis.incident import get_incident_queue
    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to import incident queue: {e}")
        raise typer.Exit(code=1) from None

    queue = get_incident_queue()

    # Check if locked
    locked, reason = queue.is_production_locked()

    if not locked:
        console.print("[yellow]Production is not currently locked[/yellow]")
        console.print()
        raise typer.Exit(code=0)

    console.print(f"\n[bold red]Production is locked:[/bold red] {reason}\n")

    if not force:
        confirm = typer.confirm("Are you sure you want to unlock production?")
        if not confirm:
            console.print("[yellow]Unlock cancelled[/yellow]")
            raise typer.Exit(code=0)

    # Manually unlock by clearing the production lock
    # This is a forceful operation - normally the lock clears when P0 incidents are resolved
    queue._production_locked = False
    queue._production_lock_reason = None

    console.print("[green]✓[/green] Production unlocked")
    console.print(
        "[yellow]Warning:[/yellow] Ensure blocking incidents are resolved before deploying"
    )
    console.print()


# ============================================================================
# Rollback Command
# ============================================================================


@typed_command(app)
def rollback(
    resource: str = typer.Argument(
        ...,
        help="Resource to rollback (kind/name, e.g., deployment/api)",
    ),
    snapshot_id: str = typer.Option(
        ...,
        "--snapshot",
        "-s",
        help="Snapshot ID to rollback to",
    ),
    namespace: str = typer.Option(
        "default",
        "--namespace",
        "-n",
        help="Kubernetes namespace",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Manually trigger rollback to a previous snapshot.

    Restores a Kubernetes resource to a previously captured state.
    Snapshots are automatically created before production deployments.

    Examples:
        aegis rollback deployment/api --snapshot snapshot-20260204-123456
        aegis rollback deployment/api -s snapshot-20260204-123456 -n production
        aegis rollback deployment/api -s snapshot-20260204-123456 --force

    """
    resource_kind, resource_name = _parse_resource_ref(resource)
    log.info(
        "manual_rollback",
        resource_kind=resource_kind,
        resource_name=resource_name,
        namespace=namespace,
        snapshot_id=snapshot_id,
    )

    console.print("\n[bold yellow]Manual Rollback Requested[/bold yellow]\n")
    console.print(f"Resource: [cyan]{resource_kind}/{resource_name}[/cyan]")
    console.print(f"Namespace: [yellow]{namespace}[/yellow]")
    console.print(f"Snapshot ID: [blue]{snapshot_id}[/blue]")
    console.print()

    if not force:
        confirm = typer.confirm(
            f"Rollback {resource_kind}/{resource_name} to snapshot {snapshot_id}?"
        )
        if not confirm:
            console.print("[yellow]Rollback cancelled[/yellow]")
            raise typer.Exit(code=0)

    # Load snapshot (in production, this would load from persistent storage)
    # For now, we'll show an error as snapshot storage isn't implemented
    console.print(
        "[bold red]Error:[/bold red] Snapshot storage not yet implemented\n"
        "[dim]Snapshots are currently stored in memory during the incident lifecycle[/dim]"
    )
    console.print()
    console.print("[yellow]Manual workaround:[/yellow]")
    console.print("  1. View snapshot details in operator logs")
    console.print("  2. Manually apply resource configuration using kubectl")
    console.print()

    raise typer.Exit(code=1)


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
    console.print(
        f"RCA: [green]{settings.agent.rca_provider.value}[/green] ({settings.agent.rca_model})"
    )
    console.print(
        "Solution: "
        f"[green]{settings.agent.solution_provider.value}[/green] "
        f"({settings.agent.solution_model})"
    )
    console.print(
        "Verifier: "
        f"[green]{settings.agent.verifier_provider.value}[/green] "
        f"({settings.agent.verifier_model})"
    )
    console.print(f"Ollama Base URL: [blue]{settings.ollama.base_url}[/blue]")
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

        # Check Groq/Gemini configuration
        groq_ok = settings.groq.enabled and bool(settings.groq.api_key)
        gemini_ok = settings.gemini.enabled and bool(settings.gemini.api_key)
        console.print(
            f"{'[green]✓[/green]' if groq_ok else '[red]✗[/red]'} Groq: "
            f"{'Configured' if groq_ok else 'Missing API key'}"
        )
        console.print(
            f"{'[green]✓[/green]' if gemini_ok else '[red]✗[/red]'} Gemini: "
            f"{'Configured' if gemini_ok else 'Missing API key'}"
        )

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
