"""AEGIS Shadow Verification package.

Shadow mode verification system for safe remediation testing.
"""

from aegis.shadow.errors import (
    ShadowWorkflowError,
    ensure_shadow_error,
    parse_shadow_error,
)
from aegis.shadow.manager import (
    ShadowEnvironment,
    ShadowManager,
    ShadowStatus,
    get_shadow_manager,
)


__all__ = [
    "ShadowEnvironment",
    "ShadowManager",
    "ShadowStatus",
    "ShadowWorkflowError",
    "ensure_shadow_error",
    "get_shadow_manager",
    "parse_shadow_error",
]
