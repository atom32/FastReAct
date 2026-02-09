# FastReAct Documentation Index

## Overview

FastReAct documentation index. Current version: v1.1.0

---

## Core Documentation (Root Level)

### Essential Reading
- **[README.md](README.md)** - Project overview and features
- **[CLAUDE.md](CLAUDE.md)** - Development rules and constraints (MUST READ for developers)
- **[LICENSE](LICENSE)** - MIT License

### Development
- **[pyproject.toml](pyproject.toml)** - Project configuration and dependencies
- **[setup.py](setup.py)** - Package setup script (version dynamically read from `__init__.py`)

### Configuration
- **[.env.example](.env.example)** - Environment variables template (copy to `.env` and configure)

---

## Code Directories

### Source Code
- **[src/](src/)** - FastReAct v1.1.0 source code (128 Python files)
  - Core engine, tools, LLM providers, MCP integration
  - Graph Agent, Tool Graph v2, SubGraph support
  - Context management, streaming callbacks

### Tests
- **[tests/](tests/)** - Test suite (pytest)

### Examples & Demos
- **[examples/](examples/)** - Usage examples and demos
- **[demos/](demos/)** - Demo scripts
- **[scripts/](scripts/)** - Utility and development scripts

### Web Interface
- **[public/](public/)** - Web UI static files

---

## v2.0 Development

### Research & Planning (Archived)
See **[docs_archive/temp/](docs_archive/temp/)** for v2.0 research:
- `nanobot_deep_analysis.md` - nanobot architecture analysis
- `fastreact_v2_final_plan.md` - v2.0 implementation plan
- `fastreact_v2_architecture_final.md` - Architecture design
- `nanobot_to_fastreact_migration.md` - Migration guide
- `v2_phase_*.md` - Phase-by-phase development documentation (Phases 1-7)

### v2.0 Code
- **[fastreact-v2/](fastreact-v2/)** - v2.0 development directory
  - Lightweight architecture based on nanobot
  - 91.9% code reduction (4,139 lines vs 50,792 lines)
  - Progressive loading, plugin system, MessageBus pattern

---

## Archived Documentation

### v1.0 Documentation
- **[docs_archive/v1_docs/](docs_archive/v1_docs/)** - Archived v1.0 specific docs
  - CHANGELOG.md, INSTALLATION.md, CLI_TROUBLESHOOTING.md
  - IEL.md, SESSION_RESUME.md, MCP integration docs
  - Configuration guides, technical deep dives
  - Development logs and sprint summaries

### Bug Fixes
- **[docs_archive/bugfixes/](docs_archive/bugfixes/)** - Bug fix records

### Sprint Summaries
- **[docs_archive/sprints/](docs_archive/sprints/)** - Sprint summaries

---

## Document Structure

```
FastReAct/
├── README.md                    # Project overview
├── DOCS_INDEX.md               # Documentation index (this file)
├── CLAUDE.md                   # Development rules
├── LICENSE                     # MIT License
│
├── src/                        # v1.1.0 source code
├── tests/                      # Test suite
├── examples/                   # Usage examples
├── demos/                      # Demo scripts
├── scripts/                    # Utility scripts
├── public/                     # Web UI files
│
├── pyproject.toml              # Project configuration
├── setup.py                    # Package setup
├── .env.example                # Environment template
│
├── fastreact-v2/               # v2.0 development directory
│
└── docs_archive/               # Archived documentation
    ├── v1_docs/                # v1.0 specific docs
    ├── temp/                   # v2.0 research & planning
    ├── bugfixes/               # Bug fix records
    └── sprints/                # Sprint summaries
```

---

## Documentation Principles

1. **Single Source of Truth** - Keep one canonical doc per topic
2. **Archive, Don't Delete** - Move outdated docs to `docs_archive/`
3. **No Emojis** - Use text markers: `[OK]`, `[ERROR]`, `[WARNING]`
4. **UTF-8 Encoding** - Specify for all file operations
5. **Cross-Platform** - Use `pathlib.Path`, never hardcode paths

---

## Version Management

**Version**: 1.1.0
**Location**: `src/fastreact/__init__.py`
**Read By**: `pyproject.toml`, `setup.py`

**Do NOT manually edit version in other files** - All version reading is dynamic from `__init__.py`.

---

**Last Updated**: 2026-02-10
