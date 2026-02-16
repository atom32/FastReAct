"""
简化版 MCP 客户端

完全绕过 MCP SDK，直接使用 asyncio HTTP 客户端实现 MCP 协议。
这样避免 anyio/asyncio 兼容性问题。

MCP 协议规范:
- JSON-RPC 2.0 over HTTP
- 端点: /mcp (POST)
- SSE 端点: /sse (GET)
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
import logging

import httpx

logger = logging.getLogger(__name__)


class SimpleMCPClient:
    """
    简化的 MCP HTTP 客户端

    直接实现 MCP 协议，不依赖 MCP SDK
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        初始化客户端

        Args:
            base_url: MCP 服务器基础 URL (e.g., "http://localhost:8000/mcp")
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None
        self._initialized = False

    async def connect(self) -> bool:
        """
        连接到 MCP 服务器并初始化会话

        Returns:
            是否连接成功
        """
        try:
            # 创建 HTTP 客户端
            self._http_client = httpx.AsyncClient(timeout=self.timeout)

            # 初始化会话
            await self._initialize_session()

            logger.info(f"[SimpleMCP] Connected to {self.base_url}")
            return True

        except Exception as e:
            logger.error(f"[SimpleMCP] Connection failed: {e}", exc_info=True)
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
                    "name": "fastreact-simple-client",
                    "version": "1.0.0"
                }
            }
        }

        response = await self._send_request(request)

        if response.get("error"):
            error = response["error"]
            raise RuntimeError(f"Initialize failed: {error}")

        # 发送 initialized 通知
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        await self._send_notification(notification)

        self._initialized = True
        logger.info("[SimpleMCP] Session initialized")

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送 JSON-RPC 请求并获取响应"""
        if not self._http_client:
            raise RuntimeError("Not connected")

        headers = {
            "Content-Type": "application/json",
        }

        # 如果有会话 ID，添加到 header
        if self._session_id:
            headers["mcp-session-id"] = self._session_id

        try:
            response = await self._http_client.post(
                self.base_url,
                json=request,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()

            # 检查响应中的 session ID
            if "mcp-session-id" in response.headers:
                self._session_id = response.headers["mcp-session-id"]

            # 解析响应
            data = response.json()

            # 处理 SSE 事件（如果有）
            # 简化版暂时忽略 SSE 流

            return data

        except httpx.HTTPError as e:
            logger.error(f"[SimpleMCP] HTTP error: {e}")
            raise

    async def _send_notification(self, notification: Dict[str, Any]) -> None:
        """发送 JSON-RPC 通知（不需要响应）"""
        if not self._http_client:
            raise RuntimeError("Not connected")

        headers = {
            "Content-Type": "application/json",
        }

        if self._session_id:
            headers["mcp-session-id"] = self._session_id

        try:
            await self._http_client.post(
                self.base_url,
                json=notification,
                headers=headers,
                timeout=self.timeout
            )
        except httpx.HTTPError as e:
            logger.warning(f"[SimpleMCP] Notification failed: {e}")

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
        if self._http_client:
            # 发送关闭会话请求
            if self._session_id:
                try:
                    await self._http_client.delete(
                        self.base_url,
                        headers={"mcp-session-id": self._session_id},
                        timeout=5.0
                    )
                except:
                    pass

            await self._http_client.aclose()
            self._http_client = None

        self._session_id = None
        self._initialized = False

        logger.info("[SimpleMCP] Disconnected")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()


class SimpleMCPManager:
    """
    简化版 MCP 管理器

    管理多个 MCP 服务器连接，使用简化版客户端
    """

    def __init__(self, servers_config: Dict[str, Dict[str, Any]]):
        """
        初始化管理器

        Args:
            servers_config: 服务器配置
                {
                    "server_name": {
                        "url": "http://localhost:8000/mcp",
                        "timeout": 30
                    }
                }
        """
        self.servers_config = servers_config
        self._clients: Dict[str, SimpleMCPClient] = {}

    async def connect_all(self) -> Dict[str, bool]:
        """连接所有服务器"""
        results = {}

        for name, config in self.servers_config.items():
            try:
                url = config.get("url")
                timeout = config.get("timeout", 30.0)

                if not url:
                    results[name] = False
                    continue

                print(f"[INFO] Connecting to '{name}' (simple client)...")

                client = SimpleMCPClient(url, timeout)
                success = await client.connect()

                if success:
                    self._clients[name] = client
                    results[name] = True
                    print(f"[INFO] Connected to '{name}'")
                else:
                    results[name] = False

            except Exception as e:
                logger.error(f"[SimpleMCP] Failed to connect to '{name}': {e}")
                results[name] = False

        return results

    async def disconnect_all(self):
        """断开所有连接"""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """列出指定服务器的工具"""
        if server_name not in self._clients:
            raise ValueError(f"Server '{server_name}' not connected")

        client = self._clients[server_name]
        return await client.list_tools()

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用指定服务器的工具"""
        if server_name not in self._clients:
            raise ValueError(f"Server '{server_name}' not connected")

        client = self._clients[server_name]
        return await client.call_tool(tool_name, arguments)

    def get_all_server_names(self) -> List[str]:
        """获取所有已连接的服务器名称"""
        return list(self._clients.keys())
