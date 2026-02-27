# Common Pitfalls (From Git History)

**Note**: This document contains historical bug fixes and development lessons learned. These issues have been fixed in the current codebase. This document is kept for reference purposes.

For current development rules, see [CLAUDE.md](../../CLAUDE.md).

---

## Bug Fixes

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

---

## Development Rules

### Development Rule: Keep Project Clean
**Problem**: Generating test files and documentation scattered across project directories
**Rule**: Keep project folders clean and organized
**Check**: Before creating any file in project root or subdirectories
```bash
# WRONG - Don't create test files in project directories
/tmp/test_feature.py  # [ERROR] If testing, use /tmp/ or tests/
./my_test_script.py   # [ERROR] Use tests/ directory
./TEMP_REPORT.md      # [ERROR] Use docs/ or docs_archive/

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

**Archived**: 2025-02-27
**Original Location**: CLAUDE.md lines 566-674
