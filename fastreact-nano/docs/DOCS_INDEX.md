# FastReAct Nano Documentation Index

Last updated: 2026-06-23

This is the maintained documentation center for FastReAct Nano `2.4.2`. Current behavior is verified against the codebase; historical reports are linked only through archive indexes.

## Quick Start

- [Repository README](../../README.md): top-level project entry and service shape.
- [Nano README](../README.md): current backend capabilities, endpoints, and boundaries.
- [5-minute quick start](../GETTING_STARTED.md): install, configure, start, and smoke test.
- [Short quickstart](../QUICKSTART.md): compact local run path.
- [Configuration file locations](CONFIG_FILE_LOCATIONS.md): config search order, recommended paths, secrets, PSKA config.

## Operations

- [Headless service manual](HEADLESS_SERVICE.md): HTTP/SSE endpoints, auth, chat, runs, traces, approvals, policy, MCP diagnostics.
- [Deployment](deployment.md): deployment notes.
- [Security model](security.md): service auth, secrets, policy, approvals, MCP isolation, limits.
- [MCP isolation](security/MCP_ISOLATION.md): deeper MCP user isolation guidance.
- [Directory structure](DIRECTORY_STRUCTURE.md): current project layout and where generated state belongs.

## Architecture

- [Architecture](architecture.md): high-level architecture.
- [Design](DESIGN.md): core design.
- [Design philosophy](ARCHITECTURE/DESIGN_PHILOSOPHY.md): Nano principles.
- [System flow](SYSTEM_FLOW.md): request and execution flow.
- [Execution loop audit](EXECUTION_LOOP_AUDIT.md): ReAct loop review and improvements.
- [Frontend/backend audit](FRONTEND_BACKEND_AUDIT.md): service console and backend boundary.

Related current/historical design material:

- [OpenClaw research](ANALYSIS/OPENCLAW_RESEARCH.md)
- [FastReAct vs nanobot vs openclaw](ANALYSIS/COMPETITIVE_ANALYSIS.md)
- [Layer responsibility analysis](ANALYSIS/LAYER_RESPONSIBILITY_ANALYSIS.md)
- [Message routing comparison](ANALYSIS/MESSAGE_ROUTING_COMPARISON.md)
- [Architecture similarity and migration](ANALYSIS/ARCHITECTURE_SIMILARITY_AND_MIGRATION.md)
- [Adapter refactoring plan](ANALYSIS/ADAPTER_REFACTORING_PLAN.md)
- [Improvement roadmap](ANALYSIS/IMPROVEMENT_ROADMAP.md)

The root `docs/` directory is now a pointer only. Maintained docs belong here.

## API And Service

- [Headless service manual](HEADLESS_SERVICE.md): authoritative endpoint map.
- [Agent session API](AGENT_SESSION_API.md): session API design.
- [Agent session API summary](AGENT_SESSION_API_SUMMARY.md): implementation summary.
- [PSKA / FastReAct protocol](PSKA_FASTREACT_PROTOCOL.md): service boundary and event schema.
- [PSKA integration TODO](PSKA_INTEGRATION_TODO.md): remaining PSKA integration work.

Current endpoint families:

- Health/readiness: `/health`, `/ready`
- Setup/metrics: `/v1/setup`, `/v1/setup/presets`, `/v1/setup/config-draft`, `/v1/metrics`
- Agent invocation: `/v1/chat/completions`
- Runs/traces: `/v1/runs/*`, `/v1/traces/*`
- Tasks: `/v1/tasks/*`
- Approvals: `/v1/approvals/*`
- Policy: `/v1/policy`, `/v1/policy/check`
- Tools/skills: `/v1/tools`, `/v1/skills`, `/v1/skills/diagnostics`
- Workspace profile: `/v1/workspace/profile`

## Integrations

- [PSKA / FastReAct protocol](PSKA_FASTREACT_PROTOCOL.md): PSKA boundary and interop contract.
- [Skills and MCP tools](SKILLS_AND_MCP.md): extension model and how skills differ from tools.
- [MCP calling mechanism](MCP_CALLING_MECHANISM.md): stdio and HTTP MCP transport behavior.
- [How to add skills and MCP](HOW_TO_ADD_SKILLS_AND_MCP.md): implementation guide.
- [Tools and extensions](PLATFORM/TOOLS_AND_EXTENSIONS.md): tool-system notes.
- [Dynamic skill selection](DYNAMIC_SKILL_SELECTION.md): skill routing design.

## Multi-Tenant And Policy

- [Multitenant guide](MULTITENANT_GUIDE.md): single/multi-tenant usage guidance.
- [Multitenant architecture](MULTITENANT_ARCHITECTURE.md): architecture implementation guide.
- [Multitenant skills/MCP audit](MULTITENANT_SKILLS_MCP_AUDIT.md): isolation audit.
- [Multitenant audit report](MULTITENANT_AUDIT_REPORT.md): broader implementation audit.
- [Security model](security.md): policy, auth, and approval posture.

When these docs disagree, treat code plus [HEADLESS_SERVICE.md](HEADLESS_SERVICE.md) and [security.md](security.md) as current. Audit reports may include historical findings.

## Development

- [Development rules](../CLAUDE.md): local development rules.
- [Changelog](../CHANGELOG.md): release history.
- [Examples](../examples/README.md): example programs.
- [Scripts](../scripts/README.md): helper scripts.
- [Tests](../tests/README.md): test suite documentation.
- [Test coverage goals](../tests/COVERAGE.md): coverage notes.
- [Release LLM gate](../tests/release/README.md): release smoke gate.

## Archive

- [Repository archive index](../../docs_archive/INDEX.md): pre-nano, v1, migration, sprint, bugfix, and temporary historical docs.
- [Nano archive index](../docs_archive/INDEX.md): nano-era implementation reports, audits, testing reports, and historical analysis.

Archive documents are not current implementation truth. Use them for background and rationale only.

## Documentation Inventory Rules

Include:

- `README.md`
- `fastreact-nano/README.md`, `GETTING_STARTED.md`, `QUICKSTART.md`, `CHANGELOG.md`, `CLAUDE.md`
- `fastreact-nano/docs/**/*.md`
- focused README files under `examples/`, `scripts/`, `tests/`, `deploy/`, `mcp_servers/`
- `skills/**/SKILL.md` when documenting built-in skill behavior

Exclude from maintained documentation inventory:

- `node_modules`
- `.pytest_cache`
- `MagicMock`
- runtime workspace memory/history such as `workspaces/*/HISTORY.md`, `workspaces/*/MEMORY.md`, `workspaces/*/SOUL.md`, `workspaces/*/AGENTS.md`
- generated logs, test output, coverage output, and temporary reports
- archived files except through archive indexes

## Maintenance Rules

- New current docs go under `fastreact-nano/docs/`.
- Root `docs/` stays a pointer only.
- Update existing docs before creating a new one.
- Add short-lived implementation notes to the appropriate archive.
- Update this index whenever adding, moving, or retiring a user-facing doc.
- Validate endpoint claims against `src/fastreact/adapters/http.py`.
- Validate version claims against `pyproject.toml`.
