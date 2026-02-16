# FastReAct Nano - Development Rules & Standards

**Version**: 2.1.0
**Last Updated**: 2025-02-16

---

## Architecture Iron Rules (Critical)

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

---

## Quick Reference

### Testing
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
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint and auto-fix
ruff check src/ tests/ --fix

# Type check
mypy src/

# All quality checks (run before commit)
black src/ tests/ && ruff check src/ tests/ --fix && mypy src/
```

### Common Commands
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
```

---

## Documentation Rules

### Where to Put Documentation

**Root Directory** (minimal, essential only):
- User-facing guides: README.md, GETTING_STARTED.md, USAGE.md
- Development rules: CLAUDE.md (this file)
- Navigation: DOCS_INDEX.md
- Release notes: RELEASE_NOTES.md

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
__version__ = "2.1.0"
```

**Read dynamically in other files**:
- `pyproject.toml`: `dynamic = ["version"]` with `[tool.setuptools.dynamic]`
- CLI: `from fastreact import __version__`

**DO NOT** duplicate version string in multiple files!

---

## Update Workflow

When making changes to FastReAct:

1. Make code change
2. Update CLAUDE.md if new pattern/pitfall introduced
3. Update DOCS_INDEX.md if structure changed
4. Run tests: `python3 run_tests.py all`
5. Run quality checks: `black src/ && ruff check src/ --fix && mypy src/`
6. Commit: `git commit -m "type: description"`

**Update Triggers** for CLAUDE.md:
- New architecture pattern emerges
- New common pitfall discovered (from git fixes)
- New workflow/command added
- Rule violation found in code review

**Quarterly Review**:
- [ ] Check line count (target: < 300 lines)
- [ ] Archive outdated sections to docs_archive/
- [ ] Update Common Pitfalls with recent fixes
- [ ] Verify all commands still work
- [ ] Remove redundant content

---

**For chronological development history, see DEVELOPMENT_LOG.md in parent project**
