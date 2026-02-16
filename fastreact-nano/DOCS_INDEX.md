# FastReAct Nano - Documentation Index

## Getting Started

- [README.md](README.md) - Project overview and features
- [GETTING_STARTED.md](GETTING_STARTED.md) - Installation and quick start guide
- [QUICKSTART.md](QUICKSTART.md) - SiliconFlow API quick start
- [QUICKSTART_WEB.md](QUICKSTART_WEB.md) - **Streamlit Web UI quick start**
- [QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md) - **Docker deployment quick start**
- [USAGE.md](USAGE.md) - Detailed usage instructions

## Core Features

### Skills System
- [SKILLS_INTEGRATION_COMPLETE.md](SKILLS_INTEGRATION_COMPLETE.md) - Skills injection into system prompts
- [SKILLS_AUTO_SELECTION.md](SKILLS_AUTO_SELECTION.md) - Automatic skill selection with progressive disclosure

## Development

**START HERE FOR DEVELOPMENT**:
- [CLAUDE.md](CLAUDE.md) - **Development rules, architecture patterns, pitfalls, quick reference**

### Testing
- [tests/README.md](tests/README.md) - Test suite documentation and current status
- [TEST_REPORT.md](TEST_REPORT.md) - **Comprehensive test implementation report (Phase 1 complete)**
- `tests/unit/` - Unit tests (pytest, 198 passing)
  - [test_safety.py](tests/unit/test_safety.py) - Safety system tests (37 tests, 100% pass)
  - [test_agent.py](tests/unit/test_agent.py) - Agent core tests (63 tests)
  - [test_events.py](tests/unit/test_events.py) - Event protocol tests (28 tests, 96% pass)
  - [test_context.py](tests/unit/test_context.py) - Context management tests (30 tests, 97% pass)
- `tests/integration/` - Integration tests (pytest, 21 tests)
- [run_tests.py](run_tests.py) - Unified test runner

### Release
- [RELEASE_NOTES.md](RELEASE_NOTES.md) - Version history and changelog

### Planning & Analysis
- [ROADMAP.md](ROADMAP.md) - **Development roadmap (Phases 1-6, through Month 6)**
- [COMPETITIVE_ANALYSIS.md](COMPETITIVE_ANALYSIS.md) - **FastReAct vs Nanobot comparison**

## Archive

Historical documentation is archived in `docs_archive/` (reference only):

### Development Docs
- `docs_archive/development/AGENT_IMPROVEMENTS.md` - Agent layer enhancements
- `docs_archive/development/CLI_ENHANCED.md` - CLI development history
- `docs_archive/development/SKILLS_INTEGRATION_COMPLETE.md` - Skills injection implementation
- `docs_archive/development/SKILLS_AUTO_SELECTION.md` - Automatic skill selection
- `docs_archive/sprints/` - Sprint summaries and design docs

### Testing Docs
- `docs_archive/testing/TEST_SUITE_COMPLETE.md` - Test suite completion report
- `docs_archive/testing/TEST_SUITE_IMPROVEMENTS.md` - Recent improvements
- `docs_archive/testing/TEST_SUITE_UNIFICATION.md` - Unified testing framework
- `docs_archive/testing/TEST_COVERAGE_ANALYSIS.md` - Coverage analysis (50% → 70%)

### Reports
- `docs_archive/reports/E2E_TEST_REPORT.md` - End-to-end testing results
- `docs_archive/reports/STEERING_COMPARISON.md` - Steering mechanism comparison
- `docs_archive/reports/SUMMARY.md` - Project summary
- `docs_archive/reports/PROJECT_STATUS.md` - Status reports
- `docs_archive/reports/README_NANO.md` - v2.0 README (archived)

## Documentation Conventions

**File Naming**:
- Descriptive names with underscores
- UPPERCASE for major features (SKILLS_*, CLI_*)
- Lowercase for general docs (readme, usage)

**Content Organization**:
- Root directory: Active, user-facing documentation (7-8 core docs)
- Archive: Historical reference only
- Tests: Organized in `tests/unit/` and `tests/integration/`

**Updating Guidelines**:
1. Check if similar doc exists before creating new
2. Update existing docs instead of duplicating
3. Archive outdated docs (don't delete)
4. Keep this index updated
5. Test files go in `tests/`, not root directory

## Quick Navigation

**For Users**:
- New to FastReAct? Start with [GETTING_STARTED.md](GETTING_STARTED.md)
- Using SiliconFlow? See [QUICKSTART.md](QUICKSTART.md)
- Want to use skills? Read [SKILLS_AUTO_SELECTION.md](SKILLS_AUTO_SELECTION.md)

**For Developers**:
- **START HERE**: [CLAUDE.md](CLAUDE.md) - Development rules and architecture
- Run tests: `pytest tests/unit/` or `python3 tests/integration/test_*.py`
- Implementation details: Check archived development docs
- Test coverage: Review integration test scripts
