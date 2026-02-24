"""
FastReAct Nano - Credentials Management

Secure credential storage with environment variable support.
Separates sensitive information from config.json.
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class Credentials:
    """
    Secure credential storage manager.

    Handles:
    - Loading from ~/.fastreact/credentials.json
    - Environment variable resolution (${VAR_NAME})
    - Default values (${VAR_NAME:-default})
    - Secure file permissions (0600)
    """

    llm_api_keys: Dict[str, str] = field(default_factory=dict)
    mcp_api_keys: Dict[str, str] = field(default_factory=dict)
    custom: Dict[str, Any] = field(default_factory=dict)

    # File path for credentials
    _credentials_path: Optional[Path] = field(default=None, init=False, repr=False)

    @classmethod
    def load(cls, credentials_path: Optional[Path] = None) -> "Credentials":
        """
        Load credentials from file or create empty instance.

        Args:
            credentials_path: Path to credentials file. If None, uses default locations.

        Returns:
            Credentials instance with loaded and resolved credentials
        """
        import sys

        # Default credential locations
        if credentials_path is None:
            default_paths = [
                Path.home() / ".fastreact" / "credentials.json",
                Path.cwd() / ".fastreact" / "credentials.json",
            ]
            for path in default_paths:
                if path.exists():
                    credentials_path = path
                    break

        credentials = cls()

        if credentials_path and credentials_path.exists():
            credentials._credentials_path = credentials_path

            try:
                with open(credentials_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Load credentials with env var resolution
                credentials.llm_api_keys = cls._resolve_dict(
                    data.get("llm_api_keys", {})
                )
                credentials.mcp_api_keys = cls._resolve_dict(
                    data.get("mcp_api_keys", {})
                )
                credentials.custom = cls._resolve_dict(
                    data.get("custom", {})
                )

                print(f"[OK] Credentials loaded from {credentials_path}", file=sys.stderr)

            except json.JSONDecodeError as e:
                print(
                    f"[WARNING] Failed to parse credentials file: {e}",
                    file=sys.stderr
                )
            except Exception as e:
                print(
                    f"[WARNING] Failed to load credentials: {e}",
                    file=sys.stderr
                )

        return credentials

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get credential value by key with environment variable priority.

        Priority order (highest to lowest):
        1. Direct environment variable (e.g., FASTRACT_LLMAPIKEYS_OPENAI)
        2. Value from credentials file
        3. Default value

        Supports dot notation for nested access:
        - "llm_api_keys.openai" -> env: FASTRACT_LLMAPIKEYS_OPENAI
        - "mcp_api_keys.graphrag" -> env: FASTRACT_MCPAPIKEYS_GRAPHRAG
        - "custom.my_setting" -> env: FASTRACT_CUSTOM_MYSETTING

        Args:
            key: Credential key (supports dot notation)
            default: Default value if not found

        Returns:
            Credential value or default
        """
        import sys

        # 1. Check environment variable first (cloud-native priority)
        env_key = f"FASTRACT_{key.upper().replace('.', '_').replace('-', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # 2. Check credentials file
        parts = key.split(".")

        # Navigate through nested structure
        current: Any = {
            "llm_api_keys": self.llm_api_keys,
            "mcp_api_keys": self.mcp_api_keys,
            "custom": self.custom,
        }

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default

        return current if current is not None else default

    def save(self, credentials_path: Optional[Path] = None) -> None:
        """
        Save credentials to file with secure permissions.

        Args:
            credentials_path: Path to save credentials. If None, uses loaded path or default.
        """
        import stat
        import sys

        if credentials_path is None:
            credentials_path = self._credentials_path or Path.home() / ".fastreact" / "credentials.json"

        # Ensure parent directory exists
        credentials_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare data
        data = {
            "llm_api_keys": self.llm_api_keys,
            "mcp_api_keys": self.mcp_api_keys,
            "custom": self.custom,
        }

        # Write to file
        with open(credentials_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Set secure permissions (user read/write only)
        credentials_path.chmod(0o600)

        self._credentials_path = credentials_path
        print(f"[OK] Credentials saved to {credentials_path} (mode: 0600)", file=sys.stderr)

    @staticmethod
    def _resolve_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve environment variables in dictionary values.

        Supports:
        - ${VAR_NAME} - use environment variable
        - ${VAR_NAME:-default} - use environment variable or default

        Args:
            data: Dictionary with potential env var references

        Returns:
            Dictionary with resolved values
        """
        resolved = {}

        for key, value in data.items():
            if isinstance(value, str):
                resolved[key] = Credentials._resolve_env_var(value)
            elif isinstance(value, dict):
                resolved[key] = Credentials._resolve_dict(value)
            elif isinstance(value, list):
                resolved[key] = [
                    Credentials._resolve_env_var(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """
        Resolve environment variable references in a string.

        Patterns:
        - ${VAR_NAME} -> os.getenv("VAR_NAME", "")
        - ${VAR_NAME:-default} -> os.getenv("VAR_NAME", "default")

        Args:
            value: String potentially containing env var references

        Returns:
            String with resolved env vars
        """
        # Pattern for ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default)

        return re.sub(pattern, replace_var, value)

    def get_auth_token(self, token_ref: str) -> Optional[str]:
        """
        Get authentication token from reference.

        Token references can be:
        - "mcp.server_name" -> mcp_api_keys["server_name"]
        - "llm.provider" -> llm_api_keys["provider"]
        - "custom.key" -> custom["key"]
        - Direct value (if no dot in reference)

        Args:
            token_ref: Token reference string

        Returns:
            Authentication token or None if not found
        """
        return self.get(token_ref)


# Default credentials instance
_default_credentials: Optional[Credentials] = None


def get_credentials(credentials_path: Optional[Path] = None) -> Credentials:
    """
    Get or create default credentials instance.

    Args:
        credentials_path: Optional path to credentials file

    Returns:
        Credentials instance (singleton)
    """
    global _default_credentials

    if _default_credentials is None:
        _default_credentials = Credentials.load(credentials_path)

    return _default_credentials
