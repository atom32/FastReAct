#!/usr/bin/env python3
"""
FastReAct Nano v2.1.0 - MCP Usage Examples

Examples of using MCP protocol with FastReAct Agent:
1. Standalone MCP server usage
2. Agent integration with MCP tools
3. Custom MCP server creation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'src')

from fastreact.mcp.client import SimpleMCPClient, call_mcp_tool
from fastreact import Agent


# ========================================
# Example 1: Standalone MCP Server Usage
# ========================================

async def example_1_standalone_server():
    """Example: Use MCP server independently"""
    print("=" * 70)
    print("Example 1: Standalone MCP Server Usage")
    print("=" * 70)

    # Path to MCP server
    server_path = Path(__file__).parent / "file_mcp_server.py"

    # Create client
    client = SimpleMCPClient(
        server_command=sys.executable,
        server_args=[str(server_path), "--base-path", "."],
    )

    try:
        # Connect
        print("\n[1] Connecting to MCP server...")
        await client.connect()
        print("[OK] Connected")

        # List available tools
        print("\n[2] Listing available tools...")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # Call a tool
        print("\n[3] Calling read_file tool...")
        result = await client.call_tool("read_file", {"path": "README.md"})
        print(f"Result:\n{result[:200]}...")

        print("\n[SUCCESS] Standalone MCP server usage complete!")

    finally:
        await client.close()


# ========================================
# Example 2: One-Shot MCP Tool Call
# ========================================

async def example_2_oneshot_call():
    """Example: Quick one-shot MCP tool call"""
    print("\n" + "=" * 70)
    print("Example 2: One-Shot MCP Tool Call")
    print("=" * 70)

    server_path = Path(__file__).parent / "file_mcp_server.py"

    # Quick one-shot call (handles connect/close automatically)
    result = await call_mcp_tool(
        server_command=sys.executable,
        server_args=[str(server_path), "--base-path", "."],
        tool_name="list_dir",
        arguments={"path": "."},
    )

    print(f"Directory listing:\n{result}")
    print("\n[SUCCESS] One-shot call complete!")


# ========================================
# Example 3: Custom MCP Server
# ========================================

class CalculatorMCPServer:
    """Custom MCP server for calculator operations"""

    def __init__(self):
        from fastreact.mcp.server import SimpleMCPServer
        self.server = SimpleMCPServer()
        self._register_tools()

    def _register_tools(self):
        """Register calculator tools"""
        self.server.register_tool(
            name="add",
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )

        self.server.register_tool(
            name="multiply",
            description="Multiply two numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )

    async def handle_tool_call(self, name: str, arguments: dict) -> str:
        """Handle calculator operations"""
        if name == "add":
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            return f"{a} + {b} = {a + b}"

        elif name == "multiply":
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            return f"{a} * {b} = {a * b}"

        return f"[ERROR] Unknown operation: {name}"


async def example_3_custom_server():
    """Example: Create and use custom MCP server"""
    print("\n" + "=" * 70)
    print("Example 3: Custom MCP Server")
    print("=" * 70)

    # Create custom server
    calc_server = CalculatorMCPServer()

    print("\n[INFO] Custom calculator server created")
    print("[INFO] Available tools:")
    for tool_name, tool_def in calc_server.server._tools.items():
        print(f"  - {tool_name}: {tool_def['description']}")

    # Note: Custom server would need to be run as subprocess
    # This is just a demonstration of the API

    print("\n[INFO] To use custom server:")
    print("  1. Implement run() method in server class")
    print("  2. Save as standalone .py file")
    print("  3. Spawn with SimpleMCPClient")

    print("\n[SUCCESS] Custom server API demonstrated!")


# ========================================
# Main Demo Runner
# ========================================

async def main():
    """Run all examples"""
    print("=" * 70)
    print("FastReAct Nano v2.1.0 - MCP Usage Examples")
    print("=" * 70)

    # Example 1: Standalone server
    await example_1_standalone_server()

    # Example 2: One-shot call
    await example_2_oneshot_call()

    # Example 3: Custom server
    await example_3_custom_server()

    print("\n" + "=" * 70)
    print("[SUCCESS] All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Demo stopped by user")
