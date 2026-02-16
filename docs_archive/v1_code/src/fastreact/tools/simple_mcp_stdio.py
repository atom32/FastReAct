"""
简化版 MCP stdio 客户端

完全绕过 MCP SDK，直接使用 asyncio subprocess 实现 MCP 协议。
这样避免 anyio/asyncio 兼容性问题。

MCP 协议规范:
- JSON-RPC 2.0 over stdin/stdout
- 每行一个 JSON 对象
"""

import asyncio
import json
import uuid
import shutil
import os
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SimpleMCPStdioClient:
    """
    简化的 MCP stdio 客户端

    直接实现 MCP 协议，不依赖 MCP SDK
    """

    def __init__(self, command: str, args: List[str], timeout: float = 30.0, env: Optional[Dict[str, str]] = None):
        """
        初始化客户端

        Args:
            command: 启动 MCP 服务器的命令
            args: 命令参数
            timeout: 请求超时时间（秒）
            env: 环境变量字典（可选）
        """
        self.command = command
        self.args = args
        self.timeout = timeout
        self.env = env
        self._process: Optional[asyncio.subprocess.Process] = None
        self._initialized = False

    async def connect(self) -> bool:
        """
        启动 MCP 服务器进程并初始化会话

        Returns:
            是否连接成功
        """
        try:
            # 准备环境变量：合并自定义 env 和系统环境变量
            process_env = os.environ.copy()

            # 添加自定义环境变量
            if self.env:
                process_env.update(self.env)

            # 确保 PYTHONUNBUFFERED 设置（用于即时 stdio 通信）
            process_env["PYTHONUNBUFFERED"] = "1"

            # 启动子进程
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env
            )

            logger.info(f"[SimpleMCP] Started process: {self.command} {' '.join(self.args)}")

            # 初始化会话
            await self._initialize_session()

            logger.info("[SimpleMCP] Session initialized")
            return True

        except Exception as e:
            logger.error(f"[SimpleMCP] Connection failed: {e}", exc_info=True)
            if self._process:
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
        logger.info("[SimpleMCP] Disconnected")

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
                logger.warning(f"[SimpleMCP] Cleanup error: {e}")

            self._process = None

        self._initialized = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()


class SimpleMCPStdioManager:
    """
    简化版 MCP stdio 管理器

    管理多个 stdio MCP 服务器连接
    """

    def __init__(self, servers_config: Dict[str, Dict[str, Any]]):
        """
        初始化管理器

        Args:
            servers_config: 服务器配置
                {
                    "server_name": {
                        "command": "python",
                        "args": ["server.py"],
                        "timeout": 30
                    }
                }
        """
        self.servers_config = servers_config
        self._clients: Dict[str, SimpleMCPStdioClient] = {}

    def _resolve_command(self, command: str) -> str:
        """
        解析命令的完整路径

        自动查找系统 PATH 中的命令，支持跨平台

        Args:
            command: 命令名称或路径

        Returns:
            命令的完整路径
        """
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(command):
            return command

        # 使用 shutil.which 查找命令
        resolved = shutil.which(command)

        if resolved:
            logger.info(f"[SimpleMCP] Resolved '{command}' -> '{resolved}'")
            return resolved

        # 找不到命令，返回原值（让错误在后面抛出）
        logger.warning(f"[SimpleMCP] Could not resolve '{command}' in PATH")
        return command

    def _expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        展开配置中的环境变量

        支持 ${VAR_NAME} 格式的环境变量引用

        Args:
            config: 原始配置

        Returns:
            展开环境变量后的配置
        """
        expanded = {}

        for key, value in config.items():
            if isinstance(value, str):
                # 展开字符串中的环境变量
                expanded_value = os.path.expandvars(value)
                # 检查是否有未展开的变量（说明环境变量未设置）
                if '${' in expanded_value:
                    var_name = expanded_value.split('${')[1].split('}')[0]
                    logger.warning(f"[SimpleMCP] Environment variable '{var_name}' not set")
                expanded[key] = expanded_value
            elif isinstance(value, dict):
                # 递归处理字典（如 env 字段）
                expanded[key] = self._expand_env_vars(value)
            elif isinstance(value, list):
                # 处理列表：只递归字典元素，字符串和其他类型保持不变
                expanded[key] = [
                    self._expand_env_vars(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                expanded[key] = value

        return expanded

    async def connect_all(self) -> Dict[str, bool]:
        """连接所有服务器"""
        results = {}

        for name, config in self.servers_config.items():
            try:
                # 展开环境变量（${VAR} -> 实际值）
                expanded_config = self._expand_env_vars(config)

                command = expanded_config.get("command")
                args = expanded_config.get("args", [])
                env = expanded_config.get("env", {})
                timeout = expanded_config.get("timeout", 30.0)

                if not command:
                    results[name] = False
                    continue

                # 自动解析命令路径（支持 npx, python, docker 等）
                resolved_command = self._resolve_command(command)

                print(f"[INFO] Connecting to '{name}' (stdio, simple client)...")

                # 传递 env 给客户端（重要！）
                client = SimpleMCPStdioClient(resolved_command, args, timeout, env)
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
