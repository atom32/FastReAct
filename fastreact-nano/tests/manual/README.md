# Manual Tests

This directory contains manual test scripts and debugging tools.

## Purpose

These scripts are not part of the automated test suite but are useful for:
- Manual testing and debugging
- One-time verification scripts
- Integration testing with external services
- Performance testing

## Running Manual Tests

These scripts should be run directly:

```bash
# Example
python tests/manual/test_mcp_tools_direct.py
```

## Files

- `test_mcp_tools_direct.py` - Direct MCP tool testing
- `test_feishu_gateway.py` - Feishu gateway integration testing

Note: These tests may require specific setup or API keys.
