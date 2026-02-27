# FastReAct Nano - Development Rules

**Version**: 2.4.2
**Core Principle**: Platform MUST support SKILL and MCP extensions

---

## Architecture Iron Rules (CRITICAL)

### 0. Platform Core Principle ⚠️ FUNDAMENTAL

**FastReAct Nano is an Agent Platform, not just a chatbot**

- ✅ All features MUST work with SKILL system
- ✅ All features MUST work with MCP tools
- ✅ Gateway: Single-tenant mode (`workspaces/default/`)
- ✅ Feishu: Multi-tenant mode (`/var/fastreact/tenants/feishu/{user_key}/`)
- ❌ NEVER bypass SKILL system
- ❌ NEVER hardcode tools (use MCP instead)

**Documentation**:
- Skills: `docs/SKILLS_AND_MCP.md`
- MCP: `docs/MCP_CALLING_MECHANISM.md`
- Multi-tenant: `docs/MULTITENANT_GUIDE.md`

---

### 1. Brain-Body Separation

**Core (The Brain)**: Pure intent generator, stateless reasoning
- Location: `src/fastreact/core/react.py`
- FORBIDDEN: Executing tools, checking safety, managing state

**Agent (The Body)**: Loop control, tool execution, safety, context
- Location: `src/fastreact/agent.py`
- FORBIDDEN: Generating reasoning (that's Core's job)

---

### 2. Event-Driven Protocol

**ALL communication via `AgentEvent` stream**:
- NO callbacks
- NO StreamChunk
- NO direct event emission

**Event Types**: SESSION_START, THINK, TOOL_CALL, TOOL_RESULT, STEP_END, SESSION_END

---

### 3. Modular Layering

**Upper layers use public APIs only**:
- FORBIDDEN: Importing `internal.py`
- FORBIDDEN: Accessing `_private` attributes cross-module
- FORBIDDEN: CLI accessing `Core._private`, Agent accessing `LLM._http_pool`

---

### 4. Stateless Orchestration

**Session state persisted to `memory.json` after each tool execution**
- Failure recovery via SESSION_RESUME mechanism
- No state held only in memory during long-running tasks

---

## Ironclad Backend Features

### 1. Infinite Loop Protection 🔴

**Location**: `src/fastreact/agent.py:677-693`

**Hard limit: 25 iterations**

```python
iteration_count = 0
max_iterations = 25

while True:
    iteration_count += 1
    if iteration_count > max_iterations:
        yield AgentEvent.session_end(session_id, "[STOPPED] Max iterations reached")
        return
```

**Tests**: 3/3 passing

---

### 2. JSON Parsing Robustness 🟡

**Location**: `src/fastreact/providers/litellm.py:319-383`

**5-level cascading repair strategy**

**Tests**: 11/11 passing

---

### 3. Multi-turn Dialog Memory 🔴

**Location**: `src/fastreact/adapters/gateway.py`

**History tracking with automatic pruning (max 50 turns)**

**Tests**: 3/3 passing

---

### 4. MCP Auto-Reconnect 🔴

**Location**: `src/fastreact/mcp/manager.py`

**Automatic reconnection with retry logic (max 3 attempts)**

**Tests**: 3/3 passing

---

### 5. MCP Zombie Resurrection 🟢

**Location**: `src/fastreact/mcp/manager.py`

**Automatic detection and resurrection of crashed MCP servers**

**Tests**: 6/6 passing

**Test Coverage Summary**: 26/26 passing (100%)

---

## Cross-Platform Rules

### Path Handling

**ALWAYS**: `pathlib.Path`, `Path.cwd()`, `Path / "subdir"`

**FORBIDDEN**: Hardcoded "C:\\", "/Users/", "./" relative paths

### File Encoding

**ALWAYS**: `encoding='utf-8'` for file I/O

### No Emoji Policy

**Use text markers**: `[OK]`, `[ERROR]`, `[WARNING]`, `[INFO]`, `[DONE]`

**FORBIDDEN**: Unicode emojis (cause Windows encoding, httpx UTF-8 errors)

**Examples**:
```python
# CORRECT
config_path = Path.cwd() / "config.json"
with open(path, 'r', encoding='utf-8') as f:
    print("[OK] Config loaded")

# AVOID
config_path = "./config.json"
print("Config loaded")  # No status indicator
```

---

## Tool System Philosophy

### Core Principle

**4 core tools + infinite Skills + exec universal tool**

**Core Tools** (never increasing):
- exec_tool - Universal shell command execution
- read_file - Read file contents
- write_file - Write/create files
- edit_file - Edit files (string replacement)

### Best Practices

**Use exec tool when**:
- Functionality available as bash command
- Quick prototyping
- Simple data processing

**Use MCP servers when**:
- Need state management (databases)
- Complex protocols (SSH, browsers)
- Cross-language integration

**Documentation**: `docs/PLATFORM/TOOLS_AND_EXTENSIONS.md`

---

## Development Quick Reference

### Backend Testing

```bash
# All tests
python3 run_tests.py all

# Unit only
python3 run_tests.py unit

# Integration tests
python3 run_tests.py integration

# Specific test
pytest tests/unit/test_config.py -v

# With coverage
pytest tests/ --cov=src/fastreact --cov-report=html
```

### Frontend Development

```bash
cd fastreact-nano-web
npm install
npm run dev    # localhost:3000
npm run build
npm start
```

### Code Quality

```bash
black src/ tests/
ruff check src/ tests/ --fix
mypy src/

# All quality checks (run before commit)
black src/ tests/ && ruff check src/ tests/ --fix && mypy src/
```

---

## Configuration Pattern

**Standard `@dataclass` with `from_env()` support**:

```python
from dataclasses import dataclass
import os

@dataclass
class LLMConfig:
    model: str = "gpt-4o-mini"
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            model=os.getenv("FASTRACT_MODEL", cls.model),
            api_base=os.getenv("FASTRACT_API_BASE", cls.api_base),
            api_key=os.getenv("FASTRACT_API_KEY", cls.api_key),
            temperature=float(os.getenv("FASTRACT_TEMPERATURE", cls.temperature)),
            max_tokens=int(os.getenv("FASTRACT_MAX_TOKENS", cls.max_tokens)),
        )
```

**Priority Order** (high to low):
1. Constructor parameters
2. Config file (`~/.fastreact/config.json`)
3. Environment variables (`FASTRACT_*`)
4. Defaults (in `@dataclass`)

---

## Critical Rules Summary

### FORBIDDEN

- ❌ Implementing features that cannot be extended via SKILL
- ❌ Hardcoding external integrations (use MCP instead)
- ❌ Breaking SKILL auto-selection
- ❌ Breaking MCP tool discovery
- ❌ Mixing user data in multi-tenant mode
- ❌ Adding more core tools (stay at 4)
- ❌ Using emojis in code/output

### REQUIRED

- ✅ Keep 4 core tools minimal
- ✅ Use exec tool for simple operations
- ✅ Use MCP for complex integrations
- ✅ Follow Brain-Body separation
- ✅ Use AgentEvent protocol
- ✅ Maintain multi-tenant isolation
- ✅ Use pathlib for paths
- ✅ Use UTF-8 encoding
- ✅ Use text markers ([OK], [ERROR])

---

## Documentation

**Where to put documentation**:

| Location | For What |
|----------|----------|
| **Root (`*.md`)** | Essential user-facing docs only (max 10 files) |
| **`docs/`** | Feature docs, guides, reference material |
| **`docs_archive/`** | Historical, sprint reports, temporary notes |

**Before creating new documentation**:
1. Check `docs/DOCS_INDEX.md` for similar topics
2. UPDATE existing doc instead of creating new one
3. For temporary/process docs → use `docs_archive/sprints/`

---

## System Status

### Backend
- ✅ Infinite loop protection (25 iterations)
- ✅ JSON parsing robustness (5-level repair)
- ✅ Multi-turn dialog memory (50 turns)
- ✅ MCP auto-reconnect (3 retries)
- ✅ MCP zombie resurrection (automatic)
- ✅ 26/26 tests passing (100%)

### Frontend
- ✅ Unified theme (6 themes)
- ✅ Background mesh effect
- ✅ Navigation bar integrated
- ✅ Ctrl+Enter to send
- ✅ Build passing

### Overall
- **Status**: Phase 1.5 Complete
- **Quality**: Ironclad + Professional
- **Ready for**: Production deployment

---

**Maintainer**: FastReAct Team
**Last Updated**: 2025-02-27
**Version**: 2.4.2
**Phase**: 1.5 Complete + Frontend Polish
