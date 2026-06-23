# FastReAct Nano Learning Path

FastReAct Nano is currently a headless HTTP/SSE agentic service. Use this path to learn the project without falling into archived or generated material.

## 1. Start And Run

- [Repository README](../../README.md)
- [Nano README](../README.md)
- [5-minute quick start](../GETTING_STARTED.md)
- [Configuration file locations](CONFIG_FILE_LOCATIONS.md)

Goal: run the daemon, understand where config lives, and send one `/v1/chat/completions` request.

## 2. Service Surface

- [Headless service manual](HEADLESS_SERVICE.md)
- [PSKA / FastReAct protocol](PSKA_FASTREACT_PROTOCOL.md)
- [Security model](security.md)

Goal: understand service auth, streaming events, runs, traces, tasks, approvals, policy, and PSKA boundaries.

## 3. Architecture

- [Architecture](architecture.md)
- [Design](DESIGN.md)
- [Design philosophy](ARCHITECTURE/DESIGN_PHILOSOPHY.md)
- [System flow](SYSTEM_FLOW.md)
- [Directory structure](DIRECTORY_STRUCTURE.md)

Goal: understand the single-agent runtime, service boundary, JSONL persistence, and where source/docs/runtime state belong.

## 4. Extensions

- [Skills and MCP tools](SKILLS_AND_MCP.md)
- [MCP calling mechanism](MCP_CALLING_MECHANISM.md)
- [How to add skills and MCP](HOW_TO_ADD_SKILLS_AND_MCP.md)
- [Tools and extensions](PLATFORM/TOOLS_AND_EXTENSIONS.md)
- [Dynamic skill selection](DYNAMIC_SKILL_SELECTION.md)

Goal: understand the difference between skill guidance and executable tools, plus stdio/HTTP MCP integration.

## 5. Operations And Security

- [Security model](security.md)
- [MCP isolation](security/MCP_ISOLATION.md)
- [Multitenant guide](MULTITENANT_GUIDE.md)
- [Multitenant architecture](MULTITENANT_ARCHITECTURE.md)

Goal: understand policy, approvals, service tokens, MCP isolation, and where historical multi-tenant guidance still needs verification.

## 6. Development

- [Development rules](../CLAUDE.md)
- [Examples](../examples/README.md)
- [Scripts](../scripts/README.md)
- [Tests](../tests/README.md)
- [Changelog](../CHANGELOG.md)

Goal: learn local development conventions and available test/support scripts.

## 7. Historical Context

- [Current documentation index](DOCS_INDEX.md)
- [Repository archive](../../docs_archive/INDEX.md)
- [Nano archive](../docs_archive/INDEX.md)
- [Historical analysis](ANALYSIS/OPENCLAW_RESEARCH.md)

Goal: use archived docs for rationale only. Current implementation truth should come from code plus the maintained docs listed above.
