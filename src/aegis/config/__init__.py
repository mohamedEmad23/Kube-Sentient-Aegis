"""AEGIS Configuration package.

Centralized configuration management using Pydantic Settings.
"""

from aegis.config.settings import Settings, get_settings

__all__: list[str] = ["Settings", "get_settings"]
