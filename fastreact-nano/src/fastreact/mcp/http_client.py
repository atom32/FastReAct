"""
FastReAct Nano - MCP HTTP Client

HTTP transport for MCP protocol supporting JSON-RPC over HTTP POST
with SSE (Server-Sent Events) for streaming responses.
"""

import asyncio
import json
from typing import Any, Optional, Dict, AsyncIterator
from urllib.parse import urljoin

import httpx


class StreamableHTTPMCPClient:
    """
    HTTP MCP Client for communicating with MCP servers over HTTP.

    Supports:
    - JSON-RPC over HTTP POST
    - Streamable HTTP transport (2025-03-26 MCP specification)
    - OAuth 2.1 Bearer token authentication
    - Server-Sent Events (SSE) for streaming
    - Compatible interface with SimpleMCPClient

    Protocol:
    - Base URL: http://host:port
    - Endpoint: /message (MCP standard endpoint)
    - Auth: Bearer token in Authorization header
    """

    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize HTTP MCP client

        Args:
            base_url: Base URL of MCP server (e.g., "http://localhost:8000")
            auth_token: OAuth 2.1 Bearer token for authentication
            timeout: Request timeout in seconds
        """
        self._base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        self._timeout = timeout
        self._request_id = 0
        self._connected = False

        # HTTP client with connection pooling
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """
        Initialize connection to MCP server.

        Performs:
        - Create HTTP client
        - Send initialize request
        - Verify server response

        Raises:
            RuntimeError: If connection fails
        """
        import sys

        try:
            # Create HTTP client
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "Content-Type": "application/json",
                },
            )

            # Add auth header if token provided
            if self._auth_token:
                self._client.headers["Authorization"] = f"Bearer {self._auth_token}"

            # Initialize session
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "fastreact-nano",
                        "version": "2.4.0",
                    },
                },
            }

            response = await self._send_request(init_request)

            if response.get("error"):
                raise RuntimeError(f"MCP init failed: {response['error']}")

            self._connected = True
            print(f"[OK] Connected to MCP HTTP server at {self._base_url}", file=sys.stderr)

        except httpx.ConnectError as e:
            raise RuntimeError(f"Failed to connect to MCP server: {e}")
        except httpx.TimeoutError as e:
            raise RuntimeError(f"Connection timeout: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize HTTP MCP client: {e}")

    async def close(self) -> None:
        """Close HTTP connection"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def list_tools(self) -> list[Dict[str, Any]]:
        """
        List available tools from MCP server

        Returns:
            List of tool definitions
        """
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }

        response = await self._send_request(request)

        if response.get("error"):
            raise RuntimeError(f"Tools list failed: {response['error']}")

        return response.get("result", {}).get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        user_key: Optional[str] = None,
    ) -> str:
        """
        Call a tool on the MCP server

        Args:
            name: Tool name
            arguments: Tool arguments
            user_key: User identifier for multi-tenant isolation (optional)

        Returns:
            Tool result as string
        """
        # Prepare request parameters
        request_params = {
            "name": name,
            "arguments": arguments,
        }

        # Add user_key if provided (for multi-tenant isolation)
        if user_key is not None:
            request_params["user_key"] = user_key

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": request_params,
        }

        response = await self._send_request(request)

        if response.get("error"):
            error_msg = response["error"].get("message", "Unknown error")
            return f"[MCP_ERROR] {error_msg}"

        result = response.get("result", {})

        # Handle different result formats
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            if "content" in result:
                content = result["content"]
                if isinstance(content, list):
                    return "\n".join(
                        item.get("text", str(item))
                        for item in content
                    )
                return str(content)
            return json.dumps(result, indent=2, ensure_ascii=False)
        else:
            return str(result)

    async def subscribe_events(
        self,
        heartbeat_interval: float = 30.0,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to server events via SSE (Server-Sent Events).

        Features:
        - Automatic heartbeat detection to keep connection alive
        - Exponential backoff reconnection on failure
        - Resilient to network issues and gateway timeouts

        Args:
            heartbeat_interval: Seconds without data before sending heartbeat ping
            max_retries: Maximum reconnection attempts
            initial_backoff: Initial backoff delay in seconds (doubles each retry)

        Yields:
            Event dictionaries from the server

        Raises:
            RuntimeError: If SSE connection fails after max retries
        """
        import sys
        import time

        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        sse_url = urljoin(self._base_url, "/events")
        retry_count = 0
        backoff = initial_backoff

        while retry_count <= max_retries:
            try:
                last_data_time = time.time()
                heartbeat_task = None

                async with self._client.stream("GET", sse_url) as response:
                    response.raise_for_status()

                    async def heartbeat_monitor():
                        """Send periodic heartbeat to keep connection alive"""
                        nonlocal last_data_time
                        while True:
                            await asyncio.sleep(5.0)  # Check every 5 seconds
                            if time.time() - last_data_time > heartbeat_interval:
                                # No data for too long, connection might be stale
                                print(
                                    f"[INFO] SSE heartbeat timeout, reconnecting...",
                                    file=sys.stderr
                                )
                                response.close()
                                break

                    async for line in response.aiter_lines():
                        last_data_time = time.time()

                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix

                            try:
                                event = json.loads(data)
                                retry_count = 0  # Reset retry count on success
                                backoff = initial_backoff
                                yield event
                            except json.JSONDecodeError:
                                # Skip non-JSON events (keepalive, etc.)
                                continue

                # Connection closed normally, exit loop
                break

            except (httpx.HTTPError, asyncio.TimeoutError) as e:
                retry_count += 1

                if retry_count > max_retries:
                    raise RuntimeError(
                        f"SSE connection failed after {max_retries} retries: {e}"
                    )

                # Exponential backoff
                print(
                    f"[WARNING] SSE connection lost, retrying in {backoff:.1f}s "
                    f"(attempt {retry_count}/{max_retries})",
                    file=sys.stderr
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)  # Max 60 seconds

                # Reconnect
                try:
                    await self.connect()
                    print(f"[OK] SSE reconnected successfully", file=sys.stderr)
                except Exception as reconnect_error:
                    print(
                        f"[ERROR] SSE reconnect failed: {reconnect_error}",
                        file=sys.stderr
                    )
                    continue

    def is_alive(self) -> bool:
        """
        Check if HTTP connection is alive.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self._client is not None

    def _next_id(self) -> int:
        """Generate next request ID"""
        self._request_id += 1
        return self._request_id

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON-RPC request to server via HTTP POST.

        Args:
            request: JSON-RPC request dict

        Returns:
            Response dict

        Raises:
            RuntimeError: If request fails
        """
        if not self._client:
            raise RuntimeError("HTTP MCP client not connected")

        url = urljoin(self._base_url, "/message")

        try:
            response = await self._client.post(url, json=request)
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Convenience function for one-shot tool calls
async def call_http_mcp_tool(
    base_url: str,
    tool_name: str,
    arguments: Dict[str, Any],
    auth_token: Optional[str] = None,
) -> str:
    """
    Quick one-shot HTTP MCP tool call

    Args:
        base_url: Base URL of MCP server
        tool_name: Tool to call
        arguments: Tool arguments
        auth_token: Optional authentication token

    Returns:
        Tool result
    """
    client = StreamableHTTPMCPClient(base_url, auth_token)

    async with client:
        result = await client.call_tool(tool_name, arguments)
        return result
