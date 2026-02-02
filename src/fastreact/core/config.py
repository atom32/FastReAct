"""
Configuration module for FastReAct core

This module provides configuration loading utilities for the core system.
It bridges between the bootstrap config_loader and core components.
"""

from ..bootstrap.config_loader import (
    load_config,
    get_api_key,
    get_base_url,
    get_model,
)

__all__ [
    "load_config",
    "get_api_key",
    "get_base_url",
    "get_model",
]
