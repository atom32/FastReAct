# Documentation Index

**Last Updated**: 2025-02-27
**Purpose**: Navigation guide for FastReAct Nano documentation

---

## Essential (Root Level)

### Core Documentation
- **[README.md](../README.md)** - User-facing overview, features, and quick start
- **[CLAUDE.md](../CLAUDE.md)** - Development rules, architecture patterns, iron rules
- **[GETTING_STARTED.md](../GETTING_STARTED.md)** - Detailed installation and setup guide
- **[QUICKSTART.md](../QUICKSTART.md)** - 5-minute tutorial
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and release notes

**Status**: ✅ Clean and focused (5 files only)

---

## Architecture (docs/ARCHITECTURE/)

### Design Documents
- **[DESIGN.md](DESIGN.md)** - Core design principles and patterns
- **[DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md)** - "Nano" philosophy: 4 tools + infinite Skills + exec
- **[DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)** - File organization and project layout

---

## Platform (docs/PLATFORM/)

### Extension Systems
- **[SKILLS_AND_MCP.md](../SKILLS_AND_MCP.md)** - Skills and MCP extension mechanisms
- **[TOOLS_AND_EXTENSIONS.md](TOOLS_AND_EXTENSIONS.md)** - Tool system comparison and best practices
- **[MCP_CALLING_MECHANISM.md](../MCP_CALLING_MECHANISM.md)** - MCP protocol usage guide

---

## Analysis (docs/ANALYSIS/)

### Research and Comparisons
- **[OPENCLAW_RESEARCH.md](OPENCLAW_RESEARCH.md)** - OpenClaw architecture analysis and findings
- **[DYNAMIC_SKILL_SELECTION.md](../DYNAMIC_SKILL_SELECTION.md)** - Advanced skill selection mechanism design

---

## Guides (docs/GUIDES/)

### User and Developer Guides
- **[MULTITENANT_GUIDE.md](../MULTITENANT_GUIDE.md)** - Multi-tenant deployment guide
- **[CONFIG_FILE_LOCATIONS.md](../CONFIG_FILE_LOCATIONS.md)** - Configuration reference

---

## Features (docs/FEATURES/)

### Product Documentation
- **[PRODUCT_ROADMAP.md](../PRODUCT_ROADMAP.md)** - Development roadmap and status

---

## Other Documentation (docs/)

### Feature Documentation
- **[FRONTEND_POLISH_COMPLETE.md](../FRONTEND_POLISH_COMPLETE.md)** - Frontend improvements
- **[MCP_DUAL_TRANSPORT_IMPLEMENTATION.md](../MCP_DUAL_TRANSPORT_IMPLEMENTATION.md)** - HTTP + SSE transport
- **[MCP_SERVERS_STANDARD_STRUCTURE.md](../MCP_SERVERS_STANDARD_STRUCTURE.md)** - MCP server conventions
- **[MCP_ADDITION_IMPROVEMENTS.md](../MCP_ADDITION_IMPROVEMENTS.md)** - MCP CLI tools proposal

### Research & Performance
- **[CONTEXT_MANAGEMENT_RESEARCH.md](../CONTEXT_MANAGEMENT_RESEARCH.md)** - Context efficiency research
- **[PROMPT_RESEARCH_REPORT.md](../PROMPT_RESEARCH_REPORT.md)** - Prompt system research

---

## Archive (docs_archive/)

### Historical Reference Only

#### sprints/
- Phase completion reports
- Sprint summaries
- Historical documentation

#### bug_fixes/
- **[COMMON_PITFALLS.md](../docs_archive/bug_fixes/COMMON_PITFALLS.md)** - Historical bug fixes and lessons learned
- Individual fix documentation (FIX_INFINITE_LOOP.md, etc.)

#### analysis_raw/
- Original analysis documents
- Source material for consolidated docs
- OpenClaw research raw data

**Note**: These are kept for historical reference only. Current documentation is in the main `docs/` directory.

---

## Documentation Statistics

### Before Cleanup (2025-02-27)
- CLAUDE.md: 1,061 lines
- docs/: 86 markdown files
- Root-level: ~15 files
- Overlapping analysis: 11+ documents

### After Cleanup (2025-02-27)
- CLAUDE.md: 933 lines (12% reduction)
- docs/: 79 markdown files
- Root-level: 5 files (67% reduction)
- Consolidated analysis: 3 comprehensive docs

### Quality Improvements
- ✅ CLAUDE.md focused on rules only (no history)
- ✅ docs/ organized by category
- ✅ Overlapping content consolidated
- ✅ All information preserved
- ✅ Better navigation and discoverability

---

## Quick Navigation

### For New Users
1. Start with [README.md](../README.md)
2. Follow [GETTING_STARTED.md](../GETTING_STARTED.md)
3. Reference [QUICKSTART.md](../QUICKSTART.md) for examples

### For Developers
1. Read [CLAUDE.md](../CLAUDE.md) for development rules
2. Study [ARCHITECTURE/DESIGN_PHILOSOPHY.md](ARCHITECTURE/DESIGN_PHILOSOPHY.md)
3. Explore [PLATFORM/TOOLS_AND_EXTENSIONS.md](PLATFORM/TOOLS_AND_EXTENSIONS.md)

### For Contributors
1. Understand [SKILLS_AND_MCP.md](../SKILLS_AND_MCP.md)
2. Review [PLATFORM/](PLATFORM/) documentation
3. Follow patterns in existing skills

---

## Documentation Maintenance

### Before Creating New Documentation

**Decision Tree**:
```
Need to document something?
  ↓
Check DOCS_INDEX.md for similar topics
  ↓
  Found? ──Yes→ UPDATE existing doc
  ↓
   No
  ↓
Is it temporary/development process?
  ↓
  Yes→ Put in docs_archive/sprints/ or docs_archive/temp/
  ↓
  No
  ↓
Create in appropriate directory (see structure above)
Update DOCS_INDEX.md
```

### Quality Checklist

- [ ] No emojis (use [OK], [ERROR], [INFO])
- [ ] UTF-8 encoding (for Chinese content)
- [ ] Links work (test relative links)
- [ ] No hardcoded paths
- [ ] Cross-platform compatible
- [ ] Updated DOCS_INDEX.md

---

**Maintainer**: FastReAct Team
**Last Updated**: 2025-02-27
**Status**: Current
