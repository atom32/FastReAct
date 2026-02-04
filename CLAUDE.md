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

### Documentation Structure

```
FastReAct/
├── DOCS_INDEX.md               # Master index (update when adding docs)
├── README.md                    # Project homepage
├── CLAUDE.md                    # This file - Development rules
├── DEVELOPMENT_LOG.md           # Chronological development history
│
├── [User Docs]
│   ├── INSTALLATION.md
│   └── CONFIG.md
│
├── [Feature Docs] - One per major feature
│   ├── MULTI_TENANT_WORKSPACE.md
│   ├── SESSION_RESUME.md
│   ├── MCP_INTEGRATION_SUCCESS.md
│   └── WORKSPACE_ISOLATION.md
│
├── [Technical Docs]
│   ├── VERSION_MANAGEMENT.md
│   ├── IEL.md
│   └── SECURITY.md
│
└── docs_archive/               # Historical docs (read-only)
    ├── INDEX.md
    └── ...
```

### Adding New Documentation

**Steps**:
1. Check `DOCS_INDEX.md` for similar existing docs
2. Create new doc with clear name: `FEATURE_NAME.md`
3. Add to appropriate category in `DOCS_INDEX.md`
4. Run `python scripts/quick_check.py` to verify no emojis
5. Commit with descriptive message

**Naming Conventions**:
- User docs: `TOPIC.md` (e.g., `INSTALLATION.md`)
- Feature docs: `FEATURE_NAME.md` (e.g., `MULTI_TENANT_WORKSPACE.md`)
- Technical docs: `TOPIC.md` (e.g., `VERSION_MANAGEMENT.md`)

### What Belongs Where

**Root Directory (keep minimal)**:
- `README.md` - Project overview, quick start
- `DOCS_INDEX.md` - Documentation navigation
- `CLAUDE.md` - Development rules (this file)
- `CHANGELOG.md` - Version history

**Feature Docs (keep one per feature)**:
- Complete implementation guide
- Usage examples
- API documentation

**Archive (move when obsolete)**:
- Development process docs
- Old test reports
- Superseded docs

**Delete (avoid completely)**:
- Duplicate content
- Empty placeholder docs
- Outdated quickstarts

### Quality Checklist

Before committing documentation:
- [ ] No emojis (use `[OK]`, `[ERROR]`, etc.)
- [ ] UTF-8 encoding (for Chinese content)
- [ ] Links work (test `./` relative links)
- [ ] No hardcoded paths (use `pathlib` or `config`)
- [ ] Cross-platform compatible (no Windows/Mac specific paths)
- [ ] Updated `DOCS_INDEX.md` if needed

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

---

**For chronological development history, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)**
