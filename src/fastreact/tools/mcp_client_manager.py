"""
MCP Client Manager

管理外部 MCP 服务器连接，自动发现和转换为 FastReAct 工具。

支持两种传输方式:
1. stdio - 本地进程通信（适合开发）
2. streamable-http - HTTP 通信（适合生产）

隔离模式（解决 anyio/asyncio 兼容性）:
- ENABLE_ISOLATED_PROXY=True 时使用线程隔离驱动
- MCP SDK 运行在独立线程的 anyio 循环中
- 通过队列与主线程的 asyncio 循环通信

简化版客户端（完全绕过 MCP SDK）:
- ENABLE_SIMPLE_CLIENT=True 时使用简化版 HTTP 客户端
- 直接实现 MCP JSON-RPC 协议
- 完全兼容 asyncio

使用示例:
    # 从配置文件加载
    manager = MCPClientManager.from_config("mcp_servers.json")
    await manager.connect_all()

    # 手动添加服务器
    manager = MCPClientManager()
    manager.add_server("filesystem", {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    })
    await manager.connect_all()

    # 获取所有工具
    tools = await manager.get_all_tools()
"""

import asyncio
import json
import anyio
import logging
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from contextlib import asynccontextmanager
import os

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client as streamable_http_client
from mcp.types import Tool, CallToolResult

from fastreact.core.tool import Tool
from fastreact.tools.mcp_adapter import MCPToolWrapper

# 是否启用隔离代理（解决 anyio/asyncio 冲突）
ENABLE_ISOLATED_PROXY = os.getenv("FASTREACT_MCP_ISOLATED_PROXY", "true").lower() == "true"

# 是否启用简化版客户端（完全绕过 MCP SDK）
ENABLE_SIMPLE_CLIENT = os.getenv("FASTREACT_MCP_SIMPLE_CLIENT", "true").lower() == "true"

logger = logging.getLogger(__name__)


class MCPServerConnection:
    """
    MCP 服务器连接封装

    管理单个 MCP 服务器的连接、会话和工具
    """

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        timeout: float = 30.0,
    ):
        """
        初始化 MCP 服务器连接

        Args:
            name: 服务器名称
            config: 服务器配置
                - 对于 stdio: {"command": "cmd", "args": [...], "env": {...}}
                - 对于 http: {"url": "http://...", "headers": {...}}
            timeout: 连接超时时间（秒）
        """
        self.name = name
        self.config = config
        self.timeout = timeout
        self._session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._client_context = None
        self._http_client_cm = None  # HTTP 客户端上下文管理器
        self._http_client_streams = None  # HTTP 客户端 streams
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected

    @property
    def session(self) -> Optional[ClientSession]:
        """获取 MCP ClientSession"""
        return self._session

    async def connect(self) -> None:
        """连接到 MCP 服务器"""
        if self._is_connected:
            return

        try:
            # 判断传输方式
            if "url" in self.config:
                # HTTP 传输 - 使用 async context manager
                url = self.config["url"]
                headers = self.config.get("headers", {})

                # 创建并进入 HTTP 客户端上下文
                self._http_client_cm = streamable_http_client(url, headers=headers)
                self._http_client_streams = await self._http_client_cm.__aenter__()

                # streamable_http_client 返回 (read_stream, write_stream, get_session_id)
                if isinstance(self._http_client_streams, tuple):
                    if len(self._http_client_streams) >= 2:
                        self._read_stream = self._http_client_streams[0]
                        self._write_stream = self._http_client_streams[1]
                        # 第三个元素是 get_session_id 方法，暂时不需要
                    elif len(self._http_client_streams) == 1:
                        self._read_stream = self._write_stream = self._http_client_streams[0]
                else:
                    # 如果不是 tuple，可能是单个 stream 对象
                    self._read_stream = self._write_stream = self._http_client_streams

            elif "command" in self.config:
                # stdio 传输
                command = self.config["command"]
                args = self.config.get("args", [])
                env = self.config.get("env", {})

                # 确保 PYTHONUNBUFFERED 用于即时 stdio 通信
                env = dict(env)  # Copy to avoid modifying original
                env.setdefault("PYTHONUNBUFFERED", "1")

                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env,
                )

                self._client_context = stdio_client(server_params)
                self._read_stream, self._write_stream = await self._client_context.__aenter__()

            else:
                raise ValueError(f"Invalid server config for {self.name}: must have 'url' or 'command'")

            # 创建会话
            self._session = ClientSession(self._read_stream, self._write_stream)

            # 初始化会话 - 使用 asyncio.wait_for 避免任何挂起
            print(f"[DEBUG] Initializing MCP session for '{self.name}'...")
            try:
                await asyncio.wait_for(self._session.initialize(), timeout=self.timeout)
                print(f"[DEBUG] MCP session initialized successfully for '{self.name}'")
            except (asyncio.TimeoutError, TimeoutError) as e:
                print(f"[DEBUG] Timeout during MCP session initialization for '{self.name}'")
                raise TimeoutError(f"Timeout connecting to MCP server '{self.name}'")

            self._is_connected = True
            print(f"[DEBUG] MCP connection '{self.name}' marked as connected")

        except (TimeoutError, asyncio.TimeoutError) as e:
            print(f"[DEBUG] Timeout during MCP session initialization for '{self.name}'")
            raise TimeoutError(f"Timeout connecting to MCP server '{self.name}'")
        except Exception as e:
            self._is_connected = False
            raise RuntimeError(f"Failed to connect to MCP server '{self.name}': {str(e)}")

    async def disconnect(self) -> None:
        """断开连接"""
        if not self._is_connected:
            return

        try:
            # 先关闭会话
            if self._session:
                await self._session.aclose()

            # 注意: 不手动退出 MCP 客户端上下文
            # MCP SDK (stdio 和 HTTP) 使用 anyio task groups
            # 手动调用 __aexit__ 会导致 "cancel scope in different task" 错误
            # 让垃圾回收器自动清理资源

        except Exception as e:
            print(f"Warning: Error disconnecting from '{self.name}': {str(e)}")

        finally:
            self._is_connected = False
            self._session = None
            # Clear references to help garbage collection
            self._read_stream = None
            self._write_stream = None
            self._client_context = None
            self._http_client_cm = None
            self._http_client_streams = None
            self._read_stream = None
            self._write_stream = None
            self._client_context = None
            self._http_client_cm = None
            self._http_client_streams = None

    async def list_tools(self) -> List[Tool]:
        """列出所有可用工具"""
        if not self._is_connected or not self._session:
            raise RuntimeError(f"Not connected to MCP server '{self.name}'")

        try:
            result = await self._session.list_tools()
            return result.tools
        except Exception as e:
            raise RuntimeError(f"Failed to list tools from '{self.name}': {str(e)}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        调用工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self._is_connected or not self._session:
            raise RuntimeError(f"Not connected to MCP server '{self.name}'")

        try:
            return await self._session.call_tool(name, arguments)
        except Exception as e:
            raise RuntimeError(f"Failed to call tool '{name}' from '{self.name}': {str(e)}")

    async def list_resources(self):
        """列出所有可用资源"""
        if not self._is_connected or not self._session:
            raise RuntimeError(f"Not connected to MCP server '{self.name}'")

        try:
            return await self._session.list_resources()
        except Exception as e:
            raise RuntimeError(f"Failed to list resources from '{self.name}': {str(e)}")

    async def list_prompts(self):
        """列出所有可用提示"""
        if not self._is_connected or not self._session:
            raise RuntimeError(f"Not connected to MCP server '{self.name}'")

        try:
            return await self._session.list_prompts()
        except Exception as e:
            raise RuntimeError(f"Failed to list prompts from '{self.name}': {str(e)}")


class MCPToolWrapperExternal(MCPToolWrapper):
    """
    外部 MCP 工具包装器

    将 MCP 服务器的工具转换为 FastReAct Tool 对象
    """

    def __init__(
        self,
        mcp_tool: Tool,
        connection: MCPServerConnection,
    ):
        """
        初始化工具包装器

        Args:
            mcp_tool: MCP 工具定义
            connection: MCP 服务器连接
        """
        self._mcp_tool = mcp_tool
        self._connection = connection

        # 提取工具信息
        self.name = mcp_tool.name
        self.description = mcp_tool.description or f"Tool from MCP: {mcp_tool.name}"

        # MCP 工具的 inputSchema 已经是 JSON Schema 格式
        self.parameters = self._extract_parameters(mcp_tool)

    def _extract_parameters(self, mcp_tool: Tool) -> Dict[str, Any]:
        """
        从 MCP 工具提取参数 schema

        Args:
            mcp_tool: MCP 工具定义

        Returns:
            JSON Schema 格式的参数定义
        """
        # MCP 的 inputSchema 已经是标准 JSON Schema
        if hasattr(mcp_tool, 'inputSchema') and mcp_tool.inputSchema:
            schema = mcp_tool.inputSchema

            # 确保有基本结构
            if "type" not in schema:
                schema["type"] = "object"
            if "properties" not in schema:
                schema["properties"] = {}
            if "required" not in schema:
                schema["required"] = []

            return schema

        # 如果没有 schema，返回空对象
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def _get_description(self) -> str:
        """返回工具描述"""
        return self.description

    def _get_parameters(self) -> Dict[str, Any]:
        """返回参数 schema"""
        return self.parameters

    async def execute_async(self, **kwargs) -> Any:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        try:
            result = await self._connection.call_tool(self.name, kwargs)

            # 解析结果
            if result.isError:
                return {
                    "status": "error",
                    "error": self._extract_error_content(result),
                }

            # 提取内容
            content = self._extract_content(result)

            return {
                "status": "success",
                "action": self.name,
                "result": content,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)}",
            }

    def _extract_content(self, result: CallToolResult) -> Any:
        """
        从 CallToolResult 提取内容

        Args:
            result: MCP 工具调用结果

        Returns:
            提取的内容
        """
        # 如果有结构化内容，优先返回
        if hasattr(result, 'structured_content') and result.structured_content:
            return result.structured_content

        # 否则从 content 列表提取
        if not result.content:
            return None

        # 如果只有一个文本内容，直接返回
        if len(result.content) == 1:
            item = result.content[0]
            if hasattr(item, 'text'):
                return item.text
            return str(item)

        # 多个内容，返回列表
        contents = []
        for item in result.content:
            if hasattr(item, 'text'):
                contents.append(item.text)
            elif hasattr(item, 'data'):
                contents.append(f"<binary data: {len(item.data)} bytes>")
            else:
                contents.append(str(item))

        return contents

    def _extract_error_content(self, result: CallToolResult) -> str:
        """
        从错误结果提取错误信息

        Args:
            result: MCP 工具调用结果（错误）

        Returns:
            错误信息字符串
        """
        if not result.content:
            return "Unknown error"

        # 提取第一个文本内容
        for item in result.content:
            if hasattr(item, 'text'):
                return item.text

        return str(result.content[0])


class MCPClientManager:
    """
    MCP 客户端管理器

    管理多个 MCP 服务器连接，提供统一的工具访问接口
    """

    def __init__(self, config_path: Optional[str] = None, timeout: float = 60.0):
        """
        初始化 MCP 客户端管理器

        Args:
            config_path: MCP 配置文件路径（可选）
            timeout: 连接超时时间（秒）
        """
        self._connections: Dict[str, MCPServerConnection] = {}
        self._config_path = config_path
        self._timeout = timeout
        self._isolated_proxy = None
        self._simple_manager = None
        self._servers_config = {}

        # 选择客户端模式
        if ENABLE_SIMPLE_CLIENT:
            self._use_simple_client = True
            self._use_isolated_proxy = False
            logger = logging.getLogger(__name__)
            logger.info("[MCPManager] Using simple HTTP client (no MCP SDK)")
        elif ENABLE_ISOLATED_PROXY:
            from fastreact.tools.mcp_isolated_proxy import AsyncMCPProxy
            self._use_isolated_proxy = True
            self._use_simple_client = False
            logger = logging.getLogger(__name__)
            logger.info("[MCPManager] Using isolated proxy (thread-isolated anyio)")
        else:
            self._use_isolated_proxy = False
            self._use_simple_client = False

        # 如果提供了配置文件，自动加载
        if config_path:
            self.load_config(config_path)

    def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """
        添加 MCP 服务器

        Args:
            name: 服务器名称（唯一标识）
            config: 服务器配置
                - stdio: {"command": "cmd", "args": [...], "env": {...}}
                - http: {"url": "http://...", "headers": {...}}
        """
        if name in self._connections:
            raise ValueError(f"Server '{name}' already exists")

        # 保存配置供隔离代理使用
        self._servers_config[name] = config

        # 创建连接对象
        self._connections[name] = MCPServerConnection(name, config, self._timeout)

    def remove_server(self, name: str) -> None:
        """
        移除 MCP 服务器

        Args:
            name: 服务器名称
        """
        if name in self._connections:
            del self._connections[name]

    def load_config(self, config_path: str) -> None:
        """
        从配置文件加载 MCP 服务器

        Args:
            config_path: 配置文件路径（JSON 格式）

        配置格式:
            {
                "mcpServers": {
                    "server_name": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
                    },
                    "http_server": {
                        "url": "http://localhost:8080/mcp",
                        "headers": {"Authorization": "Bearer token"}
                    }
                }
            }
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"MCP config file not found: {config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 提取 mcpServers 配置
        servers = config.get("mcpServers", {})
        for name, server_config in servers.items():
            self.add_server(name, server_config)

    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径（默认使用初始化时的路径）
        """
        path = config_path or self._config_path
        if not path:
            raise ValueError("No config path specified")

        # 构建配置
        config = {
            "mcpServers": {
                name: conn.config
                for name, conn in self._connections.items()
            }
        }

        # 保存到文件
        config_file = Path(path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    async def connect_all(self) -> Dict[str, bool]:
        """
        连接所有服务器

        Returns:
            连接结果字典 {server_name: success}
        """
        results = {}

        # 使用简化版客户端（完全绕过 MCP SDK）
        if ENABLE_SIMPLE_CLIENT and self._servers_config:
            # 检查是否有 stdio 配置
            has_stdio = any("command" in config for config in self._servers_config.values())

            if has_stdio:
                # 使用 stdio 简化版客户端
                from fastreact.tools.simple_mcp_stdio import SimpleMCPStdioManager

                self._simple_stdio_manager = SimpleMCPStdioManager(self._servers_config)
                self._simple_http_manager = None

                for name in self._servers_config.keys():
                    try:
                        print(f"[INFO] Connecting to '{name}' (stdio, simple client, no SDK)...")
                    except:
                        pass

                results = await self._simple_stdio_manager.connect_all()

                for name, success in results.items():
                    if success:
                        print(f"[INFO] Connected to '{name}'")
                    else:
                        print(f"[WARNING] Failed to connect to '{name}'")

                return results
            else:
                # 使用 HTTP 简化版客户端
                from fastreact.tools.simple_mcp_client import SimpleMCPManager

                self._simple_http_manager = SimpleMCPManager(self._servers_config)
                self._simple_stdio_manager = None

                for name in self._servers_config.keys():
                    try:
                        print(f"[INFO] Connecting to '{name}' (HTTP, simple client, no SDK)...")
                    except:
                        pass

                results = await self._simple_http_manager.connect_all()

                for name, success in results.items():
                    if success:
                        print(f"[INFO] Connected to '{name}'")
                    else:
                        print(f"[WARNING] Failed to connect to '{name}'")

                return results

        # 使用隔离代理模式
        if self._use_isolated_proxy and self._servers_config:
            from fastreact.tools.mcp_isolated_proxy import AsyncMCPProxy

            # 创建隔离代理
            if not self._isolated_proxy:
                self._isolated_proxy = AsyncMCPProxy(self._servers_config)

            # 连接所有服务器
            for name in self._servers_config.keys():
                try:
                    print(f"[INFO] Connecting to MCP server '{name}' (isolated mode)...")
                    success = await self._isolated_proxy.connect(name)
                    results[name] = success
                    if success:
                        print(f"[INFO] Connected to '{name}'")
                    else:
                        print(f"[WARNING] Failed to connect to '{name}'")
                except Exception as e:
                    print(f"[ERROR] Failed to connect to '{name}': {str(e)}")
                    results[name] = False

            return results

        # 使用传统直接连接模式
        for name, connection in self._connections.items():
            try:
                await connection.connect()
                results[name] = True
            except Exception as e:
                print(f"Failed to connect to '{name}': {str(e)}")
                results[name] = False

        return results

    async def disconnect_all(self) -> None:
        """断开所有服务器连接"""
        tasks = [
            connection.disconnect()
            for connection in self._connections.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def get_all_tools(self) -> List[Tool]:
        """
        获取所有服务器的工具

        Returns:
            FastReAct Tool 对象列表
        """
        all_tools = []

        # 使用简化版客户端
        if ENABLE_SIMPLE_CLIENT:
            # stdio 客户端优先
            if hasattr(self, '_simple_stdio_manager') and self._simple_stdio_manager:
                for name in self._simple_stdio_manager.get_all_server_names():
                    try:
                        print(f"[INFO] Loading tools from '{name}' (stdio simple client)...")

                        # 从简化客户端获取工具列表
                        tools_data = await self._simple_stdio_manager.list_tools(name)

                        # 创建包装工具
                        for tool_data in tools_data:
                            wrapper = SimpleMCPStdioToolWrapper(
                                tool_name=tool_data["name"],
                                description=tool_data.get("description", ""),
                                input_schema=tool_data.get("inputSchema", {}),
                                server_name=name,
                                manager=self._simple_stdio_manager
                            )
                            all_tools.append(wrapper)

                        print(f"[INFO] Loaded {len(tools_data)} tools from '{name}'")

                    except Exception as e:
                        print(f"[WARNING] Failed to get tools from '{name}': {str(e)}")
                        continue

                return all_tools

            # HTTP 客户端作为备选
            if hasattr(self, '_simple_http_manager') and self._simple_http_manager:
                for name in self._simple_http_manager.get_all_server_names():
                    try:
                        print(f"[INFO] Loading tools from '{name}' (HTTP simple client)...")

                        # 从简化客户端获取工具列表
                        tools_data = await self._simple_http_manager.list_tools(name)

                        # 创建包装工具
                        for tool_data in tools_data:
                            wrapper = SimpleMCPToolWrapper(
                                tool_name=tool_data["name"],
                                description=tool_data.get("description", ""),
                                input_schema=tool_data.get("inputSchema", {}),
                                server_name=name,
                                manager=self._simple_http_manager
                            )
                            all_tools.append(wrapper)

                        print(f"[INFO] Loaded {len(tools_data)} tools from '{name}'")

                    except Exception as e:
                        print(f"[WARNING] Failed to get tools from '{name}': {str(e)}")
                        continue

                return all_tools

        # 使用隔离代理模式
        if self._use_isolated_proxy and self._isolated_proxy:
            for name in self._servers_config.keys():
                try:
                    print(f"[INFO] Loading tools from '{name}' (isolated mode)...")

                    # 从隔离代理获取工具列表
                    tools_data = await self._isolated_proxy.list_tools(name)

                    # 创建包装工具
                    for tool_data in tools_data:
                        wrapper = IsolatedMCPToolWrapper(
                            tool_name=tool_data["name"],
                            description=tool_data.get("description", ""),
                            input_schema=tool_data.get("inputSchema", {}),
                            server_name=name,
                            proxy=self._isolated_proxy
                        )
                        all_tools.append(wrapper)

                    print(f"[INFO] Loaded {len(tools_data)} tools from '{name}'")

                except Exception as e:
                    print(f"[WARNING] Failed to get tools from '{name}': {str(e)}")
                    continue

            return all_tools

        # 使用传统直接连接模式
        for name, connection in self._connections.items():
            if not connection.is_connected:
                print(f"Warning: Server '{name}' is not connected, skipping...")
                continue

            try:
                mcp_tools = await connection.list_tools()

                for mcp_tool in mcp_tools:
                    # 创建包装器
                    wrapper = MCPToolWrapperExternal(mcp_tool, connection)
                    all_tools.append(wrapper)

            except Exception as e:
                print(f"Warning: Failed to get tools from '{name}': {str(e)}")
                continue

        return all_tools

    async def get_server_tools(self, server_name: str) -> List[Tool]:
        """
        获取指定服务器的工具

        Args:
            server_name: 服务器名称

        Returns:
            FastReAct Tool 对象列表
        """
        if server_name not in self._connections:
            raise ValueError(f"Server '{server_name}' not found")

        connection = self._connections[server_name]

        if not connection.is_connected:
            raise RuntimeError(f"Server '{server_name}' is not connected")

        mcp_tools = await connection.list_tools()

        return [
            MCPToolWrapperExternal(mcp_tool, connection)
            for mcp_tool in mcp_tools
        ]

    def list_servers(self) -> List[str]:
        """
        列出所有服务器名称

        Returns:
            服务器名称列表
        """
        return list(self._connections.keys())

    async def close_all(self) -> None:
        """
        关闭所有服务器连接

        清理所有 MCP 服务器连接资源
        """
        for name, connection in self._connections.items():
            if connection.is_connected:
                try:
                    await connection.disconnect()
                except Exception as e:
                    print(f"Warning: Error closing connection to '{name}': {str(e)}")

        self._connections.clear()

    def get_server_status(self) -> Dict[str, bool]:
        """
        获取所有服务器连接状态

        Returns:
            {server_name: is_connected}
        """
        return {
            name: conn.is_connected
            for name, conn in self._connections.items()
        }

    @asynccontextmanager
    async def auto_connect(self):
        """
        上下文管理器：自动连接和断开

        使用示例:
            async with manager.auto_connect():
                tools = await manager.get_all_tools()
                # 使用工具...
        """
        await self.connect_all()
        try:
            yield self
        finally:
            await self.disconnect_all()

    def __len__(self) -> int:
        """返回服务器数量"""
        return len(self._connections)


class IsolatedMCPToolWrapper(Tool):
    """
    隔离模式 MCP 工具包装器

    通过隔离代理调用 MCP 服务器的工具
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
        proxy: Any,
    ):
        """
        初始化工具包装器

        Args:
            tool_name: 工具名称
            description: 工具描述
            input_schema: 输入参数 schema
            server_name: MCP 服务器名称
            proxy: 隔离代理实例
        """
        self._wrapper_tool_name = tool_name
        self._wrapper_description = description
        self._wrapper_input_schema = input_schema
        self._server_name = server_name
        self._proxy = proxy

        # 调用 Tool 基类构造函数
        super().__init__()

        # 重写工具名称为实际的 MCP 工具名称
        self.name = tool_name

    def _get_description(self) -> str:
        """返回工具描述"""
        return self._wrapper_description

    def _get_parameters(self) -> Dict[str, Any]:
        """返回参数schema"""
        return self._wrapper_input_schema

    async def execute_async(self, **kwargs) -> str:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果（字符串格式）
        """
        try:
            print(f"[IsolatedMCP] Calling {self._server_name}.{self._wrapper_tool_name}")

            # 通过隔离代理调用工具
            result = await self._proxy.call_tool(
                server_name=self._server_name,
                tool_name=self._wrapper_tool_name,
                arguments=kwargs
            )

            # 提取结果文本
            if hasattr(result, 'content'):
                content = result.content
                if content and len(content) > 0:
                    first_item = content[0]
                    if hasattr(first_item, 'text'):
                        return first_item.text
                    return str(first_item)
                return "Empty result"

            return str(result)

        except Exception as e:
            error_msg = f"Error calling {self._server_name}.{self._wrapper_tool_name}: {str(e)}"
            print(f"[IsolatedMCP] {error_msg}")
            return error_msg


class SimpleMCPToolWrapper(Tool):
    """
    简化版 MCP 工具包装器（HTTP）

    通过简化版 HTTP 客户端调用 MCP 服务器的工具
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
        manager: Any,
    ):
        """
        初始化工具包装器

        Args:
            tool_name: 工具名称
            description: 工具描述
            input_schema: 输入参数 schema
            server_name: MCP 服务器名称
            manager: 简化版 MCP 管理器
        """
        self._wrapper_tool_name = tool_name
        self._wrapper_description = description
        self._wrapper_input_schema = input_schema
        self._server_name = server_name
        self._manager = manager

        # 调用 Tool 基类构造函数
        super().__init__()

        # 重写工具名称为实际的 MCP 工具名称
        self.name = tool_name

    def _get_description(self) -> str:
        """返回工具描述"""
        return self._wrapper_description

    def _get_parameters(self) -> Dict[str, Any]:
        """返回参数schema"""
        return self._wrapper_input_schema

    async def execute_async(self, **kwargs) -> str:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果（字符串格式）
        """
        try:
            print(f"[SimpleMCP-HTTP] Calling {self._server_name}.{self._wrapper_tool_name}")
            print(f"[SimpleMCP-HTTP] Arguments: {kwargs}")

            # 通过简化管理器调用工具
            result = await self._manager.call_tool(
                server_name=self._server_name,
                tool_name=self._wrapper_tool_name,
                arguments=kwargs
            )

            # 提取结果文本
            # result 格式: {"content": [{"type": "text", "text": "..."}]}
            if isinstance(result, dict):
                content = result.get("content", [])
                if content and len(content) > 0:
                    first_item = content[0]
                    if isinstance(first_item, dict):
                        text = first_item.get("text")
                        if text is not None:
                            return text
                    return str(first_item)
                return "Empty result"

            return str(result)

        except Exception as e:
            error_msg = f"Error calling {self._server_name}.{self._wrapper_tool_name}: {str(e)}"
            print(f"[SimpleMCP-HTTP] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg


class SimpleMCPStdioToolWrapper(Tool):
    """
    简化版 MCP stdio 工具包装器

    通过简化版 stdio 客户端调用 MCP 服务器的工具
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
        manager: Any,
    ):
        """
        初始化工具包装器

        Args:
            tool_name: 工具名称
            description: 工具描述
            input_schema: 输入参数 schema
            server_name: MCP 服务器名称
            manager: 简化版 stdio MCP 管理器
        """
        self._wrapper_tool_name = tool_name
        self._wrapper_description = description
        self._wrapper_input_schema = input_schema
        self._server_name = server_name
        self._manager = manager

        # 调用 Tool 基类构造函数
        super().__init__()

        # 重写工具名称为实际的 MCP 工具名称
        # 这样 agent 可以正确识别工具（如 "create_issue" 而不是 "SimpleMCPStdioToolWrapper"）
        self.name = tool_name

    def _get_description(self) -> str:
        """返回工具描述"""
        return self._wrapper_description

    def _get_parameters(self) -> Dict[str, Any]:
        """返回参数schema"""
        return self._wrapper_input_schema

    async def execute_async(self, **kwargs) -> str:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果（字符串格式）
        """
        try:
            print(f"[SimpleMCP-Stdio] Calling {self._server_name}.{self._wrapper_tool_name}")
            print(f"[SimpleMCP-Stdio] Arguments: {kwargs}")

            # 通过简化管理器调用工具
            result = await self._manager.call_tool(
                server_name=self._server_name,
                tool_name=self._wrapper_tool_name,
                arguments=kwargs
            )

            # 提取结果文本
            # result 格式: {"content": [{"type": "text", "text": "..."}]}
            if isinstance(result, dict):
                content = result.get("content", [])
                if content and len(content) > 0:
                    first_item = content[0]
                    if isinstance(first_item, dict):
                        text = first_item.get("text")
                        if text is not None:
                            return text
                    return str(first_item)
                return "Empty result"

            return str(result)

        except Exception as e:
            error_msg = f"Error calling {self._server_name}.{self._wrapper_tool_name}: {str(e)}"
            print(f"[SimpleMCP-Stdio] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
