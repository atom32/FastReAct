# Test Suite Documentation

FastReAct Nano test suite is organized into contracts, focused integration
suites, release-only LLM checks, and diagnostics scripts.

## Current Status

The default gates are intentionally smaller than the historical suite:

- **contracts**: event protocol, services, tool approval, JSONL store.
- **quick**: contracts plus core runtime integration and critical unit tests.
- **integration**: HTTP/SSE runtime, MCP, and multitenant scenarios.
- **release-llm**: manual real LLM efficiency gate, not run by default.
- **diagnostics**: local scripts under `scripts/diagnostics/`, not collected by pytest.

Real API checks read `~/api_key.txt` only when `python3 run_tests.py release-llm`
is invoked. Default CI/pytest should not depend on external LLM credentials.

**Quick Commands**:
```bash
# Contract tests
python3 run_tests.py contracts

# Quick release-safe check
python3 run_tests.py quick

# HTTP/SSE, MCP, and multitenant integration
python3 run_tests.py integration

# All release-safe backend tests
python3 run_tests.py all

# Manual real LLM gate
python3 run_tests.py release-llm
```

**For detailed test history and evolution, see**: `docs_archive/testing/`

---

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration (auto-path setup)
├── contracts/               # Stable behavior contracts
├── helpers/                 # Test helper utilities
├── unit/                    # Fast unit tests
├── integration/
│   ├── agent_runtime/       # ReAct loop and runtime service integration
│   ├── mcp/                 # MCP integration and lifecycle
│   └── multitenant/         # User isolation/concurrency
└── release/                 # Release-only LLM gate documentation
```

## Running Tests

### Unified Test Runner (Recommended)

```bash
# Run all tests
python3 run_tests.py

# Run only unit tests
python3 run_tests.py unit

# Run only integration tests
python3 run_tests.py integration

# Run quick tests (excluding slow ones)
python3 run_tests.py quick

# Verbose output
python3 run_tests.py all -v

# Filter by keyword
python3 run_tests.py all -k "skill"
```

### Direct pytest (Advanced)

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run specific test file
pytest tests/integration/test_auto_skills_pytest.py -v

# Run specific test
pytest tests/integration/test_auto_skills_pytest.py::TestAutoSkillSelection::test_git_workflow_selection -v

# Run with coverage
pytest tests/ --cov=src/fastreact --cov-report=html
```

## CI/CD Integration

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast execution (< 1 second each)
- No external dependencies
- No API calls
- Use fixtures and mocks

**Examples**:
- Configuration loading and validation
- Tool interface contract
- Event creation and serialization

### Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions

**Characteristics**:
- Slower execution (may require I/O or API calls)
- Test real workflows
- May require valid API keys
- Test end-to-end scenarios

**Examples**:
- Agent execution loop
- Skills selection and injection
- Event streaming
- CLI functionality

## Writing New Tests

### Unit Test Example

```python
# tests/unit/test_myfeature.py
import pytest
from fastreact.core.myfeature import MyFeature

class TestMyFeature:
    """Test MyFeature functionality"""

    def test_basic_operation(self):
        """Test basic feature works"""
        feature = MyFeature()
        result = feature.do_something()
        assert result is not None

    def test_edge_case(self):
        """Test edge case handling"""
        feature = MyFeature()
        with pytest.raises(ValueError):
            feature.do_something_invalid()
```

### Integration Test Example

```python
# tests/integration/test_myworkflow.py
import pytest
from fastreact import Agent, Config

class TestMyWorkflow:
    """Test complete workflow"""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create test agent"""
        config = Config.load()
        return Agent(config=config)

    @pytest.mark.asyncio
    async def test_workflow(self, agent):
        """Test end-to-end workflow"""
        events = []
        async for event in agent.run_event_stream("test query"):
            events.append(event)

        assert len(events) > 0
```

## Configuration

### pytest Configuration

Located in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

### conftest.py

The `tests/conftest.py` file provides:
- Automatic `src/` path configuration
- Shared fixtures (e.g., `config_file`, `project_root`)
- Path cleanup for multiple installations

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e .
      - run: python3 run_tests.py unit
      - run: python3 run_tests.py integration
```

## Test Coverage

**Coverage Goals**:
- Core modules (>85%): `agent.py`, `core/react.py`, `core/tools.py`
- MCP modules (>85%): `mcp/client.py`, `mcp/multitenant_manager.py`
- Config system (>85%): `core/config.py`, `core/multitenant.py`
- Tools (>80%): All tools in `src/fastreact/tools/`

**Generating Coverage Reports**:

```bash
# Generate HTML coverage report
pytest tests/ --cov=src/fastreact --cov-report=html --cov-report=term-missing

# View report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Generate with branch coverage
pytest tests/ --cov=src/fastreact --cov-branch --cov-report=html

# Check specific module coverage
pytest tests/unit/test_agent.py --cov=src/fastreact/agent --cov-report=term-missing
```

**Coverage Reports**:
- Detailed coverage analysis: See `tests/COVERAGE.md`
- HTML reports: Generated in `htmlcov/` directory
- Missing lines shown in terminal with `--cov-report=term-missing`

## Troubleshooting

### Import Errors

If you see import errors like `ModuleNotFoundError: No module named 'fastreact'`:

```bash
# Install in development mode
pip install -e .

# Or run pytest from project root
cd /path/to/fastreact-nano
pytest tests/
```

### Path Issues

The `conftest.py` should automatically handle path configuration. If you still have issues:

```python
# In your test file, add:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
```

### Async Tests

For async tests, use `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## End-to-End Tests

### Purpose

Comprehensive testing of the HTTP/SSE daemon, durable events, skills, MCP tools,
and cross-repo PSKA smoke flows.

**Files**:
- `integration/test_concurrent_users.py` - Concurrent access tests
- `helpers/test_helpers.py` - Event collection utilities

### Test Scenarios

**Scenario 1: Single-Round Knowledge Query**
- Validates MCP-SKILL integration
- Agent selects graphrag_workflow skill
- Calls appropriate GraphRAG tools
- Returns knowledge graph information

**Scenario 2: Multi-Turn Conversation**
- Validates context preservation
- Each round maintains previous context
- Conversation history persists

**Scenario 3: Concurrent Users**
- Validates multi-tenant isolation
- Each user has independent workspace
- Query results don't mix

**Scenario 4: Complex Workflows**
- Validates skill guidance
- Multiple tools in sequence
- Results synthesized from multiple sources

**Scenario 5: Error Handling**
- Validates graceful degradation
- Meaningful error messages
- Alternative solutions attempted

### Running E2E Tests

```bash
# Set API key
export FASTRACT_API_KEY="sk-xxx"

# Run concurrent user tests
pytest tests/integration/test_concurrent_users.py -v
```

### Test Helpers

```python
from tests.helpers.test_helpers import (
    collect_events,
    extract_tool_calls,
    assert_session_completed,
)

# Collect events
events = await collect_events(agent.run_event_stream("query"))

# Assert completion
assert_session_completed(events)

# Check tool usage
assert_tool_called(events, "graphrag_search_graph")
```

Use the PSKA-side `core/scripts/fastreact_http_sse_e2e.py` for cross-repo
HTTP/SSE smoke testing.

## Test Coverage Documentation

For detailed coverage targets, gap analysis, and improvement strategies, see **[COVERAGE.md](COVERAGE.md)**.

## Migration Plan

### Legacy Scripts → pytest

Current status:
- [x] `test_auto_skills_pytest.py` - Converted to pytest
- [x] `test_concurrent_users.py` - NEW concurrent tests
- [ ] `test_skills_integration.py` - To convert
- [ ] `test_agent_loop.py` - To convert
- [ ] Other integration tests - Keep as standalone scripts for manual testing

Priority for conversion:
1. High-value, frequently-run tests
2. Tests that benefit from fixtures
3. Tests used in CI/CD

Keep as standalone scripts (in `tests/manual/`):
1. Full workflow demonstrations
2. Manual testing scripts
3. Debugging/diagnostic scripts
