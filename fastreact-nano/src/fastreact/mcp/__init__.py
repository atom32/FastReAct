"""
FastReAct Nano - MCP Protocol Support

SimpleMCP-Stdio: Isolated process communication over stdio
"""

from .client import SimpleMCPClient
from .server import SimpleMCPServer
from .manager import MCPToolManager, MCPToolWrapper
from .discovery import MCPToolDiscovery, ToolInfo

__all__ = [
    "SimpleMCPClient",
    "SimpleMCPServer",
    "MCPToolManager",
    "MCPToolWrapper",
    "MCPToolDiscovery",
    "ToolInfo",
]
