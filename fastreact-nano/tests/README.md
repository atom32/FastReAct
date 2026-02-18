# Test Suite Documentation

FastReAct Nano test suite is organized into unit and integration tests.

## Current Status (v2.1.0)

**Total Tests**: 430+ tests (collected by pytest)
- **Unit Tests**: ~290 tests (config, tools, core, events, MCP, multitenant)
- **Integration Tests**: ~140 tests (agent, skills, events, E2E, Gateway)
- **Manual Tests**: 4 scripts (manual testing and debugging)

**Test Results** (as of latest run):
- Passing: 60 core tests (78.9%)
- Skipped: 16 tests (E2E tests requiring API keys)
- Failed: 0 tests
- Duration: ~20 seconds for core suite, ~2 minutes for full suite

**Recent Changes** (2026-02-18):
- [x] Removed obsolete `test_streaming.py` (streaming module deprecated in v2.0)
- [x] Removed duplicate `test_auto_skills.py` (replaced by pytest version)
- [x] Removed one-time `test_tool_signature_fix.py` (verification complete)
- [x] Reorganized root test scripts into proper directories
- [x] Created `tests/manual/` for manual testing scripts

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
├── fixtures/                # Shared test fixtures
├── helpers/                 # Test helper utilities
│   ├── mock_feishu_client.py
│   └── test_helpers.py
├── manual/                  # Manual test scripts (not automated)
│   ├── test_mcp_tools_direct.py
│   └── test_feishu_gateway.py
├── unit/                    # Unit tests (fast, no API calls)
│   ├── test_agent.py                    # Agent core functionality
│   ├── test_agent_mcp_integration.py    # Agent-MCP integration
│   ├── test_config.py                   # Configuration system
│   ├── test_context.py                  # Context management
│   ├── test_core_mocked.py              # Core React with mocks
│   ├── test_events.py                   # Event system
│   ├── test_feishu_sdk_adapter.py       # Feishu adapter
│   ├── test_mcp_discovery.py            # MCP server discovery
│   ├── test_mcp_isolation.py            # MCP multi-tenancy
│   ├── test_multitenant.py              # Multi-tenant support
│   ├── test_safety.py                   # Safety mechanisms
│   ├── test_security.py                 # Security validation
│   └── test_tools.py                    # Tool execution
└── integration/             # Integration tests
    ├── test_agent_mocked.py             # Agent with mocked LLM
    ├── test_auto_skills_pytest.py       # Auto skill selection
    ├── test_concurrent_users.py         # Concurrent user scenarios
    ├── test_e2e_feishu_graphrag.py      # E2E GraphRAG workflow
    ├── test_e2e_multitenant_graphrag.py # Multi-tenant E2E
    ├── test_e2e_real_api.py             # Real API tests
    ├── test_event_stream.py             # Event streaming
    ├── test_gateway_complex.py          # Gateway complex scenarios
    ├── test_graphrag_mcp.py             # GraphRAG MCP integration
    ├── test_mcp_integration.py          # MCP server integration
    ├── test_mcp_skill_integration.py    # MCP skill system
    ├── test_mcp_structure.py            # MCP structure validation
    ├── test_multitenant_mcp.py          # Multi-tenant MCP
    ├── test_skills_integration.py       # Skills integration
    ├── test_web_adapter.py              # Web adapter
    └── test_web_chat_features.py        # Web chat features
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

## Test Coverage Documentation

For detailed coverage targets, gap analysis, and improvement strategies, see **[COVERAGE.md](COVERAGE.md)**.

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

Keep as standalone scripts (in `tests/manual/`):
1. Full workflow demonstrations
2. Manual testing scripts
3. Debugging/diagnostic scripts
