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
    group: Optional[str] = None  # 工具分组名称
    needs_llm_client: bool = False  # 是否需要注入 LLM client

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
            # 否则使用模拟搜索（明确警告无法获取真实数据）
            await __import__('asyncio').sleep(0.1)
            return f"[WARNING] 搜索功能未配置 TAVILY_API_KEY，无法获取实时数据。查询 '{query}' 未执行真实搜索。请设置 TAVILY_API_KEY 环境变量或在 config.json 中配置。获取 API Key: https://tavily.com/"

    return Tool(
        name="search",
        label="Search",
        description="搜索互联网获取最新信息。可以搜索新闻、技术文档、百科知识等。注意：需要配置 TAVILY_API_KEY 才能获取真实搜索结果，否则会返回警告信息。",
        group="web",
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
        group="math",
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

        # 防御性编程：默认返回当前时间，而不是帮助文本
        if not action or action not in ["current", "date"]:
            action = "current"

        if action == "current":
            return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        elif action == "date":
            return f"当前日期: {now.strftime('%Y-%m-%d')}"

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
        group="web",
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
        group="system",
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
        group="code",
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
        group="code",
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
        group="code",
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
        group="file_ops",
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
        group="file_ops",
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
    """
    创建文件读取工具（Sprint 3.5: 智能路由）

    小文件（<300行）：返回全文
    大文件（>300行）：返回前100行 + 提示使用 view_file
    """
    from pathlib import Path

    async def execute(path: str, encoding: str = "utf-8") -> str:
        """
        智能读取文件内容

        Args:
            path: 文件路径（相对或绝对）
            encoding: 文件编码（默认 utf-8）

        Returns:
            文件内容或预览
        """
        try:
            file_path = Path(path)

            if not file_path.exists():
                return f"[ERROR] File not found: {file_path}"

            # 读取文件
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Sprint 3.5: 智能路由
            max_full_lines = 300
            preview_lines = 100

            if total_lines <= max_full_lines:
                # 小文件：返回全文
                content = ''.join(lines).rstrip()
                return f"[OK] File: {file_path} ({total_lines} lines)\n{content}"
            else:
                # 大文件：返回预览 + 提示
                preview = ''.join(lines[:preview_lines]).rstrip()
                return (
                    f"[INFO] File is too large ({total_lines} lines). "
                    f"Showing first {preview_lines} lines.\n"
                    f"Use view_file(path='{path}', start_line=1, end_line={preview_lines + 100}) to read more.\n"
                    f"--- File: {file_path} (preview) ---\n{preview}\n"
                    f"... ({total_lines - preview_lines} more lines)"
                )

        except Exception as e:
            return f"[ERROR] Failed to read file: {str(e)}"

    return Tool(
        name="read_file",
        label="Read File",
        description="智能读取文件内容。小文件返回全文，大文件返回预览并提示使用 view_file。",
        group="file_ops",
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


def create_deep_research_tool(llm_client=None, tavily_api_key: Optional[str] = None, model: str = "gpt-4"):
    """
    创建深度研究工具

    Args:
        llm_client: LLM 客户端（由 Agent 传入）
        tavily_api_key: Tavily API key（可选，用于真实搜索）
        model: LLM 模型名称

    Returns:
        Tool: 深度研究工具
    """
    async def execute(
        topic: str,
        depth: str = "standard",
        focus_areas: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        llm_client_runtime=None,  # 运行时注入的 LLM client
    ) -> str:
        """执行深度研究"""
        from .deep_research import DeepResearchEngine

        # 使用运行时注入的 llm_client，如果没有则使用创建时的值
        actual_llm_client = llm_client_runtime or llm_client

        # 准备搜索客户端
        search_client = None
        if tavily_api_key:
            try:
                from .tavily import TavilySearchTool
                search_client = TavilySearchTool(api_key=tavily_api_key)
            except Exception as e:
                logger.warning(f"Tavily client init failed: {e}")

        # 创建研究引擎（传入模型名和进度回调）
        engine = DeepResearchEngine(
            llm_client=actual_llm_client,
            search_client=search_client,
            enable_tavily=True,
            model=model,  # 传入模型名
            progress_callback=progress_callback,  # 传入进度回调
        )

        # 执行研究
        report = await engine.research(topic, depth, focus_areas)

        return report.to_markdown()

    return Tool(
        name="deep_research",
        label="Deep Research",
        description="""生成类似 Perplexity 的深度研究报告。

通过多轮搜索和 LLM 综合分析，生成结构化的研究报告。

研究深度：
- quick: 快速模式（2轮搜索，适合简单查询）
- standard: 标准模式（4轮搜索，平衡深度和速度）
- deep: 深度模式（6轮搜索，全面深入分析）

报告包含：
- 执行摘要
- 关键发现
- 详细章节
- 来源引用""",
        group="ai",
        needs_llm_client=True,  # 需要在运行时注入 LLM client
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "研究主题或问题"
                },
                "depth": {
                    "type": "string",
                    "description": "研究深度",
                    "enum": ["quick", "standard", "deep"],
                    "default": "standard"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "可选的关注领域列表"
                }
            },
            "required": ["topic"]
        },
        execute=execute,
    )


# ============================================================================
# 工具收集器
# ============================================================================

def create_builtin_tools(config: Optional[Dict[str, Any]] = None, model: str = "gpt-4") -> List[Tool]:
    """
    创建所有内置工具

    Args:
        config: 配置字典，可包含 API keys 等参数
        model: LLM 模型名称（用于需要 LLM 的工具）

    Returns:
        工具列表
    """
    config = config or {}
    tools_config = config.get("tools", {})

    tools = []

    # 搜索工具（可能需要 API key）
    # 支持三种配置方式:
    # 1. tools.tavily_api_key (直接配置)
    # 2. tools.tavily.api_key (嵌套配置)
    # 3. TAVILY_API_KEY 环境变量 (回退)
    tavily_api_key = tools_config.get("tavily_api_key") or tools_config.get("tavily", {}).get("api_key")

    # 环境变量回退
    if not tavily_api_key:
        import os
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if tavily_api_key:
            logger.info("Using TAVILY_API_KEY from environment variable")

    # 日志记录 API Key 状态
    if tavily_api_key:
        # 只显示前 10 个字符和后 4 个字符
        key_preview = f"{tavily_api_key[:10]}...{tavily_api_key[-4:]}"
        logger.info(f"Tavily API Key loaded: {key_preview}")
    else:
        logger.warning("Tavily API Key not configured - search will use fallback mode")

    tavily_config = tools_config.get("tavily", {})
    if tavily_config.get("enabled", True):
        tools.append(create_search_tool(
            api_key=tavily_api_key
        ))

    # 基础工具（精简后）
    tools.extend([
        create_datetime_tool(),  # 时间上下文（LLM 知识截止问题）
        create_shell_tool(),      # Stateful Shell - 万能工具（bash/curl/python/docker）
    ])

    # Coding Agent 工具（精简后）
    tools.extend([
        create_ls_repo_tool(),      # Repository Map - P1 Coding Agent feature
        create_cd_repo_tool(),      # Change Directory
        create_refresh_repo_tool(), # Refresh Map
        create_edit_file_tool(),    # Edit File - P1 Coding Agent feature
        create_write_file_tool(),   # Write File - Create new files
        # read_file 已删除，被 view_file 取代（更省 token）
    ])

    # Deep Research 工具（需要 LLM client，在运行时注入）
    # 注意：这个工具通过 needs_llm_client=True 标记，Engine 会在执行时注入 _llm_driver
    deep_research_enabled = tools_config.get("deep_research", {}).get("enabled", True)
    if deep_research_enabled:
        # 创建工具，设置默认模型（llm_client_runtime 会在执行时由 Engine 注入）
        # model 优先从配置读取，否则使用默认值
        model = tools_config.get("deep_research", {}).get("model", "gpt-4")
        tools.append(create_deep_research_tool(
            llm_client=None,  # 将在运行时由 Engine 注入
            tavily_api_key=tavily_api_key,
            model=model
        ))

    # 精细化工具（Precision Tools）- "手术刀"级工具
    # 用于替代"大锤"级工具，节省 Token，提供精准控制
    precision_enabled = tools_config.get("precision_tools", {}).get("enabled", True)
    if precision_enabled:
        from . import precision_tools
        tools.extend(precision_tools.create_precision_tools())

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

    # Gateway 工具（可选，用于分布式 Agent）
    # 如果不需要跨 Agent 调用，可以注释掉
    if config.get("gateway_enabled", False):
        from . import gateway_tools
        gateway_url = config.get("gateway_url", "http://localhost:8080")
        tools.extend(gateway_tools.create_gateway_tools(gateway_url))

    # 注意：已删除的工具（功能被 bash 取代）
    # - moltbot_tools: code_exec, text_analysis, unit_converter
    # - sandbox_tools: docker 操作可直接用 bash 执行
    # - python_tools: python 代码可直接用 bash 执行

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
