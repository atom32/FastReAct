# LLM 调用架构分析

## 现状：没有统一的中间层

### 当前调用方式

#### 1. FastReAct (engine.py)
```python
class FastReAct:
    def _get_client(self):
        """获取或创建异步客户端"""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(...)
        return self._client

    async def _chat(self, messages):
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            ...
        )
```

#### 2. GraphAgent (graph/agent.py)
```python
class GraphAgent:
    def __init__(self, llm_client, ...):
        self.llm_client = llm_client  # 外部传入

    async def _generate_plan(self, query):
        response = await self.llm_client.chat.completions.create(
            model=self.llm_client.model or "gpt-4",
            messages=[...],
            ...
        )
```

#### 3. Replanner (graph/replanner.py)
```python
class Replanner:
    def __init__(self, llm_client, ...):
        self.llm_client = llm_client

    async def reflect_and_patch(self, ...):
        response = await self.llm_client.chat.completions.create(
            model=self.llm_client.model or "gpt-4",
            messages=[...],
            ...
        )
```

#### 4. ComplexityEvaluator (cli/unified_repl.py)
```python
class ComplexityEvaluator:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def _evaluate_with_llm(self, query):
        response = await self.llm_client.chat.completions.create(
            model=self.llm_client.model or "gpt-4",
            messages=[...],
            ...
        )
```

## 问题分析

### 1. 重复的底层调用
每个地方都在调用 `client.chat.completions.create()`，导致：
- 重复的代码
- 重复的错误处理
- 重复的重试逻辑
- 重复的日志记录

### 2. 没有统一的抽象
- 没有统一的接口
- 没有统一的配置管理
- 没有统一的功能（重试、缓存、流式）

### 3. 耦合度高
- GraphAgent, Replanner 等都依赖特定的 LLM client 接口
- 如果要替换 LLM provider，需要修改多个地方

### 4. 难以扩展
- 添加新功能（如统一的 rate limiting）需要在多处修改
- 添加新的 LLM provider 支持需要改很多地方

## 应该有的架构

```
┌─────────────────────────────────────────┐
│  统一 LLM Driver 中间层                  │
│  ┌──────────────────────────────────┐   │
│  │  LLMDriver / LLMClient          │   │
│  │  - chat()                        │   │
│  │  - stream()                      │   │
│  │  - batch()                       │   │
│  │  内部处理：                       │   │
│  │  - 重试逻辑                      │   │
│  │  - 缓存                          │   │
│  │  - 速率限制                      │   │
│  │  - 错误处理                      │   │
│  │  - 日志记录                      │   │
│  └──────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │
               ├─→ client.chat.completions.create()
               │
               ├─→ client.chat.completions.create()
               │   (不同实现)
               │
               └─→ 其他 LLM provider
```

## 好处

### 1. 统一接口
```python
# 所有组件使用统一接口
result = await llm_driver.chat(messages)
```

### 2. 集中管理
- 重试策略在一处配置
- 缓存在一处管理
- 日志在一处记录

### 3. 易于扩展
- 添加新的 LLM provider 只需要修改 driver
- 添加新功能（如 rate limiting）只需要修改 driver

### 4. 解耦
- 组件不再依赖特定的 LLM client 实现
- 更容易测试和 mock

## 当前架构图

```
FastReAct._chat()
    └─→ self._get_client() → AsyncOpenAI → chat.completions.create()

GraphAgent._generate_plan()
    └─→ self.llm_client.chat.completions.create()

Replanner.reflect_and_patch()
    └─→ self.llm_client.chat.completions.create()

ComplexityEvaluator._evaluate_with_llm()
    └─→ self.llm_client.chat.completions.create()
```

**问题**：每个地方都直接调用底层 API，没有统一中间层。

---

**结论**：需要创建统一的 `LLMDriver` 中间层。
