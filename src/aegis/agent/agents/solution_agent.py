"""Solution Generation Agent.

Uses configured LLM provider (Gemini/Groq/Ollama fallback) for fix generation.
Returns Command object for routing to verifier or direct application.
"""

import json
from typing import Literal

from kubernetes import client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from aegis.agent.llm.router import chat_with_schema_with_fallback
from aegis.agent.prompts.solution_prompts import (
    SOLUTION_SYSTEM_PROMPT,
    SOLUTION_USER_PROMPT_TEMPLATE,
)
from aegis.agent.state import AgentNode, FixProposal, FixType, IncidentState
from aegis.config.settings import settings
from aegis.observability._logging import get_logger
from aegis.observability._metrics import agent_iterations_total


log = get_logger(__name__)


def _fetch_k8s_context(
    resource_type: str,
    resource_name: str,
    namespace: str,
) -> tuple[str, str]:
    """Fetch current state and labels from the Kubernetes API."""
    try:
        if settings.kubernetes.in_cluster:
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config(
                config_file=settings.kubernetes.kubeconfig_path,
                context=settings.kubernetes.context,
            )
    except k8s_config.ConfigException as exc:
        msg = f"unavailable (kubeconfig error: {exc})"
        return msg, "{}"

    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()

    kind = resource_type.lower()
    try:
        if kind in {"pod", "pods"}:
            pod = core_api.read_namespaced_pod(resource_name, namespace)
            state = {
                "phase": pod.status.phase if pod.status else None,
                "node": pod.spec.node_name if pod.spec else None,
                "pod_ip": pod.status.pod_ip if pod.status else None,
                "restarts": {
                    cs.name: cs.restart_count for cs in (pod.status.container_statuses or [])
                }
                if pod.status
                else {},
                "conditions": [cond.type for cond in (pod.status.conditions or [])]
                if pod.status
                else [],
            }
            labels = pod.metadata.labels if pod.metadata and pod.metadata.labels else {}
        elif kind in {"deployment", "deployments"}:
            deploy = apps_api.read_namespaced_deployment(resource_name, namespace)
            state = {
                "replicas": {
                    "desired": deploy.spec.replicas if deploy.spec else None,
                    "ready": deploy.status.ready_replicas if deploy.status else None,
                    "available": deploy.status.available_replicas if deploy.status else None,
                    "updated": deploy.status.updated_replicas if deploy.status else None,
                },
                "strategy": deploy.spec.strategy.type
                if deploy.spec and deploy.spec.strategy
                else None,
                "images": [
                    c.image
                    for c in (
                        deploy.spec.template.spec.containers
                        if deploy.spec and deploy.spec.template and deploy.spec.template.spec
                        else []
                    )
                ],
                "conditions": [cond.type for cond in (deploy.status.conditions or [])]
                if deploy.status
                else [],
            }
            labels = deploy.metadata.labels if deploy.metadata and deploy.metadata.labels else {}
        else:
            return f"unavailable (unsupported resource type: {resource_type})", "{}"
    except ApiException as exc:
        return f"unavailable (k8s api error: {exc.reason})", "{}"

    return json.dumps(state, indent=2, default=str), json.dumps(labels, indent=2)


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
    """Ensure the fix proposal has actionable commands or manifests.

    Applies template-based fixes for common issues if LLM fails to generate commands.
    """
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
        # Try template-based fix for common issues
        rca_result = state.get("rca_result")
        if rca_result and rca_result.root_cause:
            root_cause_lower = rca_result.root_cause.lower()
            resource_type = state["resource_type"]
            resource_name = state["resource_name"]
            namespace = state["namespace"]

            # OOMKilled fix template
            if "oom" in root_cause_lower or "memory" in root_cause_lower:
                log.info(
                    "applying_template_fix",
                    pattern="oom",
                    resource=f"{resource_type}/{resource_name}",
                )
                return fix_proposal.model_copy(
                    update={
                        "fix_type": FixType.CONFIG_CHANGE,
                        "description": "Increase memory limit to 512Mi to prevent OOMKilled",
                        "analysis_steps": [
                            "Detected OOMKilled in root cause analysis",
                            "Current memory limit appears insufficient",
                            "Applying recommended 512Mi limit with rolling update",
                        ],
                        "decision_rationale": (
                            "Increasing memory limits directly addresses OOM failures with minimal risk. "
                            "Using 512Mi provides sufficient headroom based on common patterns."
                        ),
                        "commands": [
                            f"kubectl set resources {resource_type}/{resource_name} "
                            f"--limits=memory=512Mi -n {namespace}",
                        ],
                        "rollback_commands": [
                            f"kubectl set resources {resource_type}/{resource_name} "
                            f"--limits=memory=128Mi -n {namespace}",
                        ],
                        "estimated_downtime": "zero-downtime",
                        "risks": ["Pod(s) will be recreated"],
                        "prerequisites": [],
                        "confidence_score": 0.85,
                    }
                )

        # Fallback to manual intervention
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
    current_state, labels = _fetch_k8s_context(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
    )
    user_prompt = SOLUTION_USER_PROMPT_TEMPLATE.format(
        resource_type=state["resource_type"],
        resource_name=state["resource_name"],
        namespace=state["namespace"],
        rca_result=rca_result.model_dump_json(indent=2),
        current_state=current_state,
        labels=labels,
    )

    messages = [
        {"role": "system", "content": SOLUTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Call LLM with Pydantic schema validation
        fix_proposal, provider_used, model_used = chat_with_schema_with_fallback(
            messages=messages,
            schema=FixProposal,
            provider=settings.agent.solution_provider,
            model=settings.agent.solution_model,
            temperature=0.2,  # Very low temperature for deterministic solutions
            fallback_model=settings.agent.solution_fallback_model,
        )
        assert isinstance(fix_proposal, FixProposal)
        fix_proposal = _ensure_solution_verbosity(state, fix_proposal)
        fix_proposal = _ensure_actionable_fix(state, fix_proposal)

        # Record metrics
        agent_iterations_total.labels(
            agent_name="solution_agent",
            status="completed",
        ).inc()

        llm_trace = dict(state.get("llm_trace") or {})
        llm_trace["solution_agent"] = {"provider": provider_used, "model": model_used}

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
                    "llm_trace": llm_trace,
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
                "llm_trace": llm_trace,
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
