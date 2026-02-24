# FastReAct Nano - Documentation Index

**Last Updated**: 2025-02-23
**Purpose**: Single source of truth for all documentation

---

## Essential User Documentation

### Getting Started
- **[README.md](../README.md)** - Project overview, installation, quick start
- **[GETTING_STARTED.md](../GETTING_STARTED.md)** - Detailed installation guide
- **[QUICKSTART.md](../QUICKSTART.md)** - 5-minute tutorial

### Development Rules
- **[CLAUDE.md](../CLAUDE.md)** - Development rules, architecture, patterns

---

## Architecture & Design

### Core Architecture
- **[DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)** - File organization
- **[DESIGN.md](DESIGN.md)** - Design principles and patterns

### Platform Concepts
- **[SKILLS_AND_MCP.md](SKILLS_AND_MCP.md)** - Skill system and MCP integration
- **[MCP_CALLING_MECHANISM.md](MCP_CALLING_MECHANISM.md)** - MCP tool usage
- **[MULTITENANT_GUIDE.md](MULTITENANT_GUIDE.md)** - Multi-tenant deployment

---

## Research & Analysis

### Competitive Research
- **[PROMPT_RESEARCH_REPORT.md](PROMPT_RESEARCH_REPORT.md)** - OpenClaw & NanoBot prompt system research
- **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Complete architecture visualization

### Security & Audit
- **[MULTITENANT_AUDIT_REPORT.md](MULTITENANT_AUDIT_REPORT.md)** - Multi-tenant SKILL/MCP isolation audit

### Product Planning
- **[PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)** - Product roadmap (PM-facing, feature prioritization)

---

## Configuration

- **[CONFIG_FILE_LOCATIONS.md](CONFIG_FILE_LOCATIONS.md)** - Config file search paths
- **[MULTITENANT_CONFIG_DESIGN.md](MULTITENANT_CONFIG_DESIGN.md)** - Multi-tenant config

---

## Features & Technical Reference

### Ironclad Features (v2.1.0 - v2.4.1)
- **[FIX_INFINITE_LOOP.md](FIX_INFINITE_LOOP.md)** - Infinite loop protection (25-iteration limit)
- **[FIX_JSON_PARSING.md](FIX_JSON_PARSING.md)** - JSON 5-level cascading repair
- **[FIX_MCP_ZOMBIE_RESURRECTION.md](FIX_MCP_ZOMBIE_RESURRECTION.md)** - MCP auto-restart on crash

### Other Features
- **[SESSION_QUEUE_INTERRUPT.md](SESSION_QUEUE_INTERRUPT.md)** - User interrupt mechanism
- **[MCP_TIMESERVER_INTEGRATION.md](MCP_TIMESERVER_INTEGRATION.md)** - Time server MCP example
- **[MCP_SERVERS_STANDARD_STRUCTURE.md](MCP_SERVERS_STANDARD_STRUCTURE.md)** - MCP server conventions
- **[MCP_DUAL_TRANSPORT_IMPLEMENTATION.md](MCP_DUAL_TRANSPORT_IMPLEMENTATION.md)** - HTTP transport + SSE heartbeat (v2.4.2)
- **[MCP_ADDITION_IMPROVEMENTS.md](MCP_ADDITION_IMPROVEMENTS.md)** - MCP CLI tools proposal (updated for v2.4.2)

### SKILL System
- **[SKILLS_AND_MCP.md](SKILLS_AND_MCP.md)** - Platform core principle & extension mechanisms
- **[SKILL_USAGE_GUIDE.md](SKILL_USAGE_GUIDE.md)** - How to use SKILL system
- **[SKILL_INJECTION_VERIFICATION.md](SKILL_INJECTION_VERIFICATION.md)** - SKILL injection mechanics
- **[MCP_CALLING_MECHANISM.md](MCP_CALLING_MECHANISM.md)** - MCP tool usage guide

---

## Deployment

- **[deploy/README.md](../deploy/README.md)** - Deployment guide (Docker, Cloud, One-Click)

---

## MCP Servers
- **[MCP_SERVERS_STANDARD_STRUCTURE.md](MCP_SERVERS_STANDARD_STRUCTURE.md)** - MCP server conventions

---

## Historical Reference (docs_archive/)

### Testing
- `testing/graphrag/GRAPHRAG_TEST_QUESTIONS.md` - GraphRAG test questions
- `testing/graphrag/GRAPHRAG_SKILL_TRIGGER_QUESTIONS.md` - SKILL trigger questions

### Implementation
- `implementation/neo4j/NEO4J_GRAPHRAG_IMPLEMENTATION.md` - Neo4j GraphRAG implementation

### Development
- `development/mcp/` - MCP development proposals (archived)

### Sprint Reports
- `sprints/` - Sprint planning and retrospectives

### Other Archives
- `development/` - Feature development history
- `implementation/` - Implementation notes
- `reports/` - Status reports and analyses

---

## Quick Navigation

**For Users** (Want to use FastReAct):
1. Read [README.md](../README.md)
2. Follow [GETTING_STARTED.md](../GETTING_STARTED.md)
3. Check [QUICKSTART.md](../QUICKSTART.md) for examples

**For Developers** (Want to extend FastReAct):
1. Read [CLAUDE.md](../CLAUDE.md) - Development rules
2. Read [SKILLS_AND_MCP.md](SKILLS_AND_MCP.md) - Extension mechanisms
3. Check [DESIGN.md](DESIGN.md) - Architecture patterns

**For Contributors** (Want to fix bugs):
1. Check [CLAUDE.md](../CLAUDE.md) - Common pitfalls
2. Look at [FIX_*.md](FIX_INFINITE_LOOP.md) files - Bug fix examples
3. Read [ROBUSTNESS_AUDIT.md](ROBUSTNESS_AUDIT.md) - Testing approach

---

## Documentation Guidelines

### Before Creating New Documentation

1. **Check existing docs** - Search for similar topics
2. **Update instead of create** - Modify existing doc if possible
3. **Get approval** - For new root-level docs

### Where to Put Documentation

| Location | For What |
|----------|----------|
| **Root (`*.md`)** | Essential user-facing docs only (max 10 files) |
| **`docs/`** | Feature docs, guides, reference material |
| **`docs_archive/`** | Historical, sprint reports, temporary notes |

### Quality Checklist

- [ ] No emojis (use `[OK]`, `[ERROR]`, `[INFO]`)
- [ ] UTF-8 encoding (for Chinese)
- [ ] Links work (test relative paths)
- [ ] No hardcoded paths
- [ ] Cross-platform compatible
- [ ] Updated this index (if creating new doc)

---

**Total Active Docs**: 21
**Maintainer**: Claude Code + User
**Next Review**: 2025-02-25
