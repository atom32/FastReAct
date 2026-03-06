"""
FastReAct Nano - Multi-Tenant Manager

Manages user workspace isolation for multi-tenant deployments.
"""

import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastreact.mcp.manager import MCPToolManager
    from fastreact.core.config_manager import ConfigManager


class SecurityError(Exception):
    """Security violation error"""
    pass


# ============================================================================
# Global Agent Management (Unified)
# ============================================================================

_global_agent: Optional["Agent"] = None


def get_global_agent(
    base_workspace: Optional[Path] = None,
    config: Optional["Config"] = None,
) -> "Agent":
    """
    Get or create global Agent instance (application-level singleton)

    This ensures all adapters share the same Agent for consistent behavior
    and efficient resource usage.

    Args:
        base_workspace: Base workspace path (default: ./workspace)
        config: Configuration object (default: Config.load())

    Returns:
        Shared Agent instance
    """
    global _global_agent

    if _global_agent is None:
        from fastreact.core.config import Config
        from fastreact.agent import Agent

        # Load config if not provided
        if config is None:
            config = Config.load()

        # Determine workspace
        workspace_path = base_workspace or Path.cwd() / "workspace"

        _global_agent = Agent(
            config=config,
            multitenant=True,  # Always use multi-tenant mode
            base_workspace=workspace_path,
        )
        print(f"[MULTITENANT] Created global shared Agent")

    return _global_agent


def reset_global_agent():
    """
    Reset global agent instance

    WARNING: This should only be used in tests or when completely
    shutting down the application. Use with caution.
    """
    global _global_agent
    _global_agent = None
    print(f"[MULTITENANT] Reset global agent")


# ============================================================================
# Temporary User Utilities
# ============================================================================

def generate_temp_user_key(channel: str = "web") -> str:
    """
    Generate a temporary user identifier

    Format: {channel}:temp_{uuid8}

    Args:
        channel: Channel identifier (default: "web")

    Returns:
        Temporary user key string
    """
    temp_id = uuid.uuid4().hex[:8]
    return f"{channel}:temp_{temp_id}"


def is_temp_user_key(user_key: str) -> bool:
    """
    Check if a user_key is temporary

    Args:
        user_key: User key to check

    Returns:
        True if user_key matches temp pattern
    """
    return ":temp_" in user_key


def validate_user_key(user_key: Optional[str]) -> tuple[bool, str]:
    """
    Validate user_key format

    Args:
        user_key: User key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not user_key:
        return False, "user_key is required"

    if ":" not in user_key:
        return False, f"Invalid user_key format: '{user_key}'. Expected: 'channel:user_id'"

    parts = user_key.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False, f"Invalid user_key: '{user_key}'. Channel and user_id must not be empty"

    return True, ""


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

    def __init__(
        self,
        base_workspace: Path,
        temp_user_ttl: int = 86400,
        config_manager: Optional["ConfigManager"] = None,
    ):
        """
        Initialize multi-tenant manager

        Args:
            base_workspace: Base directory for all user workspaces
            temp_user_ttl: Temporary user TTL in seconds (default: 24 hours)
            config_manager: Optional ConfigManager for config inheritance

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

        # Temporary user tracking
        self._temp_users: dict[str, datetime] = {}  # user_key -> last_activity
        self._temp_user_ttl = temp_user_ttl  # Time to live in seconds

        # Config manager for inheritance (Phase 2)
        self._config_manager = config_manager

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

            # Register with config manager for inheritance (Phase 2)
            if self._config_manager:
                self._config_manager.set_user_config(user_key, config)
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

            # Register with config manager for inheritance (Phase 2)
            if self._config_manager:
                self._config_manager.set_user_config(user_key, config)

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

    # Temporary User Management

    @staticmethod
    def validate_user_key(user_key: Optional[str]) -> tuple[bool, str]:
        """
        Validate user_key format

        Args:
            user_key: User key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return validate_user_key(user_key)

    @staticmethod
    def generate_temp_user_key(channel: str = "web") -> str:
        """
        Generate a temporary user identifier

        Args:
            channel: Channel identifier (default: "web")

        Returns:
            Temporary user key string
        """
        return generate_temp_user_key(channel)

    def is_temp_user(self, user_key: str) -> bool:
        """
        Check if a user_key is a temporary user

        Args:
            user_key: User identifier

        Returns:
            True if user_key is a temporary user
        """
        return is_temp_user_key(user_key)

    def ensure_temp_user(self, user_key: Optional[str], fallback_channel: str = "web") -> str:
        """
        Ensure we have a valid user_key (generate temp if needed)

        Args:
            user_key: User key (may be None or empty)
            fallback_channel: Channel to use for temp user generation

        Returns:
            Valid user_key (original or generated temp)
        """
        if user_key:
            # Validate format
            is_valid, error = self.validate_user_key(user_key)
            if not is_valid:
                raise ValueError(error)
            return user_key
        else:
            # Generate temporary user_key
            temp_key = self.generate_temp_user_key(fallback_channel)
            print(f"[MULTITENANT] Generated temp user_key: {temp_key}")
            return temp_key

    def register_temp_user(self, user_key: str) -> None:
        """
        Register or update a temporary user's last activity time

        Args:
            user_key: Temporary user identifier
        """
        if self.is_temp_user(user_key):
            self._temp_users[user_key] = datetime.utcnow()
            print(f"[MULTITENANT] Registered temp user: {user_key}")

    def update_temp_user_activity(self, user_key: str) -> None:
        """
        Update a temporary user's last activity time

        Args:
            user_key: User identifier (only updates if temp user)
        """
        if self.is_temp_user(user_key) and user_key in self._temp_users:
            self._temp_users[user_key] = datetime.utcnow()

    def cleanup_temp_users(self, max_age_seconds: Optional[int] = None) -> int:
        """
        Clean up expired temporary users and their workspaces

        Args:
            max_age_seconds: Maximum age in seconds (default: use temp_user_ttl)

        Returns:
            Number of users cleaned up
        """
        if max_age_seconds is None:
            max_age_seconds = self._temp_user_ttl

        now = datetime.utcnow()
        expired_users = []

        # Find expired users
        for user_key, last_activity in self._temp_users.items():
            age = (now - last_activity).total_seconds()

            if age > max_age_seconds:
                expired_users.append(user_key)

        # Clean up workspaces
        for user_key in expired_users:
            try:
                self._cleanup_user_workspace(user_key)
                del self._temp_users[user_key]

                # Also remove from user contexts cache
                if user_key in self._user_contexts:
                    del self._user_contexts[user_key]

                print(f"[MULTITENANT] Cleaned expired temp user: {user_key}")
            except Exception as e:
                print(f"[ERROR] Failed to cleanup temp user {user_key}: {e}")

        if expired_users:
            print(f"[MULTITENANT] Cleaned {len(expired_users)} expired temp users")

        return len(expired_users)

    def _cleanup_user_workspace(self, user_key: str) -> None:
        """
        Clean up a user's workspace directory

        Args:
            user_key: User identifier
        """
        try:
            workspace = self.get_user_workspace(user_key)
            if workspace.exists():
                shutil.rmtree(workspace)
                print(f"[MULTITENANT] Deleted workspace: {workspace}")
        except Exception as e:
            print(f"[ERROR] Failed to delete workspace for {user_key}: {e}")

    def get_temp_user_stats(self) -> dict:
        """
        Get statistics about temporary users

        Returns:
            Dictionary with temp user statistics
        """
        now = datetime.utcnow()
        active_count = 0
        expired_count = 0

        for user_key, last_activity in self._temp_users.items():
            age = (now - last_activity).total_seconds()
            if age > self._temp_user_ttl:
                expired_count += 1
            else:
                active_count += 1

        return {
            "total_temp_users": len(self._temp_users),
            "active_temp_users": active_count,
            "expired_temp_users": expired_count,
            "temp_user_ttl": self._temp_user_ttl,
        }
