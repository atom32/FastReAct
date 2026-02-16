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

### Test Execution Requirements (CRITICAL)

**MANDATORY: All tests MUST run through the unified test suite**

**FORBIDDEN**: Creating standalone test scripts outside the pytest framework

**RATIONALE**:
- Ensure all tests are discoverable and runnable with a single command
- Prevents orphaned test scripts that break or become unmaintained
- Enables CI/CD integration and automated testing

**RULES**:
1. **Use pytest framework ONLY** - All tests must be pytest-compatible
2. **No standalone scripts** - Do NOT create `test_xxx.py` with `if __name__ == "__main__"`
3. **Use unified runner** - Run tests via `run_tests.py` or `pytest` command
4. **Follow test structure** - Organize in `tests/unit/` and `tests/integration/`
5. **Use conftest.py fixtures** - Leverage shared fixtures and configuration

**FORBIDDEN**:
```python
# FORBIDDEN - Standalone test script
#!/usr/bin/env python3
"""Test something"""
import sys
sys.path.insert(0, "src")

def test_feature():
    assert True

if __name__ == "__main__":
    test_feature()  # BAD - Not discoverable by pytest
```

**CORRECT**:
```python
# CORRECT - pytest-compatible test
import pytest
from fastreact import Feature

class TestFeature:
    """Test Feature functionality"""

    def test_basic_operation(self):
        """Test basic feature works"""
        feature = Feature()
        assert feature.works()

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async feature"""
        feature = Feature()
        result = await feature.async_work()
        assert result
```

**Test Execution**:
```bash
# Run all tests
python3 run_tests.py all

# Run unit tests only
python3 run_tests.py unit

# Run integration tests only
python3 run_tests.py integration

# Run specific test with pytest
pytest tests/unit/test_config.py::TestConfig::test_load -v

# Run tests with markers
pytest tests/ -m "not slow"  # Skip slow tests
pytest tests/ -m "not api"   # Skip tests requiring API
```

**Test File Location Rules**

**CRITICAL: Where to put test code**

**Designated locations**:
- `tests/unit/` - Unit tests (pytest style, fast, no external dependencies)
- `tests/integration/` - Integration tests (pytest style, may require fixtures)
- `examples/` - Demo scripts and usage examples (NOT tests, but demonstrations)
- `scripts/` - Utility scripts (not tests, but development tools)

**FORBIDDEN locations**:
- Root directory - No `test_*.py` or `demo_*.py` files in root
- Scattered test files - Keep tests organized in `tests/`
- Standalone test scripts with `if __name__ == "__main__"` - Use pytest instead

### Test File Organization

**tests/ directory structure**:
```
tests/
├── conftest.py              # pytest configuration, shared fixtures
├── README.md                # Test documentation
├── unit/                    # Unit tests (fast, no API)
│   ├── test_config.py       # Configuration loading
│   ├── test_tools.py        # Tool execution
│   └── test_react_core.py   # Core reasoning
└── integration/             # Integration tests
    ├── test_agent_mock.py   # Agent with mocked LLM
    ├── test_skills.py       # Skills integration
    └── test_e2e_real_api.py # E2E tests (marked @pytest.mark.api)
```

**Test Markers**:
- `@pytest.mark.unit` - Unit tests (fast, no external deps)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (> 1 second each)
- `@pytest.mark.api` - Requires real API key (optional, skip by default)
- `@pytest.mark.e2e` - End-to-end tests

### Before Creating New Test Files

**Decision Tree**:
```
Need to test something?
    ↓
Is it a unit test (single component, fast)?
    ↓
    Yes → Create in tests/unit/test_<module>.py
    ↓
    No
    ↓
Is it integration (multiple components)?
    ↓
    Yes → Create in tests/integration/test_<feature>.py
    ↓
    No
    ↓
Is it a demo/showcase for users?
    ↓
    Yes → Create in examples/demo_<feature>.py
    ↓
    No
    ↓
Is it a one-time diagnostic script?
    ↓
    Yes → Create in scripts/ with clear name
    ↓
    No
    ↓
Use unified test suite (tests/)
```

### Naming Conventions

**Test files** (in `tests/`):
- Unit tests: `test_<module>.py` (e.g., `test_config.py`, `test_tools.py`)
- Integration tests: `test_<feature>.py` (e.g., `test_agent.py`, `test_skills.py`)
- Use descriptive names that indicate what's being tested
- MUST start with `test_` for pytest discovery

**Test classes and functions**:
- Test classes: `Test<Feature>` (e.g., `TestConfig`, `TestAgent`)
- Test functions: `test_<specific_behavior>()` (e.g., `test_load_config()`)
- Use descriptive names that document what is being tested

**Example files** (in `examples/`):
- Demos: `demo_<feature>.py` (e.g., `demo_task_chaining.py`)
- Showcase specific functionality
- Include comments explaining usage
- NOT run by test suite

### Test Quality Requirements

**Every test MUST**:
1. Use pytest framework (not unittest, not standalone scripts)
2. Follow naming convention (`test_*.py`)
3. Be discoverable by `pytest` command
4. Use shared fixtures from `conftest.py` when applicable
5. Have descriptive docstrings
6. Be runnable via `run_tests.py` or `pytest`
7. Not have `if __name__ == "__main__"` blocks

**Examples**:
```python
# CORRECT - pytest test
import pytest
from fastreact import Config

class TestConfig:
    """Test configuration loading"""

    def test_load_default_config(self):
        """Test loading default config"""
        config = Config.load()
        assert config is not None
        assert config.llm.model

# FORBIDDEN - standalone script
def test_config():
    config = Config.load()
    assert config

if __name__ == "__main__":
    test_config()  # BAD - Not discoverable
```

### Quick Verification

```bash
# Verify all tests are discoverable
pytest tests/ --collect-only

# Run all tests
python3 run_tests.py all

# Expected: All tests discovered and run
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
9. **Use test suite** - All tests MUST be pytest-compatible, runnable via `run_tests.py`
10. **No standalone test scripts** - Forbidden to create test files with `if __name__ == "__main__"`

---

**For chronological development history, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)**
