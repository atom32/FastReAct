"""
Multi-layer Configuration Manager for FastReAct

Implements four-layer configuration loading with priority:
1. Environment variables (highest priority)
2. User configuration (~/.fastreact/config.json)
3. Project configuration (./config.json)
4. Default values (lowest priority)
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Multi-layer configuration manager

    Loads configuration from multiple sources with priority:
    - ENV (highest): Environment variables
    - USER: ~/.fastreact/config.json
    - PROJECT: ./config.json
    - DEFAULT (lowest): Built-in defaults
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            project_root: Project root directory (default: auto-detect)
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.config = {}
        self._load_all()

    def _load_all(self):
        """Load configuration from all sources (priority: DEFAULT → PROJECT → USER → ENV)"""
        # Start with defaults
        self.config = self._get_defaults()

        # Layer 1: Project configuration
        project_config = self._load_project_config()
        if project_config:
            self._deep_merge(self.config, project_config)
            logger.info("[Config] Loaded project configuration")

        # Layer 2: User configuration
        user_config = self._load_user_config()
        if user_config:
            self._deep_merge(self.config, user_config)
            logger.info("[Config] Loaded user configuration")

        # Layer 3: Environment variables (highest priority)
        env_config = self._load_env_vars()
        if env_config:
            self._deep_merge(self.config, env_config)
            logger.info("[Config] Loaded environment variables")

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "llm": {
                "default_provider": "siliconflow",
                "timeout_seconds": 60,
                "retry_attempts": 3
            },
            "context": {
                "max_history_messages": 1000,
                "max_history_tokens": 48000,
                "reserve_tokens": 12000,
                "system_prompt_tokens": 2000,
                "token_model": "gpt-4",
                "smart_truncate": True,
                "memory_flush": {
                    "enabled": True,
                    "soft_threshold_tokens": 50000,
                    "hard_threshold_tokens": 55000
                },
                "retrieval": {
                    "enabled": False,
                    "provider": "modelscope",
                    "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
                    "device": "cpu",
                    "vector_store": "apsw"
                }
            },
            "react": {
                "max_iterations": 10,
                "max_concurrent_tools": 3,
                "enable_cache": True,
                "cache_size": 1000
            },
            "tools": {
                "builtin_enabled": True,
                "available_tools": [
                    "Calculator",
                    "TavilySearch",
                    "Weather",
                    "HTTP",
                    "GetCurrentTime"
                ]
            },
            "mcp": {
                "enabled": False,
                "servers": {}
            },
            "logging": {
                "level": "INFO",
                "console_output": True
            }
        }

    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """Load project configuration (./config.json)"""
        config_path = self.project_root / "config.json"

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.debug(f"[Config] Project config: {config_path}")
                return config
            except Exception as e:
                logger.warning(f"[Config] Failed to load project config: {e}")
                return None

        return None

    def _load_user_config(self) -> Optional[Dict[str, Any]]:
        """Load user configuration (~/.fastreact/config.json)"""
        home = Path.home()
        config_dir = home / ".fastreact"
        config_path = config_dir / "config.json"

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.debug(f"[Config] User config: {config_path}")
                return config
            except Exception as e:
                logger.warning(f"[Config] Failed to load user config: {e}")
                return None

        return None

    def _load_env_vars(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}

        # FastReAct API key
        api_key = os.getenv("FASTREACT_API_KEY")
        if api_key:
            if "llm" not in env_config:
                env_config["llm"] = {}
            if "providers" not in env_config["llm"]:
                env_config["llm"]["providers"] = {}

            provider = os.getenv("FASTREACT_PROVIDER", "siliconflow")
            if provider not in env_config["llm"]["providers"]:
                env_config["llm"]["providers"][provider] = {}

            env_config["llm"]["providers"][provider]["api_key"] = api_key
            logger.debug(f"[Config] API key from env (provider: {provider})")

        # GitHub token for MCP
        github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if github_token:
            if "mcp" not in env_config:
                env_config["mcp"] = {}
            if "servers" not in env_config["mcp"]:
                env_config["mcp"]["servers"] = {}
            if "github" not in env_config["mcp"]["servers"]:
                env_config["mcp"]["servers"]["github"] = {}

            env_config["mcp"]["servers"]["github"]["env"] = {
                "GITHUB_PERSONAL_ACCESS_TOKEN": github_token
            }
            logger.debug("[Config] GitHub token from env")

        # Model override
        model = os.getenv("FASTREACT_MODEL")
        if model:
            if "llm" not in env_config:
                env_config["llm"] = {}
            env_config["llm"]["model"] = model
            logger.debug(f"[Config] Model override from env: {model}")

        # Base URL override
        base_url = os.getenv("FASTREACT_BASE_URL")
        if base_url:
            if "llm" not in env_config:
                env_config["llm"] = {}
            env_config["llm"]["base_url"] = base_url
            logger.debug(f"[Config] Base URL override from env: {base_url}")

        return env_config

    def _deep_merge(self, base: Dict, update: Dict):
        """
        Deep merge dictionaries

        Args:
            base: Base dictionary (modified in place)
            update: Update dictionary (values take priority)
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._deep_merge(base[key], value)
            else:
                # Override with new value
                base[key] = value

    def get(self, key_path: str, default=None):
        """
        Get configuration value by dot-separated path

        Args:
            key_path: Dot-separated path (e.g., "llm.providers.siliconflow.api_key")
            default: Default value if not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary"""
        return self.config.copy()


def get_config_manager(project_root: Optional[Path] = None) -> ConfigManager:
    """
    Get global configuration manager instance

    Args:
        project_root: Project root directory

    Returns:
        ConfigManager instance
    """
    return ConfigManager(project_root)


# Singleton instance
_config_manager_instance = None


def get_global_config() -> ConfigManager:
    """
    Get global configuration manager singleton

    Returns:
        ConfigManager instance
    """
    global _config_manager_instance

    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()

    return _config_manager_instance
