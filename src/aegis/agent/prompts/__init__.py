"""Agent prompt templates for AEGIS incident analysis workflow."""

from aegis.agent.prompts.rca_prompts import RCA_SYSTEM_PROMPT, RCA_USER_PROMPT_TEMPLATE
from aegis.agent.prompts.solution_prompts import (
    SOLUTION_SYSTEM_PROMPT,
    SOLUTION_USER_PROMPT_TEMPLATE,
)
from aegis.agent.prompts.verifier_prompts import (
    VERIFIER_SYSTEM_PROMPT,
    VERIFIER_USER_PROMPT_TEMPLATE,
)


__all__ = [
    "RCA_SYSTEM_PROMPT",
    "RCA_USER_PROMPT_TEMPLATE",
    "SOLUTION_SYSTEM_PROMPT",
    "SOLUTION_USER_PROMPT_TEMPLATE",
    "VERIFIER_SYSTEM_PROMPT",
    "VERIFIER_USER_PROMPT_TEMPLATE",
]
