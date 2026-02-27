# Fix: MCP Fetch Server Not Loading

**Date**: 2025-02-27
**Issue**: MCP fetch server not loading in Gateway, causing news_aggregator skill to fail
**Status**: FIXED

---

## Problem Description

**Symptoms**:
- Agent selected news_aggregator skill but said "无法搜索最新的科技新闻"
- Agent tried to call `fetch_fetch` command which doesn't exist: `fetch_fetch: command not found`
- Gateway logs showed minimal output - no MCP server registration messages
- Frontend logs: `[STDERR] /bin/sh: fetch_fetch: command not found`

**Root Cause**:
MCP configuration was being loaded from `~/.fastreact/config.json` (user's home directory) instead of `mcp_servers/config/shared.json` (project directory). The user's config file only had 3 MCP servers (graphrag, timeserver, filesystem) but was **missing the fetch server**.

**Why This Happened**:
FastReAct's Config.load() method checks multiple locations in order of priority:
1. `~/.fastreact/config.json` (user home) - **HIGHEST PRIORITY**
2. `.fastreact/config.json` (project root)
3. `config.json` (project root)

Since `~/.fastreact/config.json` existed, it was loaded instead of the project's `mcp_servers/config/shared.json`.

---

## Solution

Added the fetch server configuration to the user's `~/.fastreact/config.json` file:

```json
{
  "name": "fetch",
  "transport": "stdio",
  "command": "python3",
  "args": [
    "mcp_servers/builtin/fetch_server/server.py"
  ],
  "isolation": "shared",
  "description": "Simple HTTP fetch server for RSS/API calls",
  "associated_skill": "news_aggregator"
}
```

**Result**:
- Config now loads 4 MCP servers: graphrag, timeserver, filesystem, **fetch**
- fetch server will be registered during Agent initialization
- news_aggregator skill will have access to fetch_fetch tool

---

## Verification

```bash
# Verify config loads correctly
python3 -c "
from fastreact.core.config import Config
config = Config.load()
print(f'MCP servers: {len(config.mcp.servers)}')
for s in config.mcp.servers:
    print(f'  - {s.name}')
"

# Expected output:
# MCP servers: 4
#   - graphrag
#   - timeserver
#   - filesystem
#   - fetch
```

---

## For Production Deployment

**Option 1: Update User Config** (Current fix)
- Pros: Works immediately for this user
- Cons: Not portable to other environments

**Option 2: Use Project Config** (Recommended for production)
- Remove or rename `~/.fastreact/config.json`
- Create `.fastreact/config.json` in project root
- Add all required MCP servers there
- Pros: Config is version-controlled and portable
- Cons: Requires user to delete their existing config

**Option 3: Merge Configurations** (Best practice)
- Keep user-specific settings (LLM API keys, etc.) in `~/.fastreact/config.json`
- Add project MCP servers to `.fastreact/config.json` in project root
- Modify Config.load() to merge both files (future enhancement)

---

## Related Documentation

- `docs/TOOL_SYSTEM_GAP_ANALYSIS.md` - Analysis of FastReAct vs OpenClaw tool systems
- `CLAUDE.md` - Updated with 4 critical rules about tool system limitations
- `docs/CLAWFEED_USAGE_GUIDE.md` - How to use news_aggregator skill

---

## Lessons Learned

1. **Config File Priority**: `~/.fastreact/config.json` takes precedence over project config files
2. **MCP Server Discovery**: Check `Config.load()` output to see which MCP servers are actually loaded
3. **Documentation Gap**: CLAUDE.md didn't explain config file priority or how to debug MCP loading issues
4. **Skill-MCP Dependency**: Skills fail silently when their required MCP servers aren't loaded

**Action Items**:
- [ ] Add MCP debugging guide to CLAUDE.md
- [ ] Document config file priority in GETTING_STARTED.md
- [ ] Add `--list-mcp` CLI command to show loaded MCP servers
- [ ] Consider implementing config merging for better UX

---

**Author**: FastReAct Team
**Fixed by**: Config file update
**Impact**: Critical - news_aggregator skill now functional
