# FastReAct Development Rules & Constraints

This file contains the critical rules and constraints for FastReAct development. For chronological development history, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md).

---

## IMPORTANT: Architecture Iron Rules

### 1. Transport Layer Iron Rule
**All external MCP connections MUST go through `SimpleMCP-Stdio` isolation driver.**

**FORBIDDEN**: Directly importing official MCP SDK logic containing `anyio` into the main event loop.

**RATIONALE**: Official SDK's `anyio` conflicts with FastAPI's async event loop on Windows, causing graceful shutdown failures.

```python
# CORRECT:
from fastreact.mcp.protocol import SimpleMCPStdio
mcp_client = SimpleMCPStdio(server_command="...")

# FORBIDDEN:
from mcp import ClientSession, StdioServerParameters
# This imports anyio and breaks the main event loop
```

### 2. Stateless Orchestration Rule
**Agent task execution MUST be idempotent and recoverable via `memory.json`.**

**REQUIREMENTS**:
- Session state persisted to `memory.json` after each tool execution
- Failure recovery via `SESSION_RESUME` mechanism
- No state held only in memory during long-running tasks

**RATIONALE**: Prevents task interruption from causing complete state loss.

### 3. Cross-Platform File System Rule
**All path operations MUST use `pathlib.Path`, never hardcoded slashes.**

**REQUIREMENTS**:
- Use `Path.cwd()` for current directory
- Use `Path /` operator for path joining
- Never use `"C:\\"` or `"/Users/"` literals
- Always specify `encoding='utf-8'` for file I/O

**RATIONALE**: Ensures semantic consistency between Windows host and Docker containers.

### 4. Modular Architecture Rule (NO Layer Penetration)
**模块必须保持独立，不允许层级渗透。**

**REQUIREMENTS**:
- 上层模块只能通过**公开API**访问下层模块
- 禁止直接导入下层模块的`internal.py`或私有属性
- 禁止跨层直接访问内部状态（`_private`属性）
- 每个模块应该有清晰的边界和接口

**FORBIDDEN**:
```python
# CLI直接访问core的私有属性
from fastreact.core.engine import ReActEngine
engine._context._metrics.total_tokens  # BAD - 层级渗透

# core直接访问context的内部实现
from fastreact.context.internal import _InternalState  # BAD - 跨层访问

# tools直接修改llm的内部状态
from fastreact.llm.driver import LLMDriver
driver._client._http_pool  # BAD - 越过封装边界
```

**CORRECT**:
```python
# 通过公开API访问
from fastreact.context import ContextMonitor
monitor = ContextMonitor(context_window=40960)
usage = monitor.get_progress_bar()  # GOOD - 使用公开接口

# 通过构造函数注入依赖
engine = ReActEngine(
    context_config=config,  # GOOD - 依赖注入
    llm_driver=driver
)

# 通过方法调用而非直接访问
result = agent.run_async(query)  # GOOD - 封装边界
```

**RATIONALE**:
- 保持模块独立性和可测试性
- 便于重构内部实现而不影响上层
- 遵循依赖倒置原则（依赖抽象而非具体实现）

**CHECKLIST**:
- [ ] 上层不导入下层`internal.py`
- [ ] 不访问`_private`属性（跨模块）
- [ ] 使用公开API而非直接访问内部状态
- [ ] 依赖通过构造函数注入，而非直接import

---

## IMPORTANT: No Emoji Policy

**CRITICAL**: Do NOT use emojis in code files. This causes:
- Windows console encoding errors
- UTF-8 encoding failures in httpx
- JSON serialization errors

**Always Use Text Markers Instead**:
- `[OK]`, `[ERROR]`, `[WARNING]`, `[INFO]`
- `[Query]`, `[Research]`, `[Structure]`, `[Findings]`
- `[Loop]`, `[Think]`, `[Action]`, `[Observe]`

---

## IMPORTANT: Documentation Management

### Documentation Principles

**Core Guidelines**:
1. **No emojis in docs** - Same as code, use text markers: `[OK]`, `[ERROR]`, `[WARNING]`
2. **Single source of truth** - Keep one canonical doc per topic
3. **Archive historical docs** - Move old docs to `docs_archive/` instead of deleting
4. **Update index** - Maintain `DOCS_INDEX.md` when adding/modifying docs
5. **REUSE before CREATE** - Always check if existing doc can be updated instead of creating new

### Documentation Location Rules

**CRITICAL: Where to put documentation**

**Root Directory (minimal, essential only)**:
- `README.md` - Project overview
- `DOCS_INDEX.md` - Documentation navigation
- `CLAUDE.md` - Development rules (this file)
- `CHANGELOG.md` - Version history
- `INSTALLATION.md` - Installation guide
- `CLI_TROUBLESHOOTING.md` - Common issues

**FORBIDDEN locations**:
- `/docs` directory - **DEPRECATED**, use `docs_archive/old_docs_*/` instead
- Root directory - Only essential docs, avoid clutter

**Where new docs go**:
1. **Check first** - Look at `DOCS_INDEX.md` for similar topics
2. **Update existing** - If similar doc exists, UPDATE it instead of creating new
3. **Create only if necessary** - When truly new topic, add to root with clear name
4. **Archive promptly** - Move outdated docs to `docs_archive/`

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

### What Belongs Where

**Root Directory** (keep minimal):
- User-facing guides (INSTALLATION, TROUBLESHOOTING)
- Feature documentation (IEL.md, SESSION_RESUME.md)
- Development rules (CLAUDE.md, DEVELOPMENT_LOG.md)
- Navigation (DOCS_INDEX.md, README.md)

**docs_archive/** (historical reference only):
- `bugfixes/` - Bug fix records (keep 30 days)
- `sprints/` - Sprint summaries (keep permanently)
- `temp/` - Temporary analysis (keep 7 days)
- `old_docs_*/` - Deprecated docs directories

**Delete (avoid completely)**:
- Duplicate content
- Empty placeholder docs
- Outdated quickstarts
- Process docs that belong in git history

### Quality Checklist

Before committing documentation:
- [ ] No emojis (use `[OK]`, `[ERROR]`, etc.)
- [ ] UTF-8 encoding (for Chinese content)
- [ ] Links work (test `./` relative links)
- [ ] No hardcoded paths (use `pathlib` or `config`)
- [ ] Cross-platform compatible (no Windows/Mac specific paths)
- [ ] Updated `DOCS_INDEX.md` if needed
- [ ] Checked for duplicates (reused existing doc if possible)

---

## Cross-Platform Compatibility

### Path Handling

**Always use `pathlib.Path`**:
```python
from pathlib import Path

config_path = Path("config.json")
workspace = Path.cwd() / ".fastreact"
```

**Never hardcode paths**:
```python
# AVOID THESE:
config_path = "D:\\FastReAct\\config.json"  # Windows only
config_path = "/Users/user/config.json"    # Mac only
```

### File Encoding

**Always specify UTF-8**:
```python
# CORRECT:
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# AVOID:
with open(path, 'r') as f:
    content = f.read()
```

### Version Management

**Single source of truth**: `src/fastreact/__init__.py`

```python
__version__ = "1.1.0"
```

**Read dynamically in other files**:
- `pyproject.toml`: `dynamic = ["version"]` with `[tool.setuptools.dynamic]`
- `setup.py`: `get_version()` function
- CLI: `from fastreact import __version__`

---

## Code Conventions

### Progress Callbacks

When implementing long-running tools:
1. Add optional `progress_callback` parameter
2. Check existence before calling
3. Use concise messages with category tags

```python
def __init__(self, progress_callback: Optional[Callable[[str], None]] = None):
    self._progress_callback = progress_callback

def _report_progress(self, message: str):
    if self._progress_callback:
        self._progress_callback(f"[Category] {message}")
```

### Error Handling

**Use text markers, not emojis**:
```python
# CORRECT:
print("[OK] Success")
print("[ERROR] Failed")
print("[WARNING] Warning")

# AVOID:
print("✅ Success")    # Windows encoding issues
print("❌ Failed")     # Cross-platform problems
```

---

## Testing

### Test File Location Rules

**CRITICAL: Where to put test code**

**Designated locations**:
- `tests/` - Unit tests and integration tests (pytest style)
- `examples/` - Demo scripts and usage examples
- `scripts/` - Utility scripts (not tests, but development tools)

**FORBIDDEN locations**:
- Root directory - No `test_*.py` or `demo_*.py` files in root
- Scattered test files - Keep tests organized in `tests/`

### Before Creating New Test Files

**Decision Tree**:
```
Need to test something?
    ↓
Check tests/ for similar test files
    ↓
    Found? ──Yes→ MODIFY existing test
    ↓
     No
    ↓
Is it a demo/showcase?
    ↓
    Yes→ Put in examples/ with clear name
    ↓
    No
    ↓
Create in tests/ with test_*.py naming
```

### Test File Organization

**tests/ directory structure**:
```
tests/
├── test_core/           # Core functionality tests
│   ├── test_engine.py
│   ├── test_react_agent.py
│   └── test_context_monitor.py
├── test_integration/    # Integration tests
│   ├── test_mcp_integration.py
│   └── test_cli.py
└── test_utils/          # Test utilities
    └── fixtures.py
```

**examples/ directory structure**:
```
examples/
├── demo_task_chaining.py
├── demo_session_resume.py
└── demo_auto_reflection.py
```

### Naming Conventions

**Test files** (in `tests/`):
- Unit tests: `test_<module>.py` (e.g., `test_engine.py`)
- Integration tests: `test_<feature>_integration.py`
- Use descriptive names that indicate what's being tested

**Example files** (in `examples/`):
- Demos: `demo_<feature>.py` (e.g., `demo_task_chaining.py`)
- Showcase specific functionality
- Include comments explaining usage

### Quick Verification

```bash
# Verify code quality
python scripts/quick_check.py

# Expected output:
# [SUCCESS] No issues found!
# Code is clean and cross-platform compatible
```

### Version Consistency

```bash
# Check version consistency
python test_version_consistency.py

# Expected output:
# [SUCCESS] All versions are consistent!
# Current version: 1.1.0
```

---

## Important Reminders

1. **No emojis** - Use text markers everywhere (code, docs, output)
2. **No hardcoded paths** - Use pathlib and configuration
3. **UTF-8 encoding** - Specify explicitly for file operations
4. **Version in one place** - Only `__init__.py` defines `__version__`
5. **Update docs index** - Keep `DOCS_INDEX.md` in sync
6. **Archive, don't delete** - Move old docs to `docs_archive/`
7. **REUSE before CREATE** - Update existing docs/tests before creating new ones
8. **Proper locations** - Docs in root, tests in `tests/`, examples in `examples/`

---

**For chronological development history, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)**
