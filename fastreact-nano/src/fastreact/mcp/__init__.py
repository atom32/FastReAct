"""
FastReAct Nano - MCP Protocol Support

SimpleMCP-Stdio: Isolated process communication over stdio
HTTP Transport: JSON-RPC over HTTP with SSE support
"""

from .client import SimpleMCPClient
from .http_client import StreamableHTTPMCPClient, call_http_mcp_tool
from .server import SimpleMCPServer
from .manager import MCPToolManager, MCPToolWrapper
from .discovery import MCPToolDiscovery, ToolInfo

__all__ = [
    "SimpleMCPClient",
    "StreamableHTTPMCPClient",
    "call_http_mcp_tool",
    "SimpleMCPServer",
    "MCPToolManager",
    "MCPToolWrapper",
    "MCPToolDiscovery",
    "ToolInfo",
]
