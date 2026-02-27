# FastReAct Nano Design Philosophy

**Last Updated**: 2025-02-27
**Status**: Core Design Principles

---

## Core Principles

```
FastReAct Nano =
  4 Minimal Core Tools (Stable)
  + Unlimited Skills (Extensible)
  + exec Universal Tool (Powerful)
```

---

## Three-Layer Architecture

### Layer 1: Minimal Core Tools (4)

**Never expanding, always stable**:

```
exec_tool.py       # Universal execution
read_file.py       # Read files
write_file.py      # Write files
edit_file.py       # Edit files (string replacement)
```

**Characteristics**:
- ✅ Minimal to the extreme
- ✅ Long-term stable
- ✅ No external dependencies
- ✅ Type-safe

**Promise**: These 4 tools will never increase.

---

### Layer 2: Unlimited Skills (Infinite)

**Zero-code extension, Markdown-based**:

```
skills/builtin/
├── http/              # HTTP operations
├── search/            # Web search
├── json/              # JSON processing
├── database/          # Database operations
├── image/             # Image processing
├── git/               # Git operations
├── cron/              # Scheduled tasks
├── news_aggregator/   # News aggregation (existing)
├── code_review/       # Code review (existing)
└── ...                # Infinite extension
```

**Skill Format**:

```yaml
---
name: http_fetch
description: Fetch HTTP content using curl
tags: [http, web, api]
requirements:
  bins: ["curl"]  # Declare required commands
---

# HTTP Fetch

Use `exec` tool with curl:

```bash
# GET request
curl -s https://api.example.com

# POST request
curl -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' https://api.example.com
```
```

**Characteristics**:
- ✅ Zero-code (Markdown only)
- ✅ Immediately available (if bash command exists)
- ✅ Infinite extension (add whatever you want)
- ✅ Easy to share (copy-paste SKILL.md)

---

### Layer 3: exec Universal Tool

**All functionality implemented through exec**:

```python
# Agent reasoning chain
Thought: "I need to fetch API data"
Action: "Use http_fetch Skill"
Tool: "exec"
Command: "curl -s https://api.example.com"

Thought: "I need to search the web"
Action: "Use web_search Skill"
Tool: "exec"
Command: "curl -s 'https://ddg.gg/?q=query' | grep ..."

Thought: "I need to process JSON"
Action: "Use json_process Skill"
Tool: "exec"
Command: "echo '{...}' | jq ."
```

**Execution Flow**:
```
Agent → Select Skill → Extract Command → exec Tool → Return Result
```

---

## Why This Design?

### 1. Minimal Tools = Stability

**4 tools, never increasing**:
- ✅ Small codebase (< 2000 lines core code)
- ✅ Low maintenance cost
- ✅ Complete test coverage
- ✅ Stable API

**Contrast**:
- ❌ Adding 10+ tools → Code bloat → Maintenance nightmare

---

### 2. Rich Skills = Flexibility

**Infinite extension, zero-code**:
- ✅ Need a feature? Write a SKILL.md
- ✅ No core code changes
- ✅ No recompilation
- ✅ Hot-reload support

**Examples**:
```
Need HTTP functionality?
  → Create skills/http/SKILL.md
  → Provide curl command examples
  → Ready to use ✅

Need scheduled tasks?
  → Create skills/cron/SKILL.md
  → Provide crontab command examples
  → Ready to use ✅

Need image processing?
  → Create skills/image/SKILL.md
  → Provide convert command examples
  → Ready to use ✅
```

---

### 3. exec Tool = Universality

**All functionality unified through exec**:
- ✅ Unified interface (exec tool)
- ✅ Unified calling method (bash commands)
- ✅ Unified error handling

**Advantages**:
- ✅ Low learning curve for Agent (only needs exec)
- ✅ Easy for users to understand (bash is familiar)
- ✅ Simple to debug (copy commands to terminal)

---

## Comparison with OpenClaw

| Dimension | FastReAct Nano | OpenClaw |
|-----------|----------------|----------|
| **Core Tools** | 4 (Python) | 10+ (TypeScript) |
| **Skills** | Markdown + CLI | Markdown + CLI |
| **Calling Method** | exec (unified) | exec / direct API |
| **Extension Difficulty** | Low (Markdown) | Low (Markdown) |
| **Code Base** | ~2000 lines | ~5000 lines |
| **MCP Dependency** | Optional | None (CLI-first) |

**Key Difference**:
- OpenClaw: Tools (TS) + Skills (CLI)
- FastReAct: Skills (CLI) primarily, Tools minimal

---

## Simplicity vs Features Trade-off

### The Question

**"Should we add more core tools?"**

### The Analysis

**Adding Core Tools**:
- ❌ Increases codebase (+300-500 lines per tool)
- ❌ Adds dependencies (httpx, pillow, schedule, etc.)
- ❌ Increases maintenance burden
- ❌ Breaks "Nano" philosophy
- ❌ Makes testing more complex

**Using exec + Skills**:
- ✅ Keeps codebase small
- ✅ No additional dependencies
- ✅ Leverages existing tools (curl, jq, etc.)
- ✅ Maintains "Nano" philosophy
- ✅ Easy to test and debug

### The Decision

**FastReAct chooses**: Minimal core + rich Skills

> "Less code, more power through bash."

---

## The exec Tool Advantage

### Exec Can Replace Most Specialized Tools

#### HTTP Requests (No http_tool needed)

```bash
# GET
curl -s https://api.example.com

# POST
curl -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' https://api.example.com
```

#### Web Search (No search_tool needed)

```bash
# DuckDuckGo
curl -s "https://duckduckgo.com/?q=query" | grep results

# ddgr (if installed)
ddgr query --json
```

#### JSON Processing (No json_tool needed)

```bash
# Parse and pretty-print
echo '{"name":"test"}' | jq .

# Extract field
curl -s https://api.example.com | jq '.data[0].name'
```

#### Database Operations (No database_tool needed)

```bash
# SQLite query
sqlite3 database.db "SELECT * FROM users WHERE age > 18"
```

#### Image Processing (No image_tool needed)

```bash
# Resize
convert input.jpg -resize 800x600 output.jpg

# Get info
identify input.jpg
```

#### Git Operations (No git_tool needed)

```bash
# Status
git status

# Commit
git add . && git commit -m "message"
```

---

## When to Use What

### Decision Tree

```
Need functionality?
  ↓
Can it be done with bash commands?
  ├─ Yes → Use exec tool in a Skill
  └─ No ↓
      Does it need state management or complex protocol?
        ├─ Yes → Use MCP server
        └─ No → Reconsider if it's needed
```

### Guidelines

**Use exec Tool When**:
- ✅ Functionality available as bash command
- ✅ Quick prototyping
- ✅ Simple data processing
- ✅ System operations

**Use MCP Servers When**:
- ✅ Need state management (databases)
- ✅ Complex protocols (SSH, browsers)
- ✅ Cross-language integration
- ✅ Persistent connections

**Hybrid Approach** (Recommended):
- Use exec for simple operations
- Use MCP for complex integrations
- Skills can combine both

---

## Architectural Decisions

### 1. Brain-Body Separation

**Core (The Brain)**: Pure intent generator, stateless reasoning
- Location: `src/fastreact/core/react.py`
- Responsibility: Generate THOUGHTs and TOOL_CALLs

**Agent (The Body)**: Loop control, tool execution, safety
- Location: `src/fastreact/agent.py`
- Responsibility: Execute tools, monitor context

**FORBIDDEN**: Core executing tools, Agent generating reasoning

---

### 2. Event-Driven Protocol

**All communication via AgentEvent stream**:
- NO callbacks
- NO StreamChunk
- NO direct event emission

**Unified event types**:
- SESSION_START, THINK, TOOL_CALL, TOOL_RESULT, STEP_END, SESSION_END

---

### 3. Multi-tenant Isolation

**Gateway Adapter** (Single-Tenant):
- All users share workspace: `workspaces/default/`
- Use case: Personal development, testing

**Feishu Adapter** (Multi-Tenant):
- Each user has isolated workspace: `/var/fastreact/tenants/feishu/{user_key}/`
- Use case: Enterprise deployment, SaaS

---

## Future Direction

### Commitments

1. **4 Core Tools**: Will never increase beyond 4
2. **exec Tool**: Will remain universal and powerful
3. **Skills Ecosystem**: Will continue growing
4. **MCP Support**: Will continue improving

### Not Doing

- ❌ Adding more core tools (http_tool, search_tool, etc.)
- ❌ Wrapping bash commands in Python tools
- ❌ Duplicating functionality available via exec

### Focus Areas

- ✅ Improving Skills (better patterns, examples)
- ✅ Enhancing MCP (better isolation, error handling)
- ✅ Documentation (tutorials, best practices)
- ✅ Developer Experience (easier skill creation)

---

## Recommended Skills (8 Core Skills)

Based on the "exec is enough" philosophy:

1. **HTTP Operations** - curl commands
2. **Web Search** - ddgr/curl commands
3. **JSON Processing** - jq commands
4. **Database Operations** - sqlite3 commands
5. **Image Processing** - ImageMagick commands
6. **Git Operations** - git commands
7. **Scheduled Tasks** - crontab commands
8. **Advanced File Operations** - find/xargs commands

**All using exec tool + bash commands.**

---

## Conclusion

**FastReAct Nano's Correct Approach**:

```
Minimal core (4 tools) + Rich Skills (unlimited) + exec (universal)
```

**Core Value**:
- ✅ Maintain "Nano" characteristics
- ✅ Unlimited extension capability
- ✅ Zero-code integration
- ✅ Community-friendly

**This is the true "Nano" + "Powerful" combination!**

---

**Author**: FastReAct Team
**Design Philosophy**: Minimal core, rich ecosystem
**Promise**: 4 core tools will never increase
**Last Updated**: 2025-02-27
