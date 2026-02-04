# Fix: npx command not found on Windows

## Problem
```
FileNotFoundError: [WinError 2] 系统找不到指定的文件。
```

## Root Cause
GitHub MCP server requires `npx` (comes with Node.js), but Node.js is not installed on your system.

---

## Solution Options

### Option 1: Install Node.js (Recommended)

**Download**: https://nodejs.org/

1. Visit https://nodejs.org/
2. Download LTS version (Windows Installer)
3. Run installer with default settings
4. Restart PowerShell

**Verify installation**:
```powershell
node --version
npm --version
npx --version
```

**Then retry REPL**:
```powershell
python -m fastreact.cli.main shell
```

---

### Option 2: Use Full Path to npx

If Node.js is installed but not in PATH:

```powershell
# Find npx location
where.exe npx

# Or check common paths
C:\Program Files\nodejs\npx.exe
C:\Users\[YourUser]\AppData\Roaming\npm\npx.cmd
```

Then update `config.json`:
```json
"command": "C:\\Program Files\\nodejs\\npx.cmd"
```

---

### Option 3: Skip GitHub MCP for Now

Comment out github server in `config.json`:
```json
"mcp": {
  "enabled": true,
  "servers": {
    // "github": { ... },  // Temporarily disabled
    "apollo_core": { ... }
  }
}
```

---

## Expected Output After Installing Node.js

```
[INFO] Connecting to 'github' (stdio, simple client, no SDK)...
[SimpleMCP] Started process: npx -y @modelcontextprotocol/server-github
[INFO] Session initialized
[INFO] Connected to 'github'
[INFO] Loaded 15 tools from 'github'
- create_issue
- create_pull_request
- search_code
...
```

---

## Why This Happened

GitHub MCP server (`@modelcontextprotocol/server-github`) is a Node.js package distributed via npm. It requires:
- `node` - JavaScript runtime
- `npm` - Node package manager
- `npx` - Package executor (runs packages without installing)

**Alternative**: If you prefer not to install Node.js, we could:
1. Use GitHub REST API directly (build custom tool)
2. Find alternative MCP servers (Python-based)
3. Use GitHub CLI (`gh`) instead

---

## Recommendation

**Install Node.js LTS** from https://nodejs.org/

It's a one-time setup that enables:
- GitHub MCP server
- Many other MCP tools (most are Node.js-based)
- Modern web development tools

Download size: ~30MB
Install time: 2 minutes
