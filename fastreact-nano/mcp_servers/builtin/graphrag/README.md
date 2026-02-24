# GraphRAG MCP Server

Knowledge graph powered retrieval augmented generation server for FastReAct Nano.

## Overview

This server provides GraphRAG (Graph-based Retrieval Augmented Generation) capabilities through the MCP protocol. It enables knowledge graph construction and querying for enhanced information retrieval.

## Tools

| Tool | Description |
|------|-------------|
| `graphrag_query` | Query knowledge graph using GraphRAG |
| `graphrag_build` | Build knowledge graph from documents |

## Configuration

Add to `~/.fastreact/config.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "transport": "stdio",
        "command": "python3",
        "args": ["mcp_servers/builtin/graphrag/server.py"],
        "isolation": "shared"
      }
    ]
  }
}
```

## Usage

The server is automatically loaded when FastReAct starts. Tools are available with the `graphrag_` prefix:

```
fastreact "使用graphrag_query工具查询知识图谱"
```

## Directory Structure

```
graphrag/
├── server.py       # Main server implementation
├── config.json     # Server metadata
└── README.md       # This file
```

## Migration

This server was migrated from `mcp_servers/builtin/graph_rag_server.py` to follow the standard MCP server structure.
