# Tools and Extensions System

**Last Updated**: 2025-02-27
**Status**: Current Philosophy and Best Practices

---

## Overview

FastReAct Nano follows a **"4 core tools + infinite Skills"** philosophy. This approach maintains simplicity while providing unlimited extensibility through the exec tool and Skills ecosystem.

### Core Philosophy

```
FastReAct Nano =
  4 Minimal Core Tools (Stable)
  + Unlimited Skills (Extensible)
  + exec Universal Tool (Powerful)
  + MCP Protocol (Integration)
```

### Design Principles

1. **Core Tools Stay Minimal**: Only 4 tools, never increasing
2. **exec is Universal**: Can replace most specialized tools via bash commands
3. **Skills Provide Solutions**: Knowledge and patterns, not just wrappers
4. **MCP for Complex Integration**: External services, databases, APIs

---

## Tool System Architecture

### Current Core Tools (4)

**Location**: `src/fastreact/tools/`

```
exec_tool.py      # Universal shell command execution
read_file.py      # Read file contents
write_file.py     # Write/create files
edit_file.py      # Edit files (string replacement)
```

**Characteristics**:
- ✅ **Stable API**: These 4 tools will never change
- ✅ **Complete**: Cover all fundamental operations
- ✅ **Minimal**: No unnecessary abstractions
- ✅ **Type-safe**: Full type annotations

---

### OpenClaw Comparison

| Dimension | FastReAct Nano | OpenClaw |
|-----------|----------------|----------|
| **Core Tools** | 4 (stable) | 10+ (growing) |
| **Extension** | Skills + MCP + exec | Skills (CLI) + Tools (TS) + Plugins |
| **HTTP Requests** | exec + curl | http_tool (TypeScript) |
| **Web Search** | exec + curl/ddgr | web_search_tool (TypeScript) |
| **Image Processing** | exec + ImageMagick | image_tool (TypeScript) |
| **Database** | MCP servers | database_tool (TypeScript) |
| **Philosophy** | "Keep core small" | "Add as needed" |

**Key Difference**:
- **FastReAct**: Uses bash commands via exec tool
- **OpenClaw**: Wraps functionality in TypeScript tools

Both approaches work, but FastReAct's is more maintainable and requires less code.

---

## The exec Tool Advantage

### What exec Can Do

The exec tool is **universal** - it can execute any shell command. This means:

#### HTTP Requests (No http_tool needed)

```bash
# GET request
curl -s https://api.example.com

# POST request with JSON
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"key":"value"}' \
  https://api.example.com

# With authentication
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com
```

#### Web Search (No search_tool needed)

```bash
# Using DuckDuckGo
curl -s "https://duckduckgo.com/?q=fastreact+nano" | \
  grep -oP '<a[^>]+class="result__a"[^>]*>.*?</a>' | \
  head -5

# Using ddgr (if installed)
ddgr fastreact nano --json

# Using brave-search (if installed)
brave-search "fastreact nano" --count 5
```

#### JSON Processing (No json_tool needed)

```bash
# Parse and pretty-print JSON
echo '{"name":"test"}' | jq .

# Extract specific field
curl -s https://api.example.com | jq '.data[0].name'

# Filter data
curl -s https://api.example.com | jq '.data[] | select(.age > 18)'

# Convert to CSV
curl -s https://api.example.com | jq -r '.data[] | @csv'
```

#### Image Processing (No image_tool needed)

```bash
# Resize image
convert input.jpg -resize 800x600 output.jpg

# Convert format
convert input.png output.jpg

# Crop image
convert input.jpg -crop 800x600+100+100 output.jpg

# Get image info
identify input.jpg

# Batch process
mogrify -resize 800x600 *.jpg
```

#### Database Operations (No database_tool needed)

```bash
# SQLite query
sqlite3 database.db "SELECT * FROM users WHERE age > 18"

# Export data
sqlite3 database.db ".dump" > backup.sql

# Import data
sqlite3 database.db < backup.sql

# CSV import
sqlite3 database.db ".import --csv data.csv users"
```

#### Git Operations (No git_tool needed)

```bash
# Check status
git status

# Commit changes
git add . && git commit -m "message"

# View log
git log --oneline -10

# Create branch
git checkout -b feature/new-feature
```

#### File Operations (Advanced)

```bash
# Find by name
find . -name "*.py"

# Search by content
grep -r "TODO" ./

# Combined search
find . -name "*.py" | xargs grep "TODO"

# Advanced find
find . -type f -mtime -7 -size +1M
```

#### Scheduled Tasks (No schedule_tool needed)

```bash
# List cron jobs
crontab -l

# Add cron job
(crontab -l 2>/dev/null; echo "* * * * * /path/to/command") | crontab -

# Remove cron job
crontab -l | grep -v "/path/to/command" | crontab -

# Edit crontab
crontab -e
```

---

### When to Use exec vs MCP

#### Use exec Tool When:
- ✅ Functionality is available as bash command
- ✅ Quick prototyping or one-off tasks
- ✅ Simple data processing (jq, grep, awk)
- ✅ System operations (git, file management)

#### Use MCP Servers When:
- ✅ Need state management (databases)
- ✅ Complex protocols (SSH, browser automation)
- ✅ Cross-language integration (calling TypeScript/Go tools)
- ✅ Persistent connections (websockets, streams)

#### Hybrid Approach (Recommended):
- Use exec for simple operations
- Use MCP for complex integrations
- Skills can combine both

---

## Skills: Knowledge and Patterns

### What Are Skills?

Skills are **NOT** just tool wrappers. They are:
1. **Structured Prompts**: Task-specific instructions
2. **Tool Policies**: Which tools to use and when
3. **Reasoning Patterns**: How to approach problems
4. **Best Practices**: Proven solutions

### Skill Structure

```yaml
---
name: example_skill
description: Clear description of what this skill does
version: 1.0.0
tags: [category, keywords]
author: Author name
mcp_servers: [optional_mcp_servers]
recommended_tools: [tool1, tool2]
requirements:
  bins: ["required_command"]  # External commands needed
---

# Skill Name

Detailed description of when and how to use this skill.

## When to Use

Use this skill when you need to:
- Task 1
- Task 2
- Task 3

## How It Works

Step-by-step explanation of the approach.

## Examples

**User**: "Example request"

**Actions**:
1. Step 1
2. Step 2
3. Step 3

## Implementation

### Using exec Tool

\`\`\`bash
# Command examples
command with options
\`\`\`

### Using MCP Tools

- Tool name: parameters
- Tool name: parameters
```

### Skill Development Best Practices

1. **Start Simple**: Use exec tool with bash commands
2. **Declare Dependencies**: Specify required binaries in `requirements.bins`
3. **Provide Examples**: Show common use cases
4. **Explain Reasoning**: Document the problem-solving approach
5. **Test Thoroughly**: Verify commands work on target systems

---

## MCP Integration

### What is MCP?

**MCP (Model Context Protocol)** is a JSON-RPC protocol for integrating external tools and services.

### MCP Server Isolation Modes

FastReAct supports three MCP server isolation modes:

1. **Shared** (`isolation: "shared"`)
   - Single server instance for all users
   - Use case: Stateless services, APIs
   - Example: HTTP fetch server

2. **Per-User** (`isolation: "per_user"`)
   - One server instance per user
   - Use case: Databases, file systems
   - Example: SQLite server

3. **Lazy Per-User** (`isolation: "lazy_per_user"`)
   - Start server on first use
   - Use case: Resource-intensive services
   - Example: Browser automation

### MCP Server Configuration

**Location**: `mcp_servers/config/shared.json`

```json
{
  "name": "example_server",
  "command": "python3",
  "args": ["path/to/server.py"],
  "isolation": "shared",
  "description": "Server description",
  "associated_skill": "skill_name"
}
```

### MCP vs exec

| Aspect | MCP | exec |
|--------|-----|------|
| **Complexity** | High (server process) | Low (direct command) |
| **State Management** | ✅ Yes | ❌ No |
| **Protocol Support** | ✅ Any (HTTP, SSH, etc.) | ⚠️ HTTP only |
| **Startup Cost** | High (subprocess) | Low (fork) |
| **Debugging** | Harder | Easier |
| **Best For** | Complex integrations | Simple operations |

---

## Best Practices

### Tool Selection Guidelines

**For New Functionality**, ask:

1. **Can it be done with bash commands?**
   - Yes → Use exec tool in a Skill
   - No → Continue

2. **Does it need state management or complex protocol?**
   - Yes → Consider MCP server
   - No → Use exec tool

3. **Is it a reusable integration?**
   - Yes → Create MCP server
   - No → Use exec in Skill

### Examples

#### ✅ Good: exec Tool in Skill

```yaml
---
name: fetch_weather
description: Get weather data using curl
requirements:
  bins: ["curl", "jq"]
---

## Instructions

Use `exec` tool with curl to fetch weather:

\`\`\`bash
curl -s "https://wttr.in/${city}?format=j1" | jq '.current_condition[0]'
\`\`\`
```

#### ✅ Good: MCP Server for Database

```python
# MCP server for PostgreSQL
# Provides: query, execute, list_tables tools
# Isolation: per_user (each user gets their own connection)
```

#### ❌ Bad: Creating Core Tools

Don't create new core tools like:
- ❌ `http_tool.py` - Use exec + curl
- ❌ `search_tool.py` - Use exec + ddgr
- ❌ `json_tool.py` - Use exec + jq
- ❌ `git_tool.py` - Use exec + git

---

## 8 Recommended Skills

Based on the "exec is enough" philosophy, here are 8 core skills to create:

### 1. HTTP Operations (`http/`)

**Purpose**: HTTP requests using curl

**Commands**: `curl`, `jq`

```bash
curl -s https://api.example.com | jq .
```

### 2. Web Search (`search/`)

**Purpose**: Web search using DuckDuckGo

**Commands**: `curl`, `grep`, `ddgr`

```bash
ddgr "query" --json
```

### 3. JSON Processing (`json/`)

**Purpose**: JSON parsing and transformation

**Commands**: `jq`

```bash
echo '{"key":"value"}' | jq .
```

### 4. Database Operations (`database/`)

**Purpose**: SQLite database operations

**Commands**: `sqlite3`

```bash
sqlite3 database.db "SELECT * FROM table"
```

### 5. Image Processing (`image/`)

**Purpose**: Image manipulation

**Commands**: `convert`, `identify`

```bash
convert input.jpg -resize 800x output.jpg
```

### 6. Git Operations (`git/`)

**Purpose**: Git workflow automation

**Commands**: `git`

```bash
git add . && git commit -m "message"
```

### 7. Scheduled Tasks (`cron/`)

**Purpose**: Cron job management

**Commands**: `crontab`

```bash
crontab -l
```

### 8. Advanced File Operations (`file/`)

**Purpose**: Advanced file system operations

**Commands**: `find`, `xargs`, `grep`

```bash
find . -name "*.py" | xargs grep "TODO"
```

---

## Comparison with Other Frameworks

### vs mini-claude-code

| Aspect | FastReAct Nano | mini-claude-code |
|--------|----------------|------------------|
| **Core Tools** | 4 | 4 (bash, read, write, edit) |
| **Skills** | 5 built-in, unlimited possible | 4 example skills |
| **exec Tool** | Universal, any command | Universal, any command |
| **Focus** | Production platform | Educational tutorial |

### vs OpenClaw

| Aspect | FastReAct Nano | OpenClaw |
|--------|----------------|----------|
| **Core Tools** | 4 (Python) | 10+ (TypeScript) |
| **Skills** | Markdown + CLI | Markdown + CLI + TS |
| **MCP Support** | ✅ Native (stdio + HTTP) | ❌ None (direct CLI only) |
| **Approach** | "Keep core minimal" | "Add tools as needed" |

**Key Insight**: FastReAct's approach is **more maintainable** because:
- Less code to maintain (4 tools vs 10+ tools)
- More flexible (bash commands vs TypeScript wrappers)
- Easier to extend (Markdown skills vs compiled code)

---

## Troubleshooting

### Common Issues

#### 1. Command Not Found

**Problem**: `exec` tool fails with "command not found"

**Solution**:
```bash
# Check if command exists
which command_name

# Install missing dependency
apt-get install command_name  # Debian/Ubuntu
brew install command_name      # macOS
```

**In Skill**: Declare in `requirements.bins`:
```yaml
requirements:
  bins: ["command_name"]
```

#### 2. MCP Server Not Loading

**Problem**: MCP server fails to load, tools unavailable

**Check**:
```bash
# Test MCP server manually
python3 mcp_servers/builtin/server_name/server.py

# Check Gateway logs
grep "MCP server" /tmp/gateway.log
```

**Solution**: Verify server configuration in `mcp_servers/config/`

#### 3. Skill Not Selected

**Problem**: Agent doesn't use the skill

**Check**:
1. Skill tags match query keywords
2. Skill description is clear
3. `recommended_tools` are available

**Debug**:
```python
from fastreact import Agent
agent = Agent()

# Check skill scores
agent._select_skills_auto("your query here", max_skills=10)
```

---

## Future Direction

### Commitments

1. **4 Core Tools**: Will never increase beyond 4
2. **exec Tool**: Will remain universal and powerful
3. **Skills Ecosystem**: Will continue growing
4. **MCP Support**: Will continue improving

### Not Doing

- ❌ Adding more core tools (http_tool, search_tool, etc.)
- ❌ Wrapping bash commands in Python tools
- ❌ Duplicating functionality available via exec

### Focus Areas

- ✅ Improving Skills (better patterns, examples)
- ✅ Enhancing MCP (better isolation, error handling)
- ✅ Documentation (tutorials, best practices)
- ✅ Developer Experience (easier skill creation)

---

## Conclusion

FastReAct Nano's tool system is **minimal by design, powerful in practice**.

**Core Principles**:
1. 4 tools are enough
2. exec can replace most specialized tools
3. Skills provide knowledge, not just wrappers
4. MCP handles complex integrations

**Benefits**:
- Less code to maintain
- Easier to understand
- More flexible
- Future-proof

**The "Nano" Way**:
> "Less is more, when exec is universal."

---

**Author**: FastReAct Team
**Status**: Current Philosophy
**Last Updated**: 2025-02-27
