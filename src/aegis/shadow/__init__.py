"""AEGIS Shadow Verification package.

Shadow mode verification system for safe remediation testing.
"""

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
    "get_shadow_manager",
]
