"""
FastReAct MCP Protocol Implementation

完全自主实现的 MCP 协议支持，不依赖官方 MCP SDK。
直接使用 asyncio.subprocess + JSON-RPC 2.0，完美兼容 FastReAct 架构。

特性:
- 零任何依赖冲突 (No anyio/asyncio issues)
- 原生 asyncio 性能
- 完整的 MCP 协议支持
- 支持 stdio 和 HTTP 传输

模块:
- client: MCP 客户端实现
- stdio_client: stdio 传输客户端
- http_client: HTTP 传输客户端 (待实现)
- manager: 连接管理器
"""

from .manager import MCPManager

__all__ = ['MCPManager']
