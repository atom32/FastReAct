# Skills vs MCP Tools: Architecture Guide

**Version**: 2.4.2
**Last Updated**: 2025-02-19

---

## Directory Structure (v2.4+)

FastReAct Nano now uses a standardized directory structure for skills and MCP servers:

```
fastreact-nano/
├── skills/                    # Global SKILL definitions
│   ├── builtin/              # Built-in skills (git_workflow, code_review, etc.)
│   ├── community/            # Community-contributed skills
│   └── custom/               # User-defined skills (gitignored)
│
├── mcp_servers/              # Global MCP server configurations
│   ├── builtin/              # Built-in MCP server implementations
│   ├── config/               # MCP server configuration files
│   │   ├── shared.json       # Shared mode servers (single instance)
│   │   └── per_user.json     # Per-user mode servers (isolated)
│   └── README.md             # MCP server development guide
│
└── workspaces/               # User workspaces
    └── default/              # Gateway single-tenant workspace
        ├── config.json       # User configuration
        ├── memory.json       # Conversation memory
        └── skills/           # User-specific skills (override global)
```

### Single-Tenant (Gateway) vs Multi-Tenant (Feishu)

**Gateway (Single-Tenant)**:
- Workspace: `./workspaces/default/`
- Skills: `skills/builtin/` + `workspaces/default/skills/`
- MCP: `mcp_servers/config/shared.json`

**Feishu (Multi-Tenant)**:
- Workspace: `/var/fastreact/tenants/feishu/{user_id}/`
- Skills: `skills/builtin/` + `{user_workspace}/skills/`
- MCP: `mcp_servers/config/` + `{user_workspace}/mcp_config.json`

### Skills Loading Priority

1. User workspace skills (`workspaces/{user}/skills/`)
2. Global built-in skills (`skills/builtin/`)
3. Community skills (`skills/community/`)

### MCP Server Loading Priority

1. User MCP config (`{user_workspace}/mcp_config.json`)
2. Per-user config (`mcp_servers/config/per_user.json`)
3. Shared config (`mcp_servers/config/shared.json`)

For detailed directory structure information, see [docs/DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md).

---

## Overview

This document clarifies the distinction between **Skills** (cognitive/strategy layer) and **MCP Tools** (execution/capability layer) in FastReAct Nano.

---

## Skills (Cognitive Layer)

### What Are Skills?

**Skills are NOT knowledge itself.** They are:

- **Task patterns**: How to approach certain types of problems
- **Decision templates**: Structured reasoning frameworks
- **Prompt structures**: System prompt enhancements
- **Tool policies**: Guidelines for tool selection and usage

### The Problem Skills Solve

> "When I encounter X type of task, how should I think about it?"

### Essential Characteristics

```
Skill = Structured Prompt + Tool Policy + Reasoning Pattern
```

### Example Skills

#### `git_workflow`
- **Purpose**: Automate Git operations with best practices
- **Thinking Pattern**: Branch → Commit → Push → PR workflow
- **Tool Policy**: Prefer `git_commit`, `git_push`, `git_create_pr`
- **System Prompt**: "Use Git flow workflow: feature branches, atomic commits..."

#### `code_review`
- **Purpose**: Review code for bugs, security, style
- **Thinking Pattern**: Read → Analyze → Critique → Suggest
- **Tool Policy**: Use `read_file`, `search_code`, `lint_check`
- **System Prompt**: "Check for: security issues, code smells, naming conventions..."

#### `research_mode`
- **Purpose**: Deep research with multiple sources
- **Thinking Pattern**: Query → Crawl → Extract → Synthesize
- **Tool Policy**: Use `web_search`, `read_page`, `summarize`
- **System Prompt**: "Verify claims from multiple sources, cite references..."

### Key Principle

> **Skill ≠ Tool**
>
> A Skill is "how to use tools" - not the tool itself.

---

## MCP Tools (Execution Layer)

### What Are MCP Tools?

**MCP Tools are deterministic, typed, external capabilities.**

### The Problem MCP Tools Solve

> "What can I do?"

### Essential Characteristics

```
MCP Tool = Deterministic Function + Typed Parameters + External Execution
```

### Example MCP Tools

#### `git_ls_files`
- **Purpose**: List files in Git repository
- **Input**: `{ "path": string }`
- **Output**: `{ "files": string[] }`
- **Side Effects**: None (read-only)

#### `fs_read`
- **Purpose**: Read file contents
- **Input**: `{ "path": string, "offset": int, "limit": int }`
- **Output**: `{ "content": string, "truncated": boolean }`
- **Side Effects**: None (read-only)

#### `graphrag_search`
- **Purpose**: Search knowledge graph
- **Input**: `{ "query": string, "top_k": int }`
- **Output**: `{ "results": [{ "entity", "relation", "score" }] }`
- **Side Effects**: None (read-only)

### Key Principle

> MCP tools don't "think" - they only execute.
>
> All reasoning happens in the LLM (Brain), not in the tool.

---

## Execution Flow: Complete Version

### Current Implementation (Static)

```
User Query
  ↓
Skill Selection (manual or auto)
  ↓
MCP Server Loading (based on skill requirements)
  ↓
Tool Execution (run-to-completion)
  ↓
Final Answer
```

### Future Target (Dynamic + Replannable)

```
User Query
  ↓
Context Inspection (what tools are available?)
  ↓
Skill Routing (which skill pattern matches?)
  ↓
Dynamic Tool Discovery (what MCP servers do we need?)
  ↓
Iterative Planning Loop ← CORE: stateful replanning
  ↓
Tool Execution
  ↓
State Update
  ↓
Re-plan or Exit
```

### Key Differences

| Aspect | Current | Future |
|--------|---------|--------|
| **Skill Selection** | Static (once per query) | Dynamic (can switch mid-execution) |
| **Tool Discovery** | Preload all | Lazy load on-demand |
| **Planning** | Single-shot | Iterative replanning |
| **Interrupt** | Stop execution | Interrupt + upgrade + resume |

---

## Multi-Tenant Isolation: State Boundaries

### Common Misconception

**❌ Wrong**: Shared = Stateless
**❌ Wrong**: Per-User = Stateful

### Precise Classification

| Isolation Mode | State Boundary | Use Cases | Examples |
|----------------|----------------|-----------|----------|
| **Shared** | None (stateless) | Read-only tools | Calculator, formatters, linters |
| **Session-bound** | Per Session | Temporary state | Git workspace, shell session |
| **User-bound** | Per User | Persistent state | User workspace, database |
| **On-demand isolated** | Ephemeral | Enterprise security | Sensitive database ops |

### Key Concept

> **Where is the state isolation boundary?**

### Claude Code's Design

```
User Workspace = OS Sandbox
```

- Each user gets isolated workspace directory
- Filesystem tools are scoped to user's workspace
- MCP servers can be "shared" or "per_user"
- Session-bound tools get temp directories

### Example Configurations

#### Shared Tool (All Users Share One Instance)

```json
{
  "name": "graphrag",
  "command": "python3",
  "args": ["/path/to/graph_rag_server.py"],
  "isolation": "shared",
  "description": "Knowledge graph search (read-only)"
}
```

- **State**: None (read-only knowledge base)
- **Instance Count**: 1 (shared across all users)
- **Use Case**: Reference data, search indexes

#### Session-Bound Tool (Per Session)

```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "{session_workspace}"],
  "isolation": "session_bound",
  "description": "Filesystem operations (session isolated)"
}
```

- **State**: Per session (temp workspace)
- **Instance Count**: N (one per active session)
- **Use Case**: Temporary file operations during session

#### User-Bound Tool (Per User)

```json
{
  "name": "user_database",
  "command": "python3",
  "args": ["/path/to/db_server.py", "--user-dir", "{user_workspace}"],
  "isolation": "per_user",
  "description": "User database (persistent per user)"
}
```

- **State**: Per user (persistent workspace)
- **Instance Count**: M (one per active user)
- **Use Case**: User-specific data stores

#### On-Demand Isolated (Ephemeral)

```json
{
  "name": "sensitive_ops",
  "command": "python3",
  "args": ["/path/to/secure_server.py"],
  "isolation": "lazy_per_user",
  "idle_timeout": 300,
  "max_instances": 10,
  "description": "Sensitive operations (ephemeral isolation)"
}
```

- **State**: Ephemeral (created on-demand, destroyed after timeout)
- **Instance Count**: 0 to max_instances (on-demand)
- **Use Case**: Security-sensitive operations (audit logs, compliance)

---

## WebSocket Protocol: Gateway Messages

### Client → Server

| Type | Action | Purpose | Example |
|------|---------|---------|---------|
| `query` | - | Normal user query | `{"type": "query", "content": "..."}` |
| `control` | `interrupt` | Interrupt execution | `{"type": "control", "action": "interrupt"}` |
| `control` | `cancel` | Cancel queued query | `{"type": "control", "action": "cancel", "query_id": "..."}` |
| `ping` | - | Heartbeat | `{"type": "ping"}` |

### Server → Client

| Type | Subtype | Purpose | Example |
|------|---------|---------|---------|
| `event` | `session_start` | Query started | `{"type": "event", "event_type": "session_start", ...}` |
| `event` | `think` | LLM reasoning | `{"type": "event", "event_type": "think", "content": "..."}` |
| `event` | `tool_call` | Tool being called | `{"type": "event", "event_type": "tool_call", "tool_name": "..."}` |
| `event` | `tool_result` | Tool execution result | `{"type": "event", "event_type": "tool_result", "content": "..."}` |
| `event` | `session_end` | Final answer | `{"type": "event", "event_type": "session_end", "content": "..."}` |
| `info` | - | Informational message | `{"type": "info", "content": "Execution interrupted"}` |
| `warning` | - | Warning message | `{"type": "warning", "content": "Queue full"}` |
| `error` | - | Error message | `{"type": "error", "content": "..."}` |

---

## Gateway Architecture: Phase 1 vs Future

### Current Phase (1.1): Basic Queue + Interrupt

```
Gateway (FastAPI)
  ├── Session Manager
  │   └── Session (per WebSocket)
  │       ├── Message Queue (asyncio.Queue, max_size=5)
  │       ├── Background Task (process_queue)
  │       └── Agent (multitenant=True)
  │           ├── Config (loaded from ~/.fastreact/config.json)
  │           ├── MCP Manager (lazy load on first query)
  │           └── Tool Registry (core + MCP tools)
  └── WebSocket Endpoint
      ├── Receive Message
      ├── Enqueue (control bypasses queue limit)
      └── Background Process
          ├── Control → Interrupt
          └── Query → Agent.run_event_stream
```

**Features**:
- [x] Input queue (concurrent message handling)
- [x] Graceful interrupt (control message)
- [x] MCP configuration loading
- [x] Workspace isolation (multitenant mode)
- [x] Queue full warning

**Limitations**:
- Static skill selection (once per query)
- No stateful replanning
- No tool permission gating
- No session resume

### Future Phase (2+): Claude Code Level

```
Gateway (Advanced)
  ├── Session Manager
  │   └── Session (per WebSocket)
  │       ├── Message Queue
  │       ├── State Manager (persist to disk)
  │       ├── Plan Manager (resumable)
  │       └── Agent (multitenant=True)
  │           ├── Config
  │           ├── Skill Router (dynamic)
  │           ├── MCP Manager (lazy + cached)
  │           ├── Permission Gate (tool scoping)
  │           └── Tool Registry
  └── WebSocket Endpoint
      ├── Receive Message
      ├── State Check (resume?)
      └── Execute
          ├── Control → Interrupt + Save State
          └── Query → Resume or New Plan
              ├── Dynamic Tool Discovery
              ├── Permission Check
              ├── Execute Tool
              ├── Update State
              └── Re-plan or Complete
```

**Target Features**:
- [ ] Stateful replanning loop
- [ ] Interruptible + resumable plans
- [ ] Tool permission scoping
- [ ] Session resume after disconnect
- [ ] Dynamic skill switching

---

## Configuration Examples

### Minimal Config (No MCP)

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-xxx"
  }
}
```

### With MCP Servers

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-xxx"
  },
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["/path/to/graph_rag_server.py"],
        "isolation": "shared",
        "description": "Knowledge graph search"
      },
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
        "isolation": "session_bound",
        "description": "Filesystem operations (session isolated)"
      }
    ]
  }
}
```

### With Skills (Recommended MCP Servers)

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-xxx"
  },
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["/path/to/graph_rag_server.py"],
        "isolation": "shared",
        "description": "Knowledge graph search",
        "associated_skill": "research_mode"
      },
      {
        "name": "git",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-git"],
        "isolation": "shared",
        "description": "Git operations",
        "associated_skill": "git_workflow"
      }
    ]
  }
}
```

---

## Best Practices

### For Skill Authors

1. **Skills should be task-oriented**, not tool-oriented
   - ✅ "code_review" - Review code for bugs and style
   - ❌ "use_grep_tool" - Incorrect (tool-focused)

2. **Skills should specify MCP server dependencies**
   - Add `"associated_skill": "your_skill_name"` to MCP server config
   - This enables lazy loading (only start servers when needed)

3. **Skills should be composable**
   - Design skills to work together
   - Example: "git_workflow" + "code_review" = "PR creation workflow"

### For MCP Tool Authors

1. **Tools should be deterministic**
   - Same input → same output
   - No hidden state or side effects

2. **Tools should have clear types**
   - Use JSON schema for parameters
   - Document return types

3. **Choose correct isolation mode**
   - Shared: Read-only tools, reference data
   - Session-bound: Temporary state
   - Per-user: Persistent user data
   - Lazy: Security-sensitive, on-demand

### For Gateway Operators

1. **Configure workspace isolation**
   - Always set `base_workspace` in `run_gateway()`
   - Use `multitenant=True` for multi-user environments

2. **Monitor queue capacity**
   - Adjust `max_queue_size` based on load
   - Default: 5 messages per session

3. **Secure MCP servers**
   - Use `isolation: "lazy_per_user"` for sensitive ops
   - Set `idle_timeout` to auto-cleanup idle instances

---

## Testing

### Test Queue Behavior

```bash
# Send multiple messages rapidly
for i in {1..10}; do
  echo '{"type":"query","content":"Test '$i'"}' | websocat ws://localhost:9000/ws
done
```

**Expected**: First 5 processed, next 5 rejected with "Queue full" warning.

### Test Interrupt

```typescript
// Frontend: Send interrupt
stopAgent()  // Sends: {"type":"control","action":"interrupt"}
```

**Expected**: Agent stops within 500ms with "Execution interrupted" message.

### Test MCP Discovery

```bash
# List MCP servers
curl http://localhost:9000/api/mcp/servers

# List all tools (including MCP)
curl http://localhost:9000/api/tools
```

**Expected**: Returns configured MCP servers and discovered tools.

---

## Migration Guide

### From v2.0 to v2.1

1. **Update Gateway**:
   ```python
   # Old
   session = Session(session_id, websocket)

   # New
   config = Config.load()
   session = Session(
       session_id,
       websocket,
       config=config,
       max_queue_size=5,
       base_workspace=Path.cwd() / "workspace"
   )
   ```

2. **Update Frontend**:
   ```typescript
   // Old
   stopAgent() {
     manager.send({ type: "query", content: "stop" })
   }

   // New
   stopAgent() {
     manager.send({
       type: "control",
       action: "interrupt",
       reason: "User cancelled"
     })
   }
   ```

3. **Update Config**:
   ```json
   // Add MCP servers with isolation settings
   {
     "mcp": {
       "servers": [
         {
           "name": "your_server",
           "command": "...",
           "isolation": "shared",  // or "session_bound", "per_user"
           "description": "..."
         }
       ]
     }
   }
   ```

---

## References

- **Gateway Code**: `fastreact-nano/src/fastreact/adapters/gateway.py`
- **Agent Code**: `fastreact-nano/src/fastreact/agent.py`
- **Config Code**: `fastreact-nano/src/fastreact/core/config.py`
- **Frontend WebSocket**: `fastreact-nano-web/components/chat/use-fastreact-ws.ts`

---

**Document Status**: ✅ Complete (Phase 1 implementation)
**Next Review**: After Phase 2 (stateful replanning) implementation
