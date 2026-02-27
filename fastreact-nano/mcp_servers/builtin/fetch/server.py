#!/usr/bin/env python3
"""
Simple HTTP Fetch MCP Server for FastReAct Nano

Provides HTTP GET functionality for fetching RSS feeds, APIs, etc.
"""

import asyncio
import json
from typing import Any
import httpx

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    print("[ERROR] MCP SDK not installed. Install with: pip install mcp")
    exit(1)

app = Server("fetch-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available fetch tools"""
    return [
        Tool(
            name="fetch_fetch",
            description="Fetch data from a URL via HTTP GET request. Supports JSON, XML, HTML, and plain text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch data from"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Request timeout in seconds (default: 10)",
                        "default": 10
                    }
                },
                "required": ["url"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    if name == "fetch_fetch":
        url = arguments["url"]
        timeout = arguments.get("timeout", 10)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Try to parse as JSON first
                try:
                    data = response.json()
                    result = json.dumps(data, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    # Return as text if not JSON
                    result = response.text

                return [TextContent(
                    type="text",
                    text=result
                )]

        except httpx.HTTPError as e:
            return [TextContent(
                type="text",
                text=f"[HTTP_ERROR] {str(e)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"[ERROR] {str(e)}"
            )]

    return [TextContent(
        type="text",
        text=f"[ERROR] Unknown tool: {name}"
    )]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
