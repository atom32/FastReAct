"""
FastAPI Gateway with SSE streaming support

提供 HTTP SSE 接口，支持流式响应。
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...core.streaming import StreamChunk, StreamChunkType
from ...bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model
from ... import FastReAct

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str
    enable_thinking: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@router.get("/stream")
async def chat_stream_sse(
    query: str = Query(..., description="用户查询"),
    enable_thinking: bool = Query(True, description="是否输出思考过程"),
):
    """
    SSE 流式聊天端点

    返回 Server-Sent Events 格式的流式响应。

    使用示例:
    ```bash
    curl "http://localhost:8765/v1/chat/stream?query=帮我写个排序算法"
    ```
    """
    # 加载配置
    try:
        config = load_config()
        api_key = get_api_key(config)
        base_url = get_base_url(config)
        model = get_model(config)
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        # 返回错误事件
        async def error_stream():
            error_chunk = StreamChunk(
                type=StreamChunkType.ERROR,
                content=f"配置加载失败: {e}",
            )
            yield error_chunk.to_sse()

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
        )

    async def generate():
        """生成 SSE 流式响应"""
        # 创建 Agent
        agent = FastReAct(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )

        try:
            # 流式执行
            async for chunk in agent.run_streaming(
                query=query,
                enable_thinking=enable_thinking,
            ):
                # 转换为 SSE 格式
                yield chunk.to_sse()

        except Exception as e:
            logger.error(f"流式执行错误: {e}")
            error_chunk = StreamChunk(
                type=StreamChunkType.ERROR,
                content=str(e),
            )
            yield error_chunk.to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


@router.post("/stream")
async def chat_stream_sse_post(request: ChatRequest):
    """
    SSE 流式聊天端点（POST 方法）

    使用示例:
    ```bash
    curl -X POST "http://localhost:8765/v1/chat/stream" \
      -H "Content-Type: application/json" \
      -d '{"query": "帮我写个排序算法", "enable_thinking": true}'
    ```
    """
    # 加载配置
    try:
        config = load_config()
        api_key = get_api_key(config)
        base_url = get_base_url(config)
        model = get_model(config)
    except Exception as e:
        logger.error(f"配置加载失败: {e}")

        async def error_stream():
            error_chunk = StreamChunk(
                type=StreamChunkType.ERROR,
                content=f"配置加载失败: {e}",
            )
            yield error_chunk.to_sse()

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
        )

    async def generate():
        """生成 SSE 流式响应"""
        # 创建 Agent（可以应用自定义参数）
        agent = FastReAct(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=request.temperature or 0.3,
            max_tokens=request.max_tokens or 8192,
        )

        try:
            # 流式执行
            async for chunk in agent.run_streaming(
                query=request.query,
                enable_thinking=request.enable_thinking,
            ):
                yield chunk.to_sse()

        except Exception as e:
            logger.error(f"流式执行错误: {e}")
            error_chunk = StreamChunk(
                type=StreamChunkType.ERROR,
                content=str(e),
            )
            yield error_chunk.to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def create_streaming_router() -> APIRouter:
    """创建流式响应路由器"""
    return router
