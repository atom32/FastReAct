"""
FastReAct内置工具集
"""

from fastreact.tools.calculator import CalculatorTool
from fastreact.tools.search import SearchTool
from fastreact.tools.weather import WeatherTool
from fastreact.tools.http import HTTPTool

# GraphRAG工具
from fastreact.tools.graph_rag_tools import (
    query_graph_rag,
    analyze_relationships,
    multi_hop_reasoning,
    knowledge_extraction,
    check_graph_rag_config,
)

# Python工具
from fastreact.tools.python_tools import run_python_code, calculate_expression

# MCP适配器
from fastreact.tools.mcp_adapter import export_tools_to_fastreact, get_global_registry

# MCP客户端管理器
from fastreact.tools.mcp_client_manager import (
    MCPClientManager,
    MCPServerConnection,
    MCPToolWrapperExternal,
)

# 沙箱工具
from fastreact.tools.sandbox import (
    ExecuteCodeTool,
    CreateSandboxTool,
    ExecuteInSandboxTool,
    DestroySandboxTool,
)

__all__ = [
    # 原有FastReAct工具
    "CalculatorTool",
    "SearchTool",
    "WeatherTool",
    "HTTPTool",
    # GraphRAG工具（MCP格式）
    "query_graph_rag",
    "analyze_relationships",
    "multi_hop_reasoning",
    "knowledge_extraction",
    "check_graph_rag_config",
    # Python工具（MCP格式）
    "run_python_code",
    "calculate_expression",
    # MCP适配器
    "export_tools_to_fastreact",
    "get_global_registry",
    # MCP客户端
    "MCPClientManager",
    "MCPServerConnection",
    "MCPToolWrapperExternal",
    # 沙箱工具
    "ExecuteCodeTool",
    "CreateSandboxTool",
    "ExecuteInSandboxTool",
    "DestroySandboxTool",
]
