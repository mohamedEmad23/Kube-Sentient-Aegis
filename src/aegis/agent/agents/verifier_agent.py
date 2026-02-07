"""Verification Planning Agent.

Uses configured LLM provider (Gemini/Groq/Ollama fallback) for verification planning.
Returns Command object to end workflow with verification plan.
"""

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from aegis.agent.llm.router import chat_with_schema_with_fallback
from aegis.agent.prompts.verifier_prompts import (
    VERIFIER_SYSTEM_PROMPT,
    VERIFIER_USER_PROMPT_TEMPLATE,
)
from aegis.agent.state import AgentNode, IncidentState, VerificationPlan
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import agent_iterations_total


log = get_logger(__name__)


def _ensure_verifier_verbosity(
    state: IncidentState,
    verification_plan: VerificationPlan,
) -> VerificationPlan:
    """Ensure verbose verification plan fields are populated with safe fallbacks."""
    updates: dict[str, object] = {}

    if not verification_plan.analysis_steps:
        updates["analysis_steps"] = [
            f"Matched verification type to {state['resource_type']}/{state['resource_name']} risk profile.",
            "Selected test scenarios aligned to the proposed fix.",
            "Defined measurable success criteria and rollback expectations.",
        ]

    if not verification_plan.decision_rationale:
        updates["decision_rationale"] = (
            "Selected a verification strategy that balances safety, speed, and signal quality "
            "for the proposed change."
        )

    return verification_plan.model_copy(update=updates) if updates else verification_plan


def _truncate(text: str, limit: int = 200) -> str:
    """Truncate long text for logging."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


async def verifier_agent(
    state: IncidentState,
) -> Command[Literal["__end__"]]:
    """Verification Planning agent.

    Creates comprehensive verification plan for shadow environment testing.
    Always routes to END as final step in workflow.

    Args:
        state: Current incident state with fix proposal

    Returns:
        Command: Update with verification plan and END routing
    """
    fix = state.get("fix_proposal")
    log.info(
        "verifier_agent_started",
        resource=f"{state['resource_type']}/{state['resource_name']}",
        fix_type=fix.fix_type.value if fix else "None",
    )
    log.debug(
        "verifier_agent_context",
        fix_confidence=fix.confidence_score if fix else None,
        risk_count=len(fix.risks) if fix else 0,
    )

    fix_proposal = state.get("fix_proposal")
    rca_result = state.get("rca_result")

    if not fix_proposal or not rca_result:
        log.error("verifier_agent_missing_context")
        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": "Verifier agent called without fix proposal or RCA result",
            },
        )

    # Build user prompt
    user_prompt = VERIFIER_USER_PROMPT_TEMPLATE.format(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
        root_cause=rca_result.root_cause,
        fix_proposal=fix_proposal.model_dump_json(indent=2),
        fix_type=fix_proposal.fix_type.value,
        estimated_downtime=fix_proposal.estimated_downtime or "unknown",
        risks=", ".join(fix_proposal.risks) if fix_proposal.risks else "none",
    )

    messages = [
        {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Call LLM with Pydantic schema validation
        verification_plan, provider_used, model_used = chat_with_schema_with_fallback(
            messages=messages,
            schema=VerificationPlan,
            provider=settings.agent.verifier_provider,
            model=settings.agent.verifier_model,
            temperature=0.4,  # Moderate temperature for creative test scenarios
            fallback_model=settings.agent.verifier_fallback_model,
        )
        assert isinstance(verification_plan, VerificationPlan)
        verification_plan = _ensure_verifier_verbosity(state, verification_plan)

        # Record metrics
        agent_iterations_total.labels(
            agent_name="verifier_agent",
            status="completed",
        ).inc()

        log.info(
            "verifier_agent_completed",
            verification_type=verification_plan.verification_type,
            duration=verification_plan.duration,
            test_scenarios=len(verification_plan.test_scenarios),
            approval_required=verification_plan.approval_required,
        )
        log.debug(
            "verifier_agent_output",
            analysis_steps_count=len(verification_plan.analysis_steps),
            decision_rationale=_truncate(verification_plan.decision_rationale, 240),
            success_criteria_count=len(verification_plan.success_criteria),
            load_test_enabled=verification_plan.load_test_config is not None,
            security_checks=verification_plan.security_checks,
        )

        llm_trace = dict(state.get("llm_trace") or {})
        llm_trace["verifier_agent"] = {"provider": provider_used, "model": model_used}

        # Update messages
        ai_message = AIMessage(
            content=(
                f"Verification plan created: {verification_plan.verification_type} testing "
                f"with {len(verification_plan.test_scenarios)} scenarios"
            )
        )

        # Always route to END - verification plan is the final output
        return Command(
            goto="__end__",
            update={
                "verification_plan": verification_plan,
                "current_agent": AgentNode.END,
                "messages": [ai_message],
                "llm_trace": llm_trace,
            },
        )

    except Exception as e:
        log.exception("verifier_agent_error")
        agent_iterations_total.labels(agent_name="verifier_agent", status="error").inc()

        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": f"Verifier agent failed: {e}",
                "messages": [HumanMessage(content=f"Verifier agent unexpected error: {e}")],
            },
        )


__all__ = ["verifier_agent"]
