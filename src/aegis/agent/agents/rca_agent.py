"""Root Cause Analysis (RCA) Agent.

Uses llama3.2:3b-instruct-q5_k_m for incident analysis and root cause identification.
Returns Command object for dynamic routing based on confidence score.
"""

import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from aegis.agent.llm.gemini import get_gemini_client
from aegis.agent.prompts.rca_prompts import RCA_SYSTEM_PROMPT, RCA_USER_PROMPT_TEMPLATE
from aegis.agent.state import AgentNode, IncidentState, RCAResult
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import agent_iterations_total, incident_analysis_duration_seconds


log = get_logger(__name__)


# Confidence threshold for routing decision
RCA_CONFIDENCE_THRESHOLD = 0.7


def _ensure_rca_verbosity(state: IncidentState, rca_result: RCAResult) -> RCAResult:
    """Ensure verbose RCA fields are populated with safe fallbacks."""
    updates: dict[str, object] = {}

    if not rca_result.analysis_steps:
        updates["analysis_steps"] = [
            "Reviewed K8sGPT analysis and kubectl outputs for the incident context.",
            f"Identified symptoms for {state['resource_type']}/{state['resource_name']}.",
            f"Determined the most likely root cause: {rca_result.root_cause}.",
        ]

    if not rca_result.evidence_summary:
        evidence: list[str] = []
        if state.get("kubectl_logs"):
            evidence.append("Pod logs reviewed for explicit error messages.")
        if state.get("kubectl_describe"):
            evidence.append("kubectl describe output reviewed for status conditions.")
        if state.get("kubectl_events"):
            evidence.append("Recent events reviewed for warnings and restarts.")
        k8s_analysis = state.get("k8sgpt_analysis")
        if k8s_analysis:
            evidence.append(f"K8sGPT reported {k8s_analysis.problems} problem(s).")
        updates["evidence_summary"] = evidence or ["Evidence summarized in reasoning."]

    if not rca_result.decision_rationale:
        updates["decision_rationale"] = rca_result.reasoning

    return rca_result.model_copy(update=updates) if updates else rca_result


def _truncate(text: str, limit: int = 200) -> str:
    """Truncate long text for logging."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


async def rca_agent(
    state: IncidentState,
) -> Command[Literal["solution_agent", "__end__"]]:
    """Root Cause Analysis agent.

    Analyzes K8sGPT output and Kubernetes context to identify root cause.
    Uses Command pattern for dynamic routing based on confidence score.

    Args:
        state: Current incident state with K8sGPT analysis

    Returns:
        Command: Update with RCA result and routing decision

    Routing logic:
        - confidence >= 0.7: → solution_agent
        - confidence < 0.7: → END (insufficient confidence)
    """
    log.info(
        "rca_agent_started",
        resource=f"{state['resource_type']}/{state['resource_name']}",
        namespace=state["namespace"],
    )
    log.debug(
        "rca_agent_context",
        has_k8sgpt=bool(state.get("k8sgpt_raw")),
        logs_len=len(state.get("kubectl_logs") or ""),
        describe_len=len(state.get("kubectl_describe") or ""),
        events_len=len(state.get("kubectl_events") or ""),
    )

    ollama = get_gemini_client()  # Using Gemini for faster testing

    # Build user prompt with context
    user_prompt = RCA_USER_PROMPT_TEMPLATE.format(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
        k8sgpt_analysis=json.dumps(state.get("k8sgpt_raw", {}), indent=2),
        kubectl_logs=state.get("kubectl_logs", "No logs available"),
        kubectl_describe=state.get("kubectl_describe", "No describe output"),
        kubectl_events=state.get("kubectl_events", "No recent events"),
    )

    messages = [
        {"role": "system", "content": RCA_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Time the analysis
        with incident_analysis_duration_seconds.labels(agent_name="rca_agent").time():
            # Call LLM with Pydantic schema validation
            rca_result = ollama.chat_with_schema(
                messages=messages,
                schema=RCAResult,
                model=settings.agent.rca_model,
                temperature=0.3,  # Lower temperature for more focused analysis
            )
            # Type assertion for runtime verification
            assert isinstance(rca_result, RCAResult)
            rca_result = _ensure_rca_verbosity(state, rca_result)

        # Record metrics
        agent_iterations_total.labels(
            agent_name="rca_agent",
            status="completed",
        ).inc()

        log.info(
            "rca_agent_completed",
            root_cause=rca_result.root_cause[:100],
            severity=rca_result.severity.value,
            confidence=rca_result.confidence_score,
        )
        log.debug(
            "rca_agent_output",
            analysis_steps_count=len(rca_result.analysis_steps),
            evidence_count=len(rca_result.evidence_summary),
            decision_rationale=_truncate(rca_result.decision_rationale, 240),
            reasoning=_truncate(rca_result.reasoning, 240),
        )

        # Update messages with AI response
        ai_message = AIMessage(
            content=f"Root cause identified: {rca_result.root_cause}\nConfidence: {rca_result.confidence_score}"
        )

        # Decision: proceed to solution agent if confidence is high
        if rca_result.confidence_score >= RCA_CONFIDENCE_THRESHOLD:
            log.info(
                "rca_confidence_sufficient",
                confidence=rca_result.confidence_score,
                next_agent="solution_agent",
            )
            return Command(
                goto="solution_agent",
                update={
                    "rca_result": rca_result,
                    "current_agent": AgentNode.SOLUTION,
                    "messages": [ai_message],
                },
            )
        log.warning(
            "rca_confidence_insufficient",
            confidence=rca_result.confidence_score,
            threshold=RCA_CONFIDENCE_THRESHOLD,
        )
        agent_iterations_total.labels(
            agent_name="rca_agent",
            status="low_confidence",
        ).inc()

        return Command(
            goto="__end__",
            update={
                "rca_result": rca_result,
                "current_agent": AgentNode.END,
                "error": f"Insufficient confidence in analysis ({rca_result.confidence_score:.2f} < 0.7)",
                "messages": [ai_message],
            },
        )

    except Exception as e:
        log.exception("rca_agent_error")
        agent_iterations_total.labels(agent_name="rca_agent", status="error").inc()

        return Command(
            goto="__end__",
            update={
                "current_agent": AgentNode.END,
                "error": f"RCA agent failed: {e}",
                "messages": [HumanMessage(content=f"RCA agent unexpected error: {e}")],
            },
        )


__all__ = ["rca_agent"]
