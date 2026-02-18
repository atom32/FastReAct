"""
FastReAct Nano - Multi-Tenant Manager

Manages user workspace isolation for multi-tenant deployments.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastreact.mcp.manager import MCPToolManager


class SecurityError(Exception):
    """Security violation error"""
    pass


@dataclass
class UserContext:
    """
    User-specific context for multi-tenant isolation.

    Each user has their own workspace, config, skills, and memory.
    """
    user_key: str  # Format: "channel:user_id" (e.g., "feishu:ou_xxx")
    workspace: Path
    config: dict
    skills_dir: Path
    memory_file: Path

    # Optional: User-specific MCP manager for tool isolation
    mcp_manager: Optional["MCPToolManager"] = field(default=None)


class MultiTenantManager:
    """
    Manage multi-tenant user isolation.

    Each user gets their own:
    - Workspace directory
    - Configuration file
    - Skills directory
    - Memory file

    User key format: "{channel}:{user_id}"
    Examples:
    - feishu:ou_1234567890abcdef
    - web:user@example.com
    - cli:local

    SECURITY: All paths are validated to prevent directory traversal attacks.
    """

    # Allowed characters in channel and user_id (prevent path traversal)
    _SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_@.=+-]+$')

    def __init__(self, base_workspace: Path):
        """
        Initialize multi-tenant manager

        Args:
            base_workspace: Base directory for all user workspaces

        Raises:
            ValueError: If base_workspace is not an absolute path
        """
        # Ensure base workspace is absolute path
        self._base_workspace = base_workspace.resolve()
        if not self._base_workspace.is_absolute():
            raise ValueError(
                f"base_workspace must be an absolute path, got: {base_workspace}"
            )

        self._user_contexts: dict[str, UserContext] = {}

        # Ensure base workspace exists
        self._base_workspace.mkdir(parents=True, exist_ok=True)

    def get_user_context(self, user_key: str) -> UserContext:
        """
        Get or create user context

        Args:
            user_key: User identifier in format "channel:user_id"

        Returns:
            UserContext for the user

        Raises:
            ValueError: If user_key format is invalid
        """
        if user_key not in self._user_contexts:
            self._user_contexts[user_key] = self._create_user_context(user_key)

        return self._user_contexts[user_key]

    def _create_user_context(self, user_key: str) -> UserContext:
        """
        Create user workspace and configuration

        Args:
            user_key: User identifier

        Returns:
            UserContext for the user

        Raises:
            ValueError: If user_key format is invalid
            SecurityError: If user_key contains malicious patterns
        """
        # Parse user_key
        if ":" not in user_key:
            raise ValueError(
                f"Invalid user_key format: '{user_key}'. "
                "Expected format: 'channel:user_id'"
            )

        channel, user_id = user_key.split(":", 1)

        if not channel or not user_id:
            raise ValueError(
                f"Invalid user_key: '{user_key}'. "
                "Channel and user_id must not be empty"
            )

        # SECURITY: Validate channel and user_id to prevent path traversal
        if not self._SAFE_PATTERN.match(channel):
            raise SecurityError(
                f"Channel contains unsafe characters: '{channel}'. "
                f"Allowed: alphanumeric, _, @, ., =, +, -"
            )

        if not self._SAFE_PATTERN.match(user_id):
            raise SecurityError(
                f"User ID contains unsafe characters: '{user_id}'. "
                f"Allowed: alphanumeric, _, @, ., =, +, -"
            )

        # SECURITY: Check for path traversal patterns explicitly
        dangerous_patterns = ["..", "~", "\x00"]
        for pattern in dangerous_patterns:
            if pattern in channel or pattern in user_id:
                raise SecurityError(
                    f"Path traversal attempt detected in user_key: '{user_key}'"
                )

        # Create workspace (sanitize user_id for filesystem)
        # Replace colons with underscores (already validated safe above)
        safe_user_id = user_id.replace(":", "_")
        workspace_name = f"{channel}_{safe_user_id}"

        # SECURITY: Ensure workspace is within base_workspace
        workspace = self._base_workspace / workspace_name
        workspace = workspace.resolve()  # Normalize path

        # SECURITY: Verify workspace is contained within base_workspace
        try:
            workspace.relative_to(self._base_workspace)
        except ValueError:
            raise SecurityError(
                f"Workspace path escape detected: '{workspace}' "
                f"is not contained within base_workspace: '{self._base_workspace}'"
            )

        workspace.mkdir(parents=True, exist_ok=True)

        # Create user directories
        skills_dir = workspace / "skills"
        skills_dir.mkdir(exist_ok=True)

        memory_file = workspace / "memory.json"

        # Load or create user config
        config_file = workspace / "config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            # Default config
            config = {
                "user_key": user_key,
                "channel": channel,
                "user_id": user_id,
                "preferences": {
                    "language": "zh-CN",
                    "timezone": "Asia/Shanghai",
                },
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

        return UserContext(
            user_key=user_key,
            workspace=workspace,
            config=config,
            skills_dir=skills_dir,
            memory_file=memory_file,
        )

    def list_users(self) -> list[str]:
        """List all user keys that have been loaded"""
        return list(self._user_contexts.keys())

    def get_user_workspace(self, user_key: str) -> Path:
        """
        Get user workspace path

        Args:
            user_key: User identifier

        Returns:
            Path to user workspace
        """
        context = self.get_user_context(user_key)
        return context.workspace

    def update_user_config(
        self,
        user_key: str,
        config_updates: dict,
    ) -> None:
        """
        Update user configuration

        Args:
            user_key: User identifier
            config_updates: Config keys/values to update
        """
        context = self.get_user_context(user_key)

        # Update in-memory config
        context.config.update(config_updates)

        # Persist to disk
        config_file = context.workspace / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(context.config, f, indent=2, ensure_ascii=False)

    def get_user_config(self, user_key: str) -> dict:
        """
        Get user configuration

        Args:
            user_key: User identifier

        Returns:
            User configuration dict
        """
        context = self.get_user_context(user_key)
        return context.config.copy()

    def clear_cache(self) -> None:
        """Clear all cached user contexts (does not delete workspaces)"""
        self._user_contexts.clear()
