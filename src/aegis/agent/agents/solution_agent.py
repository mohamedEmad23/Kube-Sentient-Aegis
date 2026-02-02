<<<<<<< HEAD
"""Solution Generation Agent.

Uses tinyllama:latest for generating practical fixes with kubectl commands and YAML manifests.
Returns Command object for routing to verifier or direct application.
"""

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from aegis.agent.llm.ollama import get_ollama_client
from aegis.agent.prompts.solution_prompts import (
    SOLUTION_SYSTEM_PROMPT,
    SOLUTION_USER_PROMPT_TEMPLATE,
)
from aegis.agent.state import AgentNode, FixProposal, IncidentState
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import agent_iterations_total


log = get_logger(__name__)


def _ensure_solution_verbosity(
    state: IncidentState,
    fix_proposal: FixProposal,
) -> FixProposal:
    """Ensure verbose fix proposal fields are populated with safe fallbacks."""
    updates: dict[str, object] = {}

    if not fix_proposal.analysis_steps:
        updates["analysis_steps"] = [
            f"Mapped root cause to fix type {fix_proposal.fix_type.value}.",
            f"Prepared changes for {state['resource_type']}/{state['resource_name']} in {state['namespace']}.",
            "Included rollback steps and assessed operational risk.",
        ]

    if not fix_proposal.decision_rationale:
        updates["decision_rationale"] = (
            "Chosen because it directly addresses the root cause with minimal scope and "
            "a clear rollback path."
        )

    return fix_proposal.model_copy(update=updates) if updates else fix_proposal


def _truncate(text: str, limit: int = 200) -> str:
    """Truncate long text for logging."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


async def solution_agent(
    state: IncidentState,
) -> Command[Literal["verifier_agent", "__end__"]]:
    """Solution Generation agent.

    Generates practical fixes based on root cause analysis.
    Uses Command pattern for routing to verification or direct end.

    Args:
        state: Current incident state with RCA result

    Returns:
        Command: Update with fix proposal and routing decision

    Routing logic:
        - High-risk fix or production → verifier_agent
        - Low-risk or dev/staging → END (can apply directly)
    """
    rca = state.get("rca_result")
    log.info(
        "solution_agent_started",
        resource=f"{state['resource_type']}/{state['resource_name']}",
        root_cause=rca.root_cause[:50] if rca else "None",
    )
    log.debug(
        "solution_agent_context",
        severity=rca.severity.value if rca else "unknown",
        confidence=rca.confidence_score if rca else None,
    )

    ollama = get_ollama_client()
    rca_result = state.get("rca_result")

    if not rca_result:
        log.error("solution_agent_no_rca", message="No RCA result available")
        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": "Solution agent called without RCA result",
            },
        )

    # Build user prompt
    user_prompt = SOLUTION_USER_PROMPT_TEMPLATE.format(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
        rca_result=rca_result.model_dump_json(indent=2),
        current_state="unknown",  # TODO: Get from kubectl
        labels="{}",  # TODO: Get from kubectl
    )

    messages = [
        {"role": "system", "content": SOLUTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Call LLM with Pydantic schema validation
        fix_proposal: FixProposal = ollama.chat_with_schema(
            messages=messages,
            schema=FixProposal,
            model=settings.agent.solution_model,
            temperature=0.2,  # Very low temperature for deterministic solutions
        )
        fix_proposal = _ensure_solution_verbosity(state, fix_proposal)

        # Record metrics
        agent_iterations_total.labels(
            agent_name="solution_agent",
            status="completed",
        ).inc()

        # Update messages
        ai_message = AIMessage(
            content=f"Fix proposed: {fix_proposal.fix_type.value} - {fix_proposal.description}"
        )
        log.debug(
            "solution_agent_output",
            analysis_steps_count=len(fix_proposal.analysis_steps),
            decision_rationale=_truncate(fix_proposal.decision_rationale, 240),
            commands_count=len(fix_proposal.commands),
            manifests=list(fix_proposal.manifests.keys()),
            risks_count=len(fix_proposal.risks),
        )

        # Decision: high-risk fixes need verification
        needs_verification = (
            rca_result.severity.value in ["critical", "high"]
            or state["namespace"] == "production"
            or len(fix_proposal.risks) > 0
        )

        if needs_verification:
            return Command(
                goto="verifier_agent",
                update={
                    "fix_proposal": fix_proposal,
                    "current_agent": AgentNode.VERIFIER,
                    "messages": [ai_message],
                },
            )
        log.info(
            "solution_low_risk",
            message="Fix can be applied directly without verification",
        )
        return Command(
            goto="__end__",
            update={
                "fix_proposal": fix_proposal,
                "current_agent": AgentNode.END,
                "messages": [ai_message],
            },
        )

    except Exception as e:
        log.exception("solution_agent_error")
        agent_iterations_total.labels(agent_name="solution_agent", status="error").inc()

        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": f"Solution agent failed: {e}",
                "messages": [HumanMessage(content=f"Solution agent unexpected error: {e}")],
            },
        )


__all__ = ["solution_agent"]
=======
"""Solution Generation Agent.

Uses tinyllama:latest for generating practical fixes with kubectl commands and YAML manifests.
Returns Command object for routing to verifier or direct application.
"""

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from aegis.agent.llm.ollama import get_ollama_client
from aegis.agent.prompts.solution_prompts import (
    SOLUTION_SYSTEM_PROMPT,
    SOLUTION_USER_PROMPT_TEMPLATE,
)
from aegis.agent.state import AgentNode, FixProposal, FixType, IncidentState
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import agent_iterations_total


log = get_logger(__name__)


def _ensure_solution_verbosity(
    state: IncidentState,
    fix_proposal: FixProposal,
) -> FixProposal:
    """Ensure verbose fix proposal fields are populated with safe fallbacks."""
    updates: dict[str, object] = {}

    if not fix_proposal.analysis_steps:
        updates["analysis_steps"] = [
            f"Mapped root cause to fix type {fix_proposal.fix_type.value}.",
            f"Prepared changes for {state['resource_type']}/{state['resource_name']} in {state['namespace']}.",
            "Included rollback steps and assessed operational risk.",
        ]

    if not fix_proposal.decision_rationale:
        updates["decision_rationale"] = (
            "Chosen because it directly addresses the root cause with minimal scope and "
            "a clear rollback path."
        )

    return fix_proposal.model_copy(update=updates) if updates else fix_proposal


def _ensure_actionable_fix(
    state: IncidentState,
    fix_proposal: FixProposal,
) -> FixProposal:
    """Ensure the fix proposal has actionable commands or manifests."""
    updates: dict[str, object] = {}

    commands = [cmd for cmd in fix_proposal.commands if cmd.strip()]
    if commands != fix_proposal.commands:
        updates["commands"] = commands

    if not commands and fix_proposal.manifests:
        updates["commands"] = [
            f"kubectl apply -f {filename} -n {state['namespace']}"
            for filename in fix_proposal.manifests
        ]
        return fix_proposal.model_copy(update=updates)

    if not commands and not fix_proposal.manifests:
        manual_commands = [
            f"kubectl describe {state['resource_type']}/{state['resource_name']} -n {state['namespace']}",
            (
                f"kubectl logs {state['resource_type']}/{state['resource_name']} "
                f"-n {state['namespace']} --tail=200"
            ),
            f"kubectl get events -n {state['namespace']} --sort-by=.lastTimestamp | tail -n 20",
        ]
        updates.update(
            {
                "fix_type": FixType.MANUAL,
                "description": (
                    "Manual intervention required. The proposal lacked actionable fix steps; "
                    "run diagnostic commands and apply a reviewed fix."
                ),
                "commands": manual_commands,
                "rollback_commands": [],
                "estimated_downtime": fix_proposal.estimated_downtime,
                "confidence_score": min(fix_proposal.confidence_score, 0.5),
                "risks": fix_proposal.risks or ["Manual changes require review."],
            }
        )
        return fix_proposal.model_copy(update=updates)

    return fix_proposal.model_copy(update=updates) if updates else fix_proposal


def _truncate(text: str, limit: int = 200) -> str:
    """Truncate long text for logging."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


async def solution_agent(
    state: IncidentState,
) -> Command[Literal["verifier_agent", "__end__"]]:
    """Solution Generation agent.

    Generates practical fixes based on root cause analysis.
    Uses Command pattern for routing to verification or direct end.

    Args:
        state: Current incident state with RCA result

    Returns:
        Command: Update with fix proposal and routing decision

    Routing logic:
        - High-risk fix or production → verifier_agent
        - Low-risk or dev/staging → END (can apply directly)
    """
    rca = state.get("rca_result")
    log.info(
        "solution_agent_started",
        resource=f"{state['resource_type']}/{state['resource_name']}",
        root_cause=rca.root_cause[:50] if rca else "None",
    )
    log.debug(
        "solution_agent_context",
        severity=rca.severity.value if rca else "unknown",
        confidence=rca.confidence_score if rca else None,
    )

    ollama = get_ollama_client()
    rca_result = state.get("rca_result")

    if not rca_result:
        log.error("solution_agent_no_rca", message="No RCA result available")
        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": "Solution agent called without RCA result",
            },
        )

    # Build user prompt
    user_prompt = SOLUTION_USER_PROMPT_TEMPLATE.format(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
        rca_result=rca_result.model_dump_json(indent=2),
        current_state="unknown",  # TODO: Get from kubectl
        labels="{}",  # TODO: Get from kubectl
    )

    messages = [
        {"role": "system", "content": SOLUTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Call LLM with Pydantic schema validation
        fix_proposal: FixProposal = ollama.chat_with_schema(
            messages=messages,
            schema=FixProposal,
            model=settings.agent.solution_model,
            temperature=0.2,  # Very low temperature for deterministic solutions
        )
        fix_proposal = _ensure_solution_verbosity(state, fix_proposal)
        fix_proposal = _ensure_actionable_fix(state, fix_proposal)

        # Record metrics
        agent_iterations_total.labels(
            agent_name="solution_agent",
            status="completed",
        ).inc()

        # Update messages
        ai_message = AIMessage(
            content=f"Fix proposed: {fix_proposal.fix_type.value} - {fix_proposal.description}"
        )
        log.debug(
            "solution_agent_output",
            analysis_steps_count=len(fix_proposal.analysis_steps),
            decision_rationale=_truncate(fix_proposal.decision_rationale, 240),
            commands_count=len(fix_proposal.commands),
            manifests=list(fix_proposal.manifests.keys()),
            risks_count=len(fix_proposal.risks),
        )

        # Decision: high-risk fixes need verification
        needs_verification = (
            rca_result.severity.value in ["critical", "high"]
            or state["namespace"] == "production"
            or len(fix_proposal.risks) > 0
        )

        if needs_verification:
            return Command(
                goto="verifier_agent",
                update={
                    "fix_proposal": fix_proposal,
                    "current_agent": AgentNode.VERIFIER,
                    "messages": [ai_message],
                },
            )
        log.info(
            "solution_low_risk",
            message="Fix can be applied directly without verification",
        )
        return Command(
            goto="__end__",
            update={
                "fix_proposal": fix_proposal,
                "current_agent": AgentNode.END,
                "messages": [ai_message],
            },
        )

    except Exception as e:
        log.exception("solution_agent_error")
        agent_iterations_total.labels(agent_name="solution_agent", status="error").inc()

        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": f"Solution agent failed: {e}",
                "messages": [HumanMessage(content=f"Solution agent unexpected error: {e}")],
            },
        )


__all__ = ["solution_agent"]
>>>>>>> af4493e9664b4940d61757df392615e5aaeb514e
