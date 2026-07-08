"""
FastReAct Nano - MCP Client (SimpleMCP-Stdio)

Client for communicating with MCP servers over stdio.
Uses JSON-RPC protocol with isolated subprocess communication.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Optional, Dict
from pathlib import Path

try:
    import asyncio.subprocess
except ImportError:
    import subprocess


logger = logging.getLogger(__name__)


class SimpleMCPClient:
    """
    Client for MCP server communication over stdio.

    Protocol:
    - Spawns server as subprocess
    - Communicates via stdin/stdout
    - Uses JSON-RPC format
    - Isolated execution (server crash doesn't affect client)
    """

    def __init__(
        self,
        server_command: str,
        server_args: list[str] = None,
        env: Optional[dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize MCP client

        Args:
            server_command: Command to spawn MCP server
            server_args: Arguments for server command
            timeout: Request timeout in seconds
        """
        self._server_command = server_command
        self._server_args = server_args or []
        self._env = env
        self._timeout = timeout
        self._process: Optional[asyncio.subprocess.Process] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._request_id = 0

    async def connect(self) -> None:
        """
        Spawn MCP server subprocess

        Raises:
            RuntimeError: If server fails to start
        """
        try:
            self._process = await asyncio.create_subprocess_exec(
                self._server_command,
                *self._server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **self._env} if self._env else None,
            )
            self._stderr_task = asyncio.create_task(self._relay_stderr())

            # Initialize session
            await self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "fastreact-nano",
                        "version": "2.1.0",
                    },
                },
            })

            # Wait for initialization response
            response = await self._read_response()
            if response.get("error"):
                raise RuntimeError(f"MCP init failed: {response['error']}")

        except Exception as e:
            raise RuntimeError(f"Failed to start MCP server: {e}")

    async def close(self) -> None:
        """Close MCP server connection"""
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
            except Exception:
                self._process.kill()
            finally:
                if self._stderr_task:
                    self._stderr_task.cancel()
                    try:
                        await self._stderr_task
                    except asyncio.CancelledError:
                        pass
                    self._stderr_task = None
                self._process = None

    async def list_tools(self) -> list[Dict[str, Any]]:
        """
        List available tools from MCP server

        Returns:
            List of tool definitions
        """
        await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        })

        response = await self._read_response()

        if "error" in response:
            raise RuntimeError(f"Tools list failed: {response['error']}")

        return response.get("result", {}).get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        user_key: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> str:
        """
        Call a tool on the MCP server

        Args:
            name: Tool name
            arguments: Tool arguments
            user_key: User identifier for multi-tenant isolation (optional)
            tenant_key: Tenant identifier for multi-tenant isolation (optional)

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
        if tenant_key is not None:
            request_params["tenant_key"] = tenant_key

        scope = arguments.get("scope") if isinstance(arguments.get("scope"), dict) else {}
        log_record = {
            "event": "fastreact.mcp_stdio_outbound_identity",
            "tool_name": name,
            "tenant_key": tenant_key,
            "user_key": user_key,
            "arg_tenant_id": arguments.get("tenant_id"),
            "arg_user_id": arguments.get("user_id"),
            "scope_tenant_id": scope.get("tenant_id"),
            "scope_user_id": scope.get("user_id"),
            "scope_mode": arguments.get("scope_mode") or scope.get("scope_mode") or scope.get("mode"),
            "knowledge_base_ids": arguments.get("knowledge_base_ids") or scope.get("knowledge_base_ids") or [],
            "source_item_count": len(arguments.get("source_item_ids") or scope.get("source_item_ids") or []),
        }
        logger.info(
            "FastReAct MCP stdio outbound identity tool_name=%s tenant_key=%s user_key=%s "
            "arg_tenant_id=%s arg_user_id=%s scope_tenant_id=%s "
            "scope_user_id=%s "
            "scope_mode=%s knowledge_base_ids=%s source_item_count=%s",
            name,
            tenant_key,
            user_key,
            arguments.get("tenant_id"),
            arguments.get("user_id"),
            scope.get("tenant_id"),
            scope.get("user_id"),
            arguments.get("scope_mode") or scope.get("scope_mode") or scope.get("mode"),
            arguments.get("knowledge_base_ids") or scope.get("knowledge_base_ids") or [],
            len(arguments.get("source_item_ids") or scope.get("source_item_ids") or []),
        )
        sys.stderr.write(json.dumps(log_record, ensure_ascii=False, sort_keys=True) + "\n")
        sys.stderr.flush()

        await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": request_params,
        })

        response = await self._read_response()

        if "error" in response:
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
            return json.dumps(result, indent=2)
        else:
            return str(result)

    def _next_id(self) -> int:
        """Generate next request ID"""
        self._request_id += 1
        return self._request_id

    async def _send_request(self, request: Dict[str, Any]) -> None:
        """
        Send JSON-RPC request to server

        Args:
            request: JSON-RPC request dict
        """
        if not self._process:
            raise RuntimeError("MCP server not connected")

        message = json.dumps(request) + "\n"
        self._process.stdin.write(message.encode())
        await self._process.stdin.drain()

    async def _read_response(self) -> Dict[str, Any]:
        """
        Read JSON-RPC response from server

        Returns:
            Response dict

        Raises:
            RuntimeError: If response parsing fails
        """
        if not self._process:
            raise RuntimeError("MCP server not connected")

        try:
            # Read line (JSON-RPC messages are line-delimited)
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=self._timeout,
            )

            if not line:
                raise RuntimeError("MCP server closed connection")

            # Parse JSON
            response = json.loads(line.decode())
            return response

        except asyncio.TimeoutError:
            raise RuntimeError(f"MCP request timeout ({self._timeout}s)")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid MCP response: {e}")

    async def _relay_stderr(self) -> None:
        """Relay MCP server stderr into the parent service log."""

        process = self._process
        if not process or process.stderr is None:
            return
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                text = line.decode(errors="replace")
                sys.stderr.write(text if text.endswith("\n") else f"{text}\n")
                sys.stderr.flush()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("MCP stderr relay stopped: %s", exc)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Convenience function
async def call_mcp_tool(
    server_command: str,
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """
    Quick one-shot MCP tool call

    Args:
        server_command: Command to spawn server
        tool_name: Tool to call
        arguments: Tool arguments

    Returns:
        Tool result
    """
    client = SimpleMCPClient(server_command)

    async with client:
        result = await client.call_tool(tool_name, arguments)
        return result
