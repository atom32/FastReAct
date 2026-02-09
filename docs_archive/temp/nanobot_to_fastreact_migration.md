# nanobot → FastReAct v2.0 迁移指南

## 执行摘要

本文档提供从 nanobot 迁移到 FastReAct v2.0 的详细指南，包括代码复用策略、改造步骤和验证方法。

---

## 一、代码复用决策矩阵

### 1.1 完全复用（70%）

| 模块 | nanobot | 复用原因 | 迁移难度 |
|------|---------|----------|----------|
| **Tool 基类** | 103 行 | 设计优秀，接口清晰 | 低 |
| **ToolRegistry** | 74 行 | 简洁高效，功能完整 | 低 |
| **ProviderSpec** | 341 行 | frozen dataclass，线程安全 | 低 |
| **Shell 安全防护** | 142 行 | 8 种危险模式，全面保护 | 低 |
| **Filesystem 工具** | 212 行 | 路径权限检查完善 | 低 |
| **Skills 加载** | 228 行 | 渐进式加载，Token 节省 72% | 中 |
| **ReAct 循环** | 377 行 | 核心逻辑清晰，易于扩展 | 中 |

**总计**：~1477 行（30% 的 nanobot 代码）

### 1.2 需要改造（20%）

| 模块 | 改造内容 | 工作量 |
|------|----------|--------|
| **Provider Registry** | 11+ → 6+ 提供商 | 中 |
| **Context 构建** | 集成 FastReAct Prompt | 中 |
| **会话管理** | 添加检查点支持 | 中 |

### 1.3 新增功能（10%）

| 功能 | 描述 | 工作量 |
|------|------|--------|
| **MessageBus** | 解耦核心和渠道 | 高 |
| **标准消息格式** | Channel-agnostic | 高 |
| **插件系统** | 企业特性 | 高 |

---

## 二、分阶段迁移计划

### 阶段 1：核心复用（1 周）

#### 1.1 复制核心文件

```bash
cd D:/FastReAct/fastreact-v2

# 创建核心目录
mkdir -p src/fastreact/core
mkdir -p src/fastreact/tools
mkdir -p src/fastreact/providers

# 复制 nanobot 核心文件
cp D:/nanobot/nanobot/agent/tools/base.py src/fastreact/tools/base.py
cp D:/nanobot/nanobot/agent/tools/registry.py src/fastreact/tools/registry.py
cp D:/nanobot/nanobot/agent/tools/shell.py src/fastreact/tools/shell.py
cp D:/nanobot/nanobot/agent/tools/filesystem.py src/fastreact/tools/filesystem.py
```

#### 1.2 调整导入路径

```python
# 修改前
from nanobot.agent.tools.base import Tool

# 修改后
from fastreact.tools.base import Tool
```

#### 1.3 验证核心功能

```python
# tests/test_core_tools.py
import pytest
from fastreact.tools.registry import ToolRegistry
from fastreact.tools.shell import ExecTool

def test_tool_registry():
    registry = ToolRegistry()
    tool = ExecTool(timeout=60)

    registry.register(tool)
    assert registry.has("exec")
    assert len(registry) == 1

    definitions = registry.get_definitions()
    assert len(definitions) == 1
    assert definitions[0]["type"] == "function"

@pytest.mark.asyncio
async def test_shell_execution():
    tool = ExecTool(timeout=5)
    result = await tool.execute(command="echo Hello")
    assert "Hello" in result
```

### 阶段 2：Provider 简化（3 天）

#### 2.1 创建简化版 Provider Registry

```python
# src/fastreact/providers/registry.py
"""
FastReAct v2.0 Provider Registry
基于 nanobot，简化为 6 个核心提供商
"""

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ProviderSpec:
    name: str
    keywords: tuple[str, ...]
    env_key: str
    display_name: str = ""
    litellm_prefix: str = ""
    is_local: bool = False
    default_api_base: str = ""

    @property
    def label(self) -> str:
        return self.display_name or self.name.title()

PROVIDERS: tuple[ProviderSpec, ...] = (
    # 网关
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        litellm_prefix="openrouter",
        is_local=False,
    ),

    # 标准
    ProviderSpec(
        name="anthropic",
        keywords=("anthropic", "claude"),
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        litellm_prefix="",
    ),

    ProviderSpec(
        name="openai",
        keywords=("openai", "gpt"),
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        litellm_prefix="",
    ),

    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        litellm_prefix="deepseek",
    ),

    ProviderSpec(
        name="ollama",
        keywords=("ollama",),
        env_key="OLLAMA_API_KEY",  # 可选
        display_name="Ollama",
        litellm_prefix="ollama",
        is_local=True,
    ),
)

def find_by_model(model: str) -> ProviderSpec | None:
    model_lower = model.lower()
    for spec in PROVIDERS:
        if spec.is_local:
            continue
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None
```

#### 2.2 验证 Provider 匹配

```python
# tests/test_provider_registry.py
from fastreact.providers.registry import find_by_model

def test_anthropic_matching():
    spec = find_by_model("claude-3-5-sonnet-20241022")
    assert spec is not None
    assert spec.name == "anthropic"

def test_openai_matching():
    spec = find_by_model("gpt-4-turbo")
    assert spec is not None
    assert spec.name == "openai"

def test_deepseek_matching():
    spec = find_by_model("deepseek-chat")
    assert spec is not None
    assert spec.name == "deepseek"
```

### 阶段 3：Skills 系统集成（1 周）

#### 3.1 复制 Skills 加载器

```bash
cp D:/nanobot/nanobot/agent/skills.py src/fastreact/core/skills.py
```

#### 3.2 创建 FastReAct 技能

```markdown
---
name: fastreact_task_chaining
description: "Execute complex multi-step tasks with checkpoint support"
dependencies: []
always_load: true
---

# FastReAct Task Chaining

## 概述

FastReAct 的任务链系统允许你执行复杂的多步骤任务，并在每个步骤后保存检查点。

## 使用方法

### 创建任务链

```python
from fastreact.core.chaining import TaskChain

chain = TaskChain(
    name="refactor_codebase",
    checkpoint_dir=".fastreact/checkpoints"
)

# 添加任务
chain.add_task("analyze_code", "Analyze the codebase structure")
chain.add_task("create_plan", "Create refactoring plan")
chain.add_task("execute_refactor", "Execute the refactoring")
```

### 执行和恢复

```python
# 执行
await chain.run()

# 如果中断，从检查点恢复
chain = TaskChain.resume(".fastreact/checkpoints/refactor_codebase")
await chain.run()
```

## 注意事项

- 每个任务完成后自动保存检查点
- 中断后可以从任意检查点恢复
- 支持并行任务执行
```

#### 3.3 测试 Skills 加载

```python
# tests/test_skills_loading.py
from fastreact.core.skills import SkillsLoader
from pathlib import Path

def test_always_skills_loading():
    loader = SkillsLoader(
        skills_dir=Path("tests/fixtures/skills"),
        workspace=Path.cwd()
    )

    always_skills = loader.get_always_skills()
    assert "fastreact_task_chaining" in always_skills

def test_build_skills_summary():
    loader = SkillsLoader(
        skills_dir=Path("tests/fixtures/skills"),
        workspace=Path.cwd()
    )

    summary = loader.build_skills_summary()
    assert "<skills>" in summary
    assert "<skill" in summary
    assert "available=" in summary
```

### 阶段 4：MessageBus 实现（1 周）

#### 4.1 创建标准消息格式

```python
# src/fastreact/bridge/message.py
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

@dataclass
class Attachment:
    content_type: str
    data: bytes
    filename: Optional[str] = None

@dataclass
class StandardMessage:
    """Channel-agnostic message format"""
    session_id: str
    content: str
    user_id: Optional[str] = None
    channel_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ReasoningResult:
    """Result from ReAct core"""
    answer: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### 4.2 实现 MessageBus

```python
# src/fastreact/bridge/messagebus.py
from typing import Optional, Callable
from fastreact.bridge.message import StandardMessage, ReasoningResult
from fastreact.core.loop import ReActCore

class MessageBus:
    """Bridge between ReAct core and channels"""

    def __init__(
        self,
        core: ReActCore,
        progress_callback: Optional[Callable[[str], None]] = None
    ):
        self.core = core
        self.progress_callback = progress_callback

    async def process(self, message: StandardMessage) -> ReasoningResult:
        """Process a message through the core"""
        if self.progress_callback:
            self.progress_callback(f"[MessageBus] Processing message from {message.channel_type}")

        # 构建上下文
        context = {
            "user_id": message.user_id,
            "channel_type": message.channel_type,
            "attachments": message.attachments,
            "metadata": message.metadata,
        }

        # 调用核心推理
        result = await self.core.reason(
            query=message.content,
            context=context
        )

        return result

    async def process_stream(self, message: StandardMessage):
        """Stream processing for real-time responses"""
        if self.progress_callback:
            self.progress_callback(f"[MessageBus] Starting stream from {message.channel_type}")

        context = {
            "user_id": message.user_id,
            "channel_type": message.channel_type,
        }

        async for chunk in self.core.reason_stream(message.content, context):
            yield chunk
```

#### 4.3 测试 MessageBus

```python
# tests/test_messagebus.py
import pytest
from fastreact.bridge.message import StandardMessage
from fastreact.bridge.messagebus import MessageBus
from fastreact.core.loop import ReActCore

@pytest.mark.asyncio
async def test_message_processing():
    core = ReActCore(...)  # 配置核心
    bus = MessageBus(core)

    message = StandardMessage(
        session_id="test-123",
        content="What is 2+2?",
        user_id="user-1",
        channel_type="cli"
    )

    result = await bus.process(message)

    assert result.answer
    assert isinstance(result.answer, str)
```

### 阶段 5：渠道实现（1 周）

#### 5.1 创建渠道基类

```python
# src/fastreact/channels/base.py
from abc import ABC, abstractmethod
from fastreact.bridge.message import StandardMessage, ReasoningResult

class Channel(ABC):
    """Base class for all channels"""

    @abstractmethod
    async def start(self) -> None:
        """Start the channel"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel"""
        pass

    @abstractmethod
    async def send(self, result: ReasoningResult, recipient: str) -> None:
        """Send result to recipient"""
        pass

    @abstractmethod
    async def receive(self) -> StandardMessage:
        """Receive message from channel"""
        pass
```

#### 5.2 实现 CLI 渠道

```python
# src/fastreact/channels/cli.py
from fastreact.channels.base import Channel
from fastreact.bridge.message import StandardMessage, ReasoningResult
import asyncio

class CLIChannel(Channel):
    def __init__(self, messagebus: MessageBus):
        self.bus = messagebus
        self.running = False

    async def start(self) -> None:
        self.running = True
        print("[CLI] Channel started. Type 'exit' to quit.")

        while self.running:
            try:
                user_input = await self._get_input()
                if user_input.lower() == "exit":
                    break

                message = StandardMessage(
                    session_id="cli-session",
                    content=user_input,
                    channel_type="cli"
                )

                result = await self.bus.process(message)
                print(f"\n[Assistant] {result.answer}\n")

            except KeyboardInterrupt:
                break

    async def stop(self) -> None:
        self.running = False
        print("[CLI] Channel stopped.")

    async def send(self, result: ReasoningResult, recipient: str) -> None:
        print(f"[To {recipient}] {result.answer}")

    async def receive(self) -> StandardMessage:
        user_input = await self._get_input()
        return StandardMessage(
            session_id="cli-session",
            content=user_input,
            channel_type="cli"
        )

    async def _get_input(self) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "[You] ")
```

#### 5.3 测试 CLI 渠道

```python
# tests/test_cli_channel.py
import pytest
from fastreact.channels.cli import CLIChannel
from fastreact.bridge.messagebus import MessageBus

@pytest.mark.asyncio
async def test_cli_channel():
    # 需要模拟 input()
    # 集成测试时手动验证
    pass
```

---

## 三、验证清单

### 3.1 核心功能验证

- [ ] Tool 基类正常工作
- [ ] ToolRegistry 动态注册
- [ ] Shell 安全防护生效
- [ ] Filesystem 路径权限检查
- [ ] Provider 模型匹配正确

### 3.2 Skills 系统验证

- [ ] Always skills 完整加载
- [ ] Available skills XML 摘要正确
- [ ] 依赖检查工作正常
- [ ] Agent 可以按需加载技能

### 3.3 MessageBus 验证

- [ ] 标准消息格式转换
- [ ] 核心推理解耦
- [ ] 流式输出工作
- [ ] 错误处理完善

### 3.4 渠道验证

- [ ] CLI 渠道收发消息
- [ ] Web 渠道（如实现）
- [ ] 并发处理正确
- [ ] 资源清理完善

---

## 四、回滚策略

如果迁移出现问题：

```bash
# 1. 保留 nanobot 原始代码
git checkout D:/nanobot

# 2. 使用 FastReAct v1.0
cd D:/FastReAct
git checkout v1.0

# 3. 重新评估
# - 哪些部分有问题？
# - 是否需要从头写？
# - 是否可以部分复用？
```

---

## 五、成功标准

### 5.1 功能完整性

- ✅ 保留所有 FastReAct v1.0 功能
- ✅ 添加 Skills 系统
- ✅ 添加 MessageBus
- ✅ 支持多渠道

### 5.2 性能目标

- ✅ Token 成本降低 70%
- ✅ 启动时间 <1 秒
- ✅ 首响延迟 <1 秒
- ✅ 代码量 <7000 行

### 5.3 质量目标

- ✅ 所有测试通过
- ✅ 文档完整
- ✅ 跨平台兼容
- ✅ 生产就绪

---

## 六、时间估算

| 阶段 | 时间 | 关键产出 |
|------|------|----------|
| 核心复用 | 1 周 | Tool, Registry, Shell, Filesystem |
| Provider 简化 | 3 天 | 6 个核心提供商 |
| Skills 集成 | 1 周 | SkillsLoader + 技能文件 |
| MessageBus | 1 周 | 标准消息 + 消息总线 |
| 渠道实现 | 1 周 | CLI + Web 渠道 |
| 测试验证 | 1 周 | 集成测试 + 文档 |
| **总计** | **5-6 周** | **FastReAct v2.0** |

---

**准备开始迁移了吗？**

从阶段 1 开始，逐步验证每个部分！
