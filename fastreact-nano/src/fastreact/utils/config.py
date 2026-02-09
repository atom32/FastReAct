"""
Configuration management for FastReAct Nano

All paths are configurable via environment variables or config file.
No hardcoded paths - uses pathlib for cross-platform compatibility.
"""

import os
from pathlib import Path
from typing import Any, Optional
import json
import yaml


class Config:
    """Configuration manager with environment variable support"""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = self._find_config(config_path)
        self._config: dict[str, Any] = {}
        self._load_config()

    def _find_config(self, config_path: Optional[Path]) -> Optional[Path]:
        """Find configuration file in standard locations"""
        if config_path and config_path.exists():
            return config_path

        # Check environment variable
        env_path = os.getenv("FASTREACT_CONFIG")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Check current directory
        for filename in ["fastreact.yaml", "fastreact.json", "config.json"]:
            path = Path.cwd() / filename
            if path.exists():
                return path

        return None

    def _load_config(self):
        """Load configuration from file"""
        if not self._config_path:
            return

        with open(self._config_path, "r", encoding="utf-8") as f:
            if self._config_path.suffix in [".yaml", ".yml"]:
                self._config = yaml.safe_load(f) or {}
            elif self._config_path.suffix == ".json":
                self._config = json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable override"""
        # Check environment variable first
        env_key = f"FASTREACT_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # Check config file
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_path(self, key: str, default: Optional[Path] = None) -> Path:
        """Get path configuration, returns Path object"""
        value = self.get(key)
        if value:
            return Path(value)
        return default or Path.cwd()

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes", "on"]
        return bool(value)

    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """Get list configuration"""
        value = self.get(key, default)
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",")]
        return default or []


class Paths:
    """Centralized path management - no hardcoded paths"""

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()

    @property
    def base_dir(self) -> Path:
        """Base directory for all FastReAct data"""
        return self._config.get_path("paths.base_dir", Path.cwd() / ".fastreact")

    @property
    def data_dir(self) -> Path:
        """Data directory for sessions and memory"""
        return self._config.get_path("paths.data_dir", self.base_dir / "data")

    @property
    def sessions_dir(self) -> Path:
        """Sessions storage directory"""
        return self._config.get_path("paths.sessions_dir", self.data_dir / "sessions")

    @property
    def memory_dir(self) -> Path:
        """Memory storage directory"""
        return self._config.get_path("paths.memory_dir", self.data_dir / "memory")

    @property
    def skills_dir(self) -> Path:
        """Skills directory"""
        return self._config.get_path("paths.skills_dir", Path.cwd() / "skills")

    @property
    def plugins_dir(self) -> Path:
        """Plugins directory"""
        return self._config.get_path("paths.plugins_dir", Path.cwd() / "plugins")

    @property
    def cache_dir(self) -> Path:
        """Cache directory"""
        return self._config.get_path("paths.cache_dir", self.base_dir / "cache")

    def ensure_directories(self):
        """Ensure all directories exist"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_global_config: Optional[Config] = None
_global_paths: Optional[Paths] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def get_paths() -> Paths:
    """Get global paths instance"""
    global _global_paths
    if _global_paths is None:
        _global_paths = Paths(get_config())
    return _global_paths
