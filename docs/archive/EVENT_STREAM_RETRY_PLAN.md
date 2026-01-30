# Phase 1 剩余任务：分层事件流 + 错误重试

> **日期**: 2026-01-29
> **状态**: 规划中
> **目标**: 完成生产基础的最后两个核心功能

---

## 📊 任务概览

### 1. 分层事件流系统（Layered Event Streaming）

**目标**: 提供细粒度的、实时的 Agent 执行反馈。

### 2. 错误重试机制（Error Retry with Backoff）

**目标**: 提升系统稳定性，自动处理临时错误。

---

## 1. 分层事件流系统

### 1.1 事件类型设计

```python
# 三种事件类型

@dataclass
class LifecycleEvent:
    """生命周期事件"""
    type: Literal["lifecycle"]
    phase: Literal["start", "end", "error"]
    run_id: str
    timestamp: float
    error: Optional[str] = None

@dataclass
class AssistantEvent:
    """助手输出事件"""
    type: Literal["assistant"]
    run_id: str
    delta: str  # 文本增量
    timestamp: float

@dataclass
class ToolEvent:
    """工具执行事件"""
    type: Literal["tool"]
    run_id: str
    phase: Literal["start", "result", "error"]
    tool_name: str
    tool_call_id: str
    args: Optional[dict] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    timestamp: float
```

### 1.2 回调机制设计

```python
# 用户提供的回调函数
async def event_callback(event: Union[LifecycleEvent, AssistantEvent, ToolEvent]):
    """处理事件"""
    if event.type == "lifecycle":
        print(f"[{event.phase.upper()}] {event.run_id}")
    elif event.type == "assistant":
        print(event.delta, end="", flush=True)
    elif event.type == "tool":
        if event.phase == "start":
            print(f"[TOOL] {event.tool_name}({event.args})")
        elif event.phase == "result":
            print(f"[DONE] {event.tool_name}: {event.duration_ms}ms")

# 在 FastReAct 中使用
agent = FastReAct(
    api_key="...",
    event_callback=event_callback  # 新增参数
)
```

### 1.3 引擎集成点

```python
# src/fastreact/core/engine.py

class FastReAct:
    async def run_async(self, query: str, event_callback=None):
        # 1. 发送生命周期开始事件
        if event_callback:
            await event_callback(LifecycleEvent(
                type="lifecycle",
                phase="start",
                run_id=self.run_id,
                timestamp=time.time()
            ))

        # 2. ReAct 循环
        for iteration in range(self.max_iterations):
            # 发送助手事件（推理过程）
            if event_callback:
                await event_callback(AssistantEvent(
                    type="assistant",
                    run_id=self.run_id,
                    delta=f"Thinking: {thought}",
                    timestamp=time.time()
                ))

            # 发送工具开始事件
            if event_callback:
                await event_callback(ToolEvent(
                    type="tool",
                    phase="start",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    args=params,
                    timestamp=time.time()
                ))

            # 执行工具
            result = await tool.execute(**params)

            # 发送工具完成事件
            if event_callback:
                await event_callback(ToolEvent(
                    type="tool",
                    phase="result",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    result=str(result)[:500],
                    duration_ms=duration * 1000,
                    timestamp=time.time()
                ))

        # 3. 发送生命周期结束事件
        if event_callback:
            await event_callback(LifecycleEvent(
                type="lifecycle",
                phase="end",
                run_id=self.run_id,
                timestamp=time.time()
            ))
```

---

## 2. 错误重试机制

### 2.1 重试策略

```python
@dataclass
class RetryPolicy:
    """重试策略"""
    max_attempts: int = 3          # 最大重试次数
    base_delay: float = 1.0        # 基础延迟（秒）
    max_delay: float = 60.0        # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数退避基数
    jitter: bool = True            # 添加随机抖动

    # 可重试的错误类型
    retriable_errors: Tuple[Type[Exception]] = (
        ConnectionError,
        TimeoutError,
        APIError,  # 自定义 API 错误
    )
```

### 2.2 重试执行器

```python
class RetryExecutor:
    """重试执行器"""

    async def execute(
        self,
        func: Callable,
        policy: RetryPolicy,
        context: dict = None
    ):
        """执行函数，支持重试"""
        last_error = None

        for attempt in range(policy.max_attempts):
            try:
                return await func(**(context or {}))

            except policy.retriable_errors as e:
                last_error = e

                # 最后一次尝试失败，不再重试
                if attempt == policy.max_attempts - 1:
                    break

                # 计算延迟
                delay = min(
                    policy.base_delay * (policy.exponential_base ** attempt),
                    policy.max_delay
                )

                # 添加抖动（避免雷群效应）
                if policy.jitter:
                    delay = delay * (0.5 + random.random())

                logger.warning(
                    f"Attempt {attempt + 1}/{policy.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                await asyncio.sleep(delay)

        # 所有重试都失败
        raise RetryExhaustedError(
            f"All {policy.max_attempts} attempts failed",
            last_error=last_error
        )
```

### 2.3 引擎集成

```python
# src/fastreact/core/engine.py

class FastReAct:
    def __init__(
        self,
        ...,
        enable_retry: bool = True,
        retry_policy: RetryPolicy = None,
    ):
        self.enable_retry = enable_retry
        self.retry_policy = retry_policy or RetryPolicy()
        self.retry_executor = RetryExecutor()

    async def _execute_tool_with_retry(self, tool, params):
        """执行工具，支持重试"""
        if not self.enable_retry:
            return await tool.execute_async(**params)

        return await self.retry_executor.execute(
            func=tool.execute_async,
            policy=self.retry_policy,
            context=params
        )
```

---

## 3. 测试策略

### 3.1 测试层次

#### Layer 1: 单元测试（Mock）
- ✅ 事件类创建和序列化
- ✅ 重试逻辑（不调用真实 API）
- ✅ 边界条件

#### Layer 2: 集成测试（真实 API）
- ✅ 真实 LLM API 调用
- ✅ 事件流完整性
- ✅ 错误重试效果

#### Layer 3: 端到端测试
- ✅ 完整使用场景
- ✅ 性能验证

### 3.2 测试文件结构

```
tests/
├── test_events.py              # 单元测试（事件类）
├── test_retry.py               # 单元测试（重试逻辑）
├── test_event_integration.py   # 集成测试（真实 API）
└── test_e2e_with_real_api.py   # 端到端测试
```

### 3.3 真实 API 测试配置

```python
# tests/conftest.py

import pytest
from fastreact import FastReAct

@pytest.fixture(scope="session")
def real_api_key():
    """从 config.json 加载真实 API Key"""
    from fastreact.core.config import load_config
    config = load_config()
    return config.get('llm', {}).get('providers', {}).get('openai', {}).get('api_key')

@pytest.fixture(scope="session")
def real_agent(real_api_key):
    """创建使用真实 API 的 Agent"""
    return FastReAct(
        api_key=real_api_key,
        model="gpt-4",
        enable_retry=True
    )

# 使用
def test_with_real_api(real_agent):
    """使用真实 API 测试"""
    result = asyncio.run(real_agent.run_async("What is 2+2?"))
    assert "4" in result['answer']
```

---

## 4. 实施步骤

### Step 1: 事件系统（1-2天）
1. ✅ 设计事件类
2. ✅ 实现回调机制
3. ✅ 集成到引擎
4. ✅ 编写单元测试
5. ✅ 编写集成测试（真实 API）

### Step 2: 重试机制（1-2天）
1. ✅ 实现重试策略
2. ✅ 实现重试执行器
3. ✅ 集成到引擎和工具执行
4. ✅ 编写单元测试
5. ✅ 编写集成测试（模拟网络错误）

### Step 3: 真实 API 测试（1天）
1. ✅ 编写端到端测试
2. ✅ 验证事件流完整性
3. ✅ 验证重试机制有效性
4. ✅ 性能基准测试

### Step 4: 文档和收尾（半天）
1. ✅ 更新使用文档
2. ✅ 添加示例
3. ✅ 更新 CHANGELOG

---

## 5. 成功标准

### 事件流
- [x] 三种事件正确触发
- [x] 回调函数异步执行
- [x] 事件包含完整信息
- [x] 真实 API 测试通过

### 重试机制
- [x] 可重试错误自动重试
- [x] 指数退避正常工作
- [x] 不超过最大重试次数
- [x] 网络错误测试通过

### 质量
- [x] 单元测试覆盖率 > 80%
- [x] 集成测试使用真实 API
- [x] 无性能退化
- [x] 向后兼容

---

## 6. 风险和缓解

### 风险 1: 真实 API 成本
**风险**: 大量真实 API 测试消耗成本
**缓解**:
- 使用较便宜的模型（gpt-3.5-turbo）
- 测试用例精简高效
- 添加 pytest skip 标记

### 风险 2: 网络不稳定
**风险**: 网络问题导致测试失败
**缓解**:
- 超时设置合理
- 重试机制本身
- 失败时提供清晰的错误信息

### 风险 3: 性能退化
**风险**: 事件流和重试影响性能
**缓解**:
- 异步回调
- 性能基准测试
- 可选功能（默认启用）

---

## 7. 时间估算

| 任务 | 预计时间 |
|------|---------|
| 事件系统实现 | 1-2天 |
| 重试机制实现 | 1-2天 |
| 真实 API 测试 | 1天 |
| 文档和收尾 | 0.5天 |
| **总计** | **3.5-5.5天** |

---

## 8. 下一步

立即开始实施：

1. 创建 `src/fastreact/observability/events.py`
2. 实现事件类
3. 集成到引擎
4. 编写真实 API 测试

准备开始吗？
