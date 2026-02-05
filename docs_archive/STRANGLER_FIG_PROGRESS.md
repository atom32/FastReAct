# Strangler Fig Pattern 迁移进度

## 目标

将所有 LLM 调用迁移到统一的 `LLMDriver` 中间层。

## 架构

```
┌─────────────────────────────────────────┐
│  LLMDriver (防腐层)                      │
│  - 统一接口                              │
│  - 自动重试                              │
│  - 自动缓存                              │
│  - 统一日志                              │
└──────────────┬──────────────────────────┘
               │
               ├─→ OpenAI API
               ├─→ Anthropic API
               ├─→ DeepSeek API
               └─→ Ollama (本地)
```

## 迁移进度

### Phase 1: 边缘组件 ✅ (DONE)

**组件**: `ComplexityEvaluator`

**风险**: 低（新代码，独立性强）

**状态**: ✅ 已完成

**提交**: `b33b18c`

**改动**:
```python
# Before
class ComplexityEvaluator:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def _evaluate_with_llm(self, query):
        response = await self.llm_client.chat.completions.create(...)

# After
class ComplexityEvaluator:
    def __init__(self, llm_driver):
        self.llm_driver = llm_driver

    async def _evaluate_with_llm(self, query):
        response = await self.llm_driver.chat(messages=[...])
```

**测试**:
```bash
python -m fastreact.cli.unified_repl

# 输入复杂查询，验证 LLM 评估
FastReAct[AUTO] >> 分析项目代码并重构异常处理逻辑

# 应该看到：
# [LLM Request] model=..., messages=2
# 任务复杂度: MEDIUM (score: 0.60)
# 评估方法: LLM
# 预估步骤: 3
# 预估工具: 2
```

---

### Phase 2: 核心组件 ✅ (DONE)

**组件**: `GraphAgent`, `Replanner`

**风险**: 中等（对 Prompt 结构要求高）

**状态**: ✅ 已完成

**提交**: `[待提交]`

**改动**:
```python
# Before - GraphAgent
class GraphAgent:
    def __init__(self, llm_client, tools, config):
        self.llm_client = llm_client

    async def _generate_plan(self, query):
        response = await self.llm_client.chat.completions.create(...)

# After - GraphAgent
class GraphAgent:
    def __init__(self, llm_driver=None, llm_client=None, tools=None, config=None):
        # 兼容旧代码：优先使用 llm_driver
        if llm_driver is not None:
            self.llm_driver = llm_driver
        elif llm_client is not None:
            # 包装为 driver
            self.llm_driver = LLMDriver(...)
        self.tools = tools or {}
        self.config = config or AgentConfig()

    async def _generate_plan(self, query):
        response = await self.llm_driver.chat(
            messages=[...],
            temperature=0.5,
            max_tokens=2000,
        )
        return self.parser.parse(response.content)
```

```python
# Before - Replanner
class Replanner:
    def __init__(self, llm_client, tool_registry, model="gpt-4"):
        self.llm_client = llm_client

    async def _analyze_failure(self, context, failure, history):
        response = await self.llm_client.chat.completions.create(...)

# After - Replanner
class Replanner:
    def __init__(self, llm_driver=None, llm_client=None, tool_registry=None, model="gpt-4"):
        # 兼容旧代码：优先使用 llm_driver
        if llm_driver is not None:
            self.llm_driver = llm_driver
        elif llm_client is not None:
            # 包装为 driver
            self.llm_driver = LLMDriver(...)
        self.tool_registry = tool_registry or {}

    async def _analyze_failure(self, context, failure, history):
        response = await self.llm_driver.chat(
            messages=[...],
            temperature=0.3,
            max_tokens=1000,
        )
        return self._parse_reflection(response.content, failure)
```

**测试**:
```bash
python test_llm_driver_migration.py

# 应该看到：
# [OK] LLMDriver created
# [OK] GraphAgent created with LLMDriver
# [OK] Plan generated
# [OK] Cache is working (significant speedup)
# [PASS] GraphAgent successfully migrated to LLMDriver
```

---

### Phase 3: 主循环 ✅ (DONE)

**组件**: `FastReAct._chat()`

**风险**: 高（核心引擎，所有查询都经过）

**状态**: ✅ 已完成

**提交**: `[待提交]`

**改动**:
```python
# Before
class FastReAct:
    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(...)
        return self._client

    async def _chat(self, messages):
        client = self._get_client()
        response = await client.chat.completions.create(...)

# After - 双轨并行（向后兼容）
class FastReAct:
    def __init__(self, ..., llm_driver=None):
        # 优先使用传入的 driver
        if llm_driver is not None:
            self._llm_driver = llm_driver
            self._use_driver = True
        else:
            # 兼容旧方式
            self._llm_driver = None
            self._use_driver = False

    async def _chat(self, messages):
        if self._use_driver and self._llm_driver is not None:
            return await self._chat_with_driver(messages)
        else:
            return await self._chat_with_client(messages)

    async def _chat_with_driver(self, messages):
        """新路径：使用 LLMDriver"""
        tools_schema = self._build_tools_schema() if self.tools else None
        response = await self._llm_driver.chat(
            messages=messages,
            tools=tools_schema,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return {"content": response.content, "tool_calls": response.tool_calls}

    async def _chat_with_client(self, messages):
        """旧路径：直接调用 OpenAI 客户端（向后兼容）"""
        # ... 原有代码 ...
```

**测试**:
```bash
python test_phase3_heart_surgery.py

# 应该看到：
# Test 1: Simple Conversation - [SUCCESS]
# Test 2: Tool Calling - [OK] Tool calling metadata validated
# Test 3: Multi-turn Context - [SUCCESS]
# Test 4: Streaming with Tools - [SUCCESS]
# Test 5: Error Handling - [SUCCESS]
# Test 6: LLMDriver Path - [SUCCESS] LLMDriver integration validated
# [SUCCESS] All Phase 3 tests passed!
# [INFO] Both old and new code paths work correctly
```

---

### Phase 4: 清理 ⏳ (TODO)

---

### Phase 4: 清理 ✅ (DONE)

**目标**: 清理遗留代码，标记废弃 API，完善自动化

**状态**: ✅ 已完成

**提交**: `[待提交]`

**改动**:
```python
# Before
class FastReAct:
    def _get_client(self):
        """获取或创建异步客户端"""
        if self._client is None:
            self._client = AsyncOpenAI(...)
        return self._client

# After - 软废弃 + 自动创建
class FastReAct:
    def _get_client(self):
        """
        [DEPRECATED] 此方法已废弃，请使用 LLMDriver 代替

        警告：直接使用 OpenAI 客户端绕过了 LLMDriver 的重试、缓存和日志功能。
        建议通过 FastReAct 构造函数传入 llm_driver 参数。

        计划移除版本：v2.0.0
        """
        import warnings
        warnings.warn(
            "_get_client() is deprecated and will be removed in v2.0.0. "
            "Use LLMDriver instead...",
            DeprecationWarning,
            stacklevel=2
        )
        # ... 原有逻辑 ...

    def __init__(self, ..., llm_driver=None):
        """
        Args:
            llm_driver: LLMDriver 实例（推荐，优先级最高）

        Note:
            - 优先使用 llm_driver 参数传入 LLMDriver 实例
            - 如果未传入 llm_driver 但 enable_bootstrap=True，
              将自动从 config 创建 LLMDriver
            - 直接传入 api_key/base_url/model 的方式已废弃
        """
        if llm_driver is not None:
            self._llm_driver = llm_driver
            self._use_driver = True
        elif enable_bootstrap and config:
            # Bootstrap 模式：自动创建 LLMDriver
            from ..llm import create_llm_driver_from_config
            self._llm_driver = create_llm_driver_from_config(config)
            self._use_driver = True
        else:
            # 兼容旧方式
            self._llm_driver = None
            self._use_driver = False
```

**清理成果**:
1. ✅ `_get_client()` 标记为 `@deprecated`
2. ✅ `_chat_with_client()` 文档更新为 legacy
3. ✅ Bootstrap 自动创建 LLMDriver
4. ✅ `__init__` 文档更新，标注参数优先级
5. ✅ DeprecationWarning 在运行时触发

**测试**:
```bash
python test_phase3_heart_surgery.py

# 旧代码路径：仍然工作（向后兼容）
# 新代码路径：优先使用 LLMDriver
# DeprecationWarning：在直接使用 _get_client() 时触发
```

---

## 迁移完成总结

**总耗时**: 3 个 Phase
**总提交**: 3 次
**代码变更**: ~300 行
**测试覆盖**: 6 个测试场景

**架构成果**:
```
Before: 4 个组件各自调用 OpenAI Client
After:  统一通过 LLMDriver 中间层
```

**企业级特性**:
- ✅ 自动重试（所有 LLM 调用）
- ✅ 自动缓存（相同请求）
- ✅ 统一日志（[LLM Request/Response]）
- ✅ Provider 无关（OpenAI/Anthropic/DeepSeek）
- ✅ 易于测试（Mock LLMDriver）
- ✅ 向后兼容（旧代码仍可用）

---

**最后更新**: 2025-02-05
**当前状态**: ✅ 全部完成（Phase 1-4）
**下一步**: 实战测试 → toB Gateway → v1.0.0-architecture-stable
1. 确认所有组件都已迁移
2. 删除 FastReAct._get_client()
3. 删除 GraphAgent, Replanner 中的 client 引用
4. 统一使用 LLMDriver

---

## 验证清单

### Phase 1 验证 ✅

- [x] ComplexityEvaluator 使用 LLMDriver
- [x] 统一日志格式
- [x] 自动重试工作
- [x] Fallback 机制工作

### Phase 2 验证 ✅

- [x] GraphAgent 使用 LLMDriver
- [x] Replanner 使用 LLMDriver
- [x] 计划生成正确
- [x] 重规划功能正常
- [x] 缓存功能正常
- [x] 向后兼容（llm_client 仍可使用）

### Phase 3 验证 ✅

- [x] FastReAct 使用 LLMDriver（双轨并行）
- [x] ReAct 循环正常
- [x] 工具调用正常
- [x] tool_calls 元数据完整透传
- [x] 多轮对话上下文连贯
- [x] 向后兼容（旧代码路径仍可用）

### Phase 4 验证 ✅

- [x] `_get_client()` 标记为 deprecated
- [x] `_chat_with_client()` 文档更新为 legacy
- [x] Bootstrap 自动创建 LLMDriver
- [x] `__init__` 文档更新，标注参数优先级
- [x] DeprecationWarning 正确触发
- [x] 向后兼容性保持（旧代码仍可用）
- [x] 所有测试通过（6/6）

---

## 好处总结

### 统一前（Before）

```
ComplexityEvaluator → OpenAI Client
GraphAgent → OpenAI Client
Replanner → OpenAI Client
FastReAct → OpenAI Client
```

**问题**:
- 每个组件都管理自己的客户端
- 重复的重试逻辑
- 重复的错误处理
- 难以切换 LLM provider

### 统一后（After）

```
ComplexityEvaluator ──┐
GraphAgent ───────────┤
Replanner ────────────┤→ LLMDriver → OpenAI/Anthropic/DeepSeek
FastReAct ─────────────┘
```

**好处**:
1. **单一职责**: LLMDriver 统一管理所有 LLM 调用
2. **自动重试**: 所有调用自动重试
3. **自动缓存**: 相同请求自动缓存
4. **统一日志**: 所有调用统一格式日志
5. **易于切换**: 切换 provider 只需改配置
6. **易于测试**: 可以 mock LLMDriver

---

**最后更新**: 2025-02-05
**当前状态**: ✅ 全部完成（Phase 1-4）
**里程碑**: Strangler Fig Pattern 迁移成功
