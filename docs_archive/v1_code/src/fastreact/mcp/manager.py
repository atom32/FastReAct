"""
FastReAct MCP 管理器

管理多个 MCP 服务器连接，提供统一的工具访问接口。
完全自主实现，不依赖 MCP SDK。
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

from .stdio_client import MCPStdioClient

logger = logging.getLogger(__name__)


class MCPManager:
    """
    MCP 连接管理器

    管理多个 MCP 服务器连接，提供统一的工具访问接口
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化管理器

        Args:
            config_path: 配置文件路径（可选）
        """
        self._clients: Dict[str, MCPStdioClient] = {}
        self._config_path = config_path
        self._servers_config: Dict[str, Dict[str, Any]] = {}

        # 如果提供了配置文件，自动加载
        if config_path:
            self.load_config(config_path)

    def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """
        添加 MCP 服务器

        Args:
            name: 服务器名称（唯一标识）
            config: 服务器配置
                - stdio: {"command": "cmd", "args": [...], "timeout": 30}
        """
        if name in self._clients:
            raise ValueError(f"Server '{name}' already exists")

        self._servers_config[name] = config

    def remove_server(self, name: str) -> None:
        """
        移除 MCP 服务器

        Args:
            name: 服务器名称
        """
        if name in self._servers_config:
            del self._servers_config[name]
        if name in self._clients:
            del self._clients[name]

    def load_config(self, config_path: str) -> None:
        """
        从配置文件加载 MCP 服务器

        Args:
            config_path: 配置文件路径（JSON 格式）

        配置格式:
            {
                "mcp": {
                    "enabled": true,
                    "servers": {
                        "server_name": {
                            "command": "python",
                            "args": ["server.py"],
                            "timeout": 30
                        }
                    }
                }
            }
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if not config.get("mcp", {}).get("enabled", False):
            logger.info("[MCPManager] MCP disabled in config")
            return

        servers = config.get("mcp", {}).get("servers", {})
        for name, server_config in servers.items():
            self.add_server(name, server_config)

        logger.info(f"[MCPManager] Loaded {len(servers)} servers from config")

    async def connect_all(self) -> Dict[str, bool]:
        """
        连接所有服务器

        Returns:
            连接结果字典 {server_name: success}
        """
        results = {}

        for name, config in self._servers_config.items():
            try:
                command = config.get("command")
                args = config.get("args", [])
                timeout = config.get("timeout", 30.0)

                if not command:
                    logger.warning(f"[MCPManager] Server '{name}' has no command, skipping")
                    results[name] = False
                    continue

                print(f"[INFO] Connecting to '{name}' (native MCP client)...")

                client = MCPStdioClient(command, args, timeout)
                success = await client.connect()

                if success:
                    self._clients[name] = client
                    results[name] = True
                    print(f"[INFO] Connected to '{name}'")
                else:
                    results[name] = False

            except Exception as e:
                logger.error(f"[MCPManager] Failed to connect to '{name}': {e}")
                results[name] = False

        return results

    async def disconnect_all(self) -> None:
        """断开所有服务器连接"""
        tasks = [
            client.disconnect()
            for client in self._clients.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._clients.clear()

    async def list_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取工具列表

        Args:
            server_name: 服务器名称（可选，如果不指定则获取所有）

        Returns:
            工具列表
        """
        if server_name:
            if server_name not in self._clients:
                raise ValueError(f"Server '{server_name}' not connected")

            client = self._clients[server_name]
            return await client.list_tools()

        # 返回所有服务器的工具
        all_tools = []
        for name, client in self._clients.items():
            try:
                tools = await client.list_tools()
                for tool in tools:
                    tool["_server"] = name
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"[MCPManager] Failed to list tools from '{name}': {e}")

        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用工具

        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if server_name not in self._clients:
            raise ValueError(f"Server '{server_name}' not connected")

        client = self._clients[server_name]
        return await client.call_tool(tool_name, arguments)

    def list_servers(self) -> List[str]:
        """
        列出所有服务器名称

        Returns:
            服务器名称列表
        """
        return list(self._clients.keys())

    async def get_tools_for_fastreact(self) -> List[Any]:
        """
        获取所有工具，转换为 FastReAct Tool 对象

        Returns:
            FastReAct Tool 对象列表
        """
        from fastreact.core.tool import Tool

        fastreact_tools = []

        for server_name, client in self._clients.items():
            try:
                if not client.is_connected:
                    logger.warning(f"[MCPManager] Server '{server_name}' is not connected, skipping...")
                    continue

                tools = await client.list_tools()

                for tool_data in tools:
                    # 创建 FastReAct Tool 包装器
                    wrapper = _MCPToolWrapper(
                        tool_name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=server_name,
                        manager=self
                    )
                    fastreact_tools.append(wrapper)

            except Exception as e:
                logger.error(f"[MCPManager] Failed to get tools from '{server_name}': {e}")

        return fastreact_tools


class _MCPToolWrapper(Tool):
    """
    MCP 工具包装器

    将 MCP 工具转换为 FastReAct Tool 对象
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        server_name: str,
        manager: MCPManager,
    ):
        self._wrapper_tool_name = tool_name
        self._wrapper_description = description
        self._wrapper_input_schema = input_schema
        self._server_name = server_name
        self._manager = manager

        super().__init__()

    def _get_description(self) -> str:
        return self._wrapper_description

    def _get_parameters(self) -> Dict[str, Any]:
        return self._wrapper_input_schema

    async def execute_async(self, **kwargs) -> str:
        """执行 MCP 工具"""
        try:
            logger.info(f"[MCP-Tool] Calling {self._server_name}.{self._wrapper_tool_name}")

            result = await self._manager.call_tool(
                server_name=self._server_name,
                tool_name=self._wrapper_tool_name,
                arguments=kwargs
            )

            # 提取结果文本
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
            logger.error(f"[MCP-Tool] {error_msg}")
            return error_msg
