# FastReAct Nano v2.1.0 - Complete Technical Manual

**版本**: 2.1.0
**代码行数**: 5,592 lines Python
**架构**: Brain-Body Split (Event-Driven)
**状态**: Production Ready

---

## 目录

1. [架构概览](#1-架构概览)
2. [核心组件分析](#2-核心组件分析)
3. [Brain-Body Split详解](#3-brain-body-split详解)
4. [MCP协议支持](#4-mcp协议支持)
5. [Skills系统详解](#5-skills系统详解)
6. [Adapters系统](#6-adapters系统)
7. [工具系统](#7-工具系统)
8. [事件协议](#8-事件协议)
9. [配置系统](#9-配置系统)
10. [安全策略](#10-安全策略)
11. [完整API参考](#11-完整api参考)
12. [使用示例](#12-使用示例)

---

## 1. 架构概览

### 1.1 系统架构图

```
┌──────────────────────────────────────────────────────────────┐
│                     FastReAct Nano v2.1.0                      │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                   │
│  │   Brain      │         │    Body       │                   │
│  │  (Core)      │◄───────►│   (Agent)    │                   │
│  │              │  事件   │              │                   │
│  │ 180 lines    │  流     │ 435 lines    │                   │
│  └──────────────┘         └──────────────┘                   │
│         │                         │                           │
│         │ 纯推理                  │ 执行                      │
│         │ 零副作用                │ 所有副作用                 │
│         └─────────────────────────┘                           │
│                   ↓ 事件流                                     │
│  ┌──────────────────────────────────────────────┐            │
│  │          Event Protocol (统一协议)           │            │
│  │                                              │            │
│  │  SESSION_START → THINK → TOOL_CALL          │            │
│  │      ↓              ↓         ↓             │            │
│  │  TOOL_RESULT → STEP_END → SESSION_END       │            │
│  └──────────────────────────────────────────────┘            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Tools     │  │   Skills     │  │   Adapters   │      │
│  │              │  │              │  │              │      │
│  │ 4 core tools │  │ Progressive  │  │ CLI, HTTP,   │      │
│  │              │  │ disclosure   │  │ REPL, Gateway│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 设计哲学

**The Pi Philosophy (π ≈ 3 tools)**
- 极简但充分的工具集
- `read_file` - 读取代码文件
- `write_file` - 创建/编辑文件
- `exec` - 执行shell命令
- `edit_file` - 外科手术式文本替换

**Brain-Body Split (大脑-身体分离)**
- **Brain (Core)**: 纯推理引擎，180行
  - 调用LLM
  - 发射思考事件
  - 发射工具调用意图
  - **零执行**、**零副作用**、**零状态**

- **Body (Agent)**: 完整执行层，435行
  - 循环控制
  - 工具执行
  - 安全检查
  - 上下文管理
  - 会话管理

**反熵增原则 (Anti-Entropy)**
- Core锁定在180行
- 总代码量控制在6000行以内
- 删除 > 添加

### 1.3 代码组织

```
fastreact-nano/
├── src/fastreact/                 # 核心代码 (2166 lines)
│   ├── __init__.py               # 包导出 (110 lines)
│   ├── agent.py                  # Agent (Body) (435 lines)
│   ├── core/                     # Brain层
│   │   ├── __init__.py          # Core导出
│   │   ├── react.py             # ReActCore (180 lines) ⭐
│   │   ├── messages.py          # Message, MessageQueue (163 lines)
│   │   ├── config.py            # Config (323 lines)
│   │   ├── context.py           # ContextMonitor, FilesystemMemory
│   │   ├── safety.py            # SafetyPolicy
│   │   ├── events.py            # AgentEvent, EventType (146 lines)
│   │   ├── tools.py             # ToolRegistry (554 lines)
│   │   └── providers/
│   │       └── litellm.py       # LiteLLMProvider (381 lines)
│   ├── skills/                   # Skills系统 (581 lines)
│   │   ├── __init__.py
│   │   ├── loader.py            # SkillLoader (275 lines)
│   │   ├── parser.py            # SkillParser (168 lines)
│   │   └── base.py              # Skill, SkillMetadata (116 lines)
│   ├── tools/                    # 工具系统 (554 lines)
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   ├── exec.py
│   │   └── edit_file.py
│   └── mcp/                      # MCP协议
│       └── protocol.py          # SimpleMCP-Stdio
│
├── adapters/                     # 适配器 (1116 lines)
│   ├── __init__.py
│   ├── cli.py                   # CLI Adapter (272 lines)
│   ├── http.py                  # HTTP Adapter (259 lines)
│   ├── repl.py                  # REPL Adapter (309 lines)
│   └── gateway.py               # Gateway Adapter (258 lines)
│
├── skills/                       # 内置Skills
│   ├── code_review/SKILL.md      # 代码审查 (304 lines)
│   ├── file_ops/SKILL.md         # 文件操作 (785 lines)
│   └── git_workflow/SKILL.md     # Git工作流 (286 lines)
│
└── fastreact.yaml                # 配置文件
```

**总计**: 5,592 lines Python

---

## 2. 核心组件分析

### 2.1 ReActCore (大脑) - 180 lines

**文件**: `src/fastreact/core/react.py`

**职责**:
1. 调用LLM获取推理
2. 发射THINK事件（思考内容）
3. 发射TOOL_CALL事件（工具调用意图）
4. 发射STEP_END事件（步骤完成）

**关键特性**:
- **状态无关**: 不保存任何会话状态
- **零执行**: 不执行工具，只发射意图
- **零副作用**: 不做I/O，不写文件
- **单一职责**: 只做推理

**代码结构**:
```python
class ReActCore:
    def __init__(self, llm, tools, max_iterations=20)
    async def run_step_stream(self, messages, session_id, system_prompt=None)
        """
        单步推理：
        1. 调用LLM
        2. 发射THINK事件
        3. 发射TOOL_CALL事件
        4. 发射STEP_END事件
        """
```

**使用示例**:
```python
core = ReActCore(llm, tools)

async for event in core.run_step_stream(messages, session_id):
    if event.type == EventType.THINK:
        print(f"Thinking: {event.content}")
    elif event.type == EventType.TOOL_CALL:
        print(f"Intent: Call {event.tool_name}")
    elif event.type == EventType.STEP_END:
        print("Step complete")
        break
```

### 2.2 Agent (身体) - 435 lines

**文件**: `src/fastreact/agent.py`

**职责**:
1. **循环控制**: 双层循环（外层：处理follow-up，内层：处理工具）
2. **工具执行**: 真正执行工具（带安全检查）
3. **上下文管理**: Token计数、截断
4. **会话管理**: Session状态、消息历史
5. **安全策略**: 危险操作检查

**关键代码**:
```python
class Agent:
    def __init__(self, config, skills_dir=None)

    async def run_event_stream(self, query, skills=None, session_id=None, history=None):
        """
        事件流执行：
        1. 发射SESSION_START
        2. 双层循环：
           - 外层：处理follow-up消息
           - 内层：处理工具调用
        3. 每个step：
           - 调用Core.run_step_stream()获取推理
           - 记录LLM回复到历史（关键！）
           - 执行工具（带安全检查）
           - 发射TOOL_RESULT事件
        4. 发射SESSION_END
        """
```

**关键修复（v2.1.0）**:
```python
# Line 258-267: 记忆注入（修复无限循环）
elif event.type == EventType.STEP_END:
    step_end = event
    # 关键：添加LLM回复到历史
    if step_end.content:
        messages.append({
            "role": "assistant",
            "content": step_end.content,
        })
    break
```

**使用示例**:
```python
agent = Agent()

async for event in agent.run_event_stream("What is 2+2?"):
    if event.type == EventType.THINK:
        print(f"Thinking: {event.content}")
    elif event.type == EventType.TOOL_CALL:
        print(f"Calling: {event.tool_name}")
    elif event.type == EventType.TOOL_RESULT:
        print(f"Result: {event.content}")
    elif event.type == EventType.SESSION_END:
        print(f"Answer: {event.content}")
```

### 2.3 LiteLLMProvider - 381 lines

**文件**: `src/fastreact/providers/litellm.py`

**职责**:
1. 统一LLM API（Anthropic, OpenAI, DeepSeek等）
2. 管理API连接
3. 处理streaming响应
4. 工具调用支持

**支持的后端**:
- Anthropic (Claude)
- OpenAI (GPT-4)
- DeepSeek
- 任何OpenAI-compatible API

**使用示例**:
```python
from fastreact.providers.litellm import LiteLLMProvider

llm = LiteLLMProvider(
    model="claude-3-5-sonnet-20241022",
    api_base="https://api.anthropic.com",
    api_key="sk-ant-...",
    temperature=0.7,
    max_tokens=4096,
)

response = await llm.chat(messages, tools=schemas)
print(response.content)  # LLM回复
print(response.tool_calls)  # 工具调用
```

---

## 3. Brain-Body Split详解

### 3.1 为什么要分离？

**传统架构问题**:
- 推理和执行耦合 → 代码臃肿
- 难以测试 → 浪费 tokens
- 难以并行 → 串行执行
- 难以扩展 → 修改一处影响全局

**Brain-Body Split优势**:
- ✅ **Core锁定180行** → 极简、可验证
- ✅ **推理和执行分离** → 各司其职
- ✅ **事件驱动** → 易于扩展
- ✅ **状态无关** → 易于测试

### 3.2 通信协议

```
Brain (Core)                  Body (Agent)
     │                            │
     │ run_step_stream()          │
     ├──────────────────────────► │
     │                            │
     │ 1. THINK event             │
     ├──────────────────────────► │ (转发给用户)
     │                            │
     │ 2. TOOL_CALL event         │
     ├──────────────────────────► │ (收集)
     │                            │
     │ 3. STEP_END event          │
     ├──────────────────────────► │ (记录回复)
     │                            │
     │                        (执行工具)
     │                            │
     │  run_step_stream()         │ (更新历史)
     ◄──────────────────────────┤ │
     │                            │
     ... (repeat)                │
```

### 3.3 职责划分

| 组件 | 职责 | 不做 |
|------|------|------|
| **Core (Brain)** | • LLM推理<br>• 发射事件<br>• 纯思考 | • 工具执行<br>• 状态管理<br>• 副作用 |
| **Agent (Body)** | • 循环控制<br>• 工具执行<br>• 安全检查<br>• 上下文管理 | • LLM推理<br>• (交给Core) |

### 3.4 关键设计点

**1. Core无状态**:
```python
class ReActCore:
    # ❌ 没有 self.messages (无状态)
    # ❌ 没有 self.session_id (无状态)
    # ✅ 所有状态通过参数传入
    async def run_step_stream(self, messages, session_id):
        # messages: 临时参数
        # session_id: 临时参数
        pass
```

**2. Body持有状态**:
```python
class Agent:
    def __init__(self):
        # ✅ Body持有所有状态
        self._session_queues = {}  # 会话状态
        self._context_monitor = ContextMonitor()  # 上下文状态
        self._safety_policy = SafetyPolicy()  # 安全状态
```

**3. 事件流单向**:
```python
# Core → Body (单向事件流)
async for event in core.run_step_stream(messages, session_id):
    # Body只接收，不反向调用Core
    yield event  # 转发给用户
```

---

## 4. MCP协议支持

### 4.1 什么是MCP？

**MCP (Model Context Protocol)** 是AI Agent与外部工具通信的协议。

FastReAct Nano使用 **SimpleMCP-Stdio**：
- 标准输入/输出通信
- JSON-RPC消息格式
- 隔离执行（防止LLM错误影响主进程）

### 4.2 SimpleMCP-Stdio

**文件**: `src/fastreact/mcp/protocol.py`

**特性**:
- **进程隔离**: 每个MCP服务器独立进程
- **标准通信**: stdin/stdout
- **错误隔离**: MCP崩溃不影响主进程

**架构**:
```
Agent                    MCP Server
  │                          │
  │ 1. spawn (stdio)         │
  ├─────────────────────────►│
  │                          │
  │ 2. write (JSON-RPC)      │
  ├─────────────────────────►│
  │                          │
  │ 3. read (response)       │
  ◄─────────────────────────┤│
  │                          │
  ... (repeat)               │
```

**使用示例**:
```python
from fastreact.mcp.protocol import SimpleMCPStdio

# 创建MCP客户端
mcp = SimpleMCPStdio(
    server_command="python",
    server_args=["mcp_server.py"],
)

# 连接
await mcp.connect()

# 调用工具
result = await mcp.call_tool("read_file", {"path": "README.md"})
print(result)

# 清理
await mcp.close()
```

### 4.3 MCP隔离优势

| 传统执行 | MCP隔离 |
|----------|---------|
| 子进程直接调用 | 标准输入输出 |
| 错误传播到主进程 | 错误隔离在MCP进程 |
| 难以调试 | 可独立测试MCP |
| 安全风险低 | 沙箱隔离 |

---

## 5. Skills系统详解

### 5.1 设计理念

**Progressive Disclosure (渐进式披露)**:
1. **发现**: Agent知道有哪些skills可用
2. **加载**: 按需加载skill详情
3. **使用**: 注入skill prompt到LLM

### 5.2 Skill文件格式

**文件**: `skills/code_review/SKILL.md`

```markdown
---
name: code_review
description: Automated code review and quality analysis
version: 1.0.0
tags: [code, review, quality, best-practices]
author: FastReAct Team
---

# Code Review Skill

Automated code review capabilities to maintain code quality.

## When to Use

Use this skill when you need to:
- Review code changes and pull requests
- Identify potential bugs and issues
- Check adherence to coding standards

## Capabilities

### Correctness
- Logic errors and edge cases
- Error handling and validation
- Resource management

### Security
- Injection vulnerabilities
- Authentication issues
- Data validation
```

### 5.3 Skill加载流程

```python
from fastreact.skills import SkillLoader, SkillRegistry

# 1. 发现阶段（加载skill列表）
loader = SkillLoader()
skills = loader.list_skills()
# → ['code_review', 'file_ops', 'git_workflow']

# 2. 按需加载（加载skill详情）
for skill_name in skills:
    skill = loader.load_skill(skill_name)
    print(f"{skill.name}: {skill.description}")

# 3. 获取prompt（渐进式披露）
registry = SkillRegistry(loader)
prompt = registry.get_prompt('code_review')
# → 返回完整markdown内容
```

### 5.4 Skill Registry API

```python
class SkillRegistry:
    def list_available(self) -> list[str]:
        """列出所有可用skills"""
        pass

    def get(self, name: str) -> Optional[Skill]:
        """获取skill对象（按需加载）"""
        pass

    def get_prompt(self, name: str) -> Optional[str]:
        """获取skill prompt（缓存）"""
        pass

    def list_summaries(self) -> list[str]:
        """列出skill摘要"""
        pass
```

### 5.5 Agent集成

```python
agent = Agent()

# 列出skills
skills = agent.list_skills()
# → ['code_review', 'file_ops', 'git_workflow']

# 获取skill详情
registry = agent._skills
skill = registry.get('code_review')
prompt = registry.get_prompt('code_review')
```

---

## 6. Adapters系统

### 6.1 Adapter模式

所有Adapters遵循统一模式：
1. 创建Agent
2. 调用`run_event_stream()`
3. 渲染事件到UI

### 6.2 CLI Adapter (272 lines)

**文件**: `adapters/cli.py`

**特性**:
- Rich UI (彩色输出)
- 事件流可视化
- 进度条

**使用**:
```bash
# 交互模式
python -m fastreact.adapters.cli

# 直接查询
python -m fastreact.adapters.cli run "What is 2+2?"
```

**代码**:
```python
from fastreact.adapters.cli import run

async def run_event_stream(agent, query):
    async for event in agent.run_event_stream(query):
        if event.type == EventType.THINK:
            console.print(f"[cyan]{event.content}[/]")
        elif event.type == EventType.TOOL_CALL:
            console.print(f"[yellow]→ {event.tool_name}[/]")
        elif event.type == EventType.TOOL_RESULT:
            console.print(f"[dim]{event.content[:100]}...[/]")
```

### 6.3 HTTP Adapter (259 lines)

**文件**: `adapters/http.py`

**特性**:
- FastAPI
- SSE (Server-Sent Events) 流式输出
- REST API

**使用**:
```bash
# 启动服务器
python -m fastreact.adapters.http

# 访问
curl http://localhost:8000/query?query=What+is+2+2%3F
```

**代码**:
```python
from fastapi import FastAPI
from fastreact.adapters.http import create_app

app = create_app()

@app.get("/query")
async def query(query: str):
    async def event_stream():
        agent = Agent()
        async for event in agent.run_event_stream(query):
            yield f"data: {event.json()}\n\n"

    return StreamingResponse(event_stream())
```

### 6.4 REPL Adapter (309 lines)

**文件**: `adapters/repl.py`

**特性**:
- 交互式会话
- 会话历史
- 命令: /clear, /stats, /reset, /quit

**使用**:
```bash
python -m fastreact.adapters.repl

>>> What is 2+2?
4
>>> /stats
Session ID: xxx
Messages: 2
Events: {...}
```

### 6.5 Gateway Adapter (258 lines)

**文件**: `adapters/gateway.py`

**特性**:
- WebSocket支持
- 会话管理
- 多客户端并发

**使用**:
```python
from fastreact.adapters.gateway import create_gateway_app

app = create_gateway_app()

# WebSocket连接
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    async for event in agent.run_event_stream(query):
        await websocket.send_json(event.to_dict())
```

---

## 7. 工具系统

### 7.1 核心工具 (4个)

| 工具 | 功能 | 文件 |
|------|------|------|
| `read_file` | 读取文件 | `tools/read_file.py` |
| `write_file` | 写入文件 | `tools/write_file.py` |
| `exec` | 执行命令 | `tools/exec.py` |
| `edit_file` | 编辑文件 | `tools/edit_file.py` |

### 7.2 工具接口

```python
class Tool:
    name: str           # 工具名称
    description: str    # 工具描述
    parameters: dict    # 参数schema

    async def execute(self, **params) -> str:
        """执行工具，返回结果"""
        pass
```

### 7.3 Tool Registry

```python
from fastreact.core.tools import ToolRegistry

registry = ToolRegistry()

# 注册工具
registry.register(ReadFileTool())
registry.register(WriteFileTool())

# 列出工具
tools = registry.list_all()
# → ['read_file', 'write_file']

# 执行工具
result = await registry.execute('read_file', {'path': 'README.md'})
```

### 7.4 安全执行

```python
# Agent中的安全检查
if self._safety_policy:
    decision = self._safety_policy.check_tool_call(
        tool_name='exec',
        tool_params={'command': 'rm -rf /'}
    )

    if decision.level == 'dangerous' and not decision.allowed:
        return "[SAFETY_BLOCKED] Dangerous command"
```

---

## 8. 事件协议

### 8.1 事件类型

```python
class EventType:
    SESSION_START = "session_start"    # 会话开始
    THINK = "think"                    # LLM思考
    TOOL_CALL = "tool_call"           # 工具调用
    TOOL_RESULT = "tool_result"       # 工具结果
    STEP_END = "step_end"             # 步骤结束
    SESSION_END = "session_end"       # 会话结束
    ERROR = "error"                   # 错误
```

### 8.2 事件流

```
SESSION_START
    ↓
THINK (LLM思考)
    ↓
TOOL_CALL (工具调用意图)
    ↓
TOOL_RESULT (工具执行结果)
    ↓
STEP_END (步骤完成)
    ↓
(loop)
    ↓
SESSION_END (会话结束)
```

### 8.3 AgentEvent结构

```python
class AgentEvent:
    type: EventType        # 事件类型
    content: str          # 事件内容
    session_id: str       # 会话ID
    metadata: dict        # 元数据
    timestamp: datetime   # 时间戳
```

**工具调用事件**:
```python
event = AgentEvent.tool_call(
    tool_name="read_file",
    tool_args={"path": "README.md"},
    session_id="session-123"
)
```

**工具结果事件**:
```python
event = AgentEvent.tool_result(
    tool_name="read_file",
    content="# README\n...",
    session_id="session-123"
)
```

---

## 9. 配置系统

### 9.1 配置文件 (YAML)

**文件**: `fastreact.yaml`

```yaml
llm:
  model: "claude-3-5-sonnet-20241022"
  api_base: "https://api.anthropic.com"
  api_key: "${ANTHROPIC_API_KEY}"  # 环境变量
  temperature: 0.7
  max_tokens: 4096

react:
  enable_safety: true
  enable_filesystem_memory: true
  strict_mode: false
  max_iterations: 20
  max_context_tokens: 200000
  context_warning_threshold: 0.9
  max_tool_output_chars: 10000
  max_tree_depth: 3
  max_files_per_dir: 50

tools:
  max_file_size: 100000
  exec_timeout: 30
  working_dir: "."
  protected_paths:
    - "system32"
    - "Windows"
```

### 9.2 环境变量

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export DEEPSEEK_API_KEY="..."

# FastReAct会自动检测
```

### 9.3 代码配置

```python
from fastreact import Config

# 从文件加载
config = Config.load()  # 自动查找fastreact.yaml

# 或手动创建
from fastreact.core.config import Config, LLMConfig

config = Config(
    llm=LLMConfig(
        model="gpt-4",
        api_key="sk-...",
    )
)
```

---

## 10. 安全策略

### 10.1 SafetyPolicy

```python
from fastreact.core.safety import SafetyPolicy

policy = SafetyPolicy(strict_mode=False)

decision = policy.check_tool_call(
    tool_name="exec",
    tool_params={"command": "rm -rf /"}
)

# decision.level: "safe" | "moderate" | "dangerous"
# decision.allowed: True | False
# decision.reason: "解释原因"
```

### 10.2 危险操作检测

**危险命令模式**:
- `rm -rf`
- `format`
- `del /F`
- `mkfs`
- 系统关键路径

**文件操作保护**:
- 检查protected_paths
- 文件大小限制
- 工作目录限制

### 10.3 确认回调

```python
from fastreact.core.safety import CLIConfirmationCallback

callback = CLIConfirmationCallback()

if decision.level == "dangerous":
    # 询问用户
    allowed = await callback.confirm(
        "执行危险操作: rm -rf /"
    )
```

---

## 11. 完整API参考

### 11.1 Agent API

```python
class Agent:
    def __init__(
        self,
        config: Optional[Config] = None,
        skills_dir: Optional[Path] = None,
    )

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
    ) -> AsyncIterator[AgentEvent]

    async def run(
        self,
        query: str,
        skills: Optional[list[str]] = None,
    ) -> str

    async def chat(
        self,
        message: str,
        history: Optional[list[Message]] = None,
    ) -> str

    def list_skills(self) -> list[str]
```

### 11.2 ReActCore API

```python
class ReActCore:
    def __init__(
        self,
        llm: LiteLLMProvider,
        tools: ToolRegistry,
        max_iterations: int = 20,
    )

    async def run_step_stream(
        self,
        messages: list[dict],
        session_id: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]
```

### 11.3 SkillRegistry API

```python
class SkillRegistry:
    def __init__(self, loader: Optional[SkillLoader] = None)

    def list_available(self) -> list[str]
    def list_loaded(self) -> list[str]
    def get(self, name: str, load_if_missing: bool = True) -> Optional[Skill]
    def get_prompt(self, name: str) -> Optional[str]
    def list_summaries(self) -> list[str]
    def clear_cache()
    def reload(self, name: str) -> Optional[Skill]
```

---

## 12. 使用示例

### 12.1 基础使用

```python
import asyncio
from fastreact import Agent

async def main():
    agent = Agent()

    # 简单查询
    response = await agent.run("What is 2+2?")
    print(response)

    # 事件流
    async for event in agent.run_event_stream("What is 2+2?"):
        if event.type == EventType.THINK:
            print(f"Thinking: {event.content}")
        elif event.type == EventType.SESSION_END:
            print(f"Answer: {event.content}")

asyncio.run(main())
```

### 12.2 使用Skills

```python
agent = Agent()

# 使用skill
response = await agent.run(
    "Review this code for bugs",
    skills=["code_review"]
)

# 多skills
response = await agent.run(
    "Create git branch and commit changes",
    skills=["git_workflow", "file_ops"]
)
```

### 12.3 多轮对话

```python
agent = Agent()

# 历史对话
history = [
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "4"},
    {"role": "user", "content": "What about 3+3?"},
]

async for event in agent.run_event_stream(
    "And 5+5?",
    history=history
):
    print(event.content)
```

### 12.4 自定义配置

```python
from fastreact import Agent, Config

config = Config(
    llm=LLMConfig(
        model="deepseek-chat",
        api_base="https://api.deepseek.com",
        api_key="sk-...",
        temperature=0.3,
    ),
    react=ReactConfig(
        enable_safety=True,
        max_iterations=30,
    )
)

agent = Agent(config=config)
```

---

## 附录

### A. 性能基准

| 操作 | 延迟 | 说明 |
|------|------|------|
| Agent初始化 | ~100ms | 包含LLM连接 |
| 简单查询 | ~500ms | 无工具调用 |
| 工具执行 | ~200ms | 取决于工具 |
| SSE流式 | 实时 | Server-Sent Events |

### B. 兼容性

| LLM | 状态 |
|-----|------|
| Claude (Anthropic) | ✅ 完全支持 |
| GPT-4 (OpenAI) | ✅ 完全支持 |
| DeepSeek | ✅ 完全支持 |
| 其他OpenAI-compatible | ✅ 支持 |

### C. Roadmap

**v2.2.0** (规划中):
- [ ] 并行工具执行
- [ ] LLM响应缓存
- [ ] 更丰富的内置skills
- [ ] 性能优化（asyncio）

**v3.0.0** (远期):
- [ ] 多模态支持（vision）
- [ ] 向量数据库集成
- [ ] 多Agent协作

---

*文档版本: 2.1.0*
*最后更新: 2026-02-15*
