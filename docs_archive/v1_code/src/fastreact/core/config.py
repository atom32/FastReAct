"""
Configuration module for FastReAct core

This module provides configuration loading utilities for the core system.
It bridges between the utils.config and bootstrap.config_loader modules.
"""

# Import from utils.config (the original implementation)
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastreact.utils.config import (
    Config,
    get_config as get_config_instance,
)

# Import from bootstrap config_loader (new implementation with env vars)
try:
    from fastreact.bootstrap.config_loader import (
        load_config as load_config_with_env,
        get_api_key,
        get_base_url,
        get_model,
    )
    _config_loader_available = True
except ImportError:
    _config_loader_available = False

__all__ = [
    "Config",
    "get_config",
    "load_config",
]

# Wrapper function that uses config_loader or falls back to utils.config
def load_config(config_path=None, env_prefix="FASTREACT"):
    """
    Load configuration from file and environment variables

    Args:
        config_path: Path to config.json
        env_prefix: Prefix for environment variables (default: FASTREACT)

    Returns:
        Configuration dictionary
    """
    if _config_loader_available:
        return load_config_with_env(config_path, env_prefix)
    else:
        # Fallback to utils.config
        config = get_config_instance(config_path)
        return config.config


# Re-export helper functions if available
if _config_loader_available:
    # Add individual helper functions to __all__
    __all__.extend([
        "get_api_key",
        "get_base_url",
        "get_model",
    ])
