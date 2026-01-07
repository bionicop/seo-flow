"""
seo-flow configuration module.

Provides centralized settings management using pydantic-settings.
All configuration is loaded from environment variables.
"""

from config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
