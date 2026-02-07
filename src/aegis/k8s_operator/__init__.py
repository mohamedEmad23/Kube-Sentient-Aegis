"""AEGIS Operator package.

The Kubernetes operator that manages AEGIS resources and orchestrates
incident detection and response.

Note: The module name 'operator' intentionally follows Kubernetes operator
naming conventions (e.g., kopf, kubebuilder patterns).
"""

from importlib import import_module
from types import ModuleType


def __getattr__(name: str) -> ModuleType:
    """Lazy-load heavy operator submodules for runtime and test imports."""
    if name == "handlers":
        return import_module("aegis.k8s_operator.handlers")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["handlers"]
