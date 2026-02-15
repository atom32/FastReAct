"""
FastReAct Nano - MCP Server Base Class

Base class for implementing MCP servers.
"""

import asyncio
import json
import sys
from typing import Any, Callable, Dict, Optional
from abc import ABC, abstractmethod


class SimpleMCPServer(ABC):
    """
    Base class for MCP servers using stdio transport.

    Protocol:
    - Read JSON-RPC requests from stdin
    - Write JSON-RPC responses to stdout
    - Line-delimited messages
    """

    def __init__(self):
        """Initialize MCP server"""
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._running = False

    @abstractmethod
    async def handle_tool_call(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """
        Handle tool execution (override in subclass)

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result as string
        """
        pass

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
    ) -> None:
        """
        Register a tool

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool arguments
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }

    async def run(self) -> None:
        """
        Run MCP server main loop

        Reads requests from stdin, writes responses to stdout.
        """
        self._running = True

        while self._running:
            try:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None,
                    sys.stdin.readline,
                )

                if not line:
                    break

                # Parse JSON-RPC request
                try:
                    request = json.loads(line.strip())
                except json.JSONDecodeError:
                    await self._send_error(-32700, "Parse error")
                    continue

                # Handle request
                response = await self._handle_request(request)

                # Send response
                await self._send_response(response)

            except Exception as e:
                await self._send_error(-32603, f"Internal error: {e}")

    async def stop(self) -> None:
        """Stop server"""
        self._running = False

    async def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle JSON-RPC request

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": {
                            "name": "fastreact-mcp-server",
                            "version": "2.1.0",
                        },
                    },
                }

            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": list(self._tools.values()),
                    },
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                if tool_name not in self._tools:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Tool not found: {tool_name}",
                        },
                    }

                # Execute tool
                result = await self.handle_tool_call(tool_name, tool_args)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result,
                            }
                        ]
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }

    async def _send_response(self, response: Dict[str, Any]) -> None:
        """Send JSON-RPC response to stdout"""
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    async def _send_error(self, code: int, message: str) -> None:
        """Send error response"""
        await self._send_response({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": code,
                "message": message,
            },
        })
