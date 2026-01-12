"""Solution Generation Agent.

Uses tinyllama:latest for generating practical fixes with kubectl commands and YAML manifests.
Returns Command object for routing to verifier or direct application.
"""

import json
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
        rca_result=json.dumps(rca_result.model_dump(), indent=2),
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

        # Record metrics
        agent_iterations_total.labels(
            agent_name="solution_agent",
            status="completed",
        ).inc()

        log.info(
            "solution_agent_completed",
            fix_type=fix_proposal.fix_type.value,
            confidence=fix_proposal.confidence_score,
            commands_count=len(fix_proposal.commands),
        )

        # Update messages
        ai_message = AIMessage(
            content=f"Fix proposed: {fix_proposal.fix_type.value} - {fix_proposal.description}"
        )

        # Decision: high-risk fixes need verification
        needs_verification = (
            rca_result.severity.value in ["critical", "high"]
            or state["namespace"] == "production"
            or len(fix_proposal.risks) > 0
        )

        if needs_verification:
            log.info(
                "solution_requires_verification",
                severity=rca_result.severity.value,
                namespace=state["namespace"],
                risks=len(fix_proposal.risks),
            )
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
