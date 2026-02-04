"""
FastReAct MCP stdio 客户端

通过标准输入/输出实现 MCP 协议。
完全绕过 MCP SDK，使用原生 asyncio.subprocess。

MCP 协议规范:
- JSON-RPC 2.0 over stdin/stdout
- 每行一个 JSON 对象
- 请求/响应模式
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MCPStdioClient:
    """
    MCP stdio 客户端

    通过标准输入/输出与 MCP 服务器通信
    """

    def __init__(self, command: str, args: List[str], timeout: float = 30.0):
        """
        初始化客户端

        Args:
            command: 启动 MCP 服务器的命令
            args: 命令参数
            timeout: 请求超时时间（秒）
        """
        self.command = command
        self.args = args
        self.timeout = timeout
        self._process: Optional[asyncio.subprocess.Process] = None
        self._initialized = False
        self._server_info: Optional[Dict[str, Any]] = None

    async def connect(self) -> bool:
        """
        启动 MCP 服务器进程并初始化会话

        Returns:
            是否连接成功
        """
        try:
            # 启动子进程
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PYTHONUNBUFFERED": "1"}
            )

            logger.info(f"[MCP-Stdio] Started process: {self.command} {' '.join(self.args)}")

            # 初始化会话
            await self._initialize_session()

            logger.info(f"[MCP-Stdio] Session initialized")
            return True

        except Exception as e:
            logger.error(f"[MCP-Stdio] Connection failed: {e}", exc_info=True)
            await self._cleanup()
            return False

    async def _initialize_session(self):
        """初始化 MCP 会话"""
        # 创建新会话
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    }
                },
                "clientInfo": {
                    "name": "fastreact",
                    "version": "1.1.0"
                }
            }
        }

        response = await self._send_request(request)

        if response.get("error"):
            error = response["error"]
            raise RuntimeError(f"Initialize failed: {error}")

        # 保存服务器信息
        self._server_info = response.get("result", {}).get("serverInfo", {})

        # 发送 initialized 通知
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        await self._send_notification(notification)

        self._initialized = True

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送 JSON-RPC 请求并获取响应"""
        if not self._process or not self._process.stdin:
            raise RuntimeError("Process not running")

        # 发送请求
        request_line = json.dumps(request) + "\n"
        self._process.stdin.write(request_line.encode())
        await self._process.stdin.drain()

        # 读取响应
        response_line = await asyncio.wait_for(
            self._process.stdout.readline(),
            timeout=self.timeout
        )

        if not response_line:
            raise RuntimeError("Empty response from server")

        response = json.loads(response_line.decode().strip())
        return response

    async def _send_notification(self, notification: Dict[str, Any]) -> None:
        """发送 JSON-RPC 通知（不需要响应）"""
        if not self._process or not self._process.stdin:
            raise RuntimeError("Process not running")

        notification_line = json.dumps(notification) + "\n"
        self._process.stdin.write(notification_line.encode())
        await self._process.stdin.drain()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有可用工具

        Returns:
            工具列表
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized")

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }

        response = await self._send_request(request)

        if response.get("error"):
            error = response["error"]
            raise RuntimeError(f"List tools failed: {error}")

        result = response.get("result", {})
        tools = result.get("tools", [])

        return [
            {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {})
            }
            for tool in tools
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized")

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }

        response = await self._send_request(request)

        if response.get("error"):
            error = response["error"]
            raise RuntimeError(f"Tool call failed: {error}")

        result = response.get("result", {})
        return result

    async def disconnect(self):
        """断开连接"""
        await self._cleanup()
        logger.info("[MCP-Stdio] Disconnected")

    async def _cleanup(self):
        """清理资源"""
        if self._process:
            try:
                # 关闭 stdin
                if self._process.stdin:
                    self._process.stdin.close()
                    await self._process.stdin.wait_closed()

                # 等待进程结束
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # 强制终止
                    self._process.kill()
                    await self._process.wait()

            except Exception as e:
                logger.warning(f"[MCP-Stdio] Cleanup error: {e}")

            self._process = None

        self._initialized = False
        self._server_info = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._process is not None and self._initialized

    @property
    def server_info(self) -> Optional[Dict[str, Any]]:
        """服务器信息"""
        return self._server_info
