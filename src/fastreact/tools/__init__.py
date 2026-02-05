"""
FastReAct 内置工具集

支持三种使用方式：

1. **函数式（推荐，类似 moltbot）**:
   ```python
   from fastreact.tools import create_builtin_tools
   tools = create_builtin_tools(config)
   ```

2. **手动导入工具对象**:
   ```python
   from fastreact.tools import create_search_tool, create_calculator_tool
   tools = [create_search_tool(api_key="..."), create_calculator_tool()]
   ```

3. **面向对象（向后兼容）**:
   ```python
   from fastreact.tools import SearchTool, CalculatorTool
   tools = [SearchTool(), CalculatorTool()]
   ```
"""

# 工具分组系统（V2 新增）
from fastreact.core.tool_group import (
    ToolGroup,
    GroupPolicy,
    get_predefined_group,
    list_predefined_groups,
    PREDEFINED_GROUPS,
)

from fastreact.core.tool_manager import (
    ToolManager,
    get_global_manager,
    reset_global_manager,
)

# 函数式工具（推荐方式）
from fastreact.tools.fn_registry import (
    Tool,
    create_builtin_tools,
    create_all_tools,
    create_search_tool,
    create_calculator_tool,
    create_weather_tool,
    create_datetime_tool,
    create_http_tool,
    create_shell_tool,
    create_ls_repo_tool,
    create_cd_repo_tool,
    create_refresh_repo_tool,
    create_edit_file_tool,
    create_write_file_tool,
    create_read_file_tool,
    create_deep_research_tool,
    execute_tool,
    get_tool_function_schema,
)

# Sprint 3.5: 精细化工具
from fastreact.tools.precision_tools import (
    create_view_file_tool,
    create_smart_read_tool,
    create_grep_code_tool,
    create_precision_tools,
    view_file,
    smart_read,
    grep_code,
)

# moltbot 风格扩展工具
from fastreact.tools.moltbot_tools import (
    create_code_exec_tool,
    create_text_analysis_tool,
    create_unit_converter_tool,
    create_moltbot_style_tools,
)

# Gateway 客户端工具
from fastreact.tools.gateway_tools import (
    create_gateway_tool,
    create_session_tool,
    create_spawn_subagent_tool,  # 新增
    create_gateway_tools,
)

# 工具注册表（自动发现）
from fastreact.tools.registry import ToolRegistry, get_registry, load_tools_from_config

# 手动导入（向后兼容）
from fastreact.tools.calculator import CalculatorTool
from fastreact.tools.search import SearchTool
from fastreact.tools.weather import WeatherTool
from fastreact.tools.http import HTTPTool
from fastreact.tools.shell_tool import StatefulShellTool, get_stateful_shell

# Tavily搜索工具
try:
    from fastreact.tools.tavily import (
        TavilySearchTool,
        TavilyNewsTool,
        TavilyAdvancedSearchTool,
    )
    _tavily_available = True
except ImportError:
    _tavily_available = False

# 日期时间工具
from fastreact.tools.datetime_tool import (
    GetCurrentTimeTool,
    GetDateInfoTool,
    DateTimeCalcTool,
)

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

# 沙箱工具（函数式，需要 docker 包）
try:
    from fastreact.tools.sandbox_tools import (
        create_sandbox_exec_tool,
        create_sandbox_tools,
    )
    _sandbox_available = True
except ImportError:
    _sandbox_available = False

# 旧版沙箱工具（向后兼容，类式）
try:
    from fastreact.tools.sandbox import (
        ExecuteCodeTool,
        CreateSandboxTool,
        ExecuteInSandboxTool,
        DestroySandboxTool,
    )
except ImportError:
    pass

__all__ = [
    # ============================================================================
    # 工具分组系统（V2 新增）
    # ============================================================================
    "ToolGroup",
    "GroupPolicy",
    "get_predefined_group",
    "list_predefined_groups",
    "PREDEFINED_GROUPS",
    "ToolManager",
    "get_global_manager",
    "reset_global_manager",

    # ============================================================================
    # 函数式工具（推荐方式）
    # ============================================================================
    # 基础工具工厂
    "Tool",  # 函数式 Tool 数据类
    "create_builtin_tools",
    "create_all_tools",
    "create_search_tool",
    "create_calculator_tool",
    "create_weather_tool",
    "create_datetime_tool",
    "create_http_tool",
    "create_shell_tool",
    "create_ls_repo_tool",
    "create_cd_repo_tool",
    "create_refresh_repo_tool",
    "create_edit_file_tool",
    "create_write_file_tool",
    "create_read_file_tool",
    "create_deep_research_tool",
    "execute_tool",
    "get_tool_function_schema",
    # moltbot 风格扩展工具
    "create_code_exec_tool",
    "create_text_analysis_tool",
    "create_unit_converter_tool",
    "create_moltbot_style_tools",
    # Gateway 工具
    "create_gateway_tool",
    "create_session_tool",
    "create_spawn_subagent_tool",  # 新增
    "create_gateway_tools",

    # ============================================================================
    # 工具注册表（自动发现）
    # ============================================================================
    "ToolRegistry",
    "get_registry",
    "load_tools_from_config",

    # ============================================================================
    # 旧版面向对象工具（向后兼容，不推荐新代码使用）
    # ============================================================================
    # 原有FastReAct工具
    "CalculatorTool",
    "SearchTool",
    "WeatherTool",
    "HTTPTool",
    "StatefulShellTool",
    "get_stateful_shell",
    # Tavily搜索工具
    "TavilySearchTool",
    "TavilyNewsTool",
    "TavilyAdvancedSearchTool",
    # 日期时间工具
    "GetCurrentTimeTool",
    "GetDateInfoTool",
    "DateTimeCalcTool",
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
    # 沙箱工具（函数式）
    "create_sandbox_exec_tool",
    "create_sandbox_tools",
    # 沙箱工具（旧版，向后兼容）
    "ExecuteCodeTool",
    "CreateSandboxTool",
    "ExecuteInSandboxTool",
    "DestroySandboxTool",
]
