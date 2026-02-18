# Test Coverage Analysis & Goals

FastReAct Nano test suite coverage targets, analysis, and improvement strategies.

**Last Updated**: 2026-02-18
**Version**: 2.1.0

---

## Coverage Targets

### Priority Levels

| Priority | Modules | Target | Status |
|----------|---------|--------|--------|
| **P0** | `agent.py` | >80% | ⚠️ ~70% |
| **P0** | `core/react.py` | >85% | ✅ ~85% |
| **P0** | `core/tools.py` | >90% | ✅ ~90% |
| **P0** | `core/config.py` | >85% | ⚠️ ~65% |
| **P0** | `core/multitenant.py` | >90% | ⚠️ ~75% |
| **P0** | `mcp/multitenant_manager.py` | >85% | ⚠️ ~60% |
| **P1** | `mcp/client.py` | >80% | ⚠️ ~70% |
| **P1** | `adapters/gateway.py` | >75% | ⚠️ ~50% |
| **P1** | `tools/*.py` | >85% | ✅ ~85% |

**Legend**:
- ✅ Target met
- ⚠️ Below target
- ❌ Not tested

---

## Generating Coverage Reports

### Quick Start

```bash
# Generate comprehensive coverage report
pytest tests/ --cov=src/fastreact --cov-report=html --cov-report=term-missing

# View HTML report (detailed, per-line coverage)
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Generate with branch coverage (more accurate)
pytest tests/ --cov=src/fastreact --cov-branch --cov-report=html
```

### Module-Specific Coverage

```bash
# Agent module
pytest tests/unit/test_agent.py --cov=src/fastreact/agent --cov-report=term-missing

# MCP modules
pytest tests/unit/test_mcp_isolation.py --cov=src/fastreact/mcp --cov-report=term-missing

# Config system
pytest tests/unit/test_config.py --cov=src/fastreact/core/config --cov-report=term-missing

# Multi-tenancy
pytest tests/unit/test_multitenant.py --cov=src/fastreact/core/multitenant --cov-report=term-missing
```

### Integration Coverage

```bash
# Agent with MCP integration
pytest tests/unit/test_agent_mcp_integration.py --cov=src/fastreact/agent --cov-report=term-missing

# MCP integration tests
pytest tests/integration/test_mcp_integration.py --cov=src/fastreact/mcp --cov-report=term-missing

# Multi-tenant MCP
pytest tests/integration/test_multitenant_mcp.py --cov=src/fastreact/mcp/multitenant_manager --cov-report=term-missing
```

---

## Coverage Gap Analysis

### Critical Gaps (P0 - Must Fix)

#### 1. Agent Session Management (`agent.py`)
**Current Coverage**: ~70%
**Target**: >80%

**Missing Tests**:
- [ ] Session queue lifecycle (`_session_queues`)
- [ ] Message injection into running sessions
- [ ] Session interrupt handling
- [ ] Multi-user session isolation
- [ ] Session cleanup on error
- [ ] Session state persistence

**Impact**: High - Core functionality, affects all multi-user scenarios

**Plan**: Add `tests/unit/test_agent_sessions.py` (~200 lines)

---

#### 2. MCP Multi-Tenant Isolation (`mcp/multitenant_manager.py`)
**Current Coverage**: ~60%
**Target**: >85%

**Missing Tests**:
- [ ] `shared` mode (global singleton)
- [ ] `per_user` mode (user-isolated instances)
- [ ] `lazy_per_user` mode (on-demand creation with timeout)
- [ ] Instance limit enforcement
- [ ] Lazy instance cleanup (LRU eviction)
- [ ] User parameter substitution (`{user_workspace}`, `{user_id}`)
- [ ] Concurrent user scenarios

**Impact**: High - Multi-tenant security isolation

**Plan**: Add `tests/unit/test_mcp_isolation_modes.py` (~250 lines)

---

#### 3. Configuration System (`core/config.py`)
**Current Coverage**: ~65%
**Target**: >85%

**Missing Tests**:
- [ ] v1 to v2 configuration migration
- [ ] Environment variable priority chain
- [ ] Multi-provider configuration
- [ ] Path validation and security checks
- [ ] Config file discovery (multiple search paths)
- [ ] Default value fallbacks
- [ ] Invalid config handling

**Impact**: Medium - Affects user experience and setup

**Plan**: Add `tests/unit/test_config_migration.py` (~150 lines)

---

#### 4. Multi-Tenant Security (`core/multitenant.py`)
**Current Coverage**: ~75%
**Target**: >90%

**Missing Tests**:
- [ ] Path traversal attack prevention
- [ ] Malicious user key validation
- [ ] Workspace isolation enforcement
- [ ] Config persistence isolation
- [ ] Concurrent user workspace separation
- [ ] Resource limit enforcement

**Impact**: High - Security vulnerability potential

**Plan**: Add `tests/unit/test_multitenant_security.py` (~200 lines)

---

#### 5. Agent Error Handling (`agent.py`)
**Current Coverage**: ~70%
**Target**: >80%

**Missing Tests**:
- [ ] MCP server connection failure
- [ ] Tool execution exceptions with user context
- [ ] Security policy enforcement (FORBIDDEN operations)
- [ ] Validation errors (history, parameters)
- [ ] Session interrupt and cleanup
- [ ] LLM API failure handling
- [ ] Timeout scenarios

**Impact**: High - Production reliability

**Plan**: Add `tests/unit/test_agent_error_handling.py` (~200 lines)

---

### Important Gaps (P1 - Should Fix)

#### 6. Gateway WebSocket Adapter (`adapters/gateway.py`)
**Current Coverage**: ~50%
**Target**: >75%

**Missing Tests**:
- [ ] WebSocket session lifecycle
- [ ] Real-time event streaming
- [ ] Authentication and authorization
- [ ] Concurrent connection handling
- [ ] Session state management
- [ ] Error recovery and reconnection

**Impact**: Medium - Gateway reliability

**Plan**: Add `tests/integration/test_gateway_websocket.py` (~150 lines)

---

#### 7. Tool Security (`src/fastreact/tools/`)
**Current Coverage**: ~85%
**Target**: >85%

**Missing Tests**:
- [ ] File size limit enforcement
- [ ] Protected path validation
- [ ] Atomic write operations
- [ ] Encoding error handling
- [ ] Permission denied scenarios
- [ ] Symbolic link handling

**Impact**: Medium - Security and reliability

**Plan**: Add `tests/unit/test_tool_security.py` (~150 lines)

---

## Coverage Improvement Strategy

### Phase 1: Critical Path Tests (Week 1-2)

**Priority**: P0 gaps

**Tasks**:
1. Create `tests/unit/test_agent_sessions.py`
   - Session queue management
   - Message injection
   - Interrupt handling
   - Multi-user isolation

2. Create `tests/unit/test_mcp_isolation_modes.py`
   - Three isolation modes
   - Instance limits and cleanup
   - User parameter substitution
   - Concurrent scenarios

3. Create `tests/unit/test_config_migration.py`
   - v1 to v2 migration
   - Environment priority
   - Multi-provider config
   - Path validation

4. Create `tests/unit/test_multitenant_security.py`
   - Path traversal protection
   - User key validation
   - Workspace isolation
   - Config persistence

5. Create `tests/unit/test_agent_error_handling.py`
   - MCP connection failures
   - Tool execution exceptions
   - Security enforcement
   - Validation errors

**Expected Outcome**:
- `agent.py`: 70% → 85%
- `mcp/multitenant_manager.py`: 60% → 85%
- `core/config.py`: 65% → 85%
- `core/multitenant.py`: 75% → 90%

---

### Phase 2: Integration Tests (Week 3)

**Priority**: P1 gaps

**Tasks**:
1. Create `tests/integration/test_gateway_websocket.py`
   - WebSocket lifecycle
   - Real-time streaming
   - Authentication
   - Concurrent connections

2. Create `tests/unit/test_tool_security.py`
   - File size limits
   - Protected paths
   - Atomic operations
   - Encoding errors

**Expected Outcome**:
- `adapters/gateway.py`: 50% → 75%
- `tools/*.py`: 85% → 90%

---

### Phase 3: Coverage Maintenance (Ongoing)

**Tasks**:
1. Set up pre-commit coverage checks
2. Add coverage badge to README
3. Regular coverage audits (quarterly)
4. Coverage regression testing in CI/CD
5. Coverage trend monitoring

**CI/CD Integration**:

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest tests/ --cov=src/fastreact --cov-report=xml --cov-report=term

- name: Check coverage thresholds
  run: |
    python -c "
    import xml.etree.ElementTree as ET
    tree = ET.parse('coverage.xml')
    coverage = float(tree.find('.//coverage').get('line-rate', 0))
    assert coverage >= 0.80, f'Coverage {coverage:.2%} below 80%'
    "

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
```

---

## Coverage Best Practices

### 1. Test What Matters

Focus on:
- ✅ Critical paths (happy path + common errors)
- ✅ Security boundaries
- ✅ Multi-user scenarios
- ✅ Error handling and recovery

Don't obsess over:
- ❌ Trivial getters/setters
- ❌ Dataclass fields
- ❌ Simple delegations
- ❌ Obsolete/deprecated code

### 2. Meaningful Coverage

**Good coverage**:
```python
def test_agent_handles_mcp_failure():
    """Test agent gracefully handles MCP server failure"""
    agent = Agent(config=config)

    # Mock MCP server to raise exception
    with mock.patch.object(agent._mcp_manager, 'get_server', side_effect=ConnectionError):
        events = collect_events(agent.run_event_stream("use mcp tool"))

        # Should complete with error message
        assert any(e.type == EventType.ERROR for e in events)
        assert any("MCP unavailable" in e.content for e in events if e.type == EventType.ERROR)
```

**Bad coverage** (just for numbers):
```python
def test_agent_exists():  # Pointless!
    """Test agent can be created"""
    agent = Agent()
    assert agent is not None
```

### 3. Test Design Principles

**ARRANGE-ACT-ASSERT**:
```python
def test_multitenant_isolates_user_workspaces():
    # Arrange
    user1_agent = Agent(user_id="user1")
    user2_agent = Agent(user_id="user2")

    # Act
    user1_agent.run("create file.txt")
    user2_agent.run("list files")

    # Assert
    assert "file.txt" not in user2_results
    assert "file.txt" in user1_results
```

**Test Isolation**:
- Each test should be independent
- Use fixtures for setup
- Clean up resources in `teardown()`
- Don't rely on test execution order

---

## Coverage Metrics Explained

### Line Coverage
**Percentage of executable lines that were executed**

```
Line Coverage: 85%
```
Means: 85 out of 100 executable lines were run during tests

**Limitation**: Doesn't measure if all branches were taken

---

### Branch Coverage
**Percentage of code branches that were executed**

```python
def example(x):
    if x > 0:      # Branch 1
        return True
    else:          # Branch 2
        return False
```

Line coverage: 100% (all 3 lines executed)
Branch coverage: 50% (only one branch taken per test)

**Recommendation**: Use `--cov-branch` for more accurate coverage

---

### Statement vs. Decision Coverage

**Statement coverage** (line coverage):
- Did we execute this line?

**Decision coverage** (branch coverage):
- Did we test all possible outcomes?

**Example**:
```python
if user.is_admin and user.has_permission:
    allow_access()
```

**Tests needed for full decision coverage**:
1. `admin=True, permission=True` → allow_access()
2. `admin=True, permission=False` → deny
3. `admin=False, permission=True` → deny
4. `admin=False, permission=False` → deny

---

## Troubleshooting Coverage

### Issue: Coverage Not Generated

**Problem**: No `htmlcov/` directory created

**Solutions**:
```bash
# Install pytest-cov
pip install pytest-cov

# Check installation
pytest --version

# Run with verbose output
pytest tests/ --cov=src/fastreact --cov-report=html -v
```

---

### Issue: Low Coverage for Imported Modules

**Problem**: Coverage shows 0% for some modules

**Cause**: Module imported but not executed during tests

**Solution**:
```python
# Add import-time tests
def test_module_imports():
    """Test module can be imported"""
    import fastreact.agent
    import fastreact.mcp.multitenant_manager
    # This counts as coverage!
```

---

### Issue: Coverage Excludes Files

**Problem**: Some files not included in coverage report

**Solution**:
```bash
# Explicitly include all source files
pytest tests/ --cov=src/fastreact --cov-context=test --cov-report=html

# Or specify source paths
pytest tests/ --cov=src/fastreact/agent --cov=src/fastreact/core --cov=src/fastreact/mcp
```

---

## Coverage Tools

### pytest-cov

**Installation**:
```bash
pip install pytest-cov
```

**Features**:
- HTML reports
- Terminal output
- XML output (for CI/CD)
- Branch coverage
- Combined coverage from multiple test runs

### Coverage.py (Standalone)

**Documentation**: https://coverage.readthedocs.io/

**Direct usage**:
```bash
# Run coverage
coverage run -m pytest tests/

# Generate report
coverage report -m
coverage html
```

### VS Code Extension

**Python Test Explorer**:
- Shows coverage in editor
- Highlights covered/uncovered lines
- Run tests with coverage from IDE

---

## References

### Internal Documentation
- `tests/README.md` - Test suite documentation
- `CLAUDE.md` - Development rules and standards
- `docs_archive/testing/` - Test suite history

### External Resources
- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [coverage.py documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

## Summary

**Current Status**:
- Overall coverage: ~75% (estimated)
- P0 modules: ~70% (below target)
- P1 modules: ~65% (below target)

**Immediate Actions**:
1. Create `tests/unit/test_agent_sessions.py` (P0)
2. Create `tests/unit/test_mcp_isolation_modes.py` (P0)
3. Create `tests/unit/test_config_migration.py` (P0)
4. Create `tests/unit/test_multitenant_security.py` (P0)
5. Create `tests/unit/test_agent_error_handling.py` (P0)

**Expected Results**:
- Overall coverage: ~85% (from ~75%)
- P0 modules: >85% (from ~70%)
- Better security isolation
- More reliable error handling
- Easier maintenance

---

**Next Steps**:
1. Review and approve this coverage plan
2. Implement Phase 1 tests (P0 gaps)
3. Generate coverage report to verify improvements
4. Integrate coverage checks into CI/CD
5. Schedule quarterly coverage audits

**Maintainer**: Development Team
**Review Cycle**: Quarterly (or after major features)
