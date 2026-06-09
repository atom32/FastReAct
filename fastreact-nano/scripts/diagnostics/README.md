# Manual Tests

This directory contains manual test scripts for testing specific features interactively.

## Purpose

These scripts are not part of the automated test suite but are useful for:
- Manual testing and debugging
- One-time verification scripts
- Integration testing with external services
- Performance testing

## Test Scripts

### GraphRAG Tests
- `test_gateway_graphrag.py` - Test Gateway WebSocket + GraphRAG auto-discovery
- `test_graphrag_e2e.py` - End-to-end GraphRAG integration test

### MCP Server Tests
- `test_mcp_timeserver.py` - Test timeserver MCP integration
- `test_timeserver_tool.py` - Test timeserver tool execution
- `test_mcp_tools_direct.py` - Direct MCP tool testing

### SKILL Tests
- `test_skill_injection.py` - Test SKILL injection into system prompt
- `test_skill_selection.py` - Test automatic SKILL selection
- `test_websocket_skill.py` - Test WebSocket + SKILL integration

### Other Tests
- `test_session_start_metadata.py` - Test session metadata
- `test_feishu_gateway.py` - Feishu gateway integration testing

## Running Manual Tests

These scripts should be run directly from the fastreact-nano root:

```bash
# Example
python3 tests/manual/test_gateway_graphrag.py
python3 tests/manual/test_skill_selection.py
```

## Prerequisites

- Gateway must be running on http://localhost:9000
- MCP servers must be configured in ~/.fastreact/config.json
- Required SKILLs must be in skills/builtin/

## Notes

- These are **manual tests** for development/debugging
- Automated tests are in `../unit/` and `../integration/`
- Diagnostic scripts are in `../../scripts/`
- Some tests may require specific setup or API keys
