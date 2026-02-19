# MCP-SKILL Integration Migration Guide

**Version**: 2.1.0
**Last Updated**: 2026-02-18

---

## Overview

FastReAct Nano v2.1 introduces **MCP-SKILL integration**, allowing skills to declare MCP tool dependencies. This enables:

- **Progressive Disclosure**: Skills describe tools conceptually before loading
- **Automatic Tool Loading**: MCP servers load when required skills are selected
- **Better Tool Discovery**: LLM learns about tools through skill descriptions
- **Cleaner Separation**: MCP = tools, Skills = knowledge

---

## What's New?

### 1. Skill Metadata Enhancement

Skills can now declare MCP dependencies in their frontmatter:

```yaml
---
name: github_integration
description: GitHub integration using MCP tools
mcp_servers: [github_mcp]
recommended_tools: [github_mcp_create_or_update_file, github_mcp_push_files]
---
```

**New Fields**:
- `mcp_servers`: List of MCP server names this skill requires
- `recommended_tools`: List of specific tool names to recommend

### 2. MCP Server Configuration

MCP servers can now be associated with skills:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "github_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "associated_skill": "github_integration",
        "description": "GitHub integration for repositories and PRs"
      }
    ]
  }
}
```

**New Fields**:
- `associated_skill`: Optional skill name this server belongs to
- `description`: Server description for tool discovery

### 3. Automatic Tool Loading

When you run the agent with skills:

```python
# Agent loads only the MCP servers required by specified skills
await agent.run("Create a GitHub PR", skills=["github_integration"])
```

The agent:
1. Detects `github_integration` skill requires `github_mcp`
2. Loads only `github_mcp` server
3. Injects tool descriptions into system prompt
4. LLM knows about the tools before calling them

---

## Migration Paths

### Option 1: No Changes (Backward Compatible)

**Your current setup continues to work without modifications.**

```json
// Old config still works
{
  "mcp": {
    "servers": [
      {
        "name": "github_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      }
    ]
  }
}
```

All MCP servers load at startup, regardless of skills.

**Pros**: No changes needed
**Cons**: No progressive disclosure, all tools loaded immediately

---

### Option 2: Associate Servers with Skills (Recommended)

Link MCP servers to skills for automatic loading.

#### Step 1: Update Skill Frontmatter

Edit your `SKILL.md` files:

```yaml
---
name: my_skill
description: My skill description
mcp_servers: [mcp_server_name]
recommended_tools: [mcp_server_name_tool1, mcp_server_name_tool2]
---
```

#### Step 2: Update MCP Server Config

Add `associated_skill` to your servers:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "mcp_server_name",
        "command": "npx",
        "args": ["-y", "@some/server"],
        "associated_skill": "my_skill",
        "description": "Description of what this server does"
      }
    ]
  }
}
```

#### Step 3: Use Skills in Agent Calls

```python
# MCP server loads automatically when skill is used
result = await agent.run("Do something", skills=["my_skill"])
```

**Pros**:
- Lazy loading (faster startup)
- Progressive tool disclosure
- Better user experience

**Cons**:
- Requires config updates
- Skills must be specified explicitly

---

## Step-by-Step Migration Example

### Scenario: Adding GitHub Integration

#### Before (v2.0)

```json
{
  "mcp": {
    "servers": [
      {
        "name": "github_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      }
    ]
  }
}
```

```python
# All MCP tools loaded at startup
agent = Agent()
result = await agent.run("Create a PR on GitHub")
# LLM must discover tools through trial-and-error
```

#### After (v2.1)

**Step 1**: Create skill with MCP dependencies

`skills/github_integration/SKILL.md`:
```yaml
---
name: github_integration
description: GitHub integration using MCP tools
mcp_servers: [github_mcp]
recommended_tools: [github_mcp_create_or_update_file]
---
```

**Step 2**: Associate server with skill

```json
{
  "mcp": {
    "servers": [
      {
        "name": "github_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "associated_skill": "github_integration",
        "description": "GitHub integration for repositories and PRs"
      }
    ]
  }
}
```

**Step 3**: Use the skill

```python
# MCP server loads only when needed
result = await agent.run(
    "Create a PR on GitHub",
    skills=["github_integration"]
)
```

---

## Advanced Usage

### Multiple Skills with Shared MCP Servers

One MCP server can support multiple skills:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "filesystem_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed"],
        "associated_skill": null,  // Global server (no specific skill)
        "description": "File system operations"
      }
    ]
  }
}
```

```yaml
# skills/file_management/SKILL.md
---
name: file_management
mcp_servers: [filesystem_mcp]
---

# skills/backup/SKILL.md
---
name: backup
mcp_servers: [filesystem_mcp]
---

# Both skills can use the same MCP server
```

### Global vs. Skill-Specific Servers

**Global Servers** (no `associated_skill`):
- Always load at startup
- Available to all skills
- Use for common tools (filesystem, database, etc.)

**Skill-Specific Servers** (with `associated_skill`):
- Load only when skill is used
- Isolated to specific skill
- Use for specialized tools (GitHub, GitLab, etc.)

### Tool Recommendations in Skills

Skills can recommend specific tools:

```yaml
---
name: database_admin
description: Database administration skills
mcp_servers: [postgres_mcp]
recommended_tools: [
    postgres_mcp_query,
    postgres_mcp_execute,
    postgres_mcp_list_tables
]
---
```

This helps the LLM understand which tools are most relevant.

---

## Troubleshooting

### MCP Server Not Loading

**Problem**: MCP server doesn't load when skill is specified.

**Solutions**:
1. Check skill name matches exactly (case-sensitive)
2. Verify `mcp_servers` list in skill frontmatter
3. Check `associated_skill` in server config
4. Ensure MCP server name is unique

```json
// Correct: names match
{
  "mcp": {
    "servers": [{
      "name": "github_mcp",  // <- matches skill's mcp_servers
      "associated_skill": "github_integration"  // <- matches skill name
    }]
  }
}
```

### Tools Not Appearing in System Prompt

**Problem**: MCP tools don't show up in system prompt.

**Solutions**:
1. Ensure skill is selected (auto-selection or explicit)
2. Check MCP server loaded successfully (no errors in logs)
3. Verify tool discovery service indexed the tools
4. Check skill frontmatter has `mcp_servers` field

### All MCP Servers Loading at Startup

**Problem**: All MCP servers load regardless of skills.

**Reason**: Backward compatibility mode.

**Solution**: Add `associated_skill` to servers to enable lazy loading.

---

## Configuration Examples

### Example 1: Development Workflow

```json
{
  "mcp": {
    "servers": [
      {
        "name": "github_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "associated_skill": "github_integration",
        "description": "GitHub operations"
      },
      {
        "name": "git_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-git"],
        "associated_skill": "git_workflow",
        "description": "Git version control"
      }
    ]
  }
}
```

```python
# Use both skills together
await agent.run(
    "Create a feature branch and push to GitHub",
    skills=["git_workflow", "github_integration"]
)
```

### Example 2: Data Analysis

```json
{
  "mcp": {
    "servers": [
      {
        "name": "postgres_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"],
        "associated_skill": "database_query",
        "description": "PostgreSQL database access"
      },
      {
        "name": "filesystem_mcp",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"],
        "associated_skill": null,
        "description": "File system access (global)"
      }
    ]
  }
}
```

```python
# Load only database MCP server
await agent.run(
    "Query user data from database and save to CSV",
    skills=["database_query"]
)
```

---

## Best Practices

### 1. Skill Naming

Use descriptive, consistent names:
- ✅ `github_integration`
- ✅ `database_query`
- ❌ `github`
- ❌ `db`

### 2. MCP Server Naming

Include `_mcp` suffix to distinguish from native tools:
- ✅ `github_mcp`
- ✅ `postgres_mcp`
- ❌ `github`
- ❌ `postgres`

### 3. Server Descriptions

Provide clear descriptions for tool discovery:
- ✅ "GitHub integration for repositories and PRs"
- ❌ "GitHub server"

### 4. Skill Granularity

Create focused skills with specific MCP dependencies:
- ✅ `github_integration` → `github_mcp`
- ✅ `gitlab_integration` → `gitlab_mcp`
- ❌ `vc_integration` → both `github_mcp` and `gitlab_mcp`

### 5. Progressive Disclosure

Start with skill description, then tools:
1. Skill frontmatter describes capabilities
2. System prompt includes tool summary
3. LLM calls tools when needed

---

## Testing Your Migration

### Test 1: Verify MCP Loading

```python
import asyncio
from fastreact import Agent

async def test_mcp_loading():
    agent = Agent()

    # Load MCP servers with skill requirement
    await agent._load_mcp_servers(required_skills=["github_integration"])

    # Check if server loaded
    print("Servers:", agent._mcp_manager.list_servers())
    print("Tools:", agent._mcp_manager.list_mcp_tools())

asyncio.run(test_mcp_loading())
```

### Test 2: Verify Tool Discovery

```python
async def test_tool_discovery():
    agent = Agent()
    await agent._load_mcp_servers()

    # Check discovery service
    tools = agent._mcp_discovery.get_tools_for_skill("github_integration")
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"Description: {tool.description}")

asyncio.run(test_tool_discovery())
```

### Test 3: End-to-End Test

```python
async def test_e2e():
    agent = Agent()

    # Should auto-select github_integration skill
    result = await agent.run("Create a pull request on GitHub")

    print("Result:", result)

asyncio.run(test_e2e())
```

---

## Summary

| Aspect | v2.0 (Before) | v2.1 (After) |
|--------|---------------|--------------|
| MCP Loading | All at startup | Lazy loading with skills |
| Tool Discovery | Trial-and-error | Skill-guided |
| Server Config | Basic | Skill association |
| Skill Metadata | Simple | MCP dependencies |
| System Prompt | Base only | Includes tool summary |

---

## Need Help?

- See example: `skills/github_integration/SKILL.md`
- Config example: `config.example.json`
- Test script: `examples/mcp_skill_demo.py`

**Questions?** Open an issue on GitHub!
