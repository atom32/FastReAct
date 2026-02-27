# OpenClaw Research Summary

**Date**: 2025-02-27
**Purpose**: Understand OpenClaw's architecture for FastReAct improvement

---

## Executive Summary

**Key Finding**: OpenClaw does NOT use MCP protocol. Both OpenClaw and ClawFeed use direct CLI tools and native HTTP requests.

---

## OpenClaw Architecture

### Technology Stack
- **Language**: Node.js 22+
- **Database**: SQLite
- **Extension**: Skills (Markdown) + Tools (TypeScript) + Plugins (TypeScript)

### Tool System

**Built-in Tools** (10+):
- browser-tool, canvas-tool, cron-tool, exec-tool
- sessions-* (5 tools for session management)
- message-tool, image-tool, nodes-tool

**Key Difference from FastReAct**:
- OpenClaw: Direct CLI tool integration
- FastReAct: MCP protocol for external tools

---

## ClawFeed Implementation

### Data Sources
- RSS/Atom feeds - Native HTTP GET requests
- HackerNews API - Native HTTP GET requests
- Twitter/X - Native HTTP GET requests
- GitHub Trending - Native HTTP GET requests
- Reddit - Native HTTP GET requests

### Code Example

```javascript
// ~/clawfeed/src/server.mjs
const mod = url.startsWith('https') ? https : http;
const r = mod.get(url, { headers: {
  'User-Agent': 'AI-Digest/1.0',
  'Accept': 'application/json,*/*'
} }, async (resp) => {
  // Handle response...
});
```

**Characteristics**:
- ❌ Does NOT use MCP protocol
- ❌ Does NOT need MCP servers
- ✅ Uses Node.js native http.get/https.get
- ✅ Completely standalone

---

## OpenClaw's Skills System

### Skill Format

```yaml
# ~/openclaw/skills/blogwatcher/SKILL.md
name: blogwatcher
description: Monitor blogs using blogwatcher CLI
metadata:
  openclaw:
    requires:
      bins: ["blogwatcher"]  # Requires external command
```

### Agent Behavior

1. Check if `blogwatcher` command exists in $PATH
2. If not found, prompt user to install
3. If found, call directly via exec tool

### Example Calls

```bash
# Agent calling blogwatcher skill
exec_tool(command="blogwatcher scan")
exec_tool(command="blogwatcher articles")
```

### More Skills Using CLI Tools

- `1password` → calls `op` CLI
- `apple-notes` → calls `memo` CLI
- `apple-reminders` → calls `remindctl` CLI
- `bear-notes` → calls `grizzly` CLI

**Total**: 59 skills, many using external CLI tools

---

## Comparison: OpenClaw vs FastReAct

| Dimension | OpenClaw | FastReAct Nano |
|-----------|----------|----------------|
| **Data Fetching** | Native HTTP | MCP servers |
| **Tool Integration** | CLI tools (direct) | MCP protocol |
| **Skill Dependencies** | External CLI commands | MCP servers |
| **Failure Handling** | Prompt to install | Skill unusable if MCP fails |
| **Flexibility** | High (any command) | Low (only MCP tools) |

---

## OpenClaw's MCP Support

**OpenClaw HAS an `mcporter` skill**, but it's just 1 of 59 skills:

```yaml
name: mcporter
description: Use mcporter CLI to call MCP servers
requires:
  bins: ["mcporter"]
```

**Key Points**:
- ✅ OpenClaw CAN use MCP (via mcporter skill)
- ✅ But it's OPTIONAL, not required
- ✅ Most skills use CLI tools directly, no MCP

---

## FastReAct's Current Issues

### Problem 1: MCP Configuration Priority

```python
default_paths = [
    Path.home() / ".fastreact/config.json",  # Highest priority
    Path.cwd() / ".fastreact/config.json",
    Path.cwd() / "config.json",
]
```

**Result**:
- `~/.fastreact/config.json` overrides project config
- `mcp_servers/config/shared.json` gets ignored
- Users unclear which config is active

### Problem 2: Skills Tightly Coupled to MCP

**news_aggregator skill**:
```yaml
mcp_servers: [fetch]
recommended_tools: [fetch_fetch]
```

**Result**:
- If fetch MCP server not loaded → Agent says "cannot access news"
- No fallback to exec tool
- Skill cannot work independently

### Problem 3: Missing CLI Tool Support

**What OpenClaw has**:
```yaml
requires:
  bins: ["blogwatcher"]  # Declare external commands
```

**What FastReAct lacks**:
- ❌ No `requires.bins` field
- ❌ Agent cannot check if external commands exist
- ❌ Agent cannot call CLI tools directly

---

## Recommended Solutions

### Solution A: Use exec Tool in Skills ✅ (Implemented)

**Before**:
```yaml
mcp_servers: [fetch]
recommended_tools: [fetch_fetch]
```

**After** (updated in SKILL.md):
```yaml
# No MCP server dependency
# Use exec tool + Python code
```

**Agent calls**:
```bash
# Fetch data using Python httpx
python3 -c "
import httpx
resp = httpx.get('https://hacker-news.firebaseio.com/v0/topstories.json')
print(resp.json())
"
```

**Advantages**:
- ✅ Works immediately, no MCP dependency
- ✅ Similar to OpenClaw's blogwatcher pattern
- ✅ Easy to debug

### Solution B: Implement requires.bins Field

**SKILL.md format**:
```yaml
---
name: news_aggregator_v2
description: News aggregation using external tools
requires:
  bins: [curl, python3]
---
```

**Agent behavior**:
```python
# Check if commands exist
import shutil
for bin_name in skill.requires.bins:
    if not shutil.which(bin_name):
        return f"[ERROR] Required command '{bin_name}' not found"

# Use exec tool
result = await exec_tool.execute(command="python3 -c '...'")
```

### Solution C: Adjust Config Priority

**Suggested priority**:
```python
default_paths = [
    Path.cwd() / ".fastreact/config.json",  # Project config first
    Path.cwd() / "mcp_servers/config/shared.json",  # MCP shared config
    Path.home() / ".fastreact/config.json",  # User config (append)
]
```

**Merge strategy**:
- Project config: Define required MCP servers
- User config: Override LLM API key, personal settings
- Result: Project config + User config merged

---

## Extension Mechanisms

### OpenClaw's 3-Tier System

1. **Skills** (Zero-code)
   - CLI tool wrappers
   - Markdown format
   - 59 skills available

2. **Tools** (TypeScript)
   - Core functionality
   - High-performance operations
   - Browser automation, etc.

3. **Plugins** (TypeScript)
   - Complex extensions
   - Multi-skill workflows
   - Advanced features

### Key Takeaways

**What FastReAct Can Learn**:
1. CLI tool integration is simpler than MCP for many use cases
2. Skills should be able to work independently
3. Fallback mechanisms are important
4. Direct command execution is powerful

**What to Avoid**:
1. Over-reliance on MCP for simple operations
2. Skills that break when MCP servers fail
3. Complex configuration management

---

## Migration Recommendations

### Short-term (Immediate)
- ✅ Use exec tool for simple skills (HTTP, search, JSON)
- ✅ Document MCP as optional, not required
- ✅ Provide CLI-based examples in skills

### Mid-term (1-2 weeks)
- ✅ Implement `requires.bins` field support
- ✅ Add CLI tool availability checking
- ✅ Create 8 core skills using exec pattern

### Long-term (1-2 months)
- ✅ Adjust config file priority
- ✅ Improve MCP fallback mechanisms
- ✅ Document best practices

---

## Conclusion

**OpenClaw's Strengths**:
- Simple CLI tool integration
- Skills work independently
- Direct command execution
- Flexible and extensible

**FastReAct's Strengths**:
- Brain-Body separation architecture
- Event-driven protocol
- MCP for complex integrations
- Multi-tenant support

**Best Approach for FastReAct**:
- Keep 4 core tools minimal
- Use exec tool for simple operations
- Use MCP for complex integrations
- Learn from OpenClaw's CLI-first approach

**The "Nano" Way**:
> "Core tools minimal, skills infinite, exec universal."

---

**Author**: FastReAct Team
**Status**: Research Complete
**Last Updated**: 2025-02-27
