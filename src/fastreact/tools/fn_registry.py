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
    tavily_config = tools_config.get("tavily", {})
    if tavily_config.get("enabled", True):
        tools.append(create_search_tool(
            api_key=tavily_config.get("api_key")
        ))

    # 基础工具
    tools.extend([
        create_calculator_tool(),
        create_weather_tool(),
        create_datetime_tool(),
        create_http_tool(),
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
