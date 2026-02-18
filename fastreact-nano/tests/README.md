# Test Suite Documentation

FastReAct Nano test suite is organized into unit and integration tests.

## Current Status (v2.1.0)

**Total Tests**: 76 tests
- **Unit Tests**: 39 tests (config, tools, core, streaming)
- **Integration Tests**: 21 tests (agent, skills, events, E2E)
- **Legacy Scripts**: 16 scripts (manual testing, archived)

**Test Results** (as of latest run):
- Passing: 60 tests (78.9%)
- Skipped: 16 tests (E2E tests requiring API keys)
- Failed: 0 tests
- Duration: ~20 seconds

**Quick Commands**:
```bash
# Quick check (unit tests only, ~5 seconds)
python3 run_tests.py unit

# Full test suite (including integration, ~30 seconds)
python3 run_tests.py all

# With keyword filter
python3 run_tests.py all -k "skill"
```

**For detailed test history and evolution, see**: `docs_archive/testing/`

---

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration (auto-path setup)
├── unit/                    # Unit tests (fast, no API calls)
│   ├── test_config.py       # Configuration loading
│   ├── test_streaming.py    # Event streaming (deprecated)
│   └── test_tools.py        # Tool execution
└── integration/             # Integration tests
    ├── test_auto_skills_pytest.py  # Auto skill selection
    ├── test_auto_skills.py         # Legacy script
    ├── test_skills_integration.py  # Skills injection
    ├── test_agent_loop.py          # Agent loop behavior
    ├── test_basic.py               # Basic functionality
    ├── test_e2e.py                 # End-to-end workflow
    ├── test_enhanced_cli.py        # CLI features
    ├── test_event_stream.py        # Event streaming
    ├── test_messages.py            # Message handling
    ├── test_tools.py               # Tools integration
    ├── quick_test.py               # Quick validation
    └── simple_test.py              # Simple tests
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

### Legacy Test Scripts

Some integration tests in `tests/integration/` are standalone scripts:

```bash
# Run standalone test scripts
python3 tests/integration/test_auto_skills.py
python3 tests/integration/test_e2e.py
```

Note: These will be migrated to pytest format over time.

## Test Categories

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

```bash
# Generate coverage report
pytest tests/ --cov=src/fastreact --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

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

## End-to-End Tests (NEW)

### Purpose

Comprehensive testing of Feishu + GraphRAG + Multi-tenant integration.

**Files**:
- `integration/test_e2e_feishu_graphrag.py` - Main E2E scenarios
- `integration/test_concurrent_users.py` - Concurrent access tests
- `helpers/test_helpers.py` - Event collection utilities
- `helpers/mock_feishu_client.py` - Mock Feishu client

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

# Run all E2E tests
pytest tests/integration/test_e2e_feishu_graphrag.py -v -m api

# Run specific scenario
pytest tests/integration/test_e2e_feishu_graphrag.py::TestE2ESingleRound -v -m api

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

See `integration/test_e2e_feishu_graphrag.py` for examples.

## Migration Plan

### Legacy Scripts → pytest

Current status:
- [x] `test_auto_skills_pytest.py` - Converted to pytest
- [x] `test_e2e_feishu_graphrag.py` - NEW E2E test suite
- [x] `test_concurrent_users.py` - NEW concurrent tests
- [ ] `test_skills_integration.py` - To convert
- [ ] `test_agent_loop.py` - To convert
- [ ] Other integration tests - Keep as standalone scripts for manual testing

Priority for conversion:
1. High-value, frequently-run tests
2. Tests that benefit from fixtures
3. Tests used in CI/CD

Keep as standalone scripts:
1. Full workflow demonstrations
2. Manual testing scripts
3. Debugging/diagnostic scripts
