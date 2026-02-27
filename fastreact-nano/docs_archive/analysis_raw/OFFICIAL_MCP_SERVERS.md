# Using Official MCP Servers with FastReAct

FastReAct supports **any MCP server** that uses stdio transport. This means you can directly use servers from npm ecosystem without modification.

## Official MCP Servers You Can Use

### 1. Filesystem (Official)
```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "{user_workspace}"],
  "isolation": "per_user",
  "description": "Filesystem operations"
}
```

### 2. GitHub (Official)
```json
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "isolation": "shared",
  "description": "GitHub integration"
}
```

### 3. SQLite (Official)
```json
{
  "name": "sqlite",
  "command": "npx",
  "args": ["-y", "sqlite-npx", "--db-path", "{user_workspace}/data.db"],
  "isolation": "per_user",
  "description": "SQLite database"
}
```

### 4. Brave Search (Official)
```json
{
  "name": "brave-search",
  "command": "uvx",
  "args": ["mcp-server-brave-search"],
  "isolation": "shared",
  "description": "Brave Search API"
}
```

### 5. Fetch (HTTP Requests)
```json
{
  "name": "fetch",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-fetch"],
  "isolation": "shared",
  "description": "HTTP requests for RSS/API calls"
}
```

## ClawFeed Implementation Using Official Servers

Instead of custom servers, use official ones:

### Configuration: `mcp_servers/config/shared.json`

```json
{
  "schema_version": "1.0",
  "servers": [
    {
      "name": "fetch",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "isolation": "shared",
      "description": "HTTP client for RSS/API calls"
    },
    {
      "name": "sqlite",
      "command": "npx",
      "args": ["-y", "sqlite-npx", "--db-path", "{user_workspace}/news.db"],
      "isolation": "per_user",
      "description": "News storage"
    },
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "{user_workspace}"],
      "isolation": "per_user",
      "description": "File operations for digests"
    }
  ]
}
```

### Updated `news_aggregator` skill

```yaml
---
name: news_aggregator
description: AI-powered news aggregation
version: 1.0.0
tags: [news, aggregation]
mcp_servers: [fetch, sqlite, filesystem]
recommended_tools: [fetch_fetch, sqlite_query, fs_write_file]
---

# News Aggregator Skill

## Instructions

### Fetching RSS News

Use the `fetch` tool:

1. **Fetch RSS feed**:
```
Call fetch_fetch with URL:
https://news.ycombinator.com/rss
```

2. **Parse with LLM**:
The Agent will parse the XML and extract articles.

3. **Store in SQLite**:
```
Call sqlite_query with:
CREATE TABLE IF NOT EXISTS news (id INTEGER PRIMARY KEY, title TEXT, url TEXT UNIQUE, summary TEXT, fetched_at INTEGER)
```

### Key Insight

**No custom MCP servers needed!** The official `fetch` server can handle:
- RSS feeds
- REST APIs
- HackerNews Firebase API (https://hacker-news.firebaseio.com/v0)

## Why FastReAct is Mature

1. **Standard Protocol**: Uses official MCP JSON-RPC
2. **Universal Compatibility**: Works with any stdio MCP server
3. **npm Integration**: Direct npx/uvx support
4. **Zero Custom Code**: No server implementation needed for common use cases

## When to Write Custom Servers

Only when:
1. No official server exists for your need
2. You need special logic not available elsewhere
3. You want to integrate a proprietary system

Otherwise: **Use official servers from npm!**
