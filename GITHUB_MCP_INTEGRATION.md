# GitHub MCP Integration - TODO #16

## Overview

This document describes the integration of `mcp-server-github` into FastReAct, enabling the agent to create issues, pull requests, search code, and interact with GitHub repositories via our custom SimpleMCP-Stdio driver.

**Status**: [CONFIGURED] - Ready for testing
**Milestone**: Strategic expansion to real-world tools
**Compliance**: [Transport Layer Iron Rule] - Uses SimpleMCP-Stdio isolation

---

## Architecture

```
FastReAct Engine (asyncio)
    ↓
MCPClientManager (with FASTREACT_MCP_SIMPLE_CLIENT=true)
    ↓
SimpleMCPStdioManager (stdio client, NO MCP SDK)
    ↓
npx -y @modelcontextprotocol/server-github
    ↓
GitHub API (via GITHUB_PERSONAL_ACCESS_TOKEN)
```

**Key Design Decisions**:
- **No MCP SDK**: Direct JSON-RPC over stdio, avoiding anyio conflicts
- **Environment Variable Security**: PAT passed via env, never hardcoded
- **Docker Compatible**: GitHub PAT injected via docker-compose.yml
- **Multi-Server Ready**: Can run GitHub + Apollo Core concurrently

---

## Prerequisites

### 1. GitHub Personal Access Token

**Required Scopes**:

**Option A: Classic Token (Recommended for Testing)**
- Scope: `repo` (full repository control)
- Get token: https://github.com/settings/tokens

**Option B: Fine-grained Token (Production)**
- Repository permissions: Contents (read/write), Issues (read/write), Pull Requests (read/write)
- Get token: https://github.com/settings/tokens?type=beta

### 2. Install GitHub MCP Server

```bash
# Install globally (recommended)
npm install -g @modelcontextprotocol/server-github

# Or use npx without installation (configured by default)
npx -y @modelcontextprotocol/server-github
```

---

## Configuration

### Step 1: Set Environment Variables

Create or edit `.env` file:

```bash
# Copy from template
cp .env.example .env

# Edit .env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your-token-here
GITHUB_DEFAULT_REPO=your-username/your-repo

# Enable SimpleMCP-Stdio (Iron Rule compliance)
FASTREACT_MCP_SIMPLE_CLIENT=true
```

### Step 2: Configure MCP Server

Add to `config.json`:

```json
{
  "mcp": {
    "enabled": true,
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
      }
    }
  }
}
```

**Or use the provided template**:

```bash
# Merge template with existing config
cp config.github_mcp.json config.json
```

### Step 3: Docker Deployment

Update `docker-compose.yml` (already done):

```yaml
services:
  fastreact:
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}
```

---

## Available Tools

The GitHub MCP server provides the following tools:

### Repository Operations
- **search_repositories**: Search GitHub repositories
- **create_or_update_file**: Create or update files in a repository
- **get_file_contents**: Get file contents from a repository
- **search_code**: Search code within repositories

### Issue Management
- **create_issue**: Create a new issue
- **update_issue**: Update an existing issue
- **search_issues_and_prs**: Search issues and pull requests
- **add_comment**: Add a comment to an issue or PR

### Pull Request Operations
- **create_pull_request**: Create a new pull request
- **update_pull_request**: Update an existing PR
- **review_pull_request**: Review a pull request
- **merge_pull_request**: Merge a pull request

### Repository Management
- **create_repository**: Create a new repository
- **fork_repository**: Fork a repository
- **get_repository_info**: Get repository information

---

## Usage Examples

### Example 1: Create Issue from CLI

```bash
# Start FastReAct REPL
python -m fastreact.cli.main shell

# Inside REPL
> Create a GitHub issue in repo atom32/FastReAct
  Title: "Documentation Restructuring Complete"
  Body: "Restructured CLAUDE.md and DEVELOPMENT_LOG.md for better organization..."
```

### Example 2: Programmatic Usage

```python
import asyncio
from fastreact import FastReAct

async def github_issue_demo():
    agent = FastReAct(
        api_key="your-llm-api-key",
        model="gpt-4",
        enable_mcp=True
    )

    # Agent will use GitHub MCP tool to create issue
    result = await agent.run_async(
        "Create a GitHub issue in atom32/FastReAct "
        "titled 'Test GitHub MCP Integration' "
        "with body 'Testing TODO #16 integration'"
    )

    print(result)

asyncio.run(github_issue_demo())
```

### Example 3: Search Code

```bash
# Inside REPL
> Search for "SimpleMCPStdio" in atom32/FastReAct repository
```

---

## Testing

### Manual Connection Test

```python
import asyncio
from fastreact.tools.simple_mcp_stdio import SimpleMCPStdioManager

async def test_github_mcp():
    config = {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"}
        }
    }

    manager = SimpleMCPStdioManager(config)
    results = await manager.connect_all()

    print("Connection results:", results)

    if results.get("github"):
        tools = await manager.list_tools("github")
        print(f"Available tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool['name']}")

    await manager.disconnect_all()

asyncio.run(test_github_mcp())
```

### Expected Output

```
[INFO] Connecting to 'github' (stdio, simple client)...
[SimpleMCP] Started process: npx -y @modelcontextprotocol/server-github
[SimpleMCP] Session initialized
[INFO] Connected to 'github'
Connection results: {'github': True}
Available tools: 15
  - create_issue
  - create_pull_request
  - search_issues_and_prs
  - push_file
  ...
```

---

## Iron Rule Compliance

### Transport Layer Iron Rule
[COMPLIANT] - No MCP SDK imports in main event loop
- Uses `SimpleMCPStdioManager` (pure asyncio)
- No `anyio` dependencies
- Zero conflict with FastAPI

### Stateless Orchestration Rule
[COMPLIANT] - Idempotent operations via GitHub API
- Create issue: Returns issue URL if exists
- All operations recoverable via GitHub API

### Cross-Platform File System Rule
[COMPLIANT] - Uses `pathlib` throughout
- Config loading: `Path.cwd() / 'config.json'`
- Environment parsing: `os.getenv()` (no hardcoded paths)

---

## Troubleshooting

### Issue 1: "npx: command not found"
**Solution**: Install Node.js and npm
```bash
# Ubuntu/Debian
sudo apt-get install nodejs npm

# macOS
brew install node

# Windows
# Download from https://nodejs.org/
```

### Issue 2: "GITHUB_PERSONAL_ACCESS_TOKEN not set"
**Solution**: Check environment variable
```bash
# Verify token is set
echo $GITHUB_PERSONAL_ACCESS_TOKEN

# Or test in Python
import os
print(os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"))
```

### Issue 3: "401 Bad credentials"
**Solution**: Verify token scopes and expiration
- Classic token: Must have `repo` scope
- Fine-grained token: Must have Contents/Issues/PR permissions
- Check token expiration date

### Issue 4: "MCP server timeout"
**Solution**: Increase timeout in config
```json
{
  "mcp": {
    "servers": {
      "github": {
        "timeout": 60.0
      }
    }
  }
}
```

---

## Security Considerations

### [CRITICAL] Token Storage
- [x] NEVER commit `.env` file to git
- [x] NEVER hardcode PAT in `config.json`
- [x] Use environment variables only
- [x] Rotate tokens regularly

### .gitignore
Ensure `.gitignore` contains:
```
.env
config.json
*.log
```

### Docker Secrets (Production)
For production deployment, use Docker secrets instead of environment variables:
```yaml
services:
  fastreact:
    secrets:
      - github_pat
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN_FILE=/run/secrets/github_pat

secrets:
  github_pat:
    file: ./secrets/github_pat.txt
```

---

## Next Steps (TODO #16)

### Phase 1: Connection Test
- [ ] Verify GitHub MCP server connects successfully
- [ ] List all available tools
- [ ] Test tool schema extraction

### Phase 2: Self-Consistency Test
- [ ] Agent creates issue about documentation refactoring
- [ ] Issue includes:
  - Summary of CLAUDE.md / DEVELOPMENT_LOG.md split
  - Link to commit hash
  - Rationale for architectural decision

### Phase 3: Advanced Features
- [ ] Search code in FastReAct repository
- [ ] Create pull request for new feature
- [ ] Comment on existing issues

### Phase 4: Production Hardening
- [ ] Implement token rotation
- [ ] Add rate limit handling
- [ ] Create audit logs for GitHub operations

---

## Documentation Updates

After successful integration, update:
1. `DEVELOPMENT_LOG.md` - Add "2026-02-05: GitHub MCP Integration Complete"
2. `CHANGELOG.md` - Add new feature entry
3. `README.md` - Add GitHub MCP to feature list

---

## References

- [MCP GitHub Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [GitHub REST API](https://docs.github.com/en/rest)
- [FastReAct MCP Integration History](MCP_INTEGRATION_SUCCESS.md)
- [Transport Layer Iron Rule](CLAUDE.md#transport-layer-iron-rule)

---

**FastReAct + GitHub MCP = Agent with Social Coding Capabilities**
