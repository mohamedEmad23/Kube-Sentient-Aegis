<<<<<<< HEAD
"""LangGraph workflow orchestration for AEGIS incident analysis.

Defines the complete multi-agent workflow using LangGraph's StateGraph:
- RCA Agent → Solution Agent → Verifier Agent
- Command-based dynamic routing
- Checkpointing support for human-in-the-loop
- Async execution with proper error handling
"""

from typing import TYPE_CHECKING, Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph

from aegis.agent.agents import rca_agent, solution_agent, verifier_agent
from aegis.agent.analyzer import get_k8sgpt_analyzer
from aegis.agent.state import IncidentState, K8sGPTAnalysis, create_initial_state
from aegis.observability._logging import get_logger


if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


log = get_logger(__name__)


def create_incident_workflow(
    checkpointer: InMemorySaver | None = None,
) -> "CompiledStateGraph[IncidentState]":
    """Create the incident analysis workflow graph.

    Args:
        checkpointer: Optional checkpointer for persistence and human-in-the-loop

    Returns:
        Compiled StateGraph ready for invocation

    Workflow:
        START → rca_agent → solution_agent → verifier_agent → END

        Dynamic routing via Command:
        - RCA: confidence < 0.7 → END
        - Solution: low-risk → END, high-risk → verifier
        - Verifier: always → END

    Example:
        >>> from aegis.agent.state import create_initial_state
        >>>
        >>> workflow = create_incident_workflow()
        >>> state = create_initial_state("Pod", "nginx-crashloop")
        >>>
        >>> # Run workflow
        >>> result = workflow.invoke(state)
        >>> print(result["rca_result"].root_cause)
        >>> print(result["fix_proposal"].description)
        >>> print(result["verification_plan"].verification_type)
    """
    # Initialize StateGraph with IncidentState schema
    builder = StateGraph(IncidentState)

    # Add agent nodes
    # Each agent is an async function that returns Command for routing
    builder.add_node("rca_agent", rca_agent)
    builder.add_node("solution_agent", solution_agent)
    builder.add_node("verifier_agent", verifier_agent)

    # Define workflow edges
    # START always goes to RCA agent
    builder.add_edge(START, "rca_agent")

    # Agents use Command to route dynamically:
    # - rca_agent decides: solution_agent or END
    # - solution_agent decides: verifier_agent or END
    # - verifier_agent always: END

    # Compile graph with optional checkpointing
    return builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()


# ============================================================================
# Pre-built workflow instances
# ============================================================================

# Default workflow without checkpointing
incident_workflow = create_incident_workflow()

# Workflow with in-memory checkpointing for development
incident_workflow_with_checkpoint = create_incident_workflow(checkpointer=InMemorySaver())


async def analyze_incident(
    resource_type: str,
    resource_name: str,
    namespace: str = "default",
    k8sgpt_analysis: dict[str, Any] | None = None,
    use_checkpoint: bool = False,
    thread_id: str | None = None,
    use_mock: bool = False,
) -> IncidentState:
    """High-level function to analyze an incident through the complete workflow.

    Args:
        resource_type: Type of Kubernetes resource (Pod, Deployment, etc.)
        resource_name: Name of the resource
        namespace: Kubernetes namespace
        k8sgpt_analysis: Pre-fetched K8sGPT analysis (optional)
        use_checkpoint: Use checkpointed workflow for resumable execution
        thread_id: Thread ID for checkpointing (required if use_checkpoint=True)

    Returns:
        IncidentState: Final state with RCA, fix proposal, and verification plan

    Example:
        >>> result = await analyze_incident(
        ...     resource_type="Pod",
        ...     resource_name="nginx-crashloop",
        ...     namespace="production"
        ... )
        >>> print(result["rca_result"].root_cause)
        >>> print(result["fix_proposal"].commands)
    """
    # Create initial state
    state = create_initial_state(resource_type, resource_name, namespace)

    # Fetch K8sGPT analysis if not provided
    if not k8sgpt_analysis:
        analyzer = get_k8sgpt_analyzer()
        k8sgpt_result = await analyzer.analyze(
            resource_type, resource_name, namespace, use_mock=use_mock
        )
        state["k8sgpt_raw"] = k8sgpt_result.model_dump()
        state["k8sgpt_analysis"] = k8sgpt_result
        # Store mock kubectl data if available (for development)
        mock_kubectl = k8sgpt_result.model_dump().get("_mock_kubectl", {})
        if mock_kubectl:
            state["kubectl_logs"] = mock_kubectl.get("logs", "")
            state["kubectl_describe"] = mock_kubectl.get("describe", "")
            state["kubectl_events"] = mock_kubectl.get("events", "")
    else:
        state["k8sgpt_raw"] = k8sgpt_analysis
        state["k8sgpt_analysis"] = K8sGPTAnalysis.model_validate(k8sgpt_analysis)

    # Exit early if K8sGPT found no problems
    k8sgpt_data = state["k8sgpt_analysis"]
    if k8sgpt_data and k8sgpt_data.problems == 0:
        log.info(
            "no_problems_detected",
            resource=f"{resource_type}/{resource_name}",
            namespace=namespace,
        )
        # Not an error - resource is healthy
        state["no_problems"] = True
        return state

    # Select workflow
    if use_checkpoint:
        if not thread_id:
            msg = "thread_id required when use_checkpoint=True"
            raise ValueError(msg)

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        raw_result = await incident_workflow_with_checkpoint.ainvoke(state, config=config)
        result = cast(IncidentState, raw_result)
    else:
        raw_result = await incident_workflow.ainvoke(state)
        result = cast(IncidentState, raw_result)

    log.info(
        "incident_analysis_completed",
        resource=f"{resource_type}/{resource_name}",
        current_agent=result["current_agent"].value,
        error=result.get("error"),
    )

    return result


__all__ = [
    "analyze_incident",
    "create_incident_workflow",
    "incident_workflow",
    "incident_workflow_with_checkpoint",
]
=======
"""LangGraph workflow orchestration for AEGIS incident analysis.

Defines the complete multi-agent workflow using LangGraph's StateGraph:
- RCA Agent → Solution Agent → Verifier Agent
- Command-based dynamic routing
- Checkpointing support for human-in-the-loop
- Async execution with proper error handling
"""

import asyncio
import shutil
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph

from aegis.agent.agents import rca_agent, solution_agent, verifier_agent
from aegis.agent.analyzer import get_k8sgpt_analyzer
from aegis.agent.state import IncidentState, K8sGPTAnalysis, create_initial_state
from aegis.config.settings import settings
from aegis.observability._logging import get_logger


if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


log = get_logger(__name__)

_LOKI_VALUE_FIELDS = 2


async def _run_kubectl(args: list[str], timeout_seconds: float) -> str | None:
    """Run kubectl command and return stdout if successful."""
    if not shutil.which("kubectl"):
        return None

    process = await asyncio.create_subprocess_exec(
        "kubectl",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            stdout, _stderr = await process.communicate()
    except TimeoutError:
        process.kill()
        await process.wait()
        return None

    if process.returncode != 0:
        return None

    return stdout.decode().strip() if stdout else None


def _loki_base_url() -> str | None:
    """Normalize Loki base URL for query endpoints."""
    loki_url = settings.observability.loki_url
    if not loki_url:
        return None
    base = loki_url.rstrip("/")
    for suffix in ("/loki/api/v1/push", "/loki/api/v1/query", "/loki/api/v1/query_range"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.rstrip("/")


def _build_loki_query(resource_type: str, resource_name: str, namespace: str) -> str:
    """Build a Loki label query for the resource."""
    kind = resource_type.lower()
    if kind == "pod":
        return f'{{namespace="{namespace}", pod="{resource_name}"}}'
    return f'{{namespace="{namespace}", pod=~"{resource_name}-.*"}}'


async def _fetch_loki_logs(
    resource_type: str,
    resource_name: str,
    namespace: str,
    timeout_seconds: float,
) -> str | None:
    """Fetch logs from Loki if configured."""
    if not settings.observability.loki_enabled:
        return None
    base_url = _loki_base_url()
    if not base_url:
        return None

    end = datetime.now(UTC)
    start = end - timedelta(minutes=15)
    query = _build_loki_query(resource_type, resource_name, namespace)
    params = {
        "query": query,
        "limit": "200",
        "direction": "backward",
        "start": str(int(start.timestamp() * 1_000_000_000)),
        "end": str(int(end.timestamp() * 1_000_000_000)),
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.get(f"{base_url}/loki/api/v1/query_range", params=params)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.debug("loki_query_failed", error=str(exc))
        return None

    results = payload.get("data", {}).get("result", [])
    if not results:
        return None

    entries = [
        (value[0], value[1])
        for stream in results
        for value in stream.get("values", [])
        if isinstance(value, list) and len(value) >= _LOKI_VALUE_FIELDS
    ]
    if not entries:
        return None
    entries.sort(key=lambda item: item[0])
    return "\n".join(line for _, line in entries[-200:])


async def _fetch_kubectl_context(
    resource_type: str,
    resource_name: str,
    namespace: str,
    timeout_seconds: float,
) -> dict[str, str | None]:
    """Fetch kubectl logs/describe/events to enrich RCA/solution prompts."""
    describe = await _run_kubectl(
        ["-n", namespace, "describe", resource_type, resource_name],
        timeout_seconds=timeout_seconds,
    )

    events = await _run_kubectl(
        [
            "-n",
            namespace,
            "get",
            "events",
            "--field-selector",
            f"involvedObject.name={resource_name}",
            "--sort-by=.lastTimestamp",
        ],
        timeout_seconds=timeout_seconds,
    )

    logs = None
    pod_name = None

    if resource_type.lower() == "pod":
        pod_name = resource_name
    else:
        selector_logs = await _run_kubectl(
            ["-n", namespace, "get", "pods", "-l", f"app={resource_name}", "-o", "name"],
            timeout_seconds=timeout_seconds,
        )
        if selector_logs:
            pod_name = selector_logs.splitlines()[0].split("/")[-1]
        else:
            all_pods = await _run_kubectl(
                ["-n", namespace, "get", "pods", "-o", "name"],
                timeout_seconds=timeout_seconds,
            )
            if all_pods:
                for item in all_pods.splitlines():
                    name = item.split("/")[-1]
                    if name.startswith(f"{resource_name}-"):
                        pod_name = name
                        break

    if pod_name:
        logs = await _run_kubectl(
            ["-n", namespace, "logs", pod_name, "--tail=200"],
            timeout_seconds=timeout_seconds,
        )

    loki_logs = await _fetch_loki_logs(
        resource_type=resource_type,
        resource_name=resource_name,
        namespace=namespace,
        timeout_seconds=timeout_seconds,
    )
    if loki_logs:
        logs = loki_logs

    return {"logs": logs, "describe": describe, "events": events}


def create_incident_workflow(
    checkpointer: InMemorySaver | None = None,
) -> "CompiledStateGraph[IncidentState, None, IncidentState, IncidentState]":
    """Create the incident analysis workflow graph.

    Args:
        checkpointer: Optional checkpointer for persistence and human-in-the-loop

    Returns:
        Compiled StateGraph ready for invocation

    Workflow:
        START → rca_agent → solution_agent → verifier_agent → END

        Dynamic routing via Command:
        - RCA: confidence < 0.7 → END
        - Solution: low-risk → END, high-risk → verifier
        - Verifier: always → END

    Example:
        >>> from aegis.agent.state import create_initial_state
        >>>
        >>> workflow = create_incident_workflow()
        >>> state = create_initial_state("Pod", "nginx-crashloop")
        >>>
        >>> # Run workflow
        >>> result = workflow.invoke(state)
        >>> print(result["rca_result"].root_cause)
        >>> print(result["fix_proposal"].description)
        >>> print(result["verification_plan"].verification_type)
    """
    # Initialize StateGraph with IncidentState schema
    builder = StateGraph(IncidentState)

    # Add agent nodes
    # Each agent is an async function that returns Command for routing
    builder.add_node("rca_agent", rca_agent)
    builder.add_node("solution_agent", solution_agent)
    builder.add_node("verifier_agent", verifier_agent)

    # Define workflow edges
    # START always goes to RCA agent
    builder.add_edge(START, "rca_agent")

    # Agents use Command to route dynamically:
    # - rca_agent decides: solution_agent or END
    # - solution_agent decides: verifier_agent or END
    # - verifier_agent always: END

    # Compile graph with optional checkpointing
    compiled = builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()
    return cast("CompiledStateGraph[IncidentState, None, IncidentState, IncidentState]", compiled)


# ============================================================================
# Pre-built workflow instances
# ============================================================================

# Default workflow without checkpointing
incident_workflow = create_incident_workflow()

# Workflow with in-memory checkpointing for development
incident_workflow_with_checkpoint = create_incident_workflow(checkpointer=InMemorySaver())


async def analyze_incident(
    resource_type: str,
    resource_name: str,
    namespace: str = "default",
    k8sgpt_analysis: dict[str, Any] | None = None,
    use_checkpoint: bool = False,
    thread_id: str | None = None,
    use_mock: bool = False,
) -> IncidentState:
    """High-level function to analyze an incident through the complete workflow.

    Args:
        resource_type: Type of Kubernetes resource (Pod, Deployment, etc.)
        resource_name: Name of the resource
        namespace: Kubernetes namespace
        k8sgpt_analysis: Pre-fetched K8sGPT analysis (optional)
        use_checkpoint: Use checkpointed workflow for resumable execution
        thread_id: Thread ID for checkpointing (required if use_checkpoint=True)

    Returns:
        IncidentState: Final state with RCA, fix proposal, and verification plan

    Example:
        >>> result = await analyze_incident(
        ...     resource_type="Pod",
        ...     resource_name="nginx-crashloop",
        ...     namespace="production"
        ... )
        >>> print(result["rca_result"].root_cause)
        >>> print(result["fix_proposal"].commands)
    """
    # Create initial state
    state = create_initial_state(resource_type, resource_name, namespace)

    # Fetch K8sGPT analysis if not provided
    if not k8sgpt_analysis:
        analyzer = get_k8sgpt_analyzer()
        k8sgpt_result = await analyzer.analyze(
            resource_type, resource_name, namespace, use_mock=use_mock
        )
        state["k8sgpt_raw"] = k8sgpt_result.model_dump()
        state["k8sgpt_analysis"] = k8sgpt_result
        # Store mock kubectl data if available (for development)
        mock_kubectl = k8sgpt_result.model_dump().get("_mock_kubectl", {})
        if mock_kubectl:
            state["kubectl_logs"] = mock_kubectl.get("logs", "")
            state["kubectl_describe"] = mock_kubectl.get("describe", "")
            state["kubectl_events"] = mock_kubectl.get("events", "")
    else:
        state["k8sgpt_raw"] = k8sgpt_analysis
        state["k8sgpt_analysis"] = K8sGPTAnalysis.model_validate(k8sgpt_analysis)

    # Exit early if K8sGPT found no problems
    k8sgpt_data = state["k8sgpt_analysis"]
    if k8sgpt_data and k8sgpt_data.problems == 0:
        log.info(
            "no_problems_detected",
            resource=f"{resource_type}/{resource_name}",
            namespace=namespace,
        )
        # Not an error - resource is healthy
        state["no_problems"] = True
        return state

    # Enrich context with kubectl output (real cluster only)
    if not use_mock:
        context = await _fetch_kubectl_context(
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
            timeout_seconds=settings.kubernetes.api_timeout,
        )
        state["kubectl_logs"] = context.get("logs")
        state["kubectl_describe"] = context.get("describe")
        state["kubectl_events"] = context.get("events")

    # Select workflow
    if use_checkpoint:
        if not thread_id:
            msg = "thread_id required when use_checkpoint=True"
            raise ValueError(msg)

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        raw_result = await incident_workflow_with_checkpoint.ainvoke(state, config=config)
        result = cast(IncidentState, raw_result)
    else:
        raw_result = await incident_workflow.ainvoke(state)
        result = cast(IncidentState, raw_result)

    log.info(
        "incident_analysis_completed",
        resource=f"{resource_type}/{resource_name}",
        current_agent=result["current_agent"].value,
        error=result.get("error"),
    )

    return result


__all__ = [
    "analyze_incident",
    "create_incident_workflow",
    "incident_workflow",
    "incident_workflow_with_checkpoint",
]
>>>>>>> af4493e9664b4940d61757df392615e5aaeb514e
