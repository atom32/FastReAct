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
- **[MULTITENANT_ARCHITECTURE.md](../MULTITENANT_ARCHITECTURE.md)** - Multi-tenant architecture implementation (PageIndex/OpenViking integration guide)
- **[MULTITENANT_AUDIT_REPORT.md](../MULTITENANT_AUDIT_REPORT.md)** - Multi-tenant implementation audit report (2026-03-06)
- **[MULTITENANT_GUIDE.md](../MULTITENANT_GUIDE.md)** - Multi-tenant deployment guide
- **[CONFIG_FILE_LOCATIONS.md](../CONFIG_FILE_LOCATIONS.md)** - Configuration reference

---

## Features (docs/FEATURES/)

### Product Documentation
- **[PRODUCT_ROADMAP.md](../PRODUCT_ROADMAP.md)** - Development roadmap and status

---

## System Documentation (docs/)

### System Architecture
- **[SYSTEM_FLOW.md](../SYSTEM_FLOW.md)** - Complete system flow and execution loop
- **[EXECUTION_LOOP_AUDIT.md](../EXECUTION_LOOP_AUDIT.md)** - ReAct loop audit and improvements

### Session Management
- **[AGENT_SESSION_API.md](../AGENT_SESSION_API.md)** - Session API reference
- **[AGENT_SESSION_API_SUMMARY.md](../AGENT_SESSION_API_SUMMARY.md)** - Session API summary
- **[USER_INTERRUPTION_DEBUG.md](../USER_INTERRUPTION_DEBUG.md)** - User interruption debugging

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

#### Analysis Documents (2025-03-04)
- **[GATEWAY_USER_INTERVENTION_FIX.md](../docs_archive/GATEWAY_USER_INTERVENTION_FIX.md)** - Gateway user intervention optimization
- **[GATEWAY_VS_FEISHU_INTERVENTION.md](../docs_archive/GATEWAY_VS_FEISHU_INTERVENTION.md)** - API comparison analysis
- **[FEISHU_SDK_ARCHITECTURE_ANALYSIS.md](../docs_archive/FEISHU_SDK_ARCHITECTURE_ANALYSIS.md)** - Feishu SDK architecture review
- **[BASE_ADAPTER_ANALYSIS.md](../docs_archive/BASE_ADAPTER_ANALYSIS.md)** - BaseAdapter design problems
- **[ADAPTERS_DEPRECATION_ANALYSIS.md](../docs_archive/ADAPTERS_DEPRECATION_ANALYSIS.md)** - Adapter deprecation recommendations

#### Implementation Reports (2025-03)
- **[MULTITENANT_IMPLEMENTATION_SUMMARY.md](../docs_archive/MULTITENANT_IMPLEMENTATION_SUMMARY.md)** - Multi-tenant implementation details
- **[MULTITENANT_TEST_GUIDE.md](../docs_archive/MULTITENANT_TEST_GUIDE.md)** - Multi-tenant testing guide
- **[USER_INTERVENTION_ANALYSIS.md](../docs_archive/USER_INTERVENTION_ANALYSIS.md)** - User intervention mechanism analysis
- **[USER_INTERVENTION_FIX.md](../docs_archive/USER_INTERVENTION_FIX.md)** - User intervention improvements
- **[VERBOSE_LOGGING_SUMMARY.md](../docs_archive/VERBOSE_LOGGING_SUMMARY.md)** - Verbose logging implementation
- **[DEPLOYMENT_STATUS.md](../docs_archive/DEPLOYMENT_STATUS.md)** - Deployment status report

#### Debug Scripts (Historical)
- **[FEISHU_CONFIG_TEST.py](../docs_archive/FEISHU_CONFIG_TEST.py)** - Feishu configuration validation script
- **[MCP_CHECK_SCRIPT.py](../docs_archive/MCP_CHECK_SCRIPT.py)** - MCP server loading check script
- **[MCP_DEBUG_SCRIPT.py](../docs_archive/MCP_DEBUG_SCRIPT.py)** - MCP debugging utility

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

### Today's Cleanup (2025-03-04)
- Root-level: 5 files (maintained)
- docs/: +1 file (SYSTEM_FLOW.md moved from root)
- docs_archive/: +6 files (implementation reports and analysis)

### Quality Improvements
- ✅ CLAUDE.md focused on rules only (no history)
- ✅ docs/ organized by category
- ✅ Overlapping content consolidated
- ✅ All information preserved
- ✅ Better navigation and discoverability
- ✅ Temporary docs moved to archive

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
**Last Updated**: 2025-03-04
**Status**: Current
