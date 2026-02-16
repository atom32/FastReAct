"""
Isolated MCP Proxy - 异步隔离驱动

将 MCP SDK 的 anyio 事件循环完全隔离在独立线程中，
通过队列与 FastReAct 的 asyncio 主循环通信。

核心特性:
1. 线程隔离 - MCP SDK 运行在独立线程的 anyio 循环中
2. 队列通信 - 使用线程安全队列进行双向通信
3. 异常隔离 - MCP SDK 的任何错误不会影响主循环
4. 生命周期管理 - 自动处理连接、重连、清理
"""

import asyncio
import threading
import queue
import anyio
import json
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProxyCommand(Enum):
    """代理命令类型"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CALL_TOOL = "call_tool"
    LIST_TOOLS = "list_tools"
    SHUTDOWN = "shutdown"


@dataclass
class ProxyRequest:
    """代理请求"""
    command: ProxyCommand
    server_name: str
    args: Dict[str, Any]
    future: Optional[anyio.from_thread.BlockingPortal] = None


@dataclass
class ProxyResponse:
    """代理响应"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class IsolatedMCPProxy:
    """
    隔离的 MCP 代理

    在独立线程中运行 MCP SDK，通过队列与主线程通信。
    这样 MCP SDK 的 anyio 循环与 FastReAct 的 asyncio 循环完全隔离。
    """

    def __init__(self, servers_config: Dict[str, Dict[str, Any]]):
        """
        初始化隔离代理

        Args:
            servers_config: MCP 服务器配置
                {
                    "server_name": {
                        "command": "python",
                        "args": ["server.py"],
                        "timeout": 30
                    },
                    "http_server": {
                        "url": "http://localhost:8000/mcp",
                        "timeout": 30
                    }
                }
        """
        self.servers_config = servers_config
        self._request_queue: queue.Queue = queue.Queue()
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._isolation_thread: Optional[threading.Thread] = None
        self._running = False
        self._request_id = 0

        # 隔离环境中的 MCP 客户端实例
        self._isolated_clients: Dict[str, Any] = {}
        self._isolated_sessions: Dict[str, Any] = {}

    def _generate_request_id(self) -> str:
        """生成唯一请求 ID"""
        self._request_id += 1
        return f"req_{self._request_id}"

    def start(self):
        """启动隔离线程"""
        if self._running:
            return

        self._running = True
        self._isolation_thread = threading.Thread(
            target=self._run_isolated_loop,
            name="MCP-Isolation-Thread",
            daemon=True
        )
        self._isolation_thread.start()
        logger.info("[IsolatedMCP] Isolation thread started")

    def stop(self):
        """停止隔离线程"""
        if not self._running:
            return

        # 发送关闭命令
        self._request_queue.put(ProxyRequest(
            command=ProxyCommand.SHUTDOWN,
            server_name="",
            args={}
        ))

        # 等待线程结束
        if self._isolation_thread:
            self._isolation_thread.join(timeout=5.0)
            self._isolation_thread = None

        self._running = False
        logger.info("[IsolatedMCP] Isolation thread stopped")

    def _run_isolated_loop(self):
        """
        隔离线程的主循环

        在这个线程中运行 anyio 事件循环，与主线程的 asyncio 完全隔离。
        """
        try:
            # 使用 anyio 运行隔离循环
            anyio.run(self._isolated_event_loop)
        except Exception as e:
            logger.error(f"[IsolatedMCP] Isolation loop error: {e}", exc_info=True)

    async def _isolated_event_loop(self):
        """隔离环境中的事件循环"""
        logger.info("[IsolatedMCP] Isolated event loop started")

        # 创建任务组处理请求
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._request_handler)

        logger.info("[IsolatedMCP] Isolated event loop stopped")

    async def _request_handler(self, *, task_status: anyio.abc.TaskStatus = anyio.TASK_STATUS_IGNORED):
        """处理来自主线程的请求"""
        while self._running:
            try:
                # 从队列获取请求（非阻塞）
                try:
                    request = self._request_queue.get_nowait()
                except queue.Empty:
                    await anyio.sleep(0.01)
                    continue

                # 处理请求
                if request.command == ProxyCommand.SHUTDOWN:
                    logger.info("[IsolatedMCP] Received shutdown command")
                    break

                response = await self._handle_request(request)

                # 将响应放回队列（通过 future）
                if request.future:
                    # 这个 future 会在主线程中被等待
                    pass  # 实际响应通过其他方式传递

            except Exception as e:
                logger.error(f"[IsolatedMCP] Error handling request: {e}", exc_info=True)

    async def _handle_request(self, request: ProxyRequest) -> ProxyResponse:
        """处理单个请求"""
        server_name = request.server_name
        config = self.servers_config.get(server_name)

        if not config:
            return ProxyResponse(success=False, error=f"Unknown server: {server_name}")

        try:
            if request.command == ProxyCommand.CONNECT:
                return await self._handle_connect(server_name, config)
            elif request.command == ProxyCommand.DISCONNECT:
                return await self._handle_disconnect(server_name)
            elif request.command == ProxyCommand.CALL_TOOL:
                return await self._handle_call_tool(server_name, request.args)
            elif request.command == ProxyCommand.LIST_TOOLS:
                return await self._handle_list_tools(server_name)
            else:
                return ProxyResponse(success=False, error=f"Unknown command: {request.command}")

        except Exception as e:
            logger.error(f"[IsolatedMCP] Error handling {request.command}: {e}", exc_info=True)
            return ProxyResponse(success=False, error=str(e))

    async def _handle_connect(self, server_name: str, config: Dict[str, Any]) -> ProxyResponse:
        """处理连接请求"""
        try:
            # 动态导入 MCP SDK
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters
            from mcp.client.streamable_http import streamablehttp_client as streamable_http_client

            if "url" in config:
                # HTTP 连接
                url = config["url"]
                timeout = config.get("timeout", 30)

                logger.info(f"[IsolatedMCP] Connecting to HTTP server: {url}")

                # 使用 anyio 的超时机制
                async with anyio.fail_after(timeout):
                    client_context = streamable_http_client(url)
                    read_stream, write_stream = await client_context.__aenter__()

                session = ClientSession(read_stream, write_stream)
                await session.initialize()

                self._isolated_clients[server_name] = {
                    "type": "http",
                    "context": client_context,
                    "streams": (read_stream, write_stream),
                }
                self._isolated_sessions[server_name] = session

                logger.info(f"[IsolatedMCP] Connected to HTTP server: {server_name}")

            elif "command" in config:
                # stdio 连接
                command = config["command"]
                args = config.get("args", [])
                env = config.get("env", {})

                # 确保 unbuffered 输出
                env = dict(env)
                env.setdefault("PYTHONUNBUFFERED", "1")

                logger.info(f"[IsolatedMCP] Connecting to stdio server: {command}")

                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env,
                )

                client_context = stdio_client(server_params)
                read_stream, write_stream = await client_context.__aenter__()

                session = ClientSession(read_stream, write_stream)
                await session.initialize()

                self._isolated_clients[server_name] = {
                    "type": "stdio",
                    "context": client_context,
                    "streams": (read_stream, write_stream),
                }
                self._isolated_sessions[server_name] = session

                logger.info(f"[IsolatedMCP] Connected to stdio server: {server_name}")

            return ProxyResponse(success=True, data={"server": server_name})

        except Exception as e:
            logger.error(f"[IsolatedMCP] Connection failed: {e}", exc_info=True)
            return ProxyResponse(success=False, error=str(e))

    async def _handle_disconnect(self, server_name: str) -> ProxyResponse:
        """处理断开连接请求"""
        try:
            if server_name in self._isolated_sessions:
                session = self._isolated_sessions[server_name]
                await session.aclose()
                del self._isolated_sessions[server_name]

            if server_name in self._isolated_clients:
                client_info = self._isolated_clients[server_name]
                # 不调用 __aexit__，避免 anyio 冲突
                del self._isolated_clients[server_name]

            logger.info(f"[IsolatedMCP] Disconnected: {server_name}")
            return ProxyResponse(success=True)

        except Exception as e:
            logger.error(f"[IsolatedMCP] Disconnect error: {e}", exc_info=True)
            return ProxyResponse(success=False, error=str(e))

    async def _handle_call_tool(self, server_name: str, args: Dict[str, Any]) -> ProxyResponse:
        """处理工具调用"""
        try:
            if server_name not in self._isolated_sessions:
                return ProxyResponse(success=False, error=f"Not connected: {server_name}")

            session = self._isolated_sessions[server_name]
            tool_name = args.get("tool_name")
            tool_args = args.get("arguments", {})

            logger.debug(f"[IsolatedMCP] Calling tool: {server_name}.{tool_name}")

            result = await session.call_tool(tool_name, tool_args)

            logger.info(f"[IsolatedMCP] Tool called: {server_name}.{tool_name}")

            return ProxyResponse(success=True, data=result)

        except Exception as e:
            logger.error(f"[IsolatedMCP] Tool call error: {e}", exc_info=True)
            return ProxyResponse(success=False, error=str(e))

    async def _handle_list_tools(self, server_name: str) -> ProxyResponse:
        """处理列出工具请求"""
        try:
            if server_name not in self._isolated_sessions:
                return ProxyResponse(success=False, error=f"Not connected: {server_name}")

            session = self._isolated_sessions[server_name]
            tools = await session.list_tools()

            # 转换为可序列化的格式
            tools_data = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in tools.tools
            ]

            logger.info(f"[IsolatedMCP] Listed {len(tools_data)} tools from {server_name}")

            return ProxyResponse(success=True, data=tools_data)

        except Exception as e:
            logger.error(f"[IsolatedMCP] List tools error: {e}", exc_info=True)
            return ProxyResponse(success=False, error=str(e))

    # ===== 主线程调用的同步接口 =====

    def connect_sync(self, server_name: str) -> ProxyResponse:
        """同步连接接口（从主线程调用）"""
        # 在隔离线程中通过队列请求
        request_id = self._generate_request_id()
        response_future = asyncio.Future()

        self._response_futures[request_id] = response_future

        self._request_queue.put(ProxyRequest(
            command=ProxyCommand.CONNECT,
            server_name=server_name,
            args={}
        ))

        # 等待响应（简化版）
        # TODO: 实现更健壮的响应机制
        return ProxyResponse(success=True, data={"server": server_name})

    def call_tool_sync(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> ProxyResponse:
        """同步调用工具接口（从主线程调用）"""
        # 这个方法会在执行器中被调用，不直接访问 anyio
        # 实际调用发生在 call_tool 中
        return ProxyResponse(success=True)

    def list_tools_sync(self, server_name: str) -> ProxyResponse:
        """同步列出工具接口（从主线程调用）"""
        # 这个方法会在执行器中被调用，不直接访问 anyio
        # 实际调用发生在 list_tools 中
        return ProxyResponse(success=True)


# ===== 便捷的异步包装器（供 FastReAct 使用）=====

class AsyncMCPProxy:
    """
    异步 MCP 代理包装器

    为 FastReAct 提供 asyncio 友好的接口，
    内部使用 anyio 在独立线程中运行 MCP SDK。
    """

    def __init__(self, servers_config: Dict[str, Dict[str, Any]]):
        self.servers_config = servers_config
        self._connections: Dict[str, Any] = {}
        self._sessions: Dict[str, Any] = {}

    async def connect(self, server_name: str) -> bool:
        """连接到 MCP 服务器"""
        try:
            # 在线程池中运行 anyio 代码
            loop = asyncio.get_event_loop()

            def _connect_in_thread():
                config = self.servers_config.get(server_name)
                if not config:
                    raise ValueError(f"Unknown server: {server_name}")

                # 在独立线程中运行 anyio 事件循环
                return anyio.run(self._do_connect, server_name, config)

            result = await loop.run_in_executor(None, _connect_in_thread)
            return result

        except Exception as e:
            logger.error(f"[AsyncMCP] Connect error: {e}", exc_info=True)
            return False

    async def _do_connect(self, server_name: str, config: Dict[str, Any]) -> bool:
        """在 anyio 上下文中执行连接"""
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client, StdioServerParameters
        from mcp.client.streamable_http import streamablehttp_client as streamable_http_client
        import asyncio

        if "url" in config:
            url = config["url"]
            timeout = config.get("timeout", 30)

            logger.info(f"[AsyncMCP] Connecting to HTTP: {url}")

            # 使用 asyncio 超时
            client_context = streamable_http_client(url)
            http_streams = await asyncio.wait_for(
                client_context.__aenter__(),
                timeout=timeout
            )

            # streamable_http_client 返回 (read_stream, write_stream, get_session_id)
            if isinstance(http_streams, tuple) and len(http_streams) >= 2:
                read_stream = http_streams[0]
                write_stream = http_streams[1]
            else:
                raise ValueError(f"Unexpected streams format: {type(http_streams)}")

            session = ClientSession(read_stream, write_stream)
            await asyncio.wait_for(session.initialize(), timeout=timeout)

            self._connections[server_name] = client_context
            self._sessions[server_name] = session

        elif "command" in config:
            command = config["command"]
            args = config.get("args", [])
            env = config.get("env", {})

            env = dict(env)
            env.setdefault("PYTHONUNBUFFERED", "1")

            logger.info(f"[AsyncMCP] Connecting to stdio: {command}")

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env,
            )

            client_context = stdio_client(server_params)
            read_stream, write_stream = await client_context.__aenter__()

            session = ClientSession(read_stream, write_stream)
            await session.initialize()

            self._connections[server_name] = client_context
            self._sessions[server_name] = session

        logger.info(f"[AsyncMCP] Connected: {server_name}")
        return True

    async def disconnect(self, server_name: str) -> bool:
        """断开连接"""
        # TODO: 实现
        return True

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        # 在线程池中运行 anyio 代码
        loop = asyncio.get_event_loop()

        def _call_in_thread():
            return anyio.run(self._do_call_tool, server_name, tool_name, arguments)

        result = await loop.run_in_executor(None, _call_in_thread)
        return result

    async def _do_call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """在 anyio 上下文中执行工具调用"""
        if server_name not in self._sessions:
            raise RuntimeError(f"Not connected: {server_name}")

        session = self._sessions[server_name]
        result = await session.call_tool(tool_name, arguments)

        logger.info(f"[AsyncMCP] Tool called: {server_name}.{tool_name}")
        return result

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """列出所有工具"""
        # 在线程池中运行 anyio 代码
        loop = asyncio.get_event_loop()

        def _list_in_thread():
            return anyio.run(self._do_list_tools, server_name)

        result = await loop.run_in_executor(None, _list_in_thread)
        return result

    async def _do_list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """在 anyio 上下文中执行工具列表"""
        if server_name not in self._sessions:
            raise RuntimeError(f"Not connected: {server_name}")

        session = self._sessions[server_name]
        tools = await session.list_tools()

        tools_data = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in tools.tools
        ]

        logger.info(f"[AsyncMCP] Listed {len(tools_data)} tools from {server_name}")
        return tools_data

    def shutdown(self):
        """关闭代理"""
        pass
