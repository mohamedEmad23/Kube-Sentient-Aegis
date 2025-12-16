"""AEGIS Utilities package.

Common utilities and helpers used across the AEGIS codebase.
"""

from aegis.utils.gpu import check_gpu_availability, get_recommended_model

__all__ = ["check_gpu_availability", "get_recommended_model"]
