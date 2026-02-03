"""
函数式工具定义 - 类似 moltbot 的简洁方式

不使用类继承，工具就是简单的对象 + 工厂函数
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """工具定义（简单对象，不需要继承）"""
    name: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable

    # 可选元数据
    label: Optional[str] = None
    category: Optional[str] = None

    def __post_init__(self):
        if self.label is None:
            self.label = self.name


# ============================================================================
# 工具工厂函数
# ============================================================================

def create_search_tool(api_key: Optional[str] = None) -> Tool:
    """创建搜索工具"""
    async def execute(query: str, num_results: int = 5) -> str:
        # 如果有 Tavily API key，使用真实搜索
        if api_key:
            from .tavily import TavilySearchTool
            tavily = TavilySearchTool(api_key=api_key)
            return await tavily.execute_async(query, max_results=num_results)
        else:
            # 否则使用模拟搜索
            await __import__('asyncio').sleep(0.1)
            return f"🔍 搜索 '{query}' 找到相关结果（模拟模式）"

    return Tool(
        name="search",
        label="Search",
        description="搜索互联网获取最新信息。可以搜索新闻、技术文档、百科知识等。",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回结果数量（1-10）",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        execute=execute,
    )


def create_calculator_tool() -> Tool:
    """创建计算器工具"""
    async def execute(expression: str) -> str:
        try:
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"

    return Tool(
        name="calculator",
        label="Calculator",
        description="执行数学计算。支持加减乘除、括号等数学表达式。",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '(15 + 25) * 2'"
                }
            },
            "required": ["expression"]
        },
        execute=execute,
    )


def create_weather_tool() -> Tool:
    """创建天气查询工具"""
    async def execute(location: str) -> str:
        # 模拟天气数据
        return f"{location}今天晴，温度 15-25℃，湿度 50%"

    return Tool(
        name="weather",
        label="Weather",
        description="查询天气信息。获取指定城市的当前天气状况。",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称，如 '北京' 或 '上海'"
                }
            },
            "required": ["location"]
        },
        execute=execute,
    )


def create_datetime_tool() -> Tool:
    """创建日期时间工具"""
    async def execute(action: str = "current") -> str:
        from datetime import datetime
        now = datetime.now()

        if action == "current":
            return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        elif action == "date":
            return f"当前日期: {now.strftime('%Y-%m-%d')}"
        else:
            return "可用操作: current（当前时间）, date（当前日期）"

    return Tool(
        name="datetime",
        label="DateTime",
        description="获取当前日期和时间信息",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["current", "date"],
                    "description": "操作类型",
                    "default": "current"
                }
            },
            "required": []
        },
        execute=execute,
    )


def create_http_tool() -> Tool:
    """创建 HTTP 请求工具"""
    async def execute(url: str, method: str = "GET") -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url)
                elif method.upper() == "POST":
                    response = await client.post(url)
                else:
                    return f"不支持的 HTTP 方法: {method}"

                return f"HTTP {method} {url}\n状态码: {response.status_code}\n响应: {response.text[:500]}"
        except Exception as e:
            return f"HTTP 请求失败: {str(e)}"

    return Tool(
        name="http",
        label="HTTP",
        description="发送 HTTP 请求。可以获取网页内容或调用 HTTP API。",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "请求的 URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "description": "HTTP 方法",
                    "default": "GET"
                }
            },
            "required": ["url"]
        },
        execute=execute,
    )


def create_shell_tool(timeout: int = 30) -> Tool:
    """创建持久化 Shell 工具"""
    from .shell_tool import get_stateful_shell

    # 使用单例模式获取全局 shell 实例
    shell = get_stateful_shell()

    return Tool(
        name="bash",
        label="Shell",
        description="在持久化的 Shell 会话中执行命令。状态会在命令之间保持（cd、export 等）。",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Shell 命令"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认 30",
                    "default": 30
                },
                "new_session": {
                    "type": "boolean",
                    "description": "是否创建新的 Shell 会话（重置所有状态）",
                    "default": False
                }
            },
            "required": ["command"]
        },
        execute=shell.execute_async,
    )


def create_ls_repo_tool() -> Tool:
    """创建查看项目结构工具"""
    async def execute(session_id: str = "default", force_refresh: bool = False) -> str:
        from ..context.repo_mapper import get_repo_mapper

        mapper = get_repo_mapper(session_id)
        return mapper.generate_map(force_refresh=force_refresh)

    return Tool(
        name="ls_repo",
        label="List Repository",
        description="查看当前项目的文件结构。显示目录树，自动折叠无关目录（node_modules, .git 等）。",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（通常自动传入）",
                    "default": "default"
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "是否强制重新扫描目录",
                    "default": False
                }
            },
            "required": []
        },
        execute=execute,
    )


def create_cd_repo_tool() -> Tool:
    """创建切换目录工具"""
    async def execute(path: str, session_id: str = "default") -> str:
        from ..context.repo_mapper import get_repo_mapper

        mapper = get_repo_mapper(session_id)
        return mapper.change_directory(path)

    return Tool(
        name="cd_repo",
        label="Change Repository Directory",
        description="切换项目目录并刷新文件结构。支持相对路径和绝对路径。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "目标目录路径（相对或绝对）"
                },
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（通常自动传入）",
                    "default": "default"
                }
            },
            "required": ["path"]
        },
        execute=execute,
    )


def create_refresh_repo_tool() -> Tool:
    """创建重新扫描工具"""
    async def execute(session_id: str = "default") -> str:
        from ..context.repo_mapper import get_repo_mapper

        mapper = get_repo_mapper(session_id)
        return mapper.generate_map(force_refresh=True)

    return Tool(
        name="refresh_repo",
        label="Refresh Repository",
        description="强制重新扫描当前目录结构。当文件系统发生变化时使用。",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（通常自动传入）",
                    "default": "default"
                }
            },
            "required": []
        },
        execute=execute,
    )


def create_edit_file_tool() -> Tool:
    """创建文件编辑工具"""
    from .edit_tool import get_edit_tool

    edit_tool = get_edit_tool()

    return Tool(
        name="edit_file",
        label="Edit File",
        description="精准编辑文件，使用 Search & Replace 模式修改代码块。支持模糊匹配，容忍空格和缩进差异。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对）"
                },
                "search_block": {
                    "type": "string",
                    "description": "要搜索的代码块"
                },
                "replace_block": {
                    "type": "string",
                    "description": "替换的代码块"
                },
                "fuzzy": {
                    "type": "boolean",
                    "description": "是否启用模糊匹配（默认 True）",
                    "default": True
                }
            },
            "required": ["path", "search_block", "replace_block"]
        },
        execute=edit_tool.execute_async,
    )


def create_write_file_tool() -> Tool:
    """创建文件写入工具"""
    import os
    from pathlib import Path

    async def execute(path: str, content: str, create_dirs: bool = True) -> str:
        """
        写入文件内容

        Args:
            path: 文件路径（相对或绝对）
            content: 文件内容
            create_dirs: 是否自动创建父目录（默认 True）

        Returns:
            执行结果
        """
        try:
            file_path = Path(path)

            # 创建父目录
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            file_path.write_text(content, encoding='utf-8')

            return f"[OK] File written: {file_path} ({len(content)} bytes)"

        except Exception as e:
            return f"[ERROR] Failed to write file: {str(e)}"

    return Tool(
        name="write_file",
        label="Write File",
        description="创建新文件或覆写已有文件的内容。会自动创建父目录。适用于生成代码、配置文件等。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对），如 'src/main.py' 或 '/tmp/config.json'"
                },
                "content": {
                    "type": "string",
                    "description": "文件内容，可以是代码、文本、JSON 等"
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "是否自动创建父目录（默认 True）",
                    "default": True
                }
            },
            "required": ["path", "content"]
        },
        execute=execute,
    )


def create_read_file_tool() -> Tool:
    """创建文件读取工具"""
    from pathlib import Path

    async def execute(path: str, encoding: str = "utf-8") -> str:
        """
        读取文件内容

        Args:
            path: 文件路径（相对或绝对）
            encoding: 文件编码（默认 utf-8）

        Returns:
            文件内容
        """
        try:
            file_path = Path(path)

            if not file_path.exists():
                return f"[ERROR] File not found: {file_path}"

            content = file_path.read_text(encoding=encoding)

            # 限制返回长度
            max_length = 10000
            if len(content) > max_length:
                content = content[:max_length] + f"\n... (truncated, total {len(content)} chars)"

            return f"[OK] File: {file_path}\n{content}"

        except Exception as e:
            return f"[ERROR] Failed to read file: {str(e)}"

    return Tool(
        name="read_file",
        label="Read File",
        description="读取文件内容。适用于查看代码、配置文件、日志等。返回前 10000 字符。",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对）"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码（默认 utf-8）",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        },
        execute=execute,
    )


# ============================================================================
# 工具收集器
# ============================================================================

def create_builtin_tools(config: Optional[Dict[str, Any]] = None) -> List[Tool]:
    """
    创建所有内置工具

    Args:
        config: 配置字典，可包含 API keys 等参数

    Returns:
        工具列表
    """
    config = config or {}
    tools_config = config.get("tools", {})

    tools = []

    # 搜索工具（可能需要 API key）
    # 支持两种配置方式: tavily_api_key 或 tavily.api_key
    tavily_api_key = tools_config.get("tavily_api_key") or tools_config.get("tavily", {}).get("api_key")
    tavily_config = tools_config.get("tavily", {})
    if tavily_config.get("enabled", True):
        tools.append(create_search_tool(
            api_key=tavily_api_key
        ))

    # 基础工具
    tools.extend([
        create_calculator_tool(),
        create_weather_tool(),
        create_datetime_tool(),
        create_http_tool(),
        create_shell_tool(),  # Stateful Shell - P0 Coding Agent feature
    ])

    # Coding Agent 工具
    tools.extend([
        create_ls_repo_tool(),      # Repository Map - P1 Coding Agent feature
        create_cd_repo_tool(),      # Change Directory
        create_refresh_repo_tool(), # Refresh Map
        create_edit_file_tool(),    # Edit File - P1 Coding Agent feature
        create_write_file_tool(),   # Write File - Create new files
        create_read_file_tool(),    # Read File - Read file contents
    ])

    logger.info(f"Created {len(tools)} builtin tools")
    return tools


def create_all_tools(config: Optional[Dict[str, Any]] = None) -> List[Tool]:
    """
    创建所有工具（包括扩展工具）

    Args:
        config: 配置字典

    Returns:
        工具列表
    """
    config = config or {}
    tools = create_builtin_tools(config)

    # 添加扩展工具
    from . import moltbot_tools
    tools.extend(moltbot_tools.create_moltbot_style_tools())

    # 添加 Gateway 工具（让 Agent 可以调用 Gateway）
    from . import gateway_tools
    gateway_url = config.get("gateway_url", "http://localhost:8080")
    tools.extend(gateway_tools.create_gateway_tools(gateway_url))

    # 添加沙箱工具（如果 Docker 可用）
    try:
        from . import sandbox_tools
        tools.extend(sandbox_tools.create_sandbox_tools())
        logger.info("Docker sandbox tools loaded")
    except Exception as e:
        logger.warning(f"Failed to load sandbox tools: {e}")

    logger.info(f"Created total {len(tools)} tools")
    return tools


def get_tool_function_schema(tool: Tool) -> Dict[str, Any]:
    """
    将工具转换为 OpenAI Function Calling 格式

    Args:
        tool: 工具对象

    Returns:
        Function schema
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        }
    }


async def execute_tool(tool: Tool, arguments: Dict[str, Any]) -> str:
    """
    执行工具

    Args:
        tool: 工具对象
        arguments: 工具参数

    Returns:
        执行结果
    """
    try:
        logger.info(f"Executing tool: {tool.name} with args: {arguments}")
        result = await tool.execute(**arguments)
        logger.info(f"Tool {tool.name} completed")
        return result
    except Exception as e:
        error_msg = f"Tool {tool.name} failed: {str(e)}"
        logger.error(error_msg)
        return error_msg
