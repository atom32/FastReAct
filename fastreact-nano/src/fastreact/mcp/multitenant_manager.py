"""
FastReAct Nano - Multi-Tenant MCP Manager

Manages MCP server connections with per-user isolation support.
Supports three isolation modes: shared, per_user, and lazy_per_user.
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timedelta

from fastreact.mcp.client import SimpleMCPClient
from fastreact.mcp.manager import MCPToolManager, MCPToolWrapper
from fastreact.core.tools import ToolRegistry

if TYPE_CHECKING:
    from fastreact.core.multitenant import UserContext
    from fastreact.core.config import MCPServerConfig


class LazyMCPInstance:
    """
    Lazy-loaded MCP server instance with timeout management.

    Used for lazy_per_user isolation mode to create instances on-demand
    and clean them up after a period of inactivity.
    """

    def __init__(
        self,
        manager: MCPToolManager,
        idle_timeout: int = 300,
    ):
        """
        Initialize lazy MCP instance

        Args:
            manager: The MCP tool manager for this instance
            idle_timeout: Seconds of inactivity before cleanup (default: 300)
        """
        self._manager = manager
        self._idle_timeout = idle_timeout
        self._last_used = datetime.now()
        self._ref_count = 0

    @property
    def manager(self) -> MCPToolManager:
        """Get the underlying MCP manager"""
        self._last_used = datetime.now()
        self._ref_count += 1
        return self._manager

    async def release(self) -> None:
        """Release a reference to this instance"""
        if self._ref_count > 0:
            self._ref_count -= 1

    def is_idle(self) -> bool:
        """Check if this instance has been idle longer than timeout"""
        if self._ref_count > 0:
            return False

        idle_time = (datetime.now() - self._last_used).total_seconds()
        return idle_time >= self._idle_timeout

    async def cleanup(self) -> None:
        """Clean up resources"""
        await self._manager.close_all()


class MultiTenantMCPManager:
    """
    Manage multi-user MCP tool isolation.

    This manager supports three isolation modes:
    - shared: All users share the same MCP server process
    - per_user: Each user gets their own MCP server process
    - lazy_per_user: Create user processes on-demand, cleanup after timeout

    Architecture:
        _shared_managers: Dict[server_name, MCPToolManager]
        _user_managers: Dict[user_key, Dict[server_name, LazyMCPInstance]]
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        multitenant_manager: Optional["MultiTenantManager"] = None,
    ):
        """
        Initialize multi-tenant MCP manager

        Args:
            tool_registry: FastReAct tool registry
            multitenant_manager: Multi-tenant manager for user context
        """
        self._tool_registry = tool_registry
        self._multitenant = multitenant_manager

        # Shared mode managers (one per server, all users)
        self._shared_managers: Dict[str, MCPToolManager] = {}

        # Per-user mode managers (one per user per server)
        self._user_managers: Dict[str, Dict[str, LazyMCPInstance]] = {}

        # Background cleanup task for lazy instances
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_running = False

    async def get_manager(
        self,
        server_name: str,
        server_config: "MCPServerConfig",
        user_key: Optional[str] = None,
    ) -> tuple[MCPToolManager, Optional[SimpleMCPClient]]:
        """
        Get MCP manager and client for a specific user and server.

        Args:
            server_name: Name of the MCP server
            server_config: Server configuration
            user_key: User identifier (required for per_user and lazy_per_user modes)

        Returns:
            Tuple of (MCPToolManager, Optional[SimpleMCPClient])

        Raises:
            ValueError: If user_key is required but not provided
            RuntimeError: If server fails to start
        """
        isolation = server_config.isolation

        if isolation == "shared":
            # Global shared manager
            return await self._get_shared_manager(server_name, server_config)

        elif isolation == "per_user":
            # Per-user isolation
            if not user_key:
                raise ValueError("user_key required for per_user isolation mode")
            return await self._get_per_user_manager(server_name, server_config, user_key)

        elif isolation == "lazy_per_user":
            # Lazy per-user isolation with timeout
            if not user_key:
                raise ValueError("user_key required for lazy_per_user isolation mode")
            return await self._get_lazy_manager(server_name, server_config, user_key)

        else:
            raise ValueError(f"Unknown isolation mode: {isolation}")

    async def _get_shared_manager(
        self,
        server_name: str,
        server_config: "MCPServerConfig",
    ) -> tuple[MCPToolManager, None]:
        """Get or create shared manager for all users"""
        if server_name not in self._shared_managers:
            manager = MCPToolManager(
                self._tool_registry,
                isolation_mode="shared"
            )
            await manager.add_server(
                server_config.name,
                server_config.command,
                server_config.args
            )
            self._shared_managers[server_name] = manager

        return self._shared_managers[server_name], None

    async def _get_per_user_manager(
        self,
        server_name: str,
        server_config: "MCPServerConfig",
        user_key: str,
    ) -> tuple[MCPToolManager, None]:
        """Get or create per-user manager"""
        if user_key not in self._user_managers:
            self._user_managers[user_key] = {}

        user_servers = self._user_managers[user_key]

        if server_name not in user_servers:
            # Apply user-specific arguments
            args = self._substitute_user_args(
                server_config.per_user_args_template or server_config.args,
                user_key
            )

            manager = MCPToolManager(
                self._tool_registry,
                isolation_mode="per_user"
            )
            await manager.add_server(
                server_config.name,
                server_config.command,
                args
            )

            # Wrap in lazy instance (no timeout for per_user mode)
            user_servers[server_name] = LazyMCPInstance(
                manager=manager,
                idle_timeout=0,  # No timeout
            )

        instance = self._user_managers[user_key][server_name]
        return instance.manager, None

    async def _get_lazy_manager(
        self,
        server_name: str,
        server_config: "MCPServerConfig",
        user_key: str,
    ) -> tuple[MCPToolManager, None]:
        """Get or create lazy per-user manager with timeout"""
        if user_key not in self._user_managers:
            self._user_managers[user_key] = {}

        user_servers = self._user_managers[user_key]

        # Check if instance exists and is still valid
        if server_name in user_servers:
            instance = user_servers[server_name]
            if not instance.is_idle():
                return instance.manager, None
            else:
                # Clean up idle instance
                await instance.cleanup()
                del user_servers[server_name]

        # Check max instances limit
        max_instances = server_config.max_instances or 10
        total_instances = sum(len(servers) for servers in self._user_managers.values())
        if total_instances >= max_instances:
            # Try to clean up idle instances first
            await self._cleanup_idle_instances()
            total_instances = sum(len(servers) for servers in self._user_managers.values())

            if total_instances >= max_instances:
                raise RuntimeError(
                    f"Maximum MCP instances ({max_instances}) reached. "
                    "Consider increasing max_instances or using shared mode."
                )

        # Apply user-specific arguments
        args = self._substitute_user_args(
            server_config.per_user_args_template or server_config.args,
            user_key
        )

        manager = MCPToolManager(
            self._tool_registry,
            isolation_mode="lazy_per_user"
        )
        await manager.add_server(
            server_config.name,
            server_config.command,
            args
        )

        idle_timeout = server_config.idle_timeout or 300
        instance = LazyMCPInstance(manager, idle_timeout=idle_timeout)
        user_servers[server_name] = instance

        # Start background cleanup task if not running
        if not self._cleanup_running:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._cleanup_running = True

        return instance.manager, None

    def _substitute_user_args(
        self,
        template: list[str],
        user_key: str,
    ) -> list[str]:
        """
        Substitute user-specific variables in argument template.

        Supported placeholders:
        - {user_key}: Full user key (e.g., "feishu:ou_123")
        - {user_workspace}: Path to user workspace

        Args:
            template: Argument template list
            user_key: User identifier

        Returns:
            Substituted argument list
        """
        if not self._multitenant:
            # No multi-tenant manager, return template as-is
            return template

        # Get user context
        user_context = self._multitenant.get_user_context(user_key)

        result = []
        for arg in template:
            # Substitute placeholders
            arg = arg.replace("{user_key}", user_key)
            arg = arg.replace("{user_workspace}", str(user_context.workspace))
            result.append(arg)

        return result

    async def preload_shared_servers(self, servers_config: list["MCPServerConfig"]) -> None:
        """
        Preload shared-mode servers for tool discovery.

        This method loads all servers with isolation="shared" mode so their tools
        can be discovered during agent initialization. Servers with per_user or
        lazy_per_user isolation are not preloaded and will be created on-demand.

        Args:
            servers_config: List of MCP server configurations
        """
        for server_config in servers_config:
            if server_config.isolation == "shared":
                # Preload shared servers for tool discovery
                try:
                    await self._get_shared_manager(server_config.name, server_config)
                except Exception as e:
                    # Log error but continue with other servers
                    import sys
                    print(f"[ERROR] Failed to preload shared MCP server '{server_config.name}': {e}", file=sys.stderr)

    def list_mcp_tools(self) -> list[str]:
        """
        List all MCP tool names from preloaded shared servers.

        Note: This only lists tools from shared servers that have been preloaded.
        Tools from per_user or lazy_per_user servers will be available on-demand
        during execution.

        Returns:
            List of tool names
        """
        tool_names = []
        for manager in self._shared_managers.values():
            tool_names.extend(manager.list_mcp_tools())
        return tool_names

    @property
    def _tool_wrappers(self) -> dict[str, MCPToolWrapper]:
        """
        Get all tool wrappers from preloaded shared servers.

        This property provides compatibility with MCPToolManager's interface
        for tool discovery purposes.

        Returns:
            Dictionary mapping tool names to MCPToolWrapper instances
        """
        wrappers = {}
        for manager in self._shared_managers.values():
            wrappers.update(manager._tool_wrappers)
        return wrappers

    async def _cleanup_idle_instances(self) -> None:
        """Clean up all idle instances across all users"""
        for user_key in list(self._user_managers.keys()):
            user_servers = self._user_managers[user_key]

            for server_name in list(user_servers.keys()):
                instance = user_servers[server_name]
                if instance.is_idle():
                    await instance.cleanup()
                    del user_servers[server_name]

            # Remove empty user entries
            if not user_servers:
                del self._user_managers[user_key]

    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up idle instances"""
        while self._cleanup_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_idle_instances()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue loop
                pass

    async def close_all(self) -> None:
        """Close all MCP server connections"""
        # Stop cleanup task
        self._cleanup_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close shared managers
        for manager in self._shared_managers.values():
            await manager.close_all()
        self._shared_managers.clear()

        # Close all user managers
        for user_servers in self._user_managers.values():
            for instance in user_servers.values():
                await instance.cleanup()
        self._user_managers.clear()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_all()
