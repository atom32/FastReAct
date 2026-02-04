# FastReAct Development Log

This file contains the chronological development history of FastReAct. For current rules and constraints, see [CLAUDE.md](CLAUDE.md).

---

## 2026-02-05: Milestone - Strategic Expansion to Real-World Tools (GitHub)

### Objective
Validate SimpleMCP-Stdio driver architecture against a production third-party MCP server (GitHub), enabling FastReAct to submit issues about its own refactoring work.

### Strategy
- **Security**: GitHub PAT via .env, never hardcoded
- **Architecture**: Multi-server concurrent scheduling via SimpleMCP-Stdio
- **Validation**: Self-consistency test (agent documents its own work)
- **Transport**: stdio isolation layer (compliant with Transport Layer Iron Rule)

### Implementation Phase

**Configuration Files Created**:
1. `.env.example` - Added `GITHUB_PERSONAL_ACCESS_TOKEN` and `GITHUB_DEFAULT_REPO`
2. `config.github_mcp.json` - Template configuration for GitHub MCP server
3. `docker-compose.yml` - Updated to inject GitHub PAT into containers

**Documentation Created**:
1. `GITHUB_MCP_INTEGRATION.md` - Complete integration guide
   - Architecture diagram
   - Configuration steps
   - Available tools (15+ GitHub operations)
   - Usage examples (CLI, programmatic, code search)
   - Iron Rule compliance verification
   - Troubleshooting guide
   - Security considerations

**Testing Infrastructure**:
1. `test_github_mcp.py` - Comprehensive test suite
   - Connection validation
   - Tool discovery
   - Schema extraction
   - Optional tool call test

**Architecture Compliance**:
- [Transport Layer Iron Rule] - Uses SimpleMCP-Stdio (no MCP SDK, zero anyio)
- [Stateless Orchestration] - Idempotent GitHub API operations
- [Cross-Platform] - pathlib usage throughout

### Expected GitHub MCP Tools

**Repository Operations**:
- `search_repositories`, `create_or_update_file`, `get_file_contents`, `search_code`

**Issue Management**:
- `create_issue`, `update_issue`, `search_issues_and_prs`, `add_comment`

**Pull Request Operations**:
- `create_pull_request`, `update_pull_request`, `review_pull_request`, `merge_pull_request`

### Next Steps

**Phase 1: Connection Test** (✅ COMPLETE)
- User provided GitHub PAT
- Connected successfully to GitHub MCP server
- 26 tools loaded and visible
- Bug fix: Tool wrapper now sets correct `self.name`

**Phase 2: Self-Consistency Test** (✅ COMPLETE)
- Agent successfully created GitHub issues:
  - Issue #1: "Test GitHub MCP Integration"
  - Issue #2: "Test GitHub MCP Integration" (with body)
- GitHub MCP integration verified working

**Phase 3: Advanced Features** (Ready)
- Search code in FastReAct repo
- Create PR for new features
- Comment on existing issues

### Bug Fixes During Integration

**Issue**: Agent couldn't see GitHub MCP tool names
- **Root Cause**: Tool wrappers used class name instead of actual tool name
- **Fix**: Added `self.name = tool_name` in all MCP wrapper classes
- **Result**: Agent now correctly identifies `create_issue`, `create_pull_request`, etc.

**Issue**: Multi-line input trigger confusing
- **Root Cause**: Prompt showed `>>>` but only `"""` triggered multi-line mode
- **Fix**: Added `>>>` as alternative trigger
- **Result**: More intuitive multi-line input

---

## 2026-02-04: Integration Test Suite & TODO #15 Completion

### Milestone Achievement
FastReAct has completed the transition from "fragile prototype" to "robust system" with all 4 integration tests passing (1.00/1.00 on Test 4).

### TODO #15: Persistent Embedding Cache with SQLite

**Core Implementation**:
1. Auto-detect embedding dimension from model
2. SQLite dual-layer caching (in-memory LRU + persistent storage)
3. Model change detection on startup
4. Configuration fixes (device: cpu, vector_store: apsw)

**Integration Test Suite Results**:
- Test 1: Audit & Fix Loop (PASSED)
- Test 2: Context Stress Test (PASSED)
- Test 3: Brain Reload Test (PASSED)
- Test 4: Tool Graph & Dependency Test (PASSED - 1.00/1.00)

**Files Modified**:
- `src/fastreact/memory/embeddings.py`: Complete rewrite (+800 lines)
- `src/fastreact/core/engine.py`: Config fixes, dimension auto-detection
- `src/fastreact/context/config.py`: Model change callback support
- `src/fastreact/memory/__init__.py`: Exported create_model_change_callback

**Breaking Changes**:
- `embedding_dim` removed from config.json (now auto-detected)
- Vector store backend changed to "apsw" for Windows compatibility

**Git Commits**:
- `8198bdd` - feat: Complete TODO #15 - Persistent Embedding Cache with SQLite
- `7d93ee8` - test: Add comprehensive integration test suite with 4 tests

---

## 2026-02-04: Progress Feedback System & Encoding Fixes

### Overview
Implemented comprehensive progress feedback system for long-running tools across CLI, Gateway, and Web UI. Fixed Windows encoding issues by removing all emojis from codebase.

### Features Implemented

**Progress Feedback System**:
- DeepResearchEngine accepts `progress_callback` parameter
- Engine injects callback into tools
- REPL displays progress in dim cyan
- Gateway sends progress events via WebSocket
- Web UI displays progress with spinning icon

**Windows Console Encoding Fixes**:
- Removed ALL emojis from 9+ files
- Replaced with text markers: `[OK]`, `[ERROR]`, `[WARNING]`, etc.
- Fixed UnicodeEncodeError on Windows console

**Configuration Changes**:
- Web frontend port changed from 3000 to 3001

**Files Modified** (18 files):
- CLI: main.py, repl.py
- Core: engine.py, prompt_builder.py, callbacks.py, tool_display.py
- Tools: deep_research.py, fn_registry.py, calculator.py, edit_tool.py, http.py
- Gateway: server.py, streaming.py, websocket.py
- Scripts: run_gateway.py
- Web: package.json, lib/types.ts, components/chat/event-card.tsx

**API Changes**:
- `FastReAct.set_progress_callback(callback: Optional[Callable[[str], None]])`
- `FastReAct._progress_callback` attribute

**Services**:
- Gateway: http://localhost:8080
- Web UI: http://localhost:3001

---

