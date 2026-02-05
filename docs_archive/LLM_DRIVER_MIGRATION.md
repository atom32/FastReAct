# LLM Driver 迁移指南

## 目标

将所有 LLM 调用迁移到统一的 `LLMDriver` 中间层。

## 迁移步骤

### 1. FastReAct (core/engine.py)

#### 之前
```python
class FastReAct:
    def _get_client(self):
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

#### 之后
```python
class FastReAct:
    def __init__(self, ...):
        # 创建 LLM Driver
        self._llm_driver = create_llm_driver_from_config(self.config)

    async def _chat(self, messages):
        # 使用 LLMDriver
        response = await self._llm_driver.chat(messages=messages)

        # 解析响应
        return {
            "content": response.content,
            "tool_calls": response.tool_calls,
        }
```

### 2. GraphAgent (graph/agent.py)

#### 之前
```python
class GraphAgent:
    def __init__(self, llm_client, tools, config):
        self.llm_client = llm_client

    async def _generate_plan(self, query):
        response = await self.llm_client.chat.completions.create(
            model=self.llm_client.model or "gpt-4",
            messages=[...],
            ...
        )
```

#### 之后
```python
class GraphAgent:
    def __init__(self, llm_driver, tools, config):
        # 接收 LLMDriver 而不是原始 client
        self.llm_driver = llm_driver

    async def _generate_plan(self, query):
        # 使用 LLMDriver
        response = await self.llm_driver.chat(
            messages=[...],
            temperature=0.5,  # 可以覆盖配置
        )

        # 解析响应
        return response.content
```

### 3. Replanner (graph/replanner.py)

#### 之前
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

#### 之后
```python
class Replanner:
    def __init__(self, llm_driver, ...):
        self.llm_driver = llm_driver

    async def reflect_and_patch(self, ...):
        # 使用 LLMDriver
        response = await self.llm_driver.chat(
            messages=[...],
            temperature=0.3,
        )
```

### 4. ComplexityEvaluator (cli/unified_repl.py)

#### 之前
```python
class ComplexityEvaluator:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def _evaluate_with_llm(self, query):
        response = await self.llm_client.chat.completions.create(...)
```

#### 之后
```python
class ComplexityEvaluator:
    def __init__(self, llm_driver):
        self.llm_driver = llm_driver

    async def _evaluate_with_llm(self, query):
        # 使用 LLMDriver
        response = await self.llm_driver.chat(
            messages=[...],
            temperature=0.3,
        )
```

## 修改 REPL 初始化

### unified_repl.py

```python
class UnifiedAgentREPL:
    def __init__(self, session_to_load: Optional[Path] = None):
        # 创建 LLM Driver（统一）
        from fastreact.bootstrap.config_loader import load_config
        from fastreact.llm import create_llm_driver_from_config

        config = load_config()
        self.llm_driver = create_llm_driver_from_config(config)

        # 创建 evaluator（使用 driver）
        self.complexity_evaluator = ComplexityEvaluator(
            llm_driver=self.llm_driver
        )

    def _get_or_create_react_agent(self):
        """创建 ReAct Agent（使用 driver）"""
        if self.state.react_agent is None:
            from fastreact import FastReAct

            config = load_config()

            self.state.react_agent = FastReAct(
                llm_driver=self.llm_driver,  # 传入 driver
                enable_bootstrap=True,
                config=config,
            )

        return self.state.react_agent
```

## FastReAct 修改

### core/engine.py

```python
class FastReAct:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        llm_driver: Optional[Any] = None,  # 新增：支持外部传入 driver
        enable_bootstrap: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        # 优先使用传入的 llm_driver
        if llm_driver is not None:
            self._llm_driver = llm_driver
        else:
            # 兼容旧的方式：创建 driver
            from fastreact.llm import create_llm_driver_from_config

            if enable_bootstrap and config:
                self._llm_driver = create_llm_driver_from_config(config)
            else:
                # 旧方式（直接创建）
                self._llm_driver = create_llm_driver(
                    api_key=api_key,
                    base_url=base_url,
                )

    def _get_client(self):
        """兼容旧代码（内部使用 driver）"""
        # 废弃：建议直接使用 self._llm_driver
        return self._llm_driver._get_client()

    async def _chat(self, messages, tools=None):
        """使用 LLMDriver 发送聊天请求"""
        response = await self._llm_driver.chat(
            messages=messages,
            tools=tools,
        )

        # 转换为旧格式（兼容性）
        result = {
            "content": response.content,
        }

        if response.tool_calls:
            result["tool_calls"] = response.tool_calls

        return result
```

## 好处

### 1. 统一重试逻辑
```python
# 所有 LLM 调用自动重试
driver = LLMDriver(config=LLMDriverConfig(max_retries=3))

# 自动处理：
# - 超时重试
# - 速率限制重试
# - 服务器错误重试
```

### 2. 统一缓存
```python
# 自动缓存相同的请求
driver = LLMDriver(config=LLMDriverConfig(enable_cache=True))

# 相同的消息会直接返回缓存结果
```

### 3. 统一日志
```python
# 所有 LLM 调用自动记录
driver = LLMDriver(config=LLMDriverConfig(log_requests=True))

# 自动记录：
# [LLM Request] model=gpt-4, messages=3
# [LLM Response] content_len=150, tool_calls=0
```

### 4. 易于测试
```python
# 可以 mock LLMDriver
class MockLLMDriver:
    async def chat(self, messages):
        return ChatResponse(content="mock response")

# 注入 mock driver
agent = FastReAct(llm_driver=MockLLMDriver())
```

## 实施计划

### Phase 1: 创建 LLMDriver（当前）
- [x] 创建 driver 类
- [x] 实现 chat(), stream()
- [x] 实现重试、缓存、日志

### Phase 2: 迁移 FastReAct
- [ ] 修改 __init__ 接收 llm_driver
- [ ] 修改 _chat() 使用 driver
- [ ] 保持向后兼容

### Phase 3: 迁移其他组件
- [ ] GraphAgent
- [ ] Replanner
- [ ] ComplexityEvaluator

### Phase 4: 清理
- [ ] 删除 _get_client()
- [ ] 统一使用 LLMDriver

---

**最后更新**: 2025-02-05
**状态**: 规划中，待实施
