"""
FastReAct Nano - MCP Tool Manager

Manages MCP server connections and integrates MCP tools into the ToolRegistry.
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING
from pathlib import Path

from fastreact.mcp.client import SimpleMCPClient
from fastreact.core.tools import ToolRegistry, Tool

if TYPE_CHECKING:
    from fastreact.core.multitenant import UserContext


class MCPToolWrapper(Tool):
    """
    Wrapper for MCP tools to integrate them into FastReAct's tool system.

    This allows MCP tools to be treated like native FastReAct tools.
    """

    def __init__(
        self,
        tool_name: str,
        server_name: str,
        mcp_client: SimpleMCPClient,
        mcp_manager: "MCPToolManager",  # ✅ Add manager reference
        description: str,
        parameters: Dict[str, Any],
        isolation_mode: str = "shared",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize MCP tool wrapper

        Args:
            tool_name: Name of the MCP tool
            server_name: Name of the MCP server (for namespacing)
            mcp_client: MCP client instance
            mcp_manager: MCP manager instance for resurrection
            description: Tool description from MCP server
            parameters: Tool parameter schema from MCP server
            isolation_mode: Isolation mode (shared, per_user, lazy_per_user)
            max_retries: Maximum reconnect attempts on connection loss (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)
        """
        self._tool_name = tool_name
        self._server_name = server_name
        self._mcp_client = mcp_client
        self._mcp_manager = mcp_manager  # ✅ Save manager for zombie detection
        self._description = description
        self._parameters = parameters
        self._isolation_mode = isolation_mode
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    @property
    def name(self) -> str:
        """Full tool name with server namespace"""
        return f"{self._server_name}_{self._tool_name}"

    @property
    def description(self) -> str:
        """Tool description"""
        return self._description

    @property
    def parameters(self) -> Dict[str, Any]:
        """Tool parameter schema"""
        return self._parameters

    async def execute(self, user_context: Optional["UserContext"] = None, **kwargs) -> str:
        """
        Execute the MCP tool with zombie resurrection on crash detection

        Args:
            user_context: User context for multi-tenant isolation (optional)
            **kwargs: Tool parameters

        Returns:
            Tool result as string

        This method implements:
        1. Zombie process detection (check if server crashed)
        2. Automatic resurrection if server is dead
        3. Automatic reconnection on connection loss
        4. Retry logic for transient errors
        """
        import sys
        import asyncio

        # Extract user_key from user_context
        user_key = user_context.user_key if user_context else None

        # Track actual call attempts (including retries)
        call_attempts = 0

        # Try to execute with retry logic
        for attempt in range(self._max_retries):
            try:
                call_attempts += 1
                return await self._mcp_client.call_tool(
                    self._tool_name,
                    kwargs,
                    user_key=user_key
                )

            except RuntimeError as e:
                error_msg = str(e).lower()

                # Check if it's a connection error
                if "not connected" in error_msg or "connection" in error_msg:
                    # Check if server crashed (using manager's detection)
                    if hasattr(self._mcp_manager, 'is_server_alive'):
                        if not self._mcp_manager.is_server_alive(self._server_name):
                            # Server crashed, try to resurrect
                            print(
                                f"[WARNING] Server '{self._server_name}' crashed during execution, resurrecting...",
                                file=sys.stderr
                            )
                            if await self._mcp_manager.resurrect_server(self._server_name):
                                # Resurrection successful, update client reference
                                if self._server_name in self._mcp_manager._servers:
                                    self._mcp_client = self._mcp_manager._servers[self._server_name]
                                # Retry the call
                                continue
                            else:
                                # Resurrection failed
                                return f"[MCP_ERROR] Server '{self._server_name}' crashed and resurrection failed"

                    # Check if we should try to reconnect
                    if attempt < self._max_retries - 1:
                        # Try to reconnect
                        print(
                            f"[WARNING] MCP connection lost for '{self.name}', "
                            f"reconnecting... (attempt {attempt + 1}/{self._max_retries})",
                            file=sys.stderr
                        )

                        reconnect_success = False

                        try:
                            # Wait before retry
                            await asyncio.sleep(self._retry_delay)

                            # Reconnect
                            await self._mcp_client.connect()
                            print(f"[OK] Reconnected to MCP server '{self._server_name}'", file=sys.stderr)
                            reconnect_success = True

                        except Exception as reconnect_error:
                            print(
                                f"[ERROR] Reconnect failed for '{self.name}': {reconnect_error}",
                                file=sys.stderr
                            )
                            # Reconnect failed, but will retry the call in next loop iteration
                            continue

                        # If reconnect succeeded, continue to retry the call
                        if reconnect_success:
                            continue

                # All retries exhausted or not a connection error
                return f"[MCP_ERROR] {type(e).__name__}: {str(e)} (after {call_attempts} attempts)"

            except Exception as e:
                # Non-connection errors, don't retry
                return f"[MCP_ERROR] {type(e).__name__}: {str(e)}"


class MCPToolManager:
    """
    Manage MCP server connections and tool registration.

    This manager:
    1. Connects to MCP servers
    2. Lists available tools from each server
    3. Wraps MCP tools as FastReAct tools
    4. Registers them to ToolRegistry
    5. Manages server lifecycle (connect/close)
    """

    def __init__(self, tool_registry: ToolRegistry, isolation_mode: str = "shared"):
        """
        Initialize MCP tool manager

        Args:
            tool_registry: FastReAct tool registry to register MCP tools to
            isolation_mode: Default isolation mode for tools (shared, per_user, lazy_per_user)
        """
        self._tools = tool_registry
        self._servers: Dict[str, SimpleMCPClient] = {}
        self._tool_wrappers: Dict[str, MCPToolWrapper] = {}
        self._isolation_mode = isolation_mode

        # Store server configs for resurrection (Zombie Process Resurrection)
        self._server_configs: Dict[str, Dict[str, Any]] = {}

    async def add_server(
        self,
        name: str,
        server_command: str,
        server_args: list[str] = None,
    ) -> None:
        """
        Add MCP server and register its tools

        Args:
            name: Server name (for namespacing tools)
            server_command: Command to spawn MCP server
            server_args: Arguments for server command

        Raises:
            RuntimeError: If server fails to start or tool registration fails
        """
        import sys

        try:
            # Connect to server
            client = SimpleMCPClient(
                server_command=server_command,
                server_args=server_args or [],
            )
            await client.connect()

            # List tools
            tools = await client.list_tools()

            # Register each tool to ToolRegistry
            for tool_def in tools:
                await self._register_mcp_tool(name, tool_def, client)

            self._servers[name] = client

            # ✅ Save server config for resurrection
            self._server_configs[name] = {
                "server_command": server_command,
                "server_args": server_args or [],
                "isolation_mode": self._isolation_mode,
            }
            print(f"[OK] MCP server '{name}' registered and ready for resurrection", file=sys.stderr)

        except Exception as e:
            raise RuntimeError(f"Failed to add MCP server '{name}': {e}")

    async def _register_mcp_tool(
        self,
        server_name: str,
        tool_def: Dict[str, Any],
        client: SimpleMCPClient,
    ) -> None:
        """
        Register MCP tool as a FastReAct tool

        Args:
            server_name: Server name
            tool_def: Tool definition from MCP server
            client: MCP client instance

        Raises:
            ValueError: If tool already registered
        """
        # Create wrapper
        wrapper = MCPToolWrapper(
            tool_name=tool_def["name"],
            server_name=server_name,
            mcp_client=client,
            mcp_manager=self,  # ✅ Pass manager for zombie detection
            description=tool_def.get("description", ""),
            parameters=tool_def.get("inputSchema", {}),
            isolation_mode=self._isolation_mode,
        )

        # Check if already registered
        if wrapper.name in self._tools.list_all():
            raise ValueError(f"Tool '{wrapper.name}' already registered")

        # Register to ToolRegistry
        self._tools.register(wrapper)

        # Track wrapper
        self._tool_wrappers[wrapper.name] = wrapper

    def list_servers(self) -> list[str]:
        """List all connected MCP server names"""
        return list(self._servers.keys())

    def list_mcp_tools(self) -> list[str]:
        """List all registered MCP tool names"""
        return list(self._tool_wrappers.keys())

    def is_server_alive(self, server_name: str) -> bool:
        """
        Check if MCP server process is still alive (Zombie Process Detection)

        Args:
            server_name: Name of the server to check

        Returns:
            True if process is alive, False if crashed (zombie)
        """
        import sys

        client = self._servers.get(server_name)
        if not client:
            return False

        # Check if process exists and is running
        if client._process and client._process.returncode is not None:
            # Process has exited (zombie detected!)
            print(
                f"[WARNING] Zombie process detected: MCP server '{server_name}' "
                f"crashed with exit code {client._process.returncode}",
                file=sys.stderr
            )
            return False

        return True

    async def resurrect_server(self, server_name: str) -> bool:
        """
        Resurrect a crashed MCP server (Zombie Process Resurrection)

        Automatically restarts a crashed server using its saved configuration.

        Args:
            server_name: Name of the server to resurrect

        Returns:
            True if resurrection successful, False otherwise

        Raises:
            RuntimeError: If server config not found or resurrection fails
        """
        import sys

        # Check if server config exists
        if server_name not in self._server_configs:
            print(
                f"[ERROR] Cannot resurrect '{server_name}': no saved configuration",
                file=sys.stderr
            )
            return False

        config = self._server_configs[server_name]

        try:
            print(f"[INFO] Resurrecting MCP server '{server_name}'...", file=sys.stderr)

            # Close old connection if exists
            if server_name in self._servers:
                try:
                    await self._servers[server_name].close()
                except Exception:
                    pass  # Ignore close errors

            # Create new client and connect
            client = SimpleMCPClient(
                server_command=config["server_command"],
                server_args=config["server_args"],
            )
            await client.connect()

            # List tools
            tools = await client.list_tools()

            # Re-register tools
            for tool_def in tools:
                # Remove old wrapper if exists
                old_wrapper_name = f"{server_name}_{tool_def.get('name')}"
                if old_wrapper_name in self._tool_wrappers:
                    del self._tool_wrappers[old_wrapper_name]
                if old_wrapper_name in self._tools._tools:
                    del self._tools._tools[old_wrapper_name]

                # Register new wrapper
                await self._register_mcp_tool(server_name, tool_def, client)

            # Update server reference
            self._servers[server_name] = client

            print(
                f"[OK] MCP server '{server_name}' resurrected successfully "
                f"({len(tools)} tools available)",
                file=sys.stderr
            )
            return True

        except Exception as e:
            print(
                f"[ERROR] Failed to resurrect MCP server '{server_name}': {e}",
                file=sys.stderr
            )
            return False

    async def ensure_server_alive(self, server_name: str) -> bool:
        """
        Ensure server is alive, resurrect if needed (Automatic Zombie Detection)

        This should be called before any tool execution to auto-resurrect crashed servers.

        Args:
            server_name: Name of the server to check

        Returns:
            True if server is alive or was successfully resurrected
        """
        import sys

        # Check if alive
        if self.is_server_alive(server_name):
            return True

        # Server is dead, try to resurrect
        print(
            f"[INFO] Zombie detected for '{server_name}', attempting resurrection...",
            file=sys.stderr
        )
        return await self.resurrect_server(server_name)

    async def close_all(self) -> None:
        """Close all MCP server connections"""
        for name, client in self._servers.items():
            try:
                await client.close()
            except Exception:
                # Ignore errors during close
                pass

        self._servers.clear()
        self._tool_wrappers.clear()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_all()
