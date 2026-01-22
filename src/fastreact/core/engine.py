"""
FastReAct核心引擎

高性能ReACT循环实现
- 异步并发工具调用
- 智能LRU缓存
- 流式响应支持
- 连接池复用
"""

import asyncio
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from ..core.tool import Tool, ToolCall, ToolResult
from ..core.cache import LRUCache


class FastReAct:
    """
    轻量级ReACT引擎

    核心特性：
    1. 异步HTTP请求（并发工具调用）
    2. 流式响应（实时输出）
    3. 连接池复用（httpx.AsyncClient）
    4. LRU缓存（减少重复计算）
    5. 简洁清晰的实现
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 5,
        max_concurrent_tools: int = 3,
        enable_streaming: bool = False,
        enable_cache: bool = True,
        cache_size: int = 1000,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ):
        """
        初始化FastReAct引擎

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL（支持兼容API）
            model: 模型名称
            tools: 工具列表
            max_iterations: 最大迭代次数
            max_concurrent_tools: 最大并发工具数
            enable_streaming: 是否启用流式响应
            enable_cache: 是否启用缓存
            cache_size: 缓存大小
            temperature: 温度参数
            max_tokens: 最大token数
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_iterations = max_iterations
        self.max_concurrent_tools = max_concurrent_tools
        self.enable_streaming = enable_streaming
        self.enable_cache = enable_cache
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 工具注册表
        self.tools: Dict[str, Tool] = {}
        if tools:
            for tool in tools:
                self.register_tool(tool)

        # LRU缓存
        self.cache = LRUCache(max_size=cache_size) if enable_cache else None

        # 异步客户端（延迟初始化）
        self._client = None
        self._http_client = None

        # 性能统计
        self.stats = {
            "total_calls": 0,
            "total_time": 0.0,
            "tool_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        self.tools[tool.name] = tool

    def _get_client(self):
        """获取或创建异步客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                import httpx

                # 创建带连接池的HTTP客户端
                self._http_client = httpx.AsyncClient(
                    limits=httpx.Limits(
                        max_connections=100,
                        max_keepalive_connections=20,
                    ),
                    timeout=60.0,
                )

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=self._http_client,
                    max_retries=2,
                )
            except ImportError:
                raise ImportError("请安装 openai>=1.0.0 和 httpx>=0.25.0")

        return self._client

    def _get_cache_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        return f"{tool_name}:{json.dumps(params, sort_keys=True)}"

    async def _execute_tool_async(self, tool_call: ToolCall) -> ToolResult:
        """
        异步执行工具（带缓存）

        Args:
            tool_call: 工具调用对象

        Returns:
            工具执行结果
        """
        start_time = time.time()
        tool_name = tool_call.name
        params = tool_call.parameters

        # 检查缓存
        if self.cache:
            cache_key = self._get_cache_key(tool_name, params)
            cached_result = self.cache.get(cache_key)

            if cached_result is not None:
                self.stats["cache_hits"] += 1
                return ToolResult(
                    tool_name=tool_name,
                    result=cached_result,
                    execution_time=time.time() - start_time,
                )

        # 执行工具
        try:
            tool = self.tools.get(tool_name)
            if not tool:
                raise ValueError(f"工具不存在: {tool_name}")

            result = await tool.execute_async(**params)
            execution_time = time.time() - start_time

            # 更新缓存
            if self.cache:
                self.cache.set(cache_key, result)

            self.stats["tool_calls"] += 1
            if self.cache:
                self.stats["cache_misses"] += 1

            return ToolResult(
                tool_name=tool_name,
                result=result,
                execution_time=execution_time,
            )

        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _execute_tools_concurrent(
        self, tool_calls: List[ToolCall]
    ) -> List[ToolResult]:
        """
        并发执行多个工具

        Args:
            tool_calls: 工具调用列表

        Returns:
            工具执行结果列表
        """
        # 限制并发数量
        calls_to_execute = tool_calls[: self.max_concurrent_tools]

        # 创建任务
        tasks = [self._execute_tool_async(call) for call in calls_to_execute]

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(
                    ToolResult(
                        tool_name=tool_calls[i].name, result=None, error=str(r)
                    )
                )
            else:
                final_results.append(r)

        return final_results

    def _parse_tool_calls(self, response: str) -> List[ToolCall]:
        """
        从LLM响应中解析工具调用

        支持格式：
        1. [TOOL_CALL]{"name": "...", "parameters": {...}}
        2. <tool>{"name": "...", "parameters": {...}}</tool>

        Args:
            response: LLM响应文本

        Returns:
            工具调用列表
        """
        tool_calls = []

        # 格式1: [TOOL_CALL]{"name": "...", "parameters": {...}}
        pattern1 = r"\[TOOL_CALL\]\s*(\{.*?\})"
        for match in re.finditer(pattern1, response, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                tool_calls.append(
                    ToolCall(
                        name=data.get("name", ""),
                        parameters=data.get("parameters", {}),
                        call_id=f"call_{len(tool_calls)}",
                    )
                )
            except json.JSONDecodeError:
                continue

        # 格式2: <tool>...</tool>
        pattern2 = r"<tool>\s*(\{.*?\})\s*</tool>"
        for match in re.finditer(pattern2, response, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                tool_calls.append(
                    ToolCall(
                        name=data.get("name", ""),
                        parameters=data.get("parameters", {}),
                        call_id=f"call_{len(tool_calls)}",
                    )
                )
            except json.JSONDecodeError:
                continue

        return tool_calls

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        tools_desc = "\n\n".join([
            f"### {name}\n{tool.description}\n**参数**: {json.dumps(tool.parameters, ensure_ascii=False)}"
            for name, tool in self.tools.items()
        ])

        return f"""你是一个智能助手，可以使用以下工具来完成任务：

{tools_desc}

## 工作流程

1. **Thought**: 思考需要什么信息来回答问题
2. **Action**: 调用工具获取信息
3. **Observation**: 分析工具返回结果
4. **循环**: 重复步骤1-3，直到收集到足够信息
5. **Final Answer**: 基于工具结果给出最终答案

## 工具调用格式

使用以下格式调用工具：
```
[TOOL_CALL] {{"name": "工具名", "parameters": {{"参数名": "参数值"}}}}
```

## 重要提示

- 一次可以调用多个工具（用多个[TOOL_CALL]标记）
- 工具调用结果会给你提供更多信息
- 最终答案必须基于工具返回的结果，不要编造
- 如果信息足够，直接给出Final Answer，不再调用工具

## 示例

**用户**: 北京今天的天气怎么样？

**助手**:
Thought: 需要查询北京今天的天气信息
Action: [TOOL_CALL] {{"name": "weather", "parameters": {{"city": "北京"}}}}

Observation: 北京今天晴，温度15-25℃

Thought: 已获取天气信息，可以回答了
Final Answer: 北京今天是晴天，温度15-25摄氏度。
"""

    async def _chat(
        self, messages: List[Dict[str, str]]
    ) -> str:
        """发送聊天请求"""
        client = self._get_client()

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return response.choices[0].message.content

    async def _chat_with_streaming(
        self, messages: List[Dict[str, str]], callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """发送流式聊天请求"""
        client = self._get_client()

        full_response = ""

        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response += delta
                if callback:
                    callback(delta)

        return full_response

    def _extract_final_answer(self, response: str) -> str:
        """提取最终答案"""
        # 如果包含Final Answer标记
        if "Final Answer:" in response:
            return response.split("Final Answer:")[-1].strip()

        # 如果包含最终答案标记
        if "最终答案:" in response:
            return response.split("最终答案:")[-1].strip()

        # 否则返回整个响应
        return response.strip()

    async def run_async(
        self,
        query: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        异步运行ReACT循环

        Args:
            query: 用户查询
            stream_callback: 流式回调（实时输出）
            step_callback: 步骤回调（记录每一步）

        Returns:
            {
                "answer": "最终答案",
                "steps": [步骤列表],
                "stats": {"tool_calls": 5, "cache_hits": 2, ...}
            }
        """
        start_time = time.time()
        self.stats["total_calls"] += 1

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": query},
        ]

        steps = []

        for iteration in range(self.max_iterations):
            # 调用LLM
            if self.enable_streaming:
                response = await self._chat_with_streaming(messages, stream_callback)
            else:
                response = await self._chat(messages)

            # 记录步骤
            step = {
                "iteration": iteration,
                "thought": response,
            }

            # 解析工具调用
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # 没有工具调用，说明是最终答案
                step["is_final"] = True
                step["answer"] = self._extract_final_answer(response)

                if step_callback:
                    step_callback(step)
                steps.append(step)

                # 更新统计
                elapsed = time.time() - start_time
                self.stats["total_time"] += elapsed

                return {
                    "answer": step["answer"],
                    "steps": steps,
                    "stats": self.get_stats(),
                }

            # 执行工具调用
            step["tool_calls"] = [
                {"name": tc.name, "parameters": tc.parameters} for tc in tool_calls
            ]

            if step_callback:
                step_callback(step)
            steps.append(step)

            # 并发执行工具
            results = await self._execute_tools_concurrent(tool_calls)

            # 构建观察结果
            observations = []
            for result in results:
                if result.error:
                    obs = f"❌ 错误: {result.error}"
                else:
                    obs = f"✅ {result.result}"
                observations.append(f"**{result.tool_name}**: {obs}")

            observation_text = "\n\n".join(observations)
            step["observation"] = observation_text

            if step_callback:
                step_callback(step)

            # 添加到消息历史
            messages.append({"role": "assistant", "content": response})
            messages.append(
                {
                    "role": "user",
                    "content": f"工具返回结果:\n\n{observation_text}\n\n请基于这些信息继续思考或给出最终答案。",
                }
            )

        # 达到最大迭代次数
        elapsed = time.time() - start_time
        self.stats["total_time"] += elapsed

        return {
            "answer": "达到最大迭代次数，未能完成",
            "steps": steps,
            "stats": self.get_stats(),
        }

    def run(
        self,
        query: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        同步运行ReACT循环（兼容性接口）

        Args:
            query: 用户查询
            stream_callback: 流式回调
            step_callback: 步骤回调

        Returns:
            执行结果
        """
        return asyncio.run(self.run_async(query, stream_callback, step_callback))

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.stats.copy()

        # 计算缓存命中率
        if stats["cache_hits"] + stats["cache_misses"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / (
                stats["cache_hits"] + stats["cache_misses"]
            )
        else:
            stats["cache_hit_rate"] = 0.0

        # 计算平均时间
        if stats["total_calls"] > 0:
            stats["avg_time_per_call"] = stats["total_time"] / stats["total_calls"]
        else:
            stats["avg_time_per_call"] = 0.0

        return stats

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()

    async def close(self) -> None:
        """关闭连接池"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            self._client = None

    def __del__(self):
        """析构函数"""
        if self._http_client:
            # 尝试关闭（可能已经关闭）
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except:
                pass
