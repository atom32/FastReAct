"""
Configuration loader with environment variable support
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_config(
    config_path: Optional[str] = None,
    env_prefix: str = "FASTREACT"
) -> Dict[str, Any]:
    """
    Load configuration from file and environment variables

    Priority:
    1. Environment variables (highest)
    2. Config file
    3. Default values (lowest)

    Args:
        config_path: Path to config.json (default: ./config.json)
        env_prefix: Prefix for environment variables (default: FASTREACT)

    Returns:
        Merged configuration dictionary
    """
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

    # Try config first
    api_key = config.get("llm", {}).get("api_key")
    if api_key:
        return api_key

    # Try provider-specific config
    default_provider = config.get("llm", {}).get("default_provider", "siliconflow")
    provider_config = config.get("llm", {}).get("providers", {}).get(default_provider, {})
    api_key = provider_config.get("api_key")

    if api_key:
        return api_key

    # Try environment variable
    api_key = os.getenv("FASTREACT_API_KEY")
    if api_key:
        return api_key

    raise ValueError(
        "API key not found. Set FASTREACT_API_KEY environment variable "
        "or add api_key to config.json"
    )


def get_base_url(config: Optional[Dict[str, Any]] = None) -> str:
    """Get base URL from config or environment"""
    if config is None:
        config = load_config()

    # Try environment
    base_url = os.getenv("FASTREACT_BASE_URL")
    if base_url:
        return base_url

    # Try config
    base_url = config.get("llm", {}).get("base_url")
    if base_url:
        return base_url

    # Try provider config
    default_provider = config.get("llm", {}).get("default_provider", "siliconflow")
    provider_config = config.get("llm", {}).get("providers", {}).get(default_provider, {})
    base_url = provider_config.get("base_url")

    if base_url:
        return base_url

    return "https://api.siliconflow.cn/v1"


def get_model(config: Optional[Dict[str, Any]] = None) -> str:
    """Get model from config or environment"""
    if config is None:
        config = load_config()

    # Try environment
    model = os.getenv("FASTREACT_MODEL")
    if model:
        return model

    # Try config
    model = config.get("llm", {}).get("model")
    if model:
        return model

    # Try provider config
    default_provider = config.get("llm", {}).get("default_provider", "siliconflow")
    provider_config = config.get("llm", {}).get("providers", {}).get(default_provider, {})
    model = provider_config.get("model")

    if model:
        return model

    return "deepseek-ai/DeepSeek-V3"
