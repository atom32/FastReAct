# FastReAct Nano - Development Rules & Standards

**Version**: 2.4.2
**Last Updated**: 2025-02-19
**Status**: Phase 1.5 Complete + Frontend Polish + Project Restructure

**Core Principle**: FastReAct Nano is an Agent Platform that MUST support SKILL and MCP extensions

---

## System Architecture

### Frontend: Next.js 14 + React

**Location**: `fastreact-nano-web/`

**Tech Stack**:
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- shadcn/ui components
- WebSocket (real-time communication)

**Key Pages**:
- `/` - Chat interface (main)
- `/admin` - Admin dashboard (config, sessions, metrics)
- `/marketplace` - MCP tool marketplace

**Frontend Rules**:
- Use FastReAct theme variables (see Theme System below)
- WebSocket for real-time communication with Gateway
- Ctrl+Enter to send messages (standard UX)
- All pages use background mesh effect
- Navigation bar unified across all pages

**Development**:
```bash
cd fastreact-nano-web
npm install
npm run dev    # Development server on localhost:3000
npm run build  # Production build
npm start      # Production server
```

### Backend: Python FastReAct Core

**Location**: `fastreact-nano/src/fastreact/`

**Tech Stack**:
- Python 3.11+
- FastAPI (Gateway adapter)
- WebSocket (real-time events)
- LiteLLM (LLM provider abstraction)
- MCP (Model Context Protocol)

**Key Components**:
- `core/` - ReAct loop engine (Brain)
- `agent.py` - Agent orchestration (Body)
- `providers/` - LLM providers (litellm, etc.)
- `mcp/` - MCP tool management
- `adapters/gateway.py` - FastAPI WebSocket server

**Architecture Pattern**: Brain-Body Separation (see Iron Rules below)

---

## Architecture Iron Rules (Critical)

### 0. Platform Core Principle ⚠️ FUNDAMENTAL

**FastReAct Nano is an Agent Platform that MUST support SKILL and MCP**

**Platform Definition**:
- FastReAct is NOT just a chatbot or Q&A system
- It is an **extensible AI Agent platform** with two core extension mechanisms:
  1. **SKILL** - Cognitive patterns and task strategies (See `docs/SKILLS_AND_MCP.md`)
  2. **MCP (Model Context Protocol)** - External tool integration (See `docs/MCP_CALLING_MECHANISM.md`)

**MANDATORY Requirements**:
- ✅ **All features MUST be designed to work with SKILL system**
  - SKILL = Structured Prompt + Tool Policy + Reasoning Pattern
  - Location: `skills/builtin/` (global), `{user_workspace}/skills/` (user-specific)
  - Skills can be auto-selected based on query content

- ✅ **All features MUST be compatible with MCP tools**
  - MCP = External tool integration via STDIO (JSON-RPC protocol)
  - Location: `mcp_servers/config/` (server definitions)
  - MCP servers run as isolated subprocesses
  - Support 3 isolation modes: shared, per_user, lazy_per_user

**Deployment Architecture**:
- **Gateway Adapter** (`src/fastreact/adapters/gateway.py`): **Single-Tenant Mode**
  - All users share workspace: `workspaces/default/`
  - Use case: Personal development, testing, PoC
  - Configuration: `paths.gateway_workspace`

- **Feishu Adapter** (`src/fastreact/adapters/feishu_sdk.py`): **Multi-Tenant Mode**
  - Each user has isolated workspace: `/var/fastreact/tenants/feishu/{user_key}/`
  - Use case: Enterprise deployment, SaaS applications
  - Configuration: `paths.feishu_workspace_base`
  - User identification: `user_key = "feishu:{user_id}"`

**SKILL and MCP Integration**:
```python
# Agent automatically loads skills and MCP tools
agent = Agent(
    multitenant=False,  # Gateway: single-tenant
    # or
    multitenant=True,   # Feishu: multi-tenant
    base_workspace="..."
)

# Skills are loaded from:
# 1. User workspace skills (multi-tenant only)
# 2. Global skills: skills/builtin/
# 3. Community skills: skills/community/

# MCP servers are loaded from:
# 1. User mcp_config.json (multi-tenant only)
# 2. mcp_servers/config/per_user.json (user-specific servers)
# 3. mcp_servers/config/shared.json (global servers)
```

**Development Rules**:
1. **NEVER bypass SKILL system** - Always design features that can be enhanced via skills
2. **NEVER hardcode tools** - Use MCP protocol for external integrations
3. **ALWAYS test with skills** - Verify features work when skills are loaded
4. **ALWAYS test with MCP** - Verify features work when MCP tools are available
5. **ALWAYS respect multi-tenant isolation** - Never leak user data in multi-tenant mode

**FORBIDDEN**:
- ❌ Implementing features that cannot be extended via SKILL
- ❌ Hardcoding external integrations (use MCP instead)
- ❌ Breaking SKILL auto-selection
- ❌ Breaking MCP tool discovery
- ❌ Mixing user data in multi-tenant mode

**Documentation**:
- SKILL system: `docs/SKILLS_AND_MCP.md`
- MCP integration: `docs/MCP_CALLING_MECHANISM.md`
- Multi-tenant guide: `docs/MULTITENANT_GUIDE.md`
- Directory structure: `docs/DIRECTORY_STRUCTURE.md`

---

### 1. Brain-Body Separation
- **Core (The Brain)**: Pure intent generator, stateless reasoning
  - Location: `src/fastreact/core/react.py`
  - Responsibility: Generate THOUGHTs and TOOL_CALLs only
  - FORBIDDEN: Executing tools, checking safety, managing state

- **Agent (The Body)**: Loop control, tool execution, safety, context
  - Location: `src/fastreact/agent.py`
  - Responsibility: Execute tools, monitor context, persist state
  - FORBIDDEN: Generating reasoning (that's Core's job)

### 2. Event-Driven Protocol
- All communication via `AgentEvent` stream (AsyncIterator[AgentEvent])
- NO callbacks, NO StreamChunk, NO direct event emission
- Unified event types: SESSION_START, THINK, TOOL_CALL, TOOL_RESULT, STEP_END, SESSION_END

### 3. Modular Layering (No Penetration)
- Upper layers use public APIs only
- FORBIDDEN: Importing `internal.py`, accessing `_private` attributes cross-module
- FORBIDDEN: CLI accessing `Core._private`, Agent accessing `LLM._http_pool`

### 4. Stateless Orchestration
- Session state persisted to `memory.json` after each tool execution
- Failure recovery via SESSION_RESUME mechanism
- No state held only in memory during long-running tasks

---

## Ironclad Backend Features (Phase 1.5)

### 1. Infinite Loop Protection 🔴 Critical
**Location**: `src/fastreact/agent.py:677-693`

**Problem**: Agent could loop infinitely if task too complex
**Solution**: Hard limit熔断机制 (circuit breaker)

```python
iteration_count = 0
max_iterations = self._config.react.max_iterations if self._config else 25

while True:
    iteration_count += 1
    if iteration_count > max_iterations:
        yield AgentEvent.session_end(
            session_id,
            f"[STOPPED] Maximum iteration limit ({max_iterations}) reached"
        )
        return
```

**Tests**: 3/3 passing

### 2. JSON Parsing Robustness 🟡 Medium
**Location**: `src/fastreact/providers/litellm.py:319-383`

**Problem**: LLM JSON hallucination causes crashes
**Solution**: 5-level cascading repair strategy

```python
def _parse_function_args(self, arguments: str) -> dict:
    # Level 1: Standard parsing
    try: return json.loads(arguments)

    # Level 2: Fix missing quotes on keys
    try: return json.loads(re.sub(r'(\w+):', r'"\1":', arguments))

    # Level 3: Fix trailing commas
    try: return json.loads(re.sub(r',\s*}', '}', arguments))

    # Level 4: Fix single quotes
    try: return json.loads(arguments.replace("'", '"'))

    # Level 5: Combination of all fixes
    try: return json.loads(comprehensive_fix(arguments))

    return {}  # Safe fallback
```

**Tests**: 11/11 passing

### 3. Multi-turn Dialog Memory 🔴 Critical
**Location**: `src/fastreact/adapters/gateway.py`

**Problem**: Session doesn't maintain conversation history
**Solution**: History tracking with automatic pruning

```python
class Session:
    def __init__(self, ..., max_history: int = 50):
        self._history: list[dict] = []
        self._max_history = max_history

    def _update_history(self, user_query: str, assistant_response: str):
        self._history.append({"role": "user", "content": user_query})
        self._history.append({"role": "assistant", "content": assistant_response})

        # Auto-prune if too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
```

**Tests**: 3/3 passing

### 4. MCP Auto-Reconnect 🔴 Critical
**Location**: `src/fastreact/mcp/manager.py`

**Problem**: MCP connection loss = fatal error
**Solution**: Automatic reconnection with retry logic

```python
class MCPToolWrapper:
    async def execute(self, **kwargs):
        for attempt in range(self._max_retries):
            try:
                return await self._mcp_client.call_tool(...)

            except RuntimeError as e:
                if "not connected" in str(e).lower():
                    if attempt < self._max_retries - 1:
                        await self._mcp_client.connect()
                        continue  # Retry

                return f"[MCP_ERROR] {e} (after {call_attempts} attempts)"
```

**Tests**: 3/3 passing

### 5. MCP Zombie Resurrection 🟢 Feature
**Location**: `src/fastreact/mcp/manager.py`

**Problem**: MCP server process crash = fatal error
**Solution**: Automatic detection and resurrection

```python
class MCPToolManager:
    def is_server_alive(self, server_name: str) -> bool:
        """Check if MCP server process is still alive"""
        client = self._servers.get(server_name)
        if client._process and client._process.returncode is not None:
            print(f"[WARNING] Zombie detected: '{server_name}' crashed")
            return False
        return True

    async def resurrect_server(self, server_name: str) -> bool:
        """Resurrect a crashed MCP server"""
        config = self._server_configs[server_name]

        # Close old connection, create new client, reconnect, re-register tools
        client = SimpleMCPClient(
            server_command=config["server_command"],
            server_args=config["server_args"],
        )
        await client.connect()

        # Re-register all tools
        tools = await client.list_tools()
        for tool_def in tools:
            await self._register_mcp_tool(server_name, tool_def, client)

        self._servers[server_name] = client
        return True
```

**Tests**: 6/6 passing

**Test Coverage Summary**:
- Infinite Loop Protection: 3 tests
- JSON Parsing Robustness: 11 tests
- Multi-turn Memory: 3 tests
- MCP Auto-Reconnect: 3 tests
- MCP Zombie Resurrection: 6 tests
- **Total: 26/26 passing (100%)**

---

## Frontend Theme System

**Location**: `fastreact-nano-web/app/globals.css`

**Theme Variables** (CSS Custom Properties):
```css
[data-theme="cyber-dark"] {
  --fr-bg-primary: #0a0e27;
  --fr-accent-primary: #8b5cf6;
  --fr-gradient-start: #8b5cf6;
  --fr-gradient-end: #06b6d4;
  /* ... more variables ... */
}
```

**Available Themes**:
1. **Cyber Dark** (default) - Purple/cyan, futuristic
2. **Midnight** - Blue variants, professional
3. **Solar Light** - Warm amber, bright
4. **Forest** - Green variants, natural
5. **Sunset** - Orange/pink, vibrant
6. **Matrix** - Green monochrome, hacker

**Usage in Components**:
```tsx
// Apply theme background
<div style={{ background: "var(--fr-bg-primary)" }}>

// Apply theme text
<span style={{ color: "var(--fr-text-primary)" }}>

// Apply gradient
<button style={{
  background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))"
}}>

// Apply glassmorphism
<div className="glass-panel" style={{ background: "var(--fr-bg-glass)" }}>
```

**Background Mesh Effect**:
```tsx
// Add to all pages for consistent visual depth
<div className="background-mesh" />
```

---

## Cross-Platform Rules

### Path Handling
- **ALWAYS**: `pathlib.Path`, `Path.cwd()`, `Path / "subdir"`
- **FORBIDDEN**: Hardcoded "C:\\", "/Users/", "./" relative paths

### File Encoding
- **ALWAYS**: `encoding='utf-8'` for file I/O

### No Emoji Policy
- Use text markers: `[OK]`, `[ERROR]`, `[WARNING]`, `[INFO]`, `[DONE]`
- **FORBIDDEN**: Unicode emojis (cause Windows encoding, httpx UTF-8 errors)

**Examples**:
```python
# CORRECT
config_path = Path.cwd() / "config.json"
with open(path, 'r', encoding='utf-8') as f:
    print("[OK] Config loaded")

# AVOID
config_path = "./config.json"
print("Config loaded")  # No status indicator
print("Success")  # No clear category
```

---

## Configuration Pattern

Standard pattern using `@dataclass` with `from_env()` support:

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
2. Config file (~/.fastreact/config.json or ./.fastreact/config.json)
3. Environment variables (FASTRACT_*)
4. Defaults (in @dataclass definition)

---

## Common Pitfalls (From Git History)

### Bug: Short-term Memory Loss (commit 83c5369)
**Problem**: LLM forgets previous responses, infinite loops in reasoning
**Fix**: Append assistant message to history on STEP_END
**Check**: `Agent.run_event_stream()` around line 258-271
```python
# After each step completes
if event.type == EventType.STEP_END:
    self._history.append({
        "role": "assistant",
        "content": event.content
    })
```

### Bug: Emoji Encoding Failures (commit fa73fd5)
**Problem**: Unicode emojis cause Windows console and httpx UTF-8 errors
**Fix**: Replace all emoji with text markers
**Check**: All user-facing output strings (CLI, logs, tool results)
```python
# WRONG
print("Success!")
print("Error!")

# CORRECT
print("[OK] Operation completed")
print("[ERROR] Operation failed")
```

### Bug: Hardcoded Paths (commit fa73fd5)
**Problem**: Paths like "C:/Users/admin/.fastreact" break on different machines
**Fix**: Use pathlib.Path with config search paths
**Check**: Test files, config loading, workspace initialization
```python
# WRONG
config_path = "C:/Users/admin/.fastreact/config.json"

# CORRECT
config_paths = [
    Path.cwd() / ".fastreact" / "config.json",
    Path.home() / ".fastreact" / "config.json",
]
config_path = next((p for p in config_paths if p.exists()), None)
```

### Bug: Agent._llm Access (commit 9e8c836)
**Problem**: Direct private attribute access breaks encapsulation
**Fix**: Use llm_config variable instead of adapter._core._llm
**Check**: Search for `adapter._core._llm` patterns
```python
# WRONG
model = adapter._core._llm.model

# CORRECT
model = agent.config.llm.model
```

### Bug: Infinite Agent Loop (Phase 1.5 Fix)
**Problem**: Agent could loop infinitely on complex tasks
**Fix**: Added iteration counter with hard limit (25 iterations)
**Check**: `src/fastreact/agent.py:677-693`
```python
iteration_count = 0
max_iterations = 25

while True:
    iteration_count += 1
    if iteration_count > max_iterations:
        yield AgentEvent.session_end(session_id, "[STOPPED] Max iterations reached")
        return
```

### Bug: JSON Hallucination Crashes (Phase 1.5 Fix)
**Problem**: Malformed LLM JSON output causes tool call failures
**Fix**: 5-level cascading JSON repair strategy
**Check**: `src/fastreact/providers/litellm.py:319-383`
```python
def _parse_function_args(self, arguments: str) -> dict:
    # Try 5 repair strategies before giving up
    # Level 1: Standard, Level 2: Fix quotes, Level 3: Fix commas,
    # Level 4: Fix quotes, Level 5: Combination
    return repair_json(arguments)
```

### Development Rule: Keep Project Clean
**Problem**: Generating test files and documentation scattered across project directories
**Rule**: Keep project folders clean and organized
**Check**: Before creating any file in project root or subdirectories
```bash
# WRONG - Don't create test files in project directories
/tmp/test_feature.py  # ❌ If testing, use /tmp/ or tests/
./my_test_script.py   # ❌ Use tests/ directory
./TEMP_REPORT.md      # ❌ Use docs/ or docs_archive/

# CORRECT - Use appropriate locations
tests/manual/test_feature.py           # Manual test scripts
tests/integration/test_feature.py      # Integration tests
/tmp/quick_test.py                     # Temporary throwaway tests
docs/FEATURE_REPORT.md                 # Feature documentation
docs_archive/TEMP_REPORT.md            # Archive temporary reports
```

**Guidelines**:
- **Test files**: Use `tests/` directory structure
- **Quick tests**: Use `/tmp/` for throwaway scripts
- **Documentation**: Use `docs/` for active docs, `docs_archive/` for history
- **Build artifacts**: Add to `.gitignore` (build/, dist/, *.egg-info/)
- **Never**: Create random .py, .md, .json files in project root

---

## Quick Reference

### Backend Testing
```bash
# All tests
python3 run_tests.py all

# Unit only (fast, no API required)
python3 run_tests.py unit

# Integration tests (may require API keys)
python3 run_tests.py integration

# Specific test file
pytest tests/unit/test_config.py -v

# With coverage
pytest tests/ --cov=src/fastreact --cov-report=html

# Phase 1.5 tests (Ironclad features)
pytest tests/unit/test_infinite_loop_protection.py
pytest tests/unit/test_json_parsing_robustness.py
pytest tests/unit/test_robustness.py
pytest tests/unit/test_zombie_resurrection.py
```

### Frontend Development
```bash
cd fastreact-nano-web

# Install dependencies
npm install

# Development server (localhost:3000)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Type checking
npm run type-check

# Linting
npm run lint
```

### Code Quality
```bash
# Backend
black src/ tests/
ruff check src/ tests/ --fix
mypy src/

# All quality checks (run before commit)
black src/ tests/ && ruff check src/ tests/ --fix && mypy src/
```

### Common Commands

**Backend**:
```bash
# Run agent query
fastreact "your query here" --model gpt-4o-mini

# Install development version
pip install -e ".[all]"

# Verify installation
python -c "from fastreact import Agent; print('[OK] Install OK')"

# Set API key
export FASTRACT_API_KEY=sk-xxx
export FASTRACT_MODEL=gpt-4o-mini

# Start Gateway server
python3 -m fastreact.adapters.gateway
# Or: uvicorn fastreact.adapters.gateway:create_gateway_app --host 0.0.0.0 --port 9000
```

**Frontend**:
```bash
# Start development server
cd fastreact-nano-web
npm run dev

# Build for production
npm run build
```

---

## Documentation Rules

### Where to Put Documentation

**Root Directory** (minimal, essential only):
- User-facing guides: README.md, GETTING_STARTED.md, USAGE.md
- Development rules: CLAUDE.md (this file)
- Navigation: DOCS_INDEX.md
- Release notes: RELEASE_NOTES.md

**docs/** (feature documentation):
- `docs/FIX_*.md` - Fix documentation
- `docs/PHASE_*_COMPLETE.md` - Phase completion reports
- `docs/FRONTEND_POLISH_COMPLETE.md` - Frontend improvements

**docs_archive/** (historical reference only):
- `development/` - Feature development history
- `testing/` - Test suite evolution
- `sprints/` - Sprint summaries and design docs
- `reports/` - Status reports and analyses

**tests/README.md**:
- Test suite documentation
- Current test status summary

### Before Creating New Documentation

**Decision Tree**:
```
Need to document something?
    ↓
Check DOCS_INDEX.md for similar topics
    ↓
    Found? ──Yes→ UPDATE existing doc
    ↓
     No
    ↓
Is it temporary/development process?
    ↓
    Yes→ Put in docs_archive/sprints/ or docs_archive/temp/
    ↓
    No
    ↓
Create in root with clear, descriptive name
Update DOCS_INDEX.md
```

**Quality Checklist**:
- [ ] No emojis (use `[OK]`, `[ERROR]`, etc.)
- [ ] UTF-8 encoding (for Chinese content)
- [ ] Links work (test `./` relative links)
- [ ] No hardcoded paths (use `pathlib` or config)
- [ ] Cross-platform compatible
- [ ] Updated DOCS_INDEX.md
- [ ] Checked for duplicates

---

## Version Management

**Single source of truth**: `src/fastreact/__init__.py`

```python
__version__ = "2.4.1"
```

**Read dynamically in other files**:
- `pyproject.toml`: `dynamic = ["version"]` with `[tool.setuptools.dynamic]`
- CLI: `from fastreact import __version__`

**DO NOT** duplicate version string in multiple files!

**Version History**:
- v2.4.1 (2025-02-19) - Phase 1.5 Complete + Frontend Polish
  - Infinite loop protection
  - JSON parsing robustness (5-level repair)
  - Multi-turn dialog memory
  - MCP auto-reconnect
  - MCP zombie resurrection
  - Frontend theme unification
  - Navigation bar integration
  - Ctrl+Enter to send behavior

- v2.3.0 (2025-02-16) - Gateway + Frontend Phase 2
  - Next.js 14 frontend
  - Admin dashboard
  - MCP marketplace
  - WebSocket real-time events

- v2.1.0 - Initial stable release

---

## Deployment

### Quick Start

**Backend (Gateway)**:
```bash
cd fastreact-nano
pip install -e ".[all]"

# Set API key
export FASTRACT_API_KEY=sk-xxx
export FASTRACT_MODEL=gpt-4o-mini

# Start Gateway
python3 -m fastreact.adapters.gateway
# Runs on http://0.0.0.0:9000
```

**Frontend**:
```bash
cd fastreact-nano-web
npm install
npm run dev
# Runs on http://localhost:3000
```

### Docker Deployment

**Multi-Stage Build Pattern**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS base-builder
WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[all]"

# Stage 2: Production
FROM python:3.11-slim AS production
COPY --from=base-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
CMD ["python", "-m", "fastreact.adapters.gateway"]
```

### Production Configuration

**Required Environment Variables**:
```bash
# LLM
FASTRACT_MODEL=gpt-4o-mini
FASTRACT_API_KEY=sk-xxx

# Multi-Tenant
FEISHU_MULTITENANT=true
FEISHU_BASE_WORKSPACE=/workspace

# Security
FASTRACT_MAX_FILE_SIZE=1048576
FASTRACT_EXEC_TIMEOUT=30
```

**Optional Features**:
```bash
# MCP Support
MCP_ENABLED=true

# Feishu Bot
FEISHU_ENABLED=true
FEISHU_APP_ID=xxx
FEISHU_APP_SECRET=xxx
```

---

## System Status

### Backend
- ✅ Infinite loop protection (hard limit: 25 iterations)
- ✅ JSON parsing robustness (5-level repair)
- ✅ Multi-turn dialog memory (max 50 turns)
- ✅ MCP auto-reconnect (max 3 retries)
- ✅ MCP zombie resurrection (automatic)
- ✅ 26/26 tests passing (100%)
- ✅ Gateway running (http://0.0.0.0:9000)

### Frontend
- ✅ Unified theme (6 themes)
- ✅ Background mesh effect
- ✅ Navigation bar integrated
- ✅ Ctrl+Enter to send
- ✅ Build passing
- ✅ Professional UI/UX

### Overall
- **Status**: Phase 1.5 Complete
- **Quality**: Ironclad + Professional
- **Ready for**: Production deployment

---

**Maintainer**: Claude Code + User
**Last Updated**: 2025-02-19
**Version**: 2.4.1
**Phase**: 1.5 Complete + Frontend Polish
