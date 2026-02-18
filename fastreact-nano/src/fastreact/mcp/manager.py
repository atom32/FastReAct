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
        description: str,
        parameters: Dict[str, Any],
        isolation_mode: str = "shared",
    ):
        """
        Initialize MCP tool wrapper

        Args:
            tool_name: Name of the MCP tool
            server_name: Name of the MCP server (for namespacing)
            mcp_client: MCP client instance
            description: Tool description from MCP server
            parameters: Tool parameter schema from MCP server
            isolation_mode: Isolation mode (shared, per_user, lazy_per_user)
        """
        self._tool_name = tool_name
        self._server_name = server_name
        self._mcp_client = mcp_client
        self._description = description
        self._parameters = parameters
        self._isolation_mode = isolation_mode

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
        Execute the MCP tool

        Args:
            user_context: User context for multi-tenant isolation (optional)
            **kwargs: Tool parameters

        Returns:
            Tool result as string
        """
        try:
            # Extract user_key from user_context
            user_key = user_context.user_key if user_context else None

            # Call MCP tool with user_key for isolation
            return await self._mcp_client.call_tool(
                self._tool_name,
                kwargs,
                user_key=user_key
            )
        except Exception as e:
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
