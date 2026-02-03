"""
流式响应模块

支持实时输出 <thinking> 标签、工具调用和执行结果。
提供 SSE 和 WebSocket 两种流式模式。
"""

import asyncio
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import AsyncIterator, Optional, Any, Dict, List
from datetime import datetime

from ..utils.logger import get_logger

logger = get_logger("fastreact.streaming")


class StreamChunkType(Enum):
    """流式数据块类型"""
    THINKING = "thinking"           # <thinking> 推理过程
    TOOL_CALL = "tool_call"         # 工具调用开始
    TOOL_RESULT = "tool_result"     # 工具执行结果
    ANSWER = "answer"               # 最终答案
    ERROR = "error"                 # 错误信息
    METADATA = "metadata"           # 元数据（开始、结束、统计等）
    CONTROL = "control"             # 控制信号（心跳等）


@dataclass
class StreamChunk:
    """流式响应数据块"""
    type: StreamChunkType
    content: str
    metadata: Optional[Dict[str, Any]] = None

    # 工具调用专用字段
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    tool_status: Optional[str] = None  # "start" | "progress" | "complete"
    tool_error: Optional[str] = None

    # 时间戳
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        result = {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp,
        }

        # 添加可选字段
        if self.metadata:
            result["metadata"] = self.metadata
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.tool_params:
            result["tool_params"] = self.tool_params
        if self.tool_status:
            result["tool_status"] = self.tool_status
        if self.tool_error:
            result["tool_error"] = self.tool_error

        return result

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"event: {self.type.value}\ndata: {data}\n\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamChunk":
        """从字典创建实例（用于 WebSocket 接收）"""
        return cls(
            type=StreamChunkType(data["type"]),
            content=data.get("content", ""),
            metadata=data.get("metadata"),
            tool_name=data.get("tool_name"),
            tool_params=data.get("tool_params"),
            tool_status=data.get("tool_status"),
            tool_error=data.get("tool_error"),
            timestamp=data.get("timestamp"),
        )


class StreamingContext:
    """流式上下文管理器

    管理 LLM 流式响应，解析 <thinking> 标签和工具调用。
    """

    def __init__(self, engine, enable_thinking: bool = True):
        """
        初始化流式上下文

        Args:
            engine: FastReAct 引擎实例
            enable_thinking: 是否输出 <thinking> 内容
        """
        self.engine = engine
        self.enable_thinking = enable_thinking
        self._buffer = ""
        self._in_thinking = False
        self._thinking_content = ""
        self._current_tool = None

    async def stream_with_sse(
        self,
        query: str,
    ) -> AsyncIterator[StreamChunk]:
        """
        SSE 流式响应

        Args:
            query: 用户查询

        Yields:
            StreamChunk: 流式数据块
        """
        # 1. 发送开始元数据
        yield StreamChunk(
            type=StreamChunkType.METADATA,
            content="start",
            metadata={"query": query, "mode": "sse"},
        )

        try:
            # 2. 构建消息上下文
            messages, context_metadata = await self.engine._build_messages_context(
                query,
                session_context=None,
                iteration=0,
            )

            # 3. 调用 LLM 流式 API
            async for delta in self._llm_stream_chat(messages):
                # 4. 解析 delta 内容
                async for chunk in self._process_delta(delta):
                    yield chunk

            # 5. 发送结束元数据
            stats = self.engine.get_stats()
            yield StreamChunk(
                type=StreamChunkType.METADATA,
                content="complete",
                metadata=stats,
            )

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield StreamChunk(
                type=StreamChunkType.ERROR,
                content=str(e),
            )

    async def _llm_stream_chat(self, messages: List[Dict]) -> AsyncIterator[Dict]:
        """
        调用 LLM 流式 API

        Args:
            messages: 消息列表

        Yields:
            Delta 对象（OpenAI 格式）
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.engine.api_key,
            base_url=self.engine.base_url,
        )

        stream = await client.chat.completions.create(
            model=self.engine.model,
            messages=messages,
            temperature=self.engine.temperature,
            max_tokens=self.engine.max_tokens,
            stream=True,
            tools=self._get_tool_definitions(),
        )

        async for chunk in stream:
            if chunk.choices:
                yield chunk

    def _get_tool_definitions(self) -> List[Dict]:
        """获取工具定义（OpenAI Function Calling 格式）"""
        tools = []
        for tool in self.engine.tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })
        return tools

    async def _process_delta(self, delta: Dict) -> AsyncIterator[StreamChunk]:
        """
        处理流式 delta

        Args:
            delta: OpenAI 流式响应块

        Yields:
            StreamChunk: 解析后的数据块
        """
        choice = delta.choices[0]

        # 处理推理过程
        if hasattr(choice, 'delta') and choice.delta:
            content = choice.delta.content or ""

            # 检测 <thinking> 标签
            if "<thinking>" in content:
                self._in_thinking = True

            if "</thinking>" in content:
                self._in_thinking = False
                # 发送完整的 thinking
                if self.enable_thinking and self._thinking_content:
                    yield StreamChunk(
                        type=StreamChunkType.THINKING,
                        content=self._thinking_content,
                    )
                self._thinking_content = ""
            elif self._in_thinking:
                # 累积 thinking 内容
                self._thinking_content += content
            else:
                # 普通回答内容
                if self.enable_thinking is False or not self._in_thinking:
                    # 非思考模式或不在思考标签中，作为答案输出
                    if content.strip():
                        yield StreamChunk(
                            type=StreamChunkType.ANSWER,
                            content=content,
                        )

        # 处理工具调用
        if hasattr(choice, 'delta') and choice.delta.tool_calls:
            for tool_call in choice.delta.tool_calls:
                await self._process_tool_call(tool_call)

        # 处理工具执行结果（如果有）
        # 这部分在实际实现中需要更复杂的逻辑
        # 这里简化处理

    async def _process_tool_call(self, tool_call_delta: Any) -> AsyncIterator[StreamChunk]:
        """
        处理工具调用

        Args:
            tool_call_delta: OpenAI 工具调用 delta

        Yields:
            StreamChunk: 工具调用相关的数据块
        """
        # 解析工具调用
        if hasattr(tool_call_delta, 'function'):
            tool_name = tool_call_delta.function.name
            tool_args = tool_call_delta.function.arguments

            # 发送工具调用开始事件
            yield StreamChunk(
                type=StreamChunkType.TOOL_CALL,
                content="",
                tool_name=tool_name,
                tool_params=tool_args,
                tool_status="start",
            )

            # 执行工具
            try:
                tool = self.engine.tools.get(tool_name)
                if tool:
                    result = await tool.execute(**tool_args)

                    # 发送工具结果
                    yield StreamChunk(
                        type=StreamChunkType.TOOL_RESULT,
                        content=str(result)[:1000],  # 截断
                        tool_name=tool_name,
                        tool_status="complete",
                    )
                else:
                    yield StreamChunk(
                        type=StreamChunkType.ERROR,
                        content=f"Tool not found: {tool_name}",
                        tool_name=tool_name,
                    )
            except Exception as e:
                yield StreamChunk(
                    type=StreamChunkType.ERROR,
                    content=str(e),
                    tool_name=tool_name,
                )


class AsyncIteratorWrapper:
    """异步迭代器包装器，用于简化流式处理"""

    def __init__(self, async_iterator: AsyncIterator[StreamChunk]):
        self._iterator = async_iterator

    def __aiter__(self):
        return self._iterator

    async def to_list(self) -> List[StreamChunk]:
        """收集所有数据块到列表"""
        chunks = []
        async for chunk in self._iterator:
            chunks.append(chunk)
        return chunks


def create_streaming_context(engine, enable_thinking: bool = True) -> StreamingContext:
    """
    创建流式上下文

    Args:
        engine: FastReAct 引擎实例
        enable_thinking: 是否输出思考过程

    Returns:
        StreamingContext 实例
    """
    return StreamingContext(engine, enable_thinking=enable_thinking)
