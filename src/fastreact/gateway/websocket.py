"""
WebSocket streaming support for FastReAct Gateway

提供双向流式通信，支持实时对话和流式输出。
"""

import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from ...core.streaming import StreamChunk, StreamChunkType
from ...bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model
from ... import FastReAct

logger = logging.getLogger(__name__)


class WebSocketStreamer:
    """WebSocket 流式处理器"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self._agent = None
        self._config = None

    async def initialize_agent(self):
        """初始化 Agent"""
        try:
            self._config = load_config()
            api_key = get_api_key(self._config)
            base_url = get_base_url(self._config)
            model = get_model(self._config)

            self._agent = FastReAct(
                api_key=api_key,
                base_url=base_url,
                model=model,
            )

            # 发送初始化成功消息
            await self.send_json({
                "type": "metadata",
                "content": "connected",
                "metadata": {
                    "model": model,
                    "base_url": base_url,
                },
            })

            return True
        except Exception as e:
            logger.error(f"Agent 初始化失败: {e}")
            await self.send_json({
                "type": "error",
                "content": str(e),
            })
            return False

    async def send_json(self, data: dict):
        """发送 JSON 数据"""
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise WebSocketDisconnect()

    async def send_chunk(self, chunk: StreamChunk):
        """发送流式数据块"""
        await self.send_json(chunk.to_dict())

    async def handle_message(self, message: dict):
        """处理接收到的消息"""
        msg_type = message.get("type", "query")

        if msg_type == "query":
            query = message.get("query", "")
            enable_thinking = message.get("enable_thinking", True)

            if not query:
                await self.send_json({
                    "type": "error",
                    "content": "缺少 query 参数",
                })
                return

            # 执行流式查询
            await self.stream_query(query, enable_thinking)

        elif msg_type == "stop":
            # 停止当前执行
            await self.send_json({
                "type": "control",
                "content": "stopped",
            })

        else:
            await self.send_json({
                "type": "error",
                "content": f"未知消息类型: {msg_type}",
            })

    async def stream_query(self, query: str, enable_thinking: bool = True):
        """流式执行查询"""
        if not self._agent:
            await self.send_json({
                "type": "error",
                "content": "Agent 未初始化",
            })
            return

        try:
            async for chunk in self._agent.run_streaming(
                query=query,
                enable_thinking=enable_thinking,
            ):
                await self.send_chunk(chunk)

        except Exception as e:
            logger.error(f"流式查询错误: {e}")
            await self.send_json({
                "type": "error",
                "content": str(e),
            })

    async def run_loop(self):
        """WebSocket 主循环"""
        try:
            # 初始化 Agent
            if not await self.initialize_agent():
                return

            # 主消息循环
            while True:
                message = await self.websocket.receive_json()
                await self.handle_message(message)

        except WebSocketDisconnect:
            logger.info("WebSocket 连接断开")
        except Exception as e:
            logger.error(f"WebSocket 错误: {e}")

            try:
                await self.send_json({
                    "type": "error",
                    "content": str(e),
                })
            except:
                pass


async def websocket_chat_handler(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="认证令牌"),
):
    """
    WebSocket 流式聊天端点

    连接后发送 JSON 格式消息：
    {
        "type": "query",
        "query": "帮我写个排序算法",
        "enable_thinking": true
    }

    服务器会返回流式 JSON：
    {
        "type": "thinking",  # or "tool_call", "tool_result", "answer", "error", "metadata"
        "content": "...",
        "tool_name": "...",  // for tool_call
        "tool_params": {...},  // for tool_call
        "tool_status": "start/complete",  // for tool_call
        "timestamp": 1234567890.123
    }
    """
    await websocket.accept()

    # TODO: 验证 token
    # if token != "expected_token":
    #     await websocket.close(code=1008, reason="Unauthorized")
    #     return

    # 创建流式处理器
    streamer = WebSocketStreamer(websocket)

    # 运行主循环
    await streamer.run_loop()
