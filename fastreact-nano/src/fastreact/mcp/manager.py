"""
FastReAct Nano - MCP Tool Manager

Manages MCP server connections and integrates MCP tools into the ToolRegistry.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING, Union
from pathlib import Path

from fastreact.mcp.client import SimpleMCPClient
from fastreact.mcp.http_client import StreamableHTTPMCPClient
from fastreact.core.tools import ToolRegistry, Tool
from fastreact.core.credentials import Credentials, get_credentials

if TYPE_CHECKING:
    from fastreact.core.multitenant import UserContext

logger = logging.getLogger(__name__)


class MCPToolWrapper(Tool):
    """
    Wrapper for MCP tools to integrate them into FastReAct's tool system.

    This allows MCP tools to be treated like native FastReAct tools.
    """

    def __init__(
        self,
        tool_name: str,
        server_name: str,
        mcp_client: Union[SimpleMCPClient, StreamableHTTPMCPClient],
        mcp_manager: "MCPToolManager",
        description: str,
        parameters: Dict[str, Any],
        isolation_mode: str = "shared",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        transport: str = "stdio",
    ):
        """
        Initialize MCP tool wrapper

        Args:
            tool_name: Name of the MCP tool
            server_name: Name of the MCP server (for namespacing)
            mcp_client: MCP client instance (stdio or http)
            mcp_manager: MCP manager instance for resurrection
            description: Tool description from MCP server
            parameters: Tool parameter schema from MCP server
            isolation_mode: Isolation mode (shared, per_user, lazy_per_user)
            max_retries: Maximum reconnect attempts on connection loss (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)
            transport: Transport type ("stdio" or "http")
        """
        self._tool_name = tool_name
        self._server_name = server_name
        self._mcp_client = mcp_client
        self._mcp_manager = mcp_manager
        self._description = description
        self._parameters = parameters
        self._isolation_mode = isolation_mode
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._transport = transport

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
        1. Zombie process detection (check if server crashed) - for stdio
        2. Automatic resurrection if server is dead - for stdio
        3. Automatic reconnection on connection loss - for both transports
        4. Retry logic for transient errors - for both transports
        """
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
                    # For stdio transport, check if server crashed
                    if self._transport == "stdio" and hasattr(self._mcp_manager, 'is_server_alive'):
                        if not self._mcp_manager.is_server_alive(self._server_name):
                            # Server crashed, try to resurrect
                            logger.warning(
                                "Server '%s' crashed during execution, resurrecting...",
                                self._server_name,
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

                    # For both transports, try to reconnect
                    if attempt < self._max_retries - 1:
                        # Try to reconnect
                        logger.warning(
                            "MCP connection lost for '%s', reconnecting... (attempt %s/%s)",
                            self.name,
                            attempt + 1,
                            self._max_retries,
                        )

                        reconnect_success = False

                        try:
                            # Wait before retry
                            await asyncio.sleep(self._retry_delay)

                            # Reconnect (works for both stdio and http)
                            await self._mcp_client.connect()
                            logger.info("Reconnected to MCP server '%s'", self._server_name)
                            reconnect_success = True

                        except Exception as reconnect_error:
                            logger.warning(
                                "Reconnect failed for '%s': %s",
                                self.name,
                                reconnect_error,
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
    1. Connects to MCP servers (stdio or http transport)
    2. Lists available tools from each server
    3. Wraps MCP tools as FastReAct tools
    4. Registers them to ToolRegistry
    5. Manages server lifecycle (connect/close)
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        isolation_mode: str = "shared",
        credentials: Optional[Credentials] = None,
    ):
        """
        Initialize MCP tool manager

        Args:
            tool_registry: FastReAct tool registry to register MCP tools to
            isolation_mode: Default isolation mode for tools (shared, per_user, lazy_per_user)
            credentials: Credentials instance for HTTP authentication tokens
        """
        self._tools = tool_registry
        self._servers: Dict[str, Union[SimpleMCPClient, StreamableHTTPMCPClient]] = {}
        self._tool_wrappers: Dict[str, MCPToolWrapper] = {}
        self._isolation_mode = isolation_mode
        self._credentials = credentials or get_credentials()

        # Store server configs for resurrection (Zombie Process Resurrection)
        self._server_configs: Dict[str, Dict[str, Any]] = {}

        # Builtin MCP servers path resolution
        self._builtin_path = Path(__file__).parent.parent.parent.parent / "mcp_servers" / "builtin"

    def _resolve_magic_path(self, path: str) -> str:
        """
        Resolve magic paths in MCP server configuration.

        Supported magic paths:
        - @builtin/ -> resolves to mcp_servers/builtin/
        - @cwd/ -> resolves to current working directory

        Args:
            path: Path potentially containing magic prefix

        Returns:
            Resolved absolute path

        Examples:
            "@builtin/graphrag/server.py" -> "/path/to/mcp_servers/builtin/graphrag/server.py"
            "@cwd/my_server/server.py" -> "/current/working/dir/my_server/server.py"
        """
        if path.startswith("@builtin/"):
            # Resolve to builtin MCP servers directory
            relative_path = path[9:]  # Remove "@builtin/" prefix
            resolved = str(self._builtin_path / relative_path)
            return resolved
        elif path.startswith("@cwd/"):
            # Resolve to current working directory
            relative_path = path[5:]  # Remove "@cwd/" prefix
            resolved = str(Path.cwd() / relative_path)
            return resolved
        else:
            # No magic path, return as-is
            return path

    async def add_server(
        self,
        name: str,
        transport: str = "stdio",
        server_command: str = "",
        server_args: list[str] = None,
        env: Optional[dict[str, str]] = None,
        url: Optional[str] = None,
        auth_token_ref: Optional[str] = None,
    ) -> None:
        """
        Add MCP server and register its tools

        Args:
            name: Server name (for namespacing tools)
            transport: Transport type ("stdio" or "http")
            server_command: Command to spawn MCP server (for stdio)
            server_args: Arguments for server command (for stdio).
                        Supports @builtin/ magic path prefix
            url: HTTP server URL (for http transport)
            auth_token_ref: Reference to credentials.json for auth token (for http)

        Raises:
            RuntimeError: If server fails to start or tool registration fails
        """
        import sys

        try:
            # Resolve magic paths in server_args
            resolved_args = []
            if server_args:
                for arg in server_args:
                    resolved_args.append(self._resolve_magic_path(arg))

            # Connect to server based on transport type
            if transport == "stdio":
                client = SimpleMCPClient(
                    server_command=server_command,
                    server_args=resolved_args,
                    env=env,
                )
                await client.connect()

            elif transport == "http":
                if not url:
                    raise ValueError(f"HTTP transport requires 'url' parameter for server '{name}'")

                # Get auth token from credentials if reference provided
                auth_token = None
                if auth_token_ref:
                    auth_token = self._credentials.get_auth_token(auth_token_ref)
                    if not auth_token:
                        logger.warning(
                            "Auth token '%s' not found in credentials, connecting without authentication",
                            auth_token_ref,
                        )

                client = StreamableHTTPMCPClient(
                    base_url=url,
                    auth_token=auth_token,
                )
                await client.connect()

            else:
                raise ValueError(f"Unsupported transport type: '{transport}'")

            # List tools
            tools = await client.list_tools()

            # Register each tool to ToolRegistry
            for tool_def in tools:
                await self._register_mcp_tool(name, tool_def, client, transport)

            self._servers[name] = client

            # Save server config for resurrection
            self._server_configs[name] = {
                    "transport": transport,
                    "server_command": server_command,
                    "server_args": server_args or [],
                    "env": env,
                    "url": url,
                    "auth_token_ref": auth_token_ref,
                "isolation_mode": self._isolation_mode,
            }
            logger.info("MCP server '%s' (%s) registered and ready", name, transport)

        except Exception as e:
            raise RuntimeError(f"Failed to add MCP server '{name}': {e}")

    async def _register_mcp_tool(
        self,
        server_name: str,
        tool_def: Dict[str, Any],
        client: Union[SimpleMCPClient, StreamableHTTPMCPClient],
        transport: str = "stdio",
    ) -> None:
        """
        Register MCP tool as a FastReAct tool

        Args:
            server_name: Server name
            tool_def: Tool definition from MCP server
            client: MCP client instance
            transport: Transport type ("stdio" or "http")

        Raises:
            ValueError: If tool already registered
        """
        # Create wrapper
        wrapper = MCPToolWrapper(
            tool_name=tool_def["name"],
            server_name=server_name,
            mcp_client=client,
            mcp_manager=self,
            description=tool_def.get("description", ""),
            parameters=tool_def.get("inputSchema", {}),
            isolation_mode=self._isolation_mode,
            transport=transport,
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
        Check if MCP server is still alive (Zombie Process Detection)

        For stdio transport: Checks if process is running
        For http transport: Checks if connection is active

        Args:
            server_name: Name of the server to check

        Returns:
            True if process is alive, False if crashed (zombie)
        """
        client = self._servers.get(server_name)
        if not client:
            return False

        # For stdio transport, check process status
        if isinstance(client, SimpleMCPClient):
            if client._process and client._process.returncode is not None:
                # Process has exited (zombie detected!)
                logger.warning(
                    "Zombie process detected: MCP server '%s' crashed with exit code %s",
                    server_name,
                    client._process.returncode,
                )
                return False

        # For http transport, check connection status
        elif isinstance(client, StreamableHTTPMCPClient):
            if not client.is_alive():
                logger.warning("MCP HTTP server '%s' connection lost", server_name)
                return False

        return True

    async def resurrect_server(self, server_name: str) -> bool:
        """
        Resurrect a crashed MCP server (Zombie Process Resurrection)

        Automatically restarts a crashed server using its saved configuration.
        Works for both stdio and http transports.

        Args:
            server_name: Name of the server to resurrect

        Returns:
            True if resurrection successful, False otherwise

        Raises:
            RuntimeError: If server config not found or resurrection fails
        """
        # Check if server config exists
        if server_name not in self._server_configs:
            logger.error("Cannot resurrect '%s': no saved configuration", server_name)
            return False

        config = self._server_configs[server_name]
        transport = config.get("transport", "stdio")

        try:
            logger.info("Resurrecting MCP server '%s' (%s)...", server_name, transport)

            # Close old connection if exists
            if server_name in self._servers:
                try:
                    await self._servers[server_name].close()
                except Exception:
                    pass  # Ignore close errors

            # Create new client based on transport type
            if transport == "stdio":
                # Resolve magic paths in server_args
                resolved_args = []
                for arg in config["server_args"]:
                    resolved_args.append(self._resolve_magic_path(arg))

                client = SimpleMCPClient(
                    server_command=config["server_command"],
                    server_args=resolved_args,
                    env=config.get("env"),
                )
                await client.connect()

            elif transport == "http":
                # Get auth token from credentials if reference provided
                auth_token = None
                auth_token_ref = config.get("auth_token_ref")
                if auth_token_ref:
                    auth_token = self._credentials.get_auth_token(auth_token_ref)

                client = StreamableHTTPMCPClient(
                    base_url=config["url"],
                    auth_token=auth_token,
                )
                await client.connect()

            else:
                raise ValueError(f"Unsupported transport type: '{transport}'")

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
                await self._register_mcp_tool(server_name, tool_def, client, transport)

            # Update server reference
            self._servers[server_name] = client

            logger.info(
                "MCP server '%s' resurrected successfully (%s tools available)",
                server_name,
                len(tools),
            )
            return True

        except Exception as e:
            logger.error("Failed to resurrect MCP server '%s': %s", server_name, e)
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
        # Check if alive
        if self.is_server_alive(server_name):
            return True

        # Server is dead, try to resurrect
        logger.info("Zombie detected for '%s', attempting resurrection...", server_name)
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
