"""
Configuration Manager for FastReAct Nano v2.0

Implements three-layer configuration inheritance:
- Global Config (system default)
    ↓ deep merge
- Channel Config (channel-specific)
    ↓ deep merge
- User Config (user-specific)
    ↓
- Final Config (effective config)
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from fastreact.core.config import Config


class ConfigManager:
    """
    Configuration Manager with Inheritance Support

    Manages hierarchical configuration with three layers:
    1. Global: System-wide defaults
    2. Channel: Channel-specific overrides (e.g., "feishu", "web", "cli")
    3. User: User-specific overrides

    Deep Merge Strategy:
    - Primitive types (str, int, float, bool): override replaces base
    - dict: recursive merge
    - list: override replaces base
    - None: use base value (explicit inheritance)
    """

    def __init__(
        self,
        global_config: Config,
        channel_configs_dir: Optional[Path] = None,
        multitenant_manager: Optional["MultiTenantManager"] = None,
    ):
        """
        Initialize configuration manager

        Args:
            global_config: Global/base configuration
            channel_configs_dir: Directory for channel-specific configs (optional)
            multitenant_manager: MultiTenantManager for reading user configs (optional)
        """
        self._global_config = global_config
        self._channel_configs_dir = channel_configs_dir
        self._multitenant_manager = multitenant_manager

        # Caches
        self._channel_configs: Dict[str, dict] = {}
        self._user_configs: Dict[str, dict] = {}

    def get_effective_config(
        self,
        user_key: Optional[str] = None,
    ) -> dict:
        """
        Get effective configuration with inheritance applied

        Args:
            user_key: User identifier (format: "channel:user_id")

        Returns:
            Merged configuration dictionary

        Inheritance Chain:
            1. Start with global config
            2. Apply channel config (if user_key provided)
            3. Apply user config (if user_key provided)
        """
        # Step 1: Start with global config
        config = self._config_to_dict(self._global_config)

        # Step 2: Apply channel config (if user_key provided)
        if user_key:
            channel, _ = self._parse_user_key(user_key)
            if channel:
                channel_config = self._get_channel_config(channel)
                if channel_config:
                    config = self._deep_merge(config, channel_config)

        # Step 3: Apply user config (if user_key provided)
        if user_key:
            user_config = self._get_user_config(user_key)
            if user_config:
                config = self._deep_merge(config, user_config)

        return config

    def update_user_config(
        self,
        user_key: str,
        config_updates: dict,
    ) -> None:
        """
        Update user configuration

        Args:
            user_key: User identifier
            config_updates: Configuration updates (supports partial updates)
        """
        # Get current user config
        user_config = self._get_user_config(user_key) or {}

        # Deep merge with updates
        merged = self._deep_merge(user_config, config_updates)

        # Update cache
        self._user_configs[user_key] = merged

        # Persist to user workspace (via MultiTenantManager)
        # Note: This requires the MultiTenantManager to be set up
        # The persistence will be handled by the caller/Agent

    def _parse_user_key(self, user_key: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse user_key into channel and user_id

        Args:
            user_key: User identifier (format: "channel:user_id")

        Returns:
            Tuple of (channel, user_id) or (None, None) if invalid
        """
        if ":" not in user_key:
            return None, None

        parts = user_key.split(":", 1)
        if len(parts) != 2:
            return None, None

        channel, user_id = parts
        if not channel or not user_id:
            return None, None

        return channel, user_id

    def _get_channel_config(self, channel: str) -> Optional[dict]:
        """
        Get channel-specific configuration

        Args:
            channel: Channel name (e.g., "feishu", "web", "cli")

        Returns:
            Channel config dict or None
        """
        # Check cache first
        if channel in self._channel_configs:
            return self._channel_configs[channel]

        # Try to load from file
        if self._channel_configs_dir:
            config_file = self._channel_configs_dir / f"{channel}.json"
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        self._channel_configs[channel] = config
                        return config
                except (json.JSONDecodeError, IOError):
                    pass

        return None

    def _get_user_config(self, user_key: str) -> Optional[dict]:
        """
        Get user-specific configuration

        Args:
            user_key: User identifier

        Returns:
            User config dict or None
        """
        # Check cache first
        if user_key in self._user_configs:
            return self._user_configs[user_key]

        # Try to load from MultiTenantManager
        if self._multitenant_manager:
            try:
                # Get user context (includes workspace path)
                user_context = self._multitenant_manager.get_user_context(user_key)

                # Read config file from user workspace
                config_file = user_context.workspace / "config.json"

                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        # Cache it
                        self._user_configs[user_key] = config
                        return config
            except Exception:
                # If user context doesn't exist or other error, return None
                pass

        return None

    def _deep_merge(
        self,
        base: dict,
        override: dict,
    ) -> dict:
        """
        Deep merge two dictionaries

        Merge Strategy:
        - Primitive types (str, int, float, bool): override replaces base
        - dict: recursive merge
        - list: override replaces base
        - None: use base value (explicit inheritance)

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if value is None:
                # None means "use base value" - skip this key
                continue

            if key not in result:
                # New key - add it
                result[key] = value
            elif isinstance(value, dict) and isinstance(result[key], dict):
                # Both are dicts - recursive merge
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override with new value (for primitives, lists, etc.)
                result[key] = value

        return result

    def _config_to_dict(self, config: Config) -> dict:
        """
        Convert Config object to dictionary

        Args:
            config: Config object

        Returns:
            Dictionary representation
        """
        import dataclasses

        result = {}

        for field_name in dataclasses.fields(config):
            value = getattr(config, field_name.name)

            # Convert nested dataclasses recursively
            if dataclasses.is_dataclass(value):
                result[field_name.name] = self._config_to_dict(value)
            elif isinstance(value, Path):
                result[field_name.name] = str(value)
            elif isinstance(value, list):
                # Handle lists of dataclasses (e.g., MCP servers)
                if value and dataclasses.is_dataclass(value[0]):
                    result[field_name.name] = [
                        self._config_to_dict(item) if dataclasses.is_dataclass(item) else item
                        for item in value
                    ]
                else:
                    result[field_name.name] = value
            else:
                result[field_name.name] = value

        return result

    def clear_cache(self) -> None:
        """Clear all cached configurations"""
        self._channel_configs.clear()
        self._user_configs.clear()

    def get_channel_config(self, channel: str) -> Optional[dict]:
        """
        Get channel configuration (public API)

        Args:
            channel: Channel name

        Returns:
            Channel config dict or None
        """
        return self._get_channel_config(channel)

    def get_user_config_dict(self, user_key: str) -> Optional[dict]:
        """
        Get user configuration (public API)

        Args:
            user_key: User identifier

        Returns:
            User config dict or None
        """
        return self._get_user_config(user_key)

    def set_user_config(self, user_key: str, config: dict) -> None:
        """
        Set user configuration (for MultiTenantManager integration)

        Args:
            user_key: User identifier
            config: User config dict
        """
        self._user_configs[user_key] = config
