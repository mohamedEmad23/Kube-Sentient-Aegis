# AEGIS CLI & LLM Integration Architecture
## Comprehensive Deep-Dive: K8sGPT + Ollama + Multi-Agent Design

**Date:** January 2026
**Status:** Technical Design Document
**Target:** CLI Implementation Phase

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Architecture Decision: Single vs Multi-Agent](#2-architecture-decision-single-vs-multi-agent)
3. [K8sGPT Integration Patterns](#3-k8sgpt-integration-patterns)
4. [CLI UX Design: Output Formats](#4-cli-ux-design-output-formats)
5. [Complete Implementation Guide](#5-complete-implementation-guide)
6. [Recommended Architecture](#6-recommended-architecture)
7. [Testing Strategy](#7-testing-strategy)

---

## 1. Executive Summary

### Your Questions Answered

| Question | Answer |
|----------|--------|
| **Single agent vs 3 separate agents?** | **Hybrid**: Single LangGraph workflow with 3 specialized sub-agents |
| **How does Ollama wrap K8sGPT?** | K8sGPT runs **first** (subprocess), output fed to Ollama for LLM analysis |
| **RCA report format?** | **Terminal output** + optional Markdown export, **NOT chat-based** for CLI |
| **Solution format?** | **Rich terminal tables** + optional Markdown with execution steps |

### Key Architectural Decisions

✅ **Recommended**: Hybrid multi-agent architecture
✅ **K8sGPT role**: Diagnostic data provider (pre-processing)
✅ **Ollama role**: Analysis, RCA generation, solution synthesis
✅ **CLI pattern**: Task-oriented commands (like `git`), **not** conversational
✅ **Output**: Rich terminal (Typer + Rich library) with Markdown export option

---

## 2. Architecture Decision: Single vs Multi-Agent

### 2.1 Option A: Single Monolithic Agent ❌ Not Recommended

```python
# ANTI-PATTERN: Single agent doing everything
@app.command()
def analyze(pod_name: str):
    """Single agent handles everything."""
    result = single_agent.invoke({
        "task": "analyze",
        "resource": pod_name,
        "steps": [
            "run k8sgpt",
            "perform RCA",
            "generate solution",
            "verify fix"
        ]
    })
```

**Problems:**
- ❌ Poor separation of concerns
- ❌ Difficult to debug specific failure points
- ❌ Hard to swap models per task
- ❌ No parallelization potential
- ❌ Impossible to version control prompt changes independently

### 2.2 Option B: Fully Independent 3 Agents ❌ Not Recommended

```python
# ANTI-PATTERN: Disconnected agents
@app.command()
def analyze(pod_name: str):
    # Agent 1: RCA
    rca = rca_agent.invoke({"pod": pod_name})

    # Agent 2: Solution (no context from RCA!)
    solution = solution_agent.invoke({"pod": pod_name})  # ❌ Starts from scratch!

    # Agent 3: Verification
    verified = verifier_agent.invoke({"solution": solution})
```

**Problems:**
- ❌ Agents don't share state/context
- ❌ Redundant K8sGPT calls
- ❌ No workflow orchestration
- ❌ Can't handle complex dependencies

### 2.3 Option C: LangGraph Multi-Agent Workflow ✅ RECOMMENDED

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from typing import Literal

class IncidentState(TypedDict):
    """Shared state across all agents."""
    resource_name: str
    resource_type: str
    k8sgpt_analysis: dict
    rca_report: str
    proposed_solution: dict
    verification_results: dict
    confidence_score: float

def rca_agent(state: IncidentState) -> Command[Literal["solution_agent", END]]:
    """Agent 1: Root Cause Analysis using phi3:mini"""
    k8sgpt_data = state["k8sgpt_analysis"]

    rca_prompt = f"""
    Analyze this Kubernetes issue and provide Root Cause Analysis:

    Resource: {state["resource_name"]}
    K8sGPT Findings: {k8sgpt_data}

    Provide:
    1. Root cause identification
    2. Timeline of events
    3. Impact assessment
    4. Related resources affected
    """

    response = ollama_client.chat(model="phi3:mini", messages=[...])

    return Command(
        goto="solution_agent",
        update={"rca_report": response["message"]["content"]}
    )

def solution_agent(state: IncidentState) -> Command[Literal["verification_agent", END]]:
    """Agent 2: Solution Proposal using deepseek-coder"""
    rca = state["rca_report"]

    solution_prompt = f"""
    Based on this RCA, generate a fix:

    RCA: {rca}

    Provide:
    1. Kubernetes manifests to apply
    2. Commands to execute
    3. Rollback plan
    4. Expected outcome

    Output as JSON with keys: manifests, commands, rollback, expected_state
    """

    response = ollama_client.chat(model="deepseek-coder:6.7b", messages=[...])
    solution = json.loads(response["message"]["content"])

    return Command(
        goto="verification_agent" if state.get("auto_verify") else END,
        update={"proposed_solution": solution}
    )

def verification_agent(state: IncidentState) -> Command[Literal[END]]:
    """Agent 3: Verification planning using llama3.1"""
    solution = state["proposed_solution"]

    verification_prompt = f"""
    Create a verification plan for this solution:

    Solution: {solution}

    Provide:
    1. Pre-deployment checks
    2. Health check commands
    3. Rollback triggers
    4. Success criteria
    """

    response = ollama_client.chat(model="llama3.1:8b", messages=[...])

    return Command(
        goto=END,
        update={
            "verification_results": parse_verification_plan(response),
            "confidence_score": calculate_confidence(state)
        }
    )

# Build the workflow graph
builder = StateGraph(IncidentState)
builder.add_node("rca_agent", rca_agent)
builder.add_node("solution_agent", solution_agent)
builder.add_node("verification_agent", verification_agent)

builder.add_edge(START, "rca_agent")
# Agents use Command to route dynamically

workflow = builder.compile()
```

**Benefits:**
- ✅ Shared state between agents
- ✅ Clear workflow orchestration
- ✅ Can swap models per agent
- ✅ Parallel execution potential (for independent tasks)
- ✅ Built-in checkpointing and resumption
- ✅ Easy to add human-in-the-loop approval

---

## 3. K8sGPT Integration Patterns

### 3.1 How K8sGPT Fits In

**K8sGPT is NOT an agent** - it's a **diagnostic data provider**. Think of it like running `kubectl describe` but with AI-powered problem detection.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AEGIS CLI EXECUTION FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User runs: aegis analyze pod/nginx-crashloop                   │
│                      │                                           │
│                      ▼                                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. K8sGPT PRE-PROCESSING (subprocess)                    │   │
│  │     $ k8sgpt analyze --explain --filter=Pod               │   │
│  │       --output=json --backend=localai                     │   │
│  │                                                           │   │
│  │  Output:                                                  │   │
│  │  {                                                        │   │
│  │    "problems": 1,                                         │   │
│  │    "results": [{                                          │   │
│  │      "kind": "Pod",                                       │   │
│  │      "name": "nginx-crashloop",                           │   │
│  │      "error": [{                                          │   │
│  │        "Text": "Back-off restarting failed container",    │   │
│  │        "KubernetesDoc": "Liveness probe failing..."       │   │
│  │      }]                                                   │   │
│  │    }]                                                     │   │
│  │  }                                                        │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                            │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  2. AEGIS AGENT WORKFLOW (LangGraph)                      │   │
│  │                                                           │   │
│  │  RCA Agent (phi3:mini)                                    │   │
│  │  ├─ Input: K8sGPT JSON + kubectl logs                     │   │
│  │  ├─ Process: Analyze error patterns                       │   │
│  │  └─ Output: RCA Report                                    │   │
│  │          │                                                │   │
│  │          ▼                                                │   │
│  │  Solution Agent (deepseek-coder)                          │   │
│  │  ├─ Input: RCA Report                                     │   │
│  │  ├─ Process: Generate YAML manifests, commands            │   │
│  │  └─ Output: Fix Proposal                                  │   │
│  │          │                                                │   │
│  │          ▼                                                │   │
│  │  Verification Agent (llama3.1)                            │   │
│  │  ├─ Input: Fix Proposal                                   │   │
│  │  ├─ Process: Plan verification steps                      │   │
│  │  └─ Output: Verification Plan                             │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                            │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  3. CLI OUTPUT (Typer + Rich)                             │   │
│  │                                                           │   │
│  │  • RCA Report (styled terminal)                           │   │
│  │  • Solution steps (interactive prompts)                   │   │
│  │  • Optional: Export to Markdown                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 K8sGPT Wrapper Implementation

```python
# src/aegis/agent/analyzer.py
import subprocess
import json
from typing import Dict, Optional
from aegis.config.settings import settings

class K8sGPTAnalyzer:
    """Wrapper for K8sGPT CLI tool."""

    def __init__(self, backend: str = "ollama"):
        self.backend = backend
        self.base_cmd = ["k8sgpt", "analyze"]

    def analyze_resource(
        self,
        resource_type: str,
        resource_name: Optional[str] = None,
        namespace: str = "default",
        explain: bool = True
    ) -> Dict:
        """
        Run K8sGPT analysis on a specific resource.

        Args:
            resource_type: K8s resource type (Pod, Deployment, Service, etc.)
            resource_name: Specific resource name (optional)
            namespace: K8s namespace
            explain: Include AI explanations

        Returns:
            Parsed JSON output from K8sGPT
        """
        cmd = self.base_cmd + [
            f"--filter={resource_type}",
            f"--namespace={namespace}",
            "--output=json",
            f"--backend={self.backend}"
        ]

        if explain:
            cmd.append("--explain")

        # Configure K8sGPT to use local Ollama
        env = os.environ.copy()
        env["K8SGPT_BACKEND"] = self.backend
        env["K8SGPT_MODEL"] = settings.ollama.model
        env["K8SGPT_BASE_URL"] = settings.ollama.base_url

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.kubernetes.api_timeout,
                env=env,
                check=True
            )

            analysis = json.loads(result.stdout)

            # Filter to specific resource if provided
            if resource_name:
                analysis["results"] = [
                    r for r in analysis["results"]
                    if r["name"] == resource_name
                ]

            return analysis

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"K8sGPT analysis timed out after {settings.kubernetes.api_timeout}s")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"K8sGPT failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse K8sGPT output: {e}")

    def analyze_cluster_wide(self, filters: list[str]) -> Dict:
        """Run K8sGPT analysis across multiple resource types."""
        filter_str = ",".join(filters)
        cmd = self.base_cmd + [
            f"--filter={filter_str}",
            "--output=json",
            "--explain",
            f"--backend={self.backend}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
```

### 3.3 K8sGPT Configuration for Ollama Backend

```bash
# Configure K8sGPT to use your local Ollama instance
k8sgpt auth add --backend localai --model phi3:mini --baseurl http://localhost:11434/v1

# Test the configuration
k8sgpt analyze --filter=Pod --explain --backend localai
```

---

## 4. CLI UX Design: Output Formats

### 4.1 Anti-Pattern: Chat-Based CLI ❌

```bash
# DON'T DO THIS - Chat interfaces don't belong in CLIs
$ aegis chat
> What's wrong with my pod?
Analyzing... Let me check that for you!
> Can you fix it?
Sure! I'll generate a solution...
```

**Why this is bad:**
- ❌ Can't script/automate
- ❌ Slow for experienced users
- ❌ No clear exit criteria
- ❌ Difficult to test
- ❌ Poor CI/CD integration

### 4.2 Recommended: Task-Oriented Commands ✅

```bash
# Git-style subcommands
aegis analyze pod/nginx-crashloop
aegis diagnose deployment/api-server --namespace prod
aegis fix incident/inc-2024-001
aegis verify shadow/shadow-env-123
aegis report --format markdown --output report.md
```

### 4.3 Output Format: Rich Terminal with Markdown Export

```python
# src/aegis/cli.py
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from pathlib import Path

console = Console()
app = typer.Typer(rich_markup_mode="rich")

@app.command()
def analyze(
    resource: str = typer.Argument(..., help="Resource in format type/name"),
    namespace: str = typer.Option("default", help="Kubernetes namespace"),
    explain: bool = typer.Option(True, help="Include AI-powered explanations"),
    export: Optional[Path] = typer.Option(None, "--export", help="Export to Markdown file"),
    format: str = typer.Option("terminal", help="Output format: terminal, json, markdown")
):
    """
    Analyze a Kubernetes resource for issues.

    Example:
        aegis analyze pod/nginx-crashloop
        aegis analyze deployment/api-server --namespace prod --export report.md
    """
    console.print(Panel.fit(
        f"🔍 Analyzing [cyan]{resource}[/cyan] in namespace [yellow]{namespace}[/yellow]",
        title="AEGIS Analysis"
    ))

    # Step 1: Run K8sGPT
    with console.status("[bold green]Running K8sGPT diagnostic..."):
        resource_type, resource_name = resource.split("/")
        k8sgpt_data = k8sgpt_analyzer.analyze_resource(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            explain=explain
        )

    # Step 2: Run AEGIS agent workflow
    with console.status("[bold green]Running AI analysis workflow..."):
        result = workflow.invoke({
            "resource_name": resource_name,
            "resource_type": resource_type,
            "k8sgpt_analysis": k8sgpt_data,
            "auto_verify": False
        })

    # Step 3: Display results
    if format == "terminal":
        display_terminal_output(result)
    elif format == "json":
        console.print_json(data=result)
    elif format == "markdown":
        md_content = generate_markdown_report(result)
        console.print(Markdown(md_content))

    # Step 4: Export if requested
    if export:
        md_content = generate_markdown_report(result)
        export.write_text(md_content)
        console.print(f"✅ Report exported to [green]{export}[/green]")

def display_terminal_output(result: dict):
    """Display rich terminal output with tables and panels."""

    # RCA Section
    console.print("\n")
    console.print(Panel(
        result["rca_report"],
        title="[bold red]Root Cause Analysis[/bold red]",
        border_style="red"
    ))

    # Solution Section
    console.print("\n")
    solution = result["proposed_solution"]

    # Create table for solution steps
    table = Table(title="Proposed Solution", show_header=True, header_style="bold cyan")
    table.add_column("Step", style="dim", width=6)
    table.add_column("Action", width=40)
    table.add_column("Command", style="green")

    for idx, step in enumerate(solution.get("commands", []), 1):
        table.add_row(str(idx), step["description"], f"`{step['command']}`")

    console.print(table)

    # Confidence Score
    confidence = result.get("confidence_score", 0)
    confidence_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.5 else "red"
    console.print(f"\n[bold]Confidence Score:[/bold] [{confidence_color}]{confidence:.1%}[/{confidence_color}]")

    # Next steps prompt
    if typer.confirm("\n🚀 Apply this solution to a shadow environment?"):
        shadow_name = f"shadow-{resource_name}-{int(time.time())}"
        console.print(f"Creating shadow environment: [cyan]{shadow_name}[/cyan]")
        # Trigger shadow verification workflow

def generate_markdown_report(result: dict) -> str:
    """Generate Markdown report from analysis results."""
    template = f"""
# AEGIS Analysis Report

**Resource:** {result['resource_name']}
**Type:** {result['resource_type']}
**Timestamp:** {datetime.now().isoformat()}
**Confidence:** {result['confidence_score']:.1%}

---

## Root Cause Analysis

{result['rca_report']}

---

## Proposed Solution

### Kubernetes Manifests

```yaml
{yaml.dump(result['proposed_solution'].get('manifests', {}))}
```

### Execution Steps

{generate_steps_markdown(result['proposed_solution']['commands'])}

### Rollback Plan

{result['proposed_solution'].get('rollback', 'N/A')}

---

## Verification Plan

{result.get('verification_results', {}).get('plan', 'Not yet verified')}

---

*Generated by AEGIS v{__version__}*
"""
    return template

@app.command()
def fix(
    incident_id: str = typer.Argument(..., help="Incident ID to fix"),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry run or apply fix"),
    shadow: bool = typer.Option(True, help="Verify in shadow environment first")
):
    """
    Apply a fix to a previously analyzed incident.

    Example:
        aegis fix incident/inc-2024-001 --dry-run
        aegis fix incident/inc-2024-001 --apply --no-shadow  # Dangerous!
    """
    if not dry_run and not shadow:
        if not typer.confirm("⚠️  Applying fix directly to production without shadow verification. Continue?"):
            raise typer.Abort()

    # Implementation...
```

### 4.4 Example Terminal Output

```
┌────────────────────────────────────────────────────────┐
│              AEGIS Analysis                             │
│  🔍 Analyzing pod/nginx-crashloop in namespace default │
└────────────────────────────────────────────────────────┘

⠹ Running K8sGPT diagnostic...
✓ K8sGPT analysis complete (2.3s)
⠹ Running AI analysis workflow...
  ├─ RCA Agent (phi3:mini): Analyzing error patterns...
  ├─ Solution Agent (deepseek-coder): Generating fix...
  └─ Verification Agent (llama3.1): Planning verification...
✓ Analysis complete (8.7s)

╭─ Root Cause Analysis ──────────────────────────────────╮
│                                                        │
│ Issue: CrashLoopBackOff                                │
│ Root Cause: Missing environment variable DATABASE_URL  │
│                                                        │
│ Timeline:                                              │
│  • 14:32:15 - Pod started                              │
│  • 14:32:18 - Container crashed (exit code 1)          │
│  • 14:32:25 - Kubernetes restarted pod                 │
│  • 14:32:28 - Container crashed again                  │
│                                                        │
│ Impact: Service unavailable, 0/3 replicas healthy      │
│                                                        │
╰────────────────────────────────────────────────────────╯

╭─ Proposed Solution ────────────────────────────────────╮
│                                                        │
│  Step │ Action                │ Command                │
│  ─────┼───────────────────────┼────────────────────────│
│   1   │ Add env var to spec   │ kubectl patch deploy...│
│   2   │ Wait for rollout      │ kubectl rollout status │
│   3   │ Verify pods healthy   │ kubectl get pods       │
│                                                        │
╰────────────────────────────────────────────────────────╯

Confidence Score: 92%

🚀 Apply this solution to a shadow environment? [y/N]: _
```

---

## 5. Complete Implementation Guide

### 5.1 Project Structure

```
src/aegis/
├── cli.py                      # Main CLI entry point
├── agent/
│   ├── __init__.py
│   ├── graph.py                # LangGraph workflow definition
│   ├── agents/
│   │   ├── rca_agent.py        # Root Cause Analysis agent
│   │   ├── solution_agent.py   # Solution generation agent
│   │   └── verifier_agent.py   # Verification agent
│   ├── llm/
│   │   ├── ollama.py           # Ollama client
│   │   └── prompts/
│   │       ├── rca.py          # RCA prompts
│   │       ├── solution.py     # Solution generation prompts
│   │       └── verification.py # Verification prompts
│   └── analyzer.py             # K8sGPT wrapper
├── shadow/
│   ├── vcluster.py             # Shadow environment management
│   └── verification.py         # Shadow verification logic
└── utils/
    ├── formatting.py           # Rich output formatters
    └── export.py               # Markdown export utilities
```

### 5.2 Full CLI Implementation

```python
# src/aegis/cli.py
"""AEGIS Command Line Interface."""
import typer
from rich.console import Console
from typing import Optional
from pathlib import Path

from aegis.agent.graph import create_analysis_workflow
from aegis.agent.analyzer import K8sGPTAnalyzer
from aegis.config.settings import settings
from aegis.utils.formatting import display_terminal_output, generate_markdown_report

console = Console()
app = typer.Typer(
    name="aegis",
    help="Autonomous SRE Agent with Shadow Verification",
    rich_markup_mode="rich",
    no_args_is_help=True
)

# Initialize components
k8sgpt = K8sGPTAnalyzer(backend="localai")
workflow = create_analysis_workflow()

@app.command()
def analyze(
    resource: str = typer.Argument(
        ...,
        help="Resource in format [cyan]type/name[/cyan] (e.g., pod/nginx, deployment/api)"
    ),
    namespace: str = typer.Option(
        "default",
        "--namespace", "-n",
        help="Kubernetes namespace"
    ),
    export: Optional[Path] = typer.Option(
        None,
        "--export", "-o",
        help="Export report to Markdown file"
    ),
    auto_fix: bool = typer.Option(
        False,
        "--auto-fix",
        help="Automatically apply fix after shadow verification"
    )
):
    """
    Analyze a Kubernetes resource and generate fix recommendations.

    Examples:

      [green]# Basic analysis[/green]
      aegis analyze pod/nginx-crashloop

      [green]# Export to Markdown[/green]
      aegis analyze deployment/api --namespace prod --export report.md

      [green]# Automatic fix with shadow verification[/green]
      aegis analyze pod/nginx --auto-fix
    """
    try:
        resource_type, resource_name = resource.split("/")
    except ValueError:
        console.print("[red]Error:[/red] Resource must be in format type/name")
        raise typer.Exit(1)

    # Step 1: K8sGPT Analysis
    console.print(f"\n🔍 Analyzing [cyan]{resource}[/cyan]...\n")
    with console.status("[bold green]Running K8sGPT diagnostic..."):
        k8sgpt_data = k8sgpt.analyze_resource(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace
        )

    if k8sgpt_data["problems"] == 0:
        console.print("[green]✓[/green] No issues detected!")
        raise typer.Exit(0)

    # Step 2: AEGIS Agent Workflow
    with console.status("[bold green]Running AI analysis workflow..."):
        result = workflow.invoke({
            "resource_name": resource_name,
            "resource_type": resource_type,
            "namespace": namespace,
            "k8sgpt_analysis": k8sgpt_data,
            "auto_verify": auto_fix
        })

    # Step 3: Display Results
    display_terminal_output(result, console)

    # Step 4: Export if requested
    if export:
        md_content = generate_markdown_report(result)
        export.write_text(md_content)
        console.print(f"\n✅ Report exported to [green]{export}[/green]")

    # Step 5: Auto-fix workflow
    if auto_fix or typer.confirm("\n🚀 Test fix in shadow environment?"):
        shadow_workflow(result)

@app.command()
def shadow(
    action: str = typer.Argument(..., help="Action: create, list, delete"),
    name: Optional[str] = typer.Argument(None, help="Shadow environment name")
):
    """
    Manage shadow verification environments.

    Examples:

      aegis shadow create --name test-env-1
      aegis shadow list
      aegis shadow delete test-env-1
    """
    # Implementation in next section...

@app.command()
def incident(
    action: str = typer.Argument(..., help="Action: list, show, create"),
    incident_id: Optional[str] = typer.Argument(None)
):
    """
    Manage incidents tracked by AEGIS.

    Examples:

      aegis incident list
      aegis incident show inc-2024-001
      aegis incident create --resource pod/nginx
    """
    # Implementation...

@app.command()
def config(
    action: str = typer.Argument(..., help="Action: show, set, validate")
):
    """
    Manage AEGIS configuration.

    Examples:

      aegis config show
      aegis config set ollama.model phi3:mini
      aegis config validate
    """
    # Implementation...

if __name__ == "__main__":
    app()
```

### 5.3 LangGraph Workflow Implementation

```python
# src/aegis/agent/graph.py
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from typing import Literal, TypedDict
from aegis.agent.agents.rca_agent import rca_agent
from aegis.agent.agents.solution_agent import solution_agent
from aegis.agent.agents.verifier_agent import verifier_agent

class IncidentState(TypedDict):
    """Shared state for the incident analysis workflow."""
    resource_name: str
    resource_type: str
    namespace: str
    k8sgpt_analysis: dict
    rca_report: str
    proposed_solution: dict
    verification_results: dict
    confidence_score: float
    auto_verify: bool

def create_analysis_workflow() -> StateGraph:
    """Create the LangGraph multi-agent workflow."""

    builder = StateGraph(IncidentState)

    # Add agent nodes
    builder.add_node("rca_agent", rca_agent)
    builder.add_node("solution_agent", solution_agent)
    builder.add_node("verification_agent", verifier_agent)

    # Define workflow edges
    builder.add_edge(START, "rca_agent")
    # Agents use Command() to route dynamically based on state

    return builder.compile()
```

```python
# src/aegis/agent/agents/rca_agent.py
from langgraph.types import Command
from typing import Literal
from aegis.agent.llm.ollama import ollama_client
from aegis.agent.llm.prompts.rca import RCA_PROMPT_TEMPLATE

def rca_agent(state: dict) -> Command[Literal["solution_agent", END]]:
    """Root Cause Analysis Agent using phi3:mini."""

    k8sgpt_findings = state["k8sgpt_analysis"]["results"]

    # Build context from K8sGPT data
    context = "\n".join([
        f"- {r['kind']}/{r['name']}: {r['error'][0]['Text']}"
        for r in k8sgpt_findings
    ])

    prompt = RCA_PROMPT_TEMPLATE.format(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
        k8sgpt_findings=context
    )

    response = ollama_client.chat(
        model="phi3:mini",
        messages=[
            {"role": "system", "content": "You are an expert SRE performing root cause analysis."},
            {"role": "user", "content": prompt}
        ]
    )

    rca_report = response["message"]["content"]

    return Command(
        goto="solution_agent",
        update={"rca_report": rca_report}
    )
```

---

## 6. Recommended Architecture

### 6.1 Final Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    AEGIS CLI Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Terminal                                                   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Typer CLI (cli.py)                                       │   │
│  │  • Rich output formatting                                 │   │
│  │  • Command routing                                        │   │
│  │  • User interaction                                       │   │
│  └───────────────────┬──────────────────────────────────────┘   │
│                      │                                           │
│           ┌──────────┴──────────┐                               │
│           ▼                     ▼                               │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  K8sGPT Analyzer │  │  LangGraph       │                    │
│  │  (subprocess)    │  │  Workflow        │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
│           │                     │                               │
│           │         ┌───────────┴───────────┬─────────────┐    │
│           │         ▼                       ▼             ▼    │
│           │   ┌─────────────┐   ┌─────────────┐   ┌─────────┐ │
│           │   │ RCA Agent   │   │ Solution    │   │ Verifier│ │
│           │   │ (phi3:mini) │   │ Agent       │   │ Agent   │ │
│           │   └──────┬──────┘   │(deepseek)   │   │(llama3) │ │
│           │          │          └──────┬──────┘   └────┬────┘ │
│           │          └─────────────────┼───────────────┘       │
│           │                            ▼                       │
│           │                   ┌──────────────────┐             │
│           └──────────────────>│  Ollama Server   │             │
│                               │  :11434          │             │
│                               │  • phi3:mini     │             │
│                               │  • deepseek-coder│             │
│                               │  • llama3.1:8b   │             │
│                               └──────────────────┘             │
│                                                                  │
│  Output: Terminal (Rich) + Optional Markdown Export             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Model Assignment Strategy

| Agent | Model | VRAM | Reasoning |
|-------|-------|------|-----------|
| **RCA Agent** | phi3:mini | ~5GB | Fast, good at structured analysis |
| **Solution Agent** | deepseek-coder:6.7b | ~8GB | Code-focused, generates YAML/scripts |
| **Verification Agent** | llama3.1:8b | ~10GB | General reasoning for verification plans |
| **K8sGPT** | phi3:mini (shared) | - | Lightweight diagnostic explanations |

**Total VRAM:** ~23GB (fits 3x 8GB GPUs with tensor parallelization)

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/unit/test_cli.py
from typer.testing import CliRunner
from aegis.cli import app

runner = CliRunner()

def test_analyze_command():
    result = runner.invoke(app, ["analyze", "pod/test-pod"])
    assert result.exit_code == 0
    assert "Root Cause Analysis" in result.output

def test_invalid_resource_format():
    result = runner.invoke(app, ["analyze", "invalid-format"])
    assert result.exit_code == 1
    assert "must be in format type/name" in result.output
```

### 7.2 Integration Tests

```python
# tests/integration/test_k8sgpt_integration.py
import pytest
from aegis.agent.analyzer import K8sGPTAnalyzer

@pytest.fixture
def analyzer():
    return K8sGPTAnalyzer(backend="localai")

def test_k8sgpt_pod_analysis(analyzer, k8s_cluster_with_failing_pod):
    result = analyzer.analyze_resource("Pod", "failing-pod", "default")
    assert result["problems"] > 0
    assert len(result["results"]) > 0
```

---

## Summary & Next Steps

### Key Decisions Made

✅ **Architecture:** Hybrid multi-agent with LangGraph
✅ **K8sGPT Role:** Pre-processing diagnostic tool
✅ **CLI Pattern:** Task-oriented (like git), not conversational
✅ **Output:** Rich terminal + Markdown export
✅ **Models:** phi3:mini (RCA), deepseek-coder (solutions), llama3.1 (verification)

### Implementation Order

1. **Week 1:** CLI skeleton + K8sGPT integration
2. **Week 2:** LangGraph workflow + RCA agent
3. **Week 3:** Solution agent + Markdown export
4. **Week 4:** Verification agent + shadow integration

### Commands to Start Building

```bash
# Install dependencies
pip install typer rich langgraph langchain-community ollama-python

# Test K8sGPT integration
k8sgpt auth add --backend localai --model phi3:mini --baseurl http://localhost:11434/v1
k8sgpt analyze --filter=Pod --explain --output=json --backend=localai

# Pull models
ollama pull phi3:mini
ollama pull deepseek-coder:6.7b
ollama pull llama3.1:8b

# Start building CLI
mkdir -p src/aegis/{cli,agent/{agents,llm/prompts},utils}
touch src/aegis/cli.py
```

Ready to start implementing! 🚀
