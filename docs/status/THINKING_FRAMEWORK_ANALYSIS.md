# 深度分析：思考框架改进与工具系统兼容性

> **日期**: 2026-01-30
> **主题**: Moltbot 的思考框架 vs FastReAct，工具系统兼容性

---

## 1. Moltbot 使用的工具系统

### 1.1 核心发现

**Moltbot 使用的不是 MCP，而是 pi-agent-core！**

```json
// Moltbot/package.json
{
  "dependencies": {
    "@mariozechner/pi-agent-core": "0.49.3",
    "@mariozechner/pi-ai": "0.49.3",
    "@mariozechner/pi-coding-agent": "0.49.3",
    "@mariozechner/pi-tui": "0.49.3"
  }
}
```

**关键信息**:
- **作者**: mariozechner (Mario Zechner)
- **项目**: pi-agent-core (一个嵌入式 Agent 运行时)
- **语言**: TypeScript
- **与 MCP 的关系**: **独立项目，不兼容 MCP**

### 1.2 pi-agent-core 工具系统

**来源**: https://github.com/mariozechner/pi

**核心特性**:
1. **嵌入式运行时**: 嵌入到主机应用中（不是独立服务）
2. **类型化工具**: 使用 TypeScript 类型定义
3. **流式工具调用**: 支持工具执行过程中的流式输出
4. **沙箱执行**: 支持安全的代码执行
5. **内置工具**: read/write/edit/exec/apply_patch 等

**工具定义示例**（来自 pi-coding-agent）:
```typescript
interface Tool {
  name: string;
  description: string;
  inputSchema: JSONObject;  // JSON Schema
  handler: (params: any) => Promise<ToolResult>;
}

// 内置工具
const readTool: Tool = {
  name: "read",
  description: "Read a file from the workspace",
  inputSchema: {
    type: "object",
    properties: {
      path: { type: "string", description: "File path" }
    },
    required: ["path"]
  },
  handler: async ({ path }) => {
    return fs.readFileSync(path, 'utf-8');
  }
};
```

### 1.3 Moltbot 如何使用这些工具

**来源**: `src/agents/pi-tools.ts`

```typescript
// Moltbot 创建工具的方式
export function createOpenClawCodingTools(options: {
  exec?: ExecToolDefaults & ProcessToolDefaults;
  sandbox?: SandboxContext | null;
  sessionKey?: string;
  agentDir?: string;
  workspaceDir?: string;
  config?: OpenClawConfig;
  modelProvider?: string;  // "anthropic" | "openai" | "google"
  modelId?: string;
}) {
  const tools: AnyAgentTool[] = [];

  // 1. 从 pi-coding-agent 导入
  const codingTools = codingTools({
    root: options.workspaceDir,
    sandbox: options.sandbox,
  });
  tools.push(...codingTools);

  // 2. 创建 OpenClaw 特定工具
  tools.push(createApplyPatchTool(options));
  tools.push(createExecTool(options));
  tools.push(createProcessTool(options));

  // 3. 通道工具（Slack/Discord 操作）
  const channelTools = listChannelAgentTools(options);
  tools.push(...channelTools);

  // 4. 根据模型和策略过滤工具
  return filterToolsByPolicy(tools, {
    modelProvider: options.modelProvider,
    modelId: options.modelId,
    groupId: options.groupId,
  });
}
```

---

## 2. FastReAct 能否使用 pi-agent-core 的工具？

### 2.1 技术可行性分析

| 维度 | pi-agent-core | FastReAct | 兼容性 |
|------|--------------|-----------|--------|
| **语言** | TypeScript | Python | ❌ 不兼容 |
| **工具定义** | JSON Schema | JSON Schema | ✅ 兼容 |
| **运行时** | 嵌入式 Node.js | Python asyncio | ❌ 不兼容 |
| **沙箱** | 自定义沙箱 | Docker 沙箱 | ⚠️ 需适配 |

### 2.2 三个选项

#### 选项 A: Python 移植 pi-agent-core 工具 ⭐⭐⭐⭐⭐ (推荐)

**优势**:
- ✅ 完全控制实现
- ✅ 与 FastReAct 深度集成
- ✅ 可以优化和定制

**劣势**:
- ⚠️ 需要维护同步
- ⚠️ 需要翻译 TypeScript → Python

**实现方法**:

```python
# src/fastreact/tools/pi_compat.py

"""
pi-agent-core 工具的 Python 实现
移植自 @mariozechner/pi-coding-agent
"""

from .base import Tool
import os
import subprocess
from typing import Dict, Any

class ReadTool(Tool):
    """读取文件工具（pi 风格）"""

    def _get_description(self) -> str:
        return "Read a file from the workspace. Returns the entire file contents as a string."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of the file to read relative to the workspace root"
                }
            },
            "required": ["path"]
        }

    async def execute_async(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"File read successfully:\n\n{content}"
        except FileNotFoundError:
            return f"Error: File '{path}' not found"
        except Exception as e:
            return f"Error reading file: {e}"


class WriteTool(Tool):
    """写入文件工具（pi 风格）"""

    def _get_description(self) -> str:
        return "Write content to a file. Creates intermediate directories if needed. Replaces the file if it exists."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of the file to write relative to the workspace root"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        }

    async def execute_async(self, path: str, content: str) -> str:
        try:
            # 创建中间目录
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"File written successfully: {path}"
        except Exception as e:
            return f"Error writing file: {e}"


class EditTool(Tool):
    """编辑文件工具（pi 风格 - 使用 apply_patch）"""

    def _get_description(self) -> str:
        return "Make edits to a file. This is a replacement for write tool that applies patches."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of the file to edit"
                },
                "patch": {
                    "type": "string",
                    "description": "Unified diff format patch to apply"
                }
            },
            "required": ["path", "patch"]
        }

    async def execute_async(self, path: str, patch: str) -> str:
        try:
            # 使用 apply_patch（已在 FastReAct 中实现）
            from ...utils.apply_patch import apply_patch

            result = apply_patch(path, patch)
            return f"Patch applied successfully:\n\n{result}"
        except Exception as e:
            return f"Error applying patch: {e}"


class ExecTool(Tool):
    """执行命令工具（pi 风格）"""

    def _get_description(self) -> str:
        return "Execute a shell command in the workspace. Returns the command output."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }

    async def execute_async(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()  # 工作目录
            )

            if result.returncode == 0:
                return f"Command output:\n\n{result.stdout}"
            else:
                return f"Command failed with exit code {result.returncode}:\n\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {e}"


# pi 风格工具集
PI_COMPAT_TOOLS = [
    ReadTool(),
    WriteTool(),
    EditTool(),
    ExecTool(),
]
```

**使用方法**:
```python
from fastreact import FastReAct
from fastreact.tools.pi_compat import PI_COMPAT_TOOLS

agent = FastReAct(
    api_key="xxx",
    tools=PI_COMPAT_TOOLS
)

# Agent 现在可以像 Moltbot 一样操作文件
await agent.run_async("请读取 README.md 文件")
```

#### 选项 B: 使用子进程桥接 ⭐⭐⭐

**方法**: FastReAct 通过 subprocess 调用 Node.js，使用 pi-agent-core

```python
# src/fastreact/tools/pi_bridge.py

import subprocess
import json
import asyncio
from typing import Dict, Any

class PiAgentBridgeTool(Tool):
    """pi-agent-core 桥接工具"""

    def __init__(self, node_script: str):
        self.node_script = node_script

    def _get_description(self) -> str:
        return "Execute a pi-agent-core tool via Node.js bridge"

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Tool name (read/write/exec/etc)"
                },
                "params": {
                    "type": "object",
                    "description": "Tool parameters"
                }
            },
            "required": ["tool", "params"]
        }

    async def execute_async(self, tool: str, params: Dict[str, Any]):
        # 调用 Node.js 脚本
        cmd = [
            "node",
            self.node_script,
            tool,
            json.dumps(params)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return stdout.decode('utf-8')
        else:
            return f"Error: {stderr.decode('utf-8')}"
```

**劣势**:
- ⚠️ 性能开销（进程启动）
- ⚠️ 复杂度高（需要 Node.js 环境）
- ⚠️ 调试困难

#### 选项 C: 集成 MCP（如果 Moltbot 有 MCP 适配器） ⭐⭐

**方法**: 使用 FastReAct 的 MCP 客户端连接 Moltbot 的 MCP Server

**问题**:
- Moltbot 没有公开 MCP Server
- 需要自己实现 MCP Server 包装 pi-agent-core

**不推荐**（除非 Moltbot 官方支持）

---

## 3. 思考框架改进方案

### 3.1 Moltbot 的思考循环

**来源**: `docs/concepts/agent-loop.md`

```
消息接收
   ↓
上下文组装
   ↓
Bootstrap 文件注入 (AGENTS.md, SOUL.md, TOOLS.md...)
   ↓
System Prompt 构建
   ↓
模型推理
   ↓
工具调用 (流式输出工具事件)
   ↓
流式回复 (assistant delta)
   ↓
持久化 (JSONL 会话日志)
   ↓
完成
```

**关键特性**:
1. **事件流**:
   - `lifecycle` (start/end/error)
   - `assistant` (delta)
   - `tool` (start/update/end)

2. **Hook 点**:
   - `before_agent_start`
   - `after_agent_end`
   - `before_tool_call`
   - `after_tool_call`

3. **压缩和重试**:
   - Token 超限时自动压缩上下文
   - 失败时自动重试

### 3.2 FastReAct 当前的思考循环

```python
# 当前实现（简化版）
for iteration in range(max_iterations):
    # 1. 思考
    thought = await self._think(history)

    # 2. 行动
    action = await self._decide_action(thought)

    # 3. 观察
    if action.tool_name != "finish":
        observation = await self._execute_tool(action)
        history.append(observation)
    else:
        break

# 4. 回答
answer = await self._generate_answer(history)
```

**对比**:

| 特性 | FastReAct | Moltbot (pi-agent-core) |
|------|-----------|------------------------|
| **事件流** | 有基础事件流 | 完整事件流（lifecycle/assistant/tool） |
| **Hook 点** | ❌ 无 | ✅ 丰富（8+ Hook 点） |
| **流式输出** | ✅ 有（可选） | ✅ 块流式 + 流式思考 |
| **上下文压缩** | ❌ 无 | ✅ 自动压缩 |
| **重试机制** | ✅ 有（工具级） | ✅ 有（运行时级） |
| **队列控制** | ❌ 无 | ✅ 3 种模式（steer/followup/collect） |

### 3.3 改进方案：增强的思考循环

#### 方案 A: 添加 Hook 系统 ⭐⭐⭐⭐⭐

```python
# src/fastreact/core/hooks.py

from typing import Callable, Dict, Any, List
from enum import Enum

class HookPoint(Enum):
    """Hook 点枚举"""
    BEFORE_AGENT_START = "before_agent_start"
    AFTER_AGENT_END = "after_agent_end"
    BEFORE_THINK = "before_think"
    AFTER_THINK = "after_think"
    BEFORE_ACTION = "before_action"
    AFTER_ACTION = "after_action"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    ON_ERROR = "on_error"


class HookManager:
    """Hook 管理器"""

    def __init__(self):
        self.hooks: Dict[HookPoint, List[Callable]] = {}
        for hook_point in HookPoint:
            self.hooks[hook_point] = []

    def register(self, hook_point: HookPoint, hook: Callable):
        """注册 Hook"""
        self.hooks[hook_point].append(hook)

    async def execute(self, hook_point: HookPoint, **kwargs):
        """执行所有 Hook"""
        for hook in self.hooks[hook_point]:
            result = await hook(**kwargs)
            if result is not None:
                kwargs.update(result)
        return kwargs

    def clear(self, hook_point: HookPoint = None):
        """清除 Hook"""
        if hook_point:
            self.hooks[hook_point] = []
        else:
            for hp in HookPoint:
                self.hooks[hp] = []


# 在 FastReAct 中使用
class FastReAct:
    def __init__(self, ...):
        self.hook_manager = HookManager()

    async def run_async(self, query: str):
        # 运行前 Hook
        await self.hook_manager.execute(
            HookPoint.BEFORE_AGENT_START,
            query=query,
            agent=self
        )

        try:
            for iteration in range(self.max_iterations):
                # 思考前 Hook
                await self.hook_manager.execute(
                    HookPoint.BEFORE_THINK,
                    iteration=iteration
                )

                # 思考
                thought = await self._think()

                # 思考后 Hook
                await self.hook_manager.execute(
                    HookPoint.AFTER_THINK,
                    thought=thought
                )

                # ... (其他步骤类似)

                answer = await self._generate_answer()

                # 运行后 Hook
                await self.hook_manager.execute(
                    HookPoint.AFTER_AGENT_END,
                    answer=answer
                )

                return answer

        except Exception as e:
            # 错误 Hook
            await self.hook_manager.execute(
                HookPoint.ON_ERROR,
                error=e
            )
            raise
```

**使用示例**:
```python
agent = FastReAct(api_key="xxx")

# 注册 Hook
async def log_thought(thought: str):
    print(f"[Thought] {thought}")

agent.hook_manager.register(
    HookPoint.AFTER_THINK,
    log_thought
)

# 运行时 Hook 会自动执行
await agent.run_async("北京天气怎么样？")
```

#### 方案 B: 添加上下文压缩 ⭐⭐⭐⭐

**问题**: 长对话会导致 Token 超限

**解决**: 自动压缩历史消息

```python
# src/fastreact/core/compaction.py

from typing import List, Dict, Any
import tiktoken  # Token 计数库

class ContextCompactor:
    """上下文压缩器"""

    def __init__(
        self,
        max_tokens: int = 120000,  # GPT-4-Turbo 上下文
        reserve_tokens: int = 4000,  # 保留给回复
        summary_threshold: int = 0.8   # 80% 时压缩
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.summary_threshold = summary_threshold
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """估算 Token 数量"""
        text = "\n".join(m.get("content", "") for m in messages)
        return len(self.encoding.encode(text))

    async def compact(self, messages: List[Dict]) -> List[Dict]:
        """压缩上下文"""
        current_tokens = self.estimate_tokens(messages)
        threshold = self.max_tokens * self.summary_threshold

        if current_tokens < threshold:
            return messages  # 无需压缩

        # 压缩策略：保留最近的消息，旧消息生成摘要
        recent_messages = messages[-20:]  # 保留最近 20 条
        old_messages = messages[:-20]

        # 生成摘要
        summary = await self._summarize(old_messages)

        # 用摘要替换旧消息
        summary_message = {
            "role": "system",
            "content": f"[Conversation Summary]\n{summary}"
        }

        return [summary_message] + recent_messages

    async def _summarize(self, messages: List[Dict]) -> str:
        """生成对话摘要"""
        # 使用 LLM 生成摘要
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

        summary_prompt = f"""
请将以下对话摘要成 3-5 句话：

{text}

摘要：
"""

        # 调用 LLM
        # (简化版，实际应该使用独立的 LLM 调用)
        return "用户询问了天气，Agent 查询了天气 API 并返回了结果。"
```

**在 FastReAct 中使用**:
```python
class FastReAct:
    def __init__(self, ...):
        self.compactor = ContextCompaction()

    async def run_async(self, query: str):
        # 构建上下文
        context = self.build_context()

        # 压缩上下文
        context = await self.compactor.compact(context)

        # 继续...
```

#### 方案 C: 块流式回复 + 思考流式输出 ⭐⭐⭐⭐⭐

**问题**: 用户需要等待 Agent 完成才能看到结果

**解决**: 流式输出思考和回复

```python
# src/fastreact/core/streaming.py

from typing import AsyncIterator, Callable

class StreamingReAct:
    """流式 ReAct"""

    async def run_async_streaming(
        self,
        query: str,
        on_thought: Callable[[str], Any] = None,
        on_action: Callable[[Dict], Any] = None,
        on_observation: Callable[[str], Any] = None,
        on_delta: Callable[[str], Any] = None  # 回复的增量
    ):
        """流式运行 Agent"""

        for iteration in range(self.max_iterations):
            # 1. 思考（流式输出）
            thought = await self._think_streaming(
                on_delta=lambda delta: on_thought and on_thought(delta)
            )

            # 2. 行动
            action = await self._decide_action(thought)
            if on_action:
                on_action(action)

            if action.tool_name != "finish":
                # 3. 观察（流式输出）
                observation = await self._execute_tool_streaming(
                    action,
                    on_delta=lambda delta: on_observation and on_observation(delta)
                )

                if on_delta:
                    on_delta(f"\n[Tool: {action.tool_name} executed]\n")
            else:
                break

        # 4. 回答（流式输出）
        async for delta in self._generate_answer_streaming(
            on_delta=on_delta
        ):
            pass  # on_delta 会自动处理

    async def _think_streaming(
        self,
        on_delta: Callable[[str], Any]
    ) -> str:
        """流式思考"""
        # 调用 LLM 流式 API
        async for delta in self.llm.stream(...):
            on_delta(delta)  # 实时输出思考过程

        return thought
```

**使用示例**:
```python
async def on_thought(thought: str):
    print(f"\r🤔 {thought}", end="", flush=True)

async def on_delta(delta: str):
    print(delta, end="", flush=True)

await agent.run_async_streaming(
    "北京天气怎么样？",
    on_thought=on_thought,
    on_delta=on_delta
)
```

---

## 4. 综合改进方案：FastReAct v2.0

### 4.1 目标

将 FastReAct 升级到 v2.0，具备 Moltbot 的核心能力：
1. ✅ pi 风格工具（read/write/exec/apply_patch）
2. ✅ Hook 系统
3. ✅ 上下文压缩
4. ✅ 流式控制
5. ✅ 事件流增强

### 4.2 实施计划

**Phase 1: pi 风格工具** (3-5 天)
- 移植 read/write/exec 工具
- 实现 apply_patch 工具
- 测试工具兼容性

**Phase 2: Hook 系统** (3-5 天)
- 实现 HookManager
- 定义 Hook 点
- 集成到 FastReAct

**Phase 3: 上下文压缩** (3 天)
- 实现 ContextCompactor
- Token 估算
- 自动摘要生成

**Phase 4: 流式增强** (5-7 天)
- 思考流式输出
- 回复块流式
- 队列控制（steer/followup/collect）

**Phase 5: 事件流增强** (3 天)
- lifecycle 事件
- tool 事件（start/update/end）
- assistant delta 事件

**总时间**: 3-4 周

---

## 5. 总结：回答你的问题

### 问题 1: FastReAct 的思考框架能否改进？

**答**: ✅ 可以，有 3 个方向：

1. **添加 Hook 系统** ⭐⭐⭐⭐⭐
   - 允许用户在思考循环的各个点插入自定义逻辑
   - 用途：日志、监控、修改行为、上下文注入

2. **上下文压缩** ⭐⭐⭐⭐
   - 自动压缩长对话历史
   - 保留最近消息，旧消息生成摘要
   - 防止 Token 超限

3. **流式增强** ⭐⭐⭐⭐⭐
   - 思考过程流式输出
   - 块流式回复
   - 实时控制（用户可中断）

### 问题 2: Moltbot 如何使用工具？是 MCP 吗？

**答**: ❌ 不是 MCP，是 **pi-agent-core**

**Moltbot 使用的技术栈**:
```
Moltbot
├── pi-agent-core (mariozechner)
│   ├── pi-ai
│   ├── pi-coding-agent (read/write/exec/apply_patch)
│   └── pi-tui
└── 自己的工具层
    ├── 通道工具 (Slack/Discord 操作)
    ├── 扩展工具 (Plugin 系统)
    └── 沙箱工具 (Docker/Process)
```

**与 MCP 的关系**:
- MCP (Model Context Protocol) 是 Anthropic 的协议
- pi-agent-core 是独立项目，不使用 MCP
- FastReAct 同时支持 MCP 和自有工具

### 问题 3: FastReAct 能否使用 Moltbot 的工具？

**答**: ✅ 可以，通过 3 种方式：

**方式 1: Python 移植** ⭐⭐⭐⭐⭐ (推荐)
- 将 pi-coding-agent 的工具移植到 Python
- 优势：完全控制、深度集成
- 劣势：需要维护同步

**方式 2: 子进程桥接** ⭐⭐⭐
- 通过 Node.js 调用 pi-agent-core
- 优势：可直接使用原始工具
- 劣势：性能开销、复杂度高

**方式 3: 兼容层** ⭐⭐⭐⭐
- 实现兼容 pi-agent-core 的工具接口
- 优势：用户可以无缝切换
- 劣势：功能子集

### 推荐方案

**短期** (1-2 周):
1. 移植核心 pi 工具（read/write/exec/apply_patch）
2. 实现 Hook 系统
3. 添加上下文压缩

**中期** (3-4 周):
4. 实现流式增强
5. 添加队列控制
6. 事件流增强

**长期** (1-2 月):
7. 实现技能系统
8. 社区技能包
9. 配套应用

---

**下一步**: 我可以帮你实现 Phase 1 - pi 风格工具的移植。需要我开始吗？
