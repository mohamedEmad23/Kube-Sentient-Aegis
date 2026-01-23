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
from aegis.kubernetes.context import fetch_resource_context
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
    # log.info("creating_incident_workflow", checkpointer_enabled=checkpointer is not None)

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
    if checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        # log.info("workflow_compiled", checkpointing="enabled")
    else:
        graph = builder.compile()
        # log.info("workflow_compiled", checkpointing="disabled")

    return graph


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
    # log.info(
    #     "starting_incident_analysis",
    #     resource=f"{resource_type}/{resource_name}",
    #     namespace=namespace,
    # )

    # Create initial state
    state = create_initial_state(resource_type, resource_name, namespace)

    # Fetch K8sGPT analysis if not provided
    if not k8sgpt_analysis:
        analyzer = get_k8sgpt_analyzer()
        k8sgpt_result = await analyzer.analyze(resource_type, resource_name, namespace)
        state["k8sgpt_raw"] = k8sgpt_result.model_dump()
        state["k8sgpt_analysis"] = k8sgpt_result
    else:
        state["k8sgpt_raw"] = k8sgpt_analysis
        state["k8sgpt_analysis"] = K8sGPTAnalysis.model_validate(k8sgpt_analysis)

    # Enrich state with Kubernetes context for RCA prompts
    k8s_context = await fetch_resource_context(resource_type, resource_name, namespace)
    state["kubectl_logs"] = k8s_context.logs or "No logs available"
    state["kubectl_describe"] = k8s_context.describe or "No describe output"
    state["kubectl_events"] = k8s_context.events or "No recent events"

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
