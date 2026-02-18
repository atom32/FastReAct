# E2E Test Quick Start Guide

## Prerequisites

1. **Set API Key** (required for API-marked tests):
   ```bash
   export FASTRACT_API_KEY="sk-your-api-key-here"
   ```

2. **Verify Installation**:
   ```bash
   cd /Users/xudawei/FastReAct/fastreact-nano
   python3 -m pytest --version
   ```

## Running Tests

### All E2E Tests (with real API)
```bash
pytest tests/integration/test_e2e_feishu_graphrag.py -v -m api
```

### Specific Scenarios

#### Scenario 1: Single-Round Query
```bash
pytest tests/integration/test_e2e_feishu_graphrag.py::TestE2ESingleRound -v -m api
```

#### Scenario 2: Multi-Turn Conversation
```bash
pytest tests/integration/test_e2e_feishu_graphrag.py::TestE2EMultiTurn -v -m api
```

#### Scenario 3: Concurrent Users
```bash
pytest tests/integration/test_e2e_feishu_graphrag.py::TestE2EConcurrentUsers -v -m api
```

#### Scenario 4: Complex Workflows
```bash
pytest tests/integration/test_e2e_feishu_graphrag.py::TestE2EComplexWorkflows -v -m api
```

#### Scenario 5: Error Handling
```bash
pytest tests/integration/test_e2e_feishu_graphrag.py::TestE2EErrorHandling -v -m api
```

### Concurrent User Tests
```bash
# All concurrent tests (some don't require API key)
pytest tests/integration/test_concurrent_users.py -v

# Only concurrent tests with GraphRAG (requires API key)
pytest tests/integration/test_concurrent_users.py::TestConcurrentUserAccess::test_concurrent_users_with_graphrag -v -m api
```

## Expected Output

### Successful Test Run
```
tests/integration/test_e2e_feishu_graphrag.py::TestE2ESingleRound::test_knowledge_search_with_graphrag_skill PASSED
tests/integration/test_e2e_feishu_graphrag.py::TestE2ESingleRound::test_auto_skill_selection_for_knowledge_query PASSED
...
========================= 11 passed in 45.23s =========================
```

### Test Markers Explained

- `@pytest.mark.api` - Uses real LLM API (requires FASTRACT_API_KEY)
- `@pytest.mark.asyncio` - Async test
- `@pytest.mark.slow` - Slow test (skip with `-m "not slow"`)

## Troubleshooting

### "FASTRACT_API_KEY not set"
```bash
export FASTRACT_API_KEY="sk-your-key-here"
```

### "ModuleNotFoundError: No module named 'fastreact'"
```bash
cd /Users/xudawei/FastReAct/fastreact-nano
pip install -e .
```

### MCP server not starting
```bash
# Test GraphRAG server manually
python3 examples/graph_rag_server.py
```

### Import errors
```bash
# Ensure you're in project root
cd /Users/xudawei/FastReAct/fastreact-nano
pytest tests/integration/test_e2e_feishu_graphrag.py -v
```

## Test Coverage Summary

| Scenario | Tests | API Required |
|----------|-------|--------------|
| 1. Single-Round | 2 | ✅ |
| 2. Multi-Turn | 2 | ✅ |
| 3. Concurrent Users | 4 | ✅ |
| 4. Complex Workflows | 2 | ✅ |
| 5. Error Handling | 3 | ✅ |
| **Total** | **11** | **11** |

| Component | Tests | API Required |
|-----------|-------|--------------|
| Concurrent Access | 3 | 1 |
| Workspace Isolation | 3 | 0 |
| Session Isolation | 2 | 0 |
| Stress Tests | 2 | 0 |
| **Total** | **10** | **1** |

## Next Steps

1. ✅ Implementation complete
2. ⏳ Run tests to validate
3. ⏳ Fix any issues
4. ⏳ Add edge cases as needed

## Documentation

- **Full Summary**: `E2E_TEST_IMPLEMENTATION_SUMMARY.md`
- **Test README**: `tests/README.md`
- **Test Helpers**: `tests/helpers/test_helpers.py`
- **Mock Client**: `tests/helpers/mock_feishu_client.py`
