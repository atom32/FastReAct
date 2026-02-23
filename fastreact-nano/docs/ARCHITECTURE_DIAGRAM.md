# FastReAct Nano v2.4.1 - Architecture Diagram

**Last Updated**: 2025-02-23
**Purpose**: Complete architecture visualization and explanation

---

## Overall Architecture

```
FastReAct Nano v2.4.1 Architecture
    (Brain-Body Separation)

                                   User Query
                                  "分析这个代码库"

                    │              │              │
                    ▼              ▼              ▼
         ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
         │   CLI Adapter   │ │  HTTP Adapter   │ │ Gateway Adapter  │
         │   (Terminal)    │ │   (REST/SSE)    │ │  (WebSocket)     │
         └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                  │                   │                   │
                  └───────────────────┼───────────────────┘
                                      │
                    ┌──────────────────────────────────────────────┐
                    │              ADAPTER LAYER                   │
                    │         (Unified Interface)                 │
                    └────────────────────────┬─────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENT (The Body)                                 │
│                         src/fastreact/agent.py                                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Main Event Loop                                │  │
│  │  while iteration_count < max_iterations:                              │  │
│  │      1. Check for steering/followup messages                          │  │
│  │      2. Call Core to generate THOUGHT + TOOL_CALL                    │  │
│  │      3. Execute tools (with safety checks)                           │  │
│  │      4. Update memory (FilesystemMemory)                             │  │
│  │      5. Emit STEP_END event                                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Responsibilities:                                                            │
│  • Loop control (max 25 iterations)                                          │
│  • Tool execution                                                            │
│  • Safety checks                                                             │
│  • Context monitoring (token limits)                                        │
│  • Memory persistence (memory.json)                                         │
│  • Session management (50-turn history)                                     │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              │ calls
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE (The Brain)                                │
│                         src/fastreact/core/react.py                          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           ReActCore                                   │  │
│  │                                                                        │  │
│  │  run_step_stream(tools: list[Tool]) -> AsyncIterator[Event]         │  │
│  │      │                                                                │  │
│  │      ├─→ _generate_thought()     # LLM reasoning                     │  │
│  │      │        └─→ Emit THINK event                                   │  │
│  │      │                                                                │  │
│  │      └─→ _emit_tool_call()      # Tool call intent                   │  │
│  │                 └─→ Emit TOOL_CALL event                             │  │
│  │                                                                        │  │
│  │  FORBIDDEN:                                                            │  │
│  │  • Executing tools                                                     │  │
│  │  • Checking safety                                                     │  │
│  │  • Managing state                                                       │  │
│  │  • Control flow logic                                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Properties:                                                                  │
│  • 180 lines of pure reasoning                                              │
│  • Zero state                                                                │
│  • Zero side effects                                                         │
│  • Zero control flow                                                         │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM PROVIDER LAYER                                   │
│                       src/fastreact/providers/                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         LiteLLMProvider                               │  │
│  │                                                                        │  │
│  │  chat(messages, tools) → LLMResponse                                  │  │
│  │      │                                                                │  │
│  │      ├─→ Select model (OpenAI/Anthropic/DeepSeek/etc.)               │  │
│  │      ├─→ Format tools (JSON Schema)                                  │  │
│  │      ├─→ Call LLM API                                                 │  │
│  │      └─→ Parse response (5-level JSON repair)                        │  │
│  │                                                                        │  │
│  │  Returns:                                                              │  │
│  │  • content: str (LLM reasoning)                                       │  │
│  │  • tool_calls: list[ToolCall]                                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              │ manages
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TOOL SYSTEM                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Core Tools (built-in)                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  ReadFile    │  │  WriteFile   │  │     Exec     │              │   │
│  │  │  Tool        │  │  Tool        │  │    Tool      │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  - File operations with safety checks                               │   │
│  │  - Size limits (1MB max)                                             │   │
│  │  - Encoding validation (UTF-8)                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    MCP Tools (external)                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ Time Server  │  │  Filesystem  │  │   Custom...  │              │   │
│  │  │     MCP      │  │     MCP      │  │              │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  Managed by MCPToolManager                                          │   │
│  │  - Auto-reconnect (max 3 retries)                                   │   │
│  │  - Zombie resurrection (crash recovery)                             │   │
│  │  - JSON-RPC over STDIO                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ extends via
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SKILL SYSTEM (Extensions)                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Skill Registry                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ code_review  │  │ file_ops     │  │ git_workflow │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  - Progressive disclosure (info → basic → advanced)                 │   │
│  │  - Auto-selection (Chinese n-gram matching)                         │   │
│  │  - Tool policy (restrict available tools)                           │   │
│  │  - Reasoning pattern (custom prompt template)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Structure:                                                                   │
│  skills/builtin/          - Global skills (all users)                       │
│  workspaces/{user}/skills/ - User-specific skills (multi-tenant)            │
│  skills/community/        - Community skills (optional)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Event Protocol

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVENT PROTOCOL                                       │
│                   (Unified Communication Layer)                              │
│                                                                              │
│  EventType.SESSION_START  → "开始新会话"                                     │
│  EventType.THINK          → "LLM 思考内容"                                   │
│  EventType.TOOL_CALL      → "工具调用意图"                                   │
│  EventType.TOOL_RESULT    → "工具执行结果"                                   │
│  EventType.STEP_END        → "推理步骤完成"                                   │
│  EventType.SESSION_END    → "会话结束"                                      │
│  EventType.ERROR          → "错误信息"                                      │
│  EventType.ASK_USER       → "请求用户确认"                                   │
│                                                                              │
│  All adapters emit AsyncIterator[AgentEvent]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Tenant Support

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-TENANT SUPPORT                                      │
│                                                                              │
│  ┌─────────────────────────┐         ┌─────────────────────────┐           │
│  │   Single-Tenant         │         │   Multi-Tenant          │           │
│  │   (Gateway Adapter)     │         │   (Feishu Adapter)      │           │
│  │                         │         │                         │           │
│  │  workspaces/default/    │         │  /var/fastreact/tenants/ │           │
│  │  └── memory.json        │         │  └── feishu/            │           │
│  │      config.json        │         │      ├── {user1}/       │           │
│  │      skills/            │         │      │   ├── memory.json │           │
│  │                         │         │      │   ├── config.json │           │
│  │  All users share        │         │      │   └── skills/     │           │
│  │  same workspace         │         │      └── {user2}/       │           │
│  └─────────────────────────┘         │                          │           │
│                                      │  Each user isolated    │           │
│                                      └─────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Ironclad Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       IRONCLAD FEATURES (v2.1.0+)                            │
│                                                                              │
│  1. Infinite Loop Protection    → max_iterations = 25 (hard limit)          │
│  2. JSON Parsing Robustness     → 5-level cascading repair strategy         │
│  3. Multi-turn Dialog Memory    → Auto-prune at 50 turns                    │
│  4. MCP Auto-Reconnect          → max 3 retries with exponential backoff   │
│  5. MCP Zombie Resurrection     → Auto-detect and restart crashed servers  │
│                                                                              │
│  Test Coverage: 528/528 passing (100%)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example

```
User: "分析这个代码库"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ ADAPTER: Receive query                                       │
│   "分析这个代码库"                                            │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ AGENT: Initialize session                                    │
│   session_id = "uuid-123"                                    │
│   Load memory.json (previous context)                        │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ CORE: Generate thought + tool call                           │
│   THINK: "我需要先了解项目结构"                               │
│   TOOL_CALL: ExecTool(command="find . -name '*.py'")        │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ AGENT: Execute tool                                          │
│   Safety check: OK                                           │
│   Execute: find . -name '*.py'                               │
│   Result: ["src/fastreact/agent.py", "src/fastreact/core/"] │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ CORE: Process result, generate next action                   │
│   THINK: "我看到有 131 个 Python 文件，让我读取核心文件..."  │
│   TOOL_CALL: ReadFile(path="src/fastreact/agent.py")        │
└────┬────────────────────────────────────────────────────────┘
     │
     ▼
    ... (repeat until max_iterations or task complete)
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ SESSION_END: "这个项目是一个 AI Agent SDK，采用 Brain-Body..."│
└─────────────────────────────────────────────────────────────┘
```

---

## Core Modules Reference

### Core (src/fastreact/core/)

| File | Purpose | Key Classes |
|------|---------|-------------|
| `messages.py` | Message system for dual-loop architecture | Message, MessageQueue |
| `react.py` | Pure intent generator (Brain) | ReActCore |
| `tools.py` | Tool abstraction layer | Tool, ToolRegistry |
| `config.py` | Configuration management | Config, LLMConfig, ToolConfig |
| `context.py` | Context monitoring | ContextMonitor, FilesystemMemory |
| `safety.py` | Safety policy system | SafetyPolicy, ConfirmationCallback |
| `events.py` | Unified event protocol | EventType, AgentEvent |
| `session.py` | Session management | Session |
| `memory.py` | Memory management (v2.4.0) | MemoryManager |
| `prompts.py` | Prompt templates | SYSTEM_PROMPT_CORE |
| `multitenant.py` | Multi-tenant support | MultiTenantManager, UserContext |

### Agent (src/fastreact/agent.py)

| Component | Purpose |
|-----------|---------|
| `Agent` class | Main orchestrator (Body) |
| `run_event_stream()` | Main event loop |
| `_execute_tool()` | Tool execution with safety |
| `_check_steering_followup()` | Real-time intervention |

### Adapters (src/fastreact/adapters/)

| File | Purpose | Protocol |
|------|---------|----------|
| `cli.py` | Command-line interface | stdin/stdout |
| `http.py` | REST API | SSE streaming |
| `gateway.py` | WebSocket server | WebSocket |
| `repl.py` | Interactive shell | REPL |
| `telegram.py` | Telegram bot | Telegram API |
| `feishu_sdk.py` | Feishu bot | Feishu SDK |

### Tools (src/fastreact/tools/)

| File | Purpose | Safety Features |
|------|---------|-----------------|
| `read_file.py` | Read file contents | Size limit (1MB) |
| `write_file.py` | Write files | Path validation |
| `exec_tool.py` | Execute shell commands | Timeout (30s) |
| `edit_file.py` | Edit files in-place | Backup mechanism |

### MCP (src/fastreact/mcp/)

| File | Purpose |
|------|---------|
| `manager.py` | MCP tool lifecycle management |
| `client.py` | JSON-RPC client for MCP |
| `discovery.py` | Automatic tool discovery |
| `multitenant_manager.py` | Per-user MCP management |
| `server.py` | MCP server wrapper |

### Skills (src/fastreact/skills/)

| File | Purpose |
|------|---------|
| `base.py` | Skill base classes |
| `loader.py` | Dynamic skill loading |
| `parser.py` | Skill definition parser |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `config.example.json` | Full configuration template |
| `config.simple.json` | Minimal configuration |
| `pyproject.toml` | Package metadata and dependencies |
| `.env.example` | Environment variable template |

---

**Document Version**: 1.0
**Author**: Claude Code + User
**License**: MIT
