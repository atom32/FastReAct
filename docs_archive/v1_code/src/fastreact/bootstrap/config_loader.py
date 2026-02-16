"""
Configuration loader with multi-layer priority support

Priority (highest to lowest):
1. Environment variables (ENV) - CI/CD, multi-tenant
2. User configuration (~/.fastreact/config.json) - Personal API keys
3. Project configuration (./config.json) - Team shared settings
4. Default values (code) - Fallback
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Import the new ConfigManager for 4-layer configuration
try:
    from fastreact.core.config_manager import ConfigManager
    _USE_CONFIG_MANAGER = True
except ImportError:
    _USE_CONFIG_MANAGER = False


def load_config(
    config_path: Optional[str] = None,
    env_prefix: str = "FASTREACT"
) -> Dict[str, Any]:
    """
    Load configuration from multiple sources with priority

    Priority (highest to lowest):
    1. Environment variables (ENV)
    2. User configuration (~/.fastreact/config.json)
    3. Project configuration (./config.json)
    4. Default values (code)

    Args:
        config_path: Path to config.json (default: auto-detect)
        env_prefix: Prefix for environment variables (default: FASTREACT)

    Returns:
        Merged configuration dictionary
    """
    # Use new ConfigManager if available (4-layer priority)
    if _USE_CONFIG_MANAGER:
        manager = ConfigManager(project_root=Path.cwd())
        return manager.get_config()

    # Fallback to old 3-layer system
    config = _get_default_config()

    # Load from file
    if config_path is None:
        # Try default locations
        for location in ["./config.json", "./config/config.json", "~/.fastreact/config.json"]:
            path = Path(location).expanduser()
            if path.exists():
                config_path = str(path)
                break

    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            file_config = json.load(f)
        config = _merge_config(config, file_config)

    # Override with environment variables
    env_config = _load_env_config(env_prefix)
    config = _merge_config(config, env_config)

    return config


def _get_default_config() -> Dict[str, Any]:
    """Get default configuration"""
    return {
        "llm": {
            "providers": {
                "siliconflow": {
                    "enabled": True,
                    "base_url": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "model": "deepseek-ai/DeepSeek-V3"
                },
                "openai": {
                    "enabled": False,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "",
                    "model": "gpt-4"
                }
            },
            "default_provider": "siliconflow"
        },
        "react": {
            "max_iterations": 10,
            "max_concurrent_tools": 3,
            "enable_cache": True,
            "enable_streaming": False
        },
        "context": {
            "max_history_messages": 1000,
            "max_history_tokens": 48000,
            "reserve_tokens": 12000,
            "system_prompt_tokens": 2000,
            "token_model": "gpt-4",
            "smart_truncate": True,
            "pruning": {
                "enabled": True,
                "target_ratio": 0.5
            }
        },
        "tools": {
            "builtin_enabled": True,
            "available_tools": [
                "Calculator",
                "DateTime",
                "Sandbox"
            ]
        },
        "tool_policy": {
            "mode": "permissive",
            "deny_list": ["rm_*", "format*"]
        },
        "approval": {
            "mode": "ask_high_risk"
        },
        "display": {
            "mode": "normal",
            "use_colors": True
        }
    }


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two config dictionaries"""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value

    return result


def _load_env_config(prefix: str) -> Dict[str, Any]:
    """Load configuration from environment variables

    Environment variable format:
    - FASTREACT_API_KEY
    - FASTREACT_BASE_URL
    - FASTREACT_MODEL
    - FASTREACT_PROVIDER
    """
    config = {}

    # LLM configuration
    if os.getenv(f"{prefix}_API_KEY"):
        config.setdefault("llm", {})
        config["llm"]["api_key"] = os.getenv(f"{prefix}_API_KEY")

    if os.getenv(f"{prefix}_BASE_URL"):
        config.setdefault("llm", {})
        config["llm"]["base_url"] = os.getenv(f"{prefix}_BASE_URL")

    if os.getenv(f"{prefix}_MODEL"):
        config.setdefault("llm", {})
        config["llm"]["model"] = os.getenv(f"{prefix}_MODEL")

    if os.getenv(f"{prefix}_PROVIDER"):
        config.setdefault("llm", {})
        config["llm"]["default_provider"] = os.getenv(f"{prefix}_PROVIDER")

    # Feature flags
    if os.getenv(f"{prefix}_ENABLE_PRUNING"):
        config.setdefault("context", {})
        config["context"]["pruning"] = {
            "enabled": os.getenv(f"{prefix}_ENABLE_PRUNING").lower() == "true"
        }

    if os.getenv(f"{prefix}_ENABLE_APPROVAL"):
        config.setdefault("approval", {})
        config["approval"]["mode"] = "ask_high_risk"

    return config


def get_api_key(config: Optional[Dict[str, Any]] = None) -> str:
    """Get API key from config or environment"""
    if config is None:
        config = load_config()

    # Try environment variable first (highest priority)
    api_key = os.getenv("FASTREACT_API_KEY")
    if api_key:
        return api_key

    # Try provider-specific config (new format from ConfigManager)
    default_provider = config.get("llm", {}).get("default_provider", "siliconflow")
    providers = config.get("llm", {}).get("providers", {})

    if providers and default_provider in providers:
        provider_config = providers[default_provider]
        api_key = provider_config.get("api_key")
        if api_key:
            return api_key

    # Try old format (llm.api_key)
    api_key = config.get("llm", {}).get("api_key")
    if api_key:
        return api_key

    raise ValueError(
        "API key not found. Options:\n"
        "  1. Set FASTREACT_API_KEY environment variable\n"
        "  2. Add api_key to ~/.fastreact/config.json (recommended for personal use)\n"
        "  3. Add api_key to ./config.json (for team use, be careful not to commit)\n"
        "Run 'python test_config_priority.py' to check your configuration."
    )


def get_base_url(config: Optional[Dict[str, Any]] = None) -> str:
    """Get base URL from config or environment"""
    if config is None:
        config = load_config()

    # Try environment first (highest priority)
    base_url = os.getenv("FASTREACT_BASE_URL")
    if base_url:
        return base_url

    # Try provider-specific config (new format from ConfigManager)
    default_provider = config.get("llm", {}).get("default_provider", "siliconflow")
    providers = config.get("llm", {}).get("providers", {})

    if providers and default_provider in providers:
        provider_config = providers[default_provider]
        base_url = provider_config.get("base_url")
        if base_url:
            return base_url

    # Try old format (llm.base_url)
    base_url = config.get("llm", {}).get("base_url")
    if base_url:
        return base_url

    return "https://api.siliconflow.cn/v1"


def get_model(config: Optional[Dict[str, Any]] = None) -> str:
    """Get model from config or environment"""
    if config is None:
        config = load_config()

    # Try environment first (highest priority)
    model = os.getenv("FASTREACT_MODEL")
    if model:
        return model

    # Try provider-specific config (new format from ConfigManager)
    default_provider = config.get("llm", {}).get("default_provider", "siliconflow")
    providers = config.get("llm", {}).get("providers", {})

    if providers and default_provider in providers:
        provider_config = providers[default_provider]
        model = provider_config.get("model")
        if model:
            return model

    # Try old format (llm.model)
    model = config.get("llm", {}).get("model")
    if model:
        return model

    return "deepseek-ai/DeepSeek-V3"
