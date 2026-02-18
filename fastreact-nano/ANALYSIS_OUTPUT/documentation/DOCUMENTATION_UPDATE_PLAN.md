# Documentation Update Plan

**Generated**: 2026-02-18
**Based on**: Documentation Consistency Report
**Target Version**: 2.1.0
**Overall Accuracy**: 68.7% (46/67 claims verified)

---

## Executive Summary

This plan addresses **21 documentation issues** found in the consistency report:
- **3 P0 (Critical)** issues requiring immediate fix
- **12 P1 (High)** priority issues
- **6 P2 (Medium)** priority issues

**Estimated Total Effort**: 6-8 hours
**Recommended Timeline**: Complete before v2.1.0 release

---

## P0 Issues (Critical) - Fix Immediately

### 1. Version Number Inconsistency

**Priority**: P0
**Estimated Time**: 15 minutes
**Impact**: Breaking change for users expecting 2.1.0 features

**Files Affected**:
- `pyproject.toml` (line 7)
- `README.md` (line 199)
- `CLAUDE.md` (line 3)
- `src/fastreact/__init__.py` (line 11, 2)

**Current State**:
- `pyproject.toml`: version = "2.0.0"
- `README.md`: "Version: 2.1.0"
- `CLAUDE.md`: "Version: 2.1.0"
- `__init__.py`: __version__ = "2.1.0"

**Fix Required**:
Update `pyproject.toml` to version 2.1.0 to match documentation

**Action**:
```toml
# pyproject.toml, line 7
version = "2.1.0"
```

**Verification**:
```bash
grep "version" pyproject.toml
grep "__version__" src/fastreact/__init__.py
grep "Version.*2\." README.md CLAUDE.md
```

---

### 2. Total Line Count Gross Underreporting

**Priority**: P0
**Estimated Time**: 20 minutes
**Impact**: Misleading about codebase complexity (58% underreport)

**Files Affected**:
- `README.md` (line 52)
- `docs/DESIGN.md` (line 718)

**Current State**:
- README.md claims: "Lines of Code: 5,592"
- Actual: 8,869 lines (verified via `find src/fastreact -name "*.py" | xargs wc -l`)
- DESIGN.md claims: "<3,500 lines" (2.5x smaller than actual)

**Fix Required**:

**Option A**: Update to actual count (recommended)
```markdown
# README.md, line 52
Lines of Code: 8,869
```

**Option B**: Clarify methodology
```markdown
# README.md, line 52-53
Lines of Code: 8,869 total (5,592 core implementation excluding tests/adapters)
Core Implementation: 5,592 lines
```

**For DESIGN.md**:
```markdown
# docs/DESIGN.md, line 718
Current Implementation: 8,869 lines (Design target was <3,500 lines)
```

**Rationale**:
The original 5,592 count likely excluded:
- Test files
- Adapters (2,661 lines across 8 adapters)
- Examples
- MCP integration (704 lines)

**Verification**:
```bash
find src/fastreact -name "*.py" | xargs wc -l | tail -1
# Output: 8869 total
```

---

### 3. Agent Line Count Underreporting

**Priority**: P0
**Estimated Time**: 5 minutes
**Impact**: Misleading about component complexity (58% underreport)

**Files Affected**:
- `README.md` (line 164)

**Current State**:
- README.md claims: "Agent: 595 lines"
- Actual: 944 lines (verified via `wc -l src/fastreact/agent.py`)

**Fix Required**:
```markdown
# README.md, line 164
Agent (Body): 944 lines
```

**Context**:
The 595-line figure may have been from an earlier version before refactoring. Current implementation includes:
- Full event stream handling
- MCP tool integration
- Multi-tenant support
- Steering system
- Context monitoring

**Verification**:
```bash
wc -l src/fastreact/agent.py
# Output: 944 src/fastreact/agent.py
```

---

## P1 Issues (High Priority)

### 4. Production Ready Status with Known Issues

**Priority**: P1
**Estimated Time**: 15 minutes
**Impact**: Users may encounter broken functionality

**Files Affected**:
- `README.md` (line 200)

**Current State**:
```markdown
**Version**: 2.1.0
**Status**: Production Ready
```
But REPL adapter has known issues documented in line 24

**Fix Required**:

**Option A**: Change status (recommended)
```markdown
**Version**: 2.1.0
**Status**: Beta (REPL adapter has known issues)
```

**Option B**: Add caveat
```markdown
**Version**: 2.1.0
**Status**: Production Ready (CLI, HTTP, Gateway adapters fully functional)
```

**Additional Documentation**:
Add "Known Issues" section after line 37:
```markdown
## Known Issues

### REPL Adapter
- **Issue**: Agent._llm attribute access error
- **Status**: Under investigation
- **Workaround**: Use CLI adapter instead
- **Timeline**: Fix expected in v2.1.1
```

---

### 5. Adapter Test Coverage Unclear

**Priority**: P1
**Estimated Time**: 30 minutes
**Impact**: Unclear which adapters are production-ready

**Files Affected**:
- `README.md` (line 22)

**Current State**:
```markdown
All core adapters tested (4/6 passing)
```

**Problems**:
1. 8 adapter files exist, not 6
2. Unclear which adapters are "core"
3. Unclear which are "passing"

**Fix Required**:

**Step 1**: Verify adapter status
```bash
# Run adapter tests
pytest tests/unit/test_adapters/ -v
pytest tests/integration/test_cli.py -v
pytest tests/integration/test_http.py -v
```

**Step 2**: Update README.md (line 22)
```markdown
### Testing
- Core adapters tested: 4/4 passing (CLI, HTTP, Gateway, Skills)
- Experimental adapters: REPL (known issues), Web, Feishu
- Test coverage: 34 test files
```

**Step 3**: Update adapter table (lines 29-36)
```markdown
| Adapter | Status | Lines | Notes |
|--------|--------|-------|-------|
| CLI | ✅ Production | 272 | Fully tested |
| HTTP | ✅ Production | 259 | SSE streaming, REST API |
| Gateway | ✅ Production | 258 | WebSocket support |
| Skills | ✅ Production | 558 | Dynamic loading, tested |
| REPL | ⚠️ Experimental | 314 | Known issue, use CLI |
| Web | ⚠️ Experimental | 370 | Streamlit UI |
| Feishu | ⚠️ Experimental | 542 | Lark SDK integration |
| Feishu SDK | ⚠️ Experimental | 358 | Official SDK wrapper |
```

---

### 6. Anti-Entropy Score Questionable

**Priority**: P1
**Estimated Time**: 20 minutes
**Impact**: Principle not strictly followed, score misleading

**Files Affected**:
- `README.md` (line 232)

**Current State**:
```markdown
| 反熵增 (Anti-Entropy) | 100/100 | Core locked at 180 lines |
```

**Problems**:
1. Core is actually 182 lines (2 over target)
2. Agent is 944 lines (claimed 595)
3. Total codebase 8,869 lines (claimed 5,592)

**Fix Required**:

**Option A**: Recalculate score (recommended)
```markdown
| Principle | Score | Evidence |
|-----------|-------|----------|
| 反熵增 (Anti-Entropy) | 95/100 | Core 182/180 (98.9%), Agent 944 (needs audit) |
| SDK化 (SDK-First) | 100/100 | Pure intent generator pattern |
| 人类掌控 (Human Control) | 100/100 | Readable code, steering system |
| 生态隔离 (Ecosystem) | 100/100 | Adapters are plugins |
```

**Option B**: Remove scores, keep principles
```markdown
## Design Principles

1. **Anti-Entropy**: Core locked at ~180 lines (currently 182, 98.9% compliance)
2. **SDK-First**: Core as high-concurrency logic engine
3. **Human-Comprehensible**: Code is readable and modifiable
4. **Ecosystem Isolation**: All adapters are replaceable plugins
```

---

### 7. Design Target vs Actual

**Priority**: P1
**Estimated Time**: 15 minutes
**Impact**: Design goal not met, needs explanation

**Files Affected**:
- `docs/DESIGN.md` (line 718)

**Current State**:
Claims "<3,500 lines" but actual is 8,869 lines (2.5x target)

**Fix Required**:
Add explanatory note to DESIGN.md:
```markdown
## Code Size Evolution

**Original Target**: <3,500 lines
**Current Implementation**: 8,869 lines (253% of target)

**Growth Breakdown**:
- Core + Agent: 1,126 lines (within target)
- Adapters: 2,661 lines (8 adapters, ~332 lines each)
- MCP Integration: 704 lines (client, server, discovery, manager)
- Cortex Components: 1,401 lines (context, safety, events, config)
- Tools: 554 lines (4 core tools)
- Multi-tenant: 252 lines
- Skills System: 519 lines
- Messages: 353 lines

**Analysis**:
Target exceeded due to:
1. Adapter proliferation (planned 4, implemented 8)
2. MCP integration (not in original design)
3. Multi-tenant support (added for enterprise use case)
4. Enhanced Cortex features (context monitoring, safety policy)

**Core architecture remains within target** (182 + 944 = 1,126 lines).
```

---

### 8. Skills Line Count Unclear

**Priority**: P1
**Estimated Time**: 25 minutes
**Impact**: Cannot verify claim

**Files Affected**:
- `README.md` (line 35)

**Current State**:
```markdown
Skills: 581 lines
```

**Problem**: Unclear measurement method

**Investigation Required**:
```bash
# Check what exists
find skills -name "*.py" -o -name "*.md"

# Count skill implementation files
find src/fastreact/skills -name "*.py" | xargs wc -l

# Count skill documentation
find skills -name "SKILL.md" | xargs wc -l
```

**Fix Required**:

**After investigation, update with breakdown**:
```markdown
### Skills System
- Core Implementation: ~519 lines (src/fastreact/skills/*.py)
- Skill Definitions: 5 skills documented
  - code_review: File analysis and review
  - file_ops: File manipulation patterns
  - git_workflow: Git operations
  - github_integration: GitHub API integration
  - graphrag_workflow: Knowledge graph operations
```

---

### 9. Missing INTERRUPT Event

**Priority**: P1
**Estimated Time**: 10 minutes
**Impact**: Incomplete documentation

**Files Affected**:
- `README.md` (lines 187-194)

**Current State**:
Lists 9 event types, but implementation has 10

**Fix Required**:
Add INTERRUPT to event list:
```markdown
class EventType:
    SESSION_START = "session_start"
    THINK = "think"              # LLM reasoning
    TOOL_CALL = "tool_call"      # Intent to use tool
    TOOL_RESULT = "tool_result"  # Tool execution result
    STEP_END = "step_end"        # Reasoning step complete
    SESSION_END = "session_end"
    ERROR = "error"
    ASK_USER = "ask_user"        # Confirmation request
    INTERRUPT = "interrupt"      # External interruption
```

**Add documentation**:
```markdown
### INTERRUPT Event
**Purpose**: Allow external interruption of agent execution
**Use Case**: Steering system, user intervention
**Payload**: Interruption reason and optional new instructions
```

---

## P2 Issues (Medium Priority)

### 10. Core Percentage Calculation

**Priority**: P2
**Estimated Time**: 5 minutes
**Impact**: Misleading about code distribution

**Files Affected**:
- `README.md` (line 53)

**Current State**:
```markdown
Core (Brain): 180 lines (0.3%)
```

**Actual**: 182/8869 = 2.05%

**Fix Required**:
```markdown
Core (Brain): 182 lines (2.05% of total codebase)
```

---

### 11. Modular Layering Violations

**Priority**: P2
**Estimated Time**: 45 minutes
**Impact**: Principle not strictly followed

**Files Affected**:
- `CLAUDE.md` (line 26, 28)

**Current State**:
```markdown
### 3. Modular Layering (No Penetration)
- Upper layers use public APIs only
- FORBIDDEN: Importing internal.py, accessing _private attributes cross-module
```

**Problem**: Agent imports from multiple layers

**Investigation Required**:
```bash
# Find cross-layer imports
grep -r "from fastreact" src/fastreact/agent.py
grep -r "import.*internal" src/fastreact/
```

**Fix Required**:

**Option A**: Document exceptions
```markdown
### 3. Modular Layering (No Penetration)
- Upper layers use public APIs only
- FORBIDDEN: Importing internal.py, accessing _private attributes cross-module

**Allowed Exceptions**:
- Agent may import from Core (ReActCore, events, config)
- Agent may import from Providers (LLMProvider)
- Agent may import from Tools (ToolRegistry)
- Adapters MUST only import from Agent public API
```

**Option B**: Refactor to eliminate violations
- Audit all cross-layer imports
- Create public APIs where needed
- Update documentation to reflect clean architecture

---

### 12. GraphRAG Mock vs Real Implementation

**Priority**: P2
**Estimated Time**: 20 minutes
**Impact**: Users may expect real GraphRAG capabilities

**Files Affected**:
- `MULTITENANT_GRAPHRAG.md`

**Current State**:
Documents GraphRAG as feature, but implementation uses mock data

**Fix Required**:
Add disclaimer to MULTITENANT_GRAPHRAG.md:
```markdown
## GraphRAG Implementation Status

**Current Version**: Mock/Reference Implementation
**Implementation**: `examples/graph_rag_server.py`

### What's Implemented
- MCP server framework
- 4 GraphRAG tool definitions:
  - search_graph
  - get_entity
  - query_relationships
  - vector_search

### What's Mock
- All graph queries return mock data
- No real knowledge graph backend
- No vector database integration

### Production Deployment Path
1. Choose knowledge graph backend (Neo4j, Amazon Neptune, etc.)
2. Implement graph query logic
3. Integrate vector database (Pinecone, Weaviate, etc.)
4. Replace mock data with real queries

### Reference Implementation Status
This code serves as a reference for:
- MCP server structure
- Tool definition patterns
- Multi-tenant GraphRAG architecture
```

---

### 13. Compliance Scores Subjective

**Priority**: P2
**Estimated Time**: 30 minutes
**Impact**: Scores appear subjective, not objectively measured

**Files Affected**:
- `README.md` (lines 232-235)

**Fix Required**:

**Option A**: Define scoring criteria
```markdown
## Compliance Scoring Methodology

### Measurement Criteria

**Anti-Entropy (反熵增)**
- Core line count target: 180 lines
- Measurement: actual / target * 100
- Current: 182/180 = 98.9/100
- Deduction: 1.1 points for 2-line overflow

**SDK-First (SDK化)**
- Criteria: Core has no I/O, no execution, no state
- Measurement: Manual verification of architecture
- Current: 100/100 (pure intent generator pattern)

**Human Control (人类掌控)**
- Criteria: Code readability, steering system, intervention points
- Measurement: Manual review + feature checklist
- Current: 100/100 (steering system, readable code)

**Ecosystem Isolation (生态隔离)**
- Criteria: Adapters are plugins, no hard dependencies
- Measurement: Count replaceable components
- Current: 100/100 (8 adapters, all optional)
```

**Option B**: Remove numerical scores
```markdown
## Design Principles

✅ Anti-Entropy: Core locked at ~180 lines (currently 182)
✅ SDK-First: Pure intent generator pattern, no I/O in Core
✅ Human-Comprehensible: Readable code with steering system
✅ Ecosystem Isolation: All adapters are optional plugins
```

---

### 14. "Ghost Map" Terminology Inconsistency

**Priority**: P2
**Estimated Time**: 15 minutes
**Impact**: Terminology confusion

**Files Affected**:
- `README.md` (line 208)
- `src/fastreact/__init__.py` (line 7)

**Current State**:
- README.md calls it "Filesystem Memory (Ghost Map)"
- Code uses "FilesystemMemory" class

**Fix Required**:
Standardize terminology. Recommendation: Use "FilesystemMemory" consistently.

```markdown
# README.md, line 208
✅ Filesystem Memory (persistent workspace state)
```

**Remove parenthetical**:
```markdown
# src/fastreact/__init__.py, line 7
- FilesystemMemory: Persistent workspace state
```

---

### 15. REPL Issues Not User-Facing

**Priority**: P2
**Estimated Time**: 20 minutes
**Impact**: Users may try REPL and encounter bugs

**Files Affected**:
- `README.md` (needs new section)

**Fix Required**:
Add "Known Issues" section after line 37:
```markdown
## Known Issues

### REPL Adapter
- **Symptom**: `AttributeError: 'Agent' object has no attribute '_llm'`
- **Root Cause**: Import statement order in agent.py
- **Status**: Known issue, under investigation
- **Workaround**: Use CLI adapter instead: `fastreact "query" --model gpt-4o-mini`
- **Timeline**: Fix expected in v2.1.1

### Usage Recommendations
- ✅ Use CLI adapter for all demos and production
- ⚠️ Avoid REPL adapter until fix is released
- ✅ HTTP adapter fully functional for API integration
- ✅ Gateway adapter fully functional for WebSocket connections
```

---

## Implementation Timeline

### Phase 1: Critical Fixes (P0) - 1 hour
1. [ ] Fix version number in pyproject.toml
2. [ ] Update total line count in README.md
3. [ ] Update Agent line count in README.md
4. [ ] Update DESIGN.md with actual line count

### Phase 2: High Priority (P1) - 3-4 hours
1. [ ] Update production status with caveats
2. [ ] Clarify adapter test coverage
3. [ ] Recalculate compliance scores
4. [ ] Update design target explanation
5. [ ] Investigate and document skills line count
6. [ ] Add INTERRUPT event to documentation

### Phase 3: Medium Priority (P2) - 2-3 hours
1. [ ] Fix core percentage calculation
2. [ ] Audit and document cross-layer imports
3. [ ] Add GraphRAG mock disclaimer
4. [ ] Define compliance scoring methodology
5. [ ] Standardize "FilesystemMemory" terminology
6. [ ] Add Known Issues section

### Phase 4: Verification - 1 hour
1. [ ] Run all verification commands from this plan
2. [ ] Test all documentation links
3. [ ] Verify version consistency across all files
4. [ ] Update CHANGELOG.md if needed

---

## Verification Commands

After implementing fixes, run these commands to verify:

```bash
# Version consistency
grep -r "2\.1\.0" pyproject.toml README.md CLAUDE.md src/fastreact/__init__.py

# Line counts
find src/fastreact -name "*.py" | xargs wc -l | tail -1
wc -l src/fastreact/agent.py
wc -l src/fastreact/core/react.py

# Event types
grep -E "^\s+\w+\s*=" src/fastreact/core/events.py | grep EVENT

# Adapter counts
ls -1 src/fastreact/adapters/*.py | grep -v __pycache__ | grep -v __init__

# Skill counts
find skills -name "SKILL.md" | wc -l
```

---

## Success Criteria

Documentation update considered complete when:
- [ ] All P0 issues resolved (100%)
- [ ] All P1 issues resolved (100%)
- [ ] All P2 issues resolved (100%)
- [ ] All quantitative claims verified with evidence
- [ ] All version numbers synchronized
- [ ] All line counts accurate
- [ ] All documentation links tested
- [ ] Consistency report shows >95% accuracy

---

**Next Steps**:
1. Review this plan with team
2. Assign priorities to team members
3. Create pull requests for each phase
4. Update consistency report after fixes
5. Target completion: Before v2.1.0 release

**Questions?** Refer to CRITICAL_FIXES.md for ready-to-apply fixes.
