# FastReAct Nano - Multi-Tenant & GraphRAG Integration

This document describes the multi-tenant support, Feishu integration, and GraphRAG tools implementation for FastReAct Nano.

## Overview

FastReAct Nano now supports:

1. **Multi-Tenant Architecture** - Each user has isolated workspace, config, and skills
2. **Feishu Channel Integration** - Bots can receive and respond to Feishu messages
3. **GraphRAG MCP Server** - Knowledge graph tools with mock data
4. **MCP Tool Integration** - MCP tools are automatically registered to Agent

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Feishu Platform                          │
│  (User: ou_xxx, Messages, Events, Cards)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Webhook (POST)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              FeishuChannel Adapter                           │
│  - Extract user_id: ou_xxx                                   │
│  - user_key = "feishu:ou_xxx"                               │
│  - Get user workspace                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ user_key, query
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  MultiTenantManager                          │
│  - user_workspace = workspace/feishu_ou_xxx/                │
│  - user_config = workspace/feishu_ou_xxx/config.json        │
│  - user_skills = workspace/feishu_ou_xxx/skills/            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ query, workspace, config
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  Agent (The Body)                            │
│  - Session: user_key + session_uuid                         │
│  - Tools: Core + MCP (GraphRAG)                             │
│  - Event stream processing                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ AgentEvent stream
                       ↓
┌─────────────────────────────────────────────────────────────┐
│            MCP Tool Manager                                  │
│  - Registers MCP tools to ToolRegistry                      │
│  - Manages MCP server lifecycle                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ MCP call
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           GraphRAG MCP Server                                │
│  - search_graph: Search knowledge graph                     │
│  - get_entity: Get entity details                           │
│  - query_path: Query relationships                         │
│  - vector_search: Vector similarity search                  │
└─────────────────────────────────────────────────────────────┘
```

## User Identification

**Format**: `{channel}:{user_id}`

**Examples**:
- Feishu user: `feishu:ou_1234567890abcdef`
- Web user: `web:user@example.com`
- CLI user: `cli:local`

**Uses**:
- Session prefix: `feishu:ou_xxx:session-uuid`
- Workspace directory: `workspace/feishu_ou_xxx/`
- Configuration isolation

## Quick Start

### 1. Multi-Tenant Agent

```python
from fastreact import Agent
from pathlib import Path

# Create multi-tenant agent
agent = Agent(
    multitenant=True,
    base_workspace=Path.cwd() / "workspace",
)

# Process query for specific user
async for event in agent.run_event_stream(
    "Create file test.txt with content 'Hello'",
    user_key="feishu:ou_123",
):
    print(f"Event: {event.type}, Content: {event.content}")
```

### 2. GraphRAG Integration

**Configuration** (`config.json`):

```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["examples/graph_rag_server.py"]
      }
    ]
  }
}
```

**Usage**:

```python
from fastreact import Agent, Config

# Load config with MCP servers
config = Config.load("config.json")

# Create agent
agent = Agent(config=config)

# Query knowledge graph
async for event in agent.run_event_stream(
    "Search for information about Artificial Intelligence"
):
    if event.type == EventType.SESSION_END:
        print(f"Answer: {event.content}")
```

### 3. Feishu Bot

```python
from fastreact import Agent, Config
from fastreact.adapters.feishu import FeishuChannel
from fastreact.core.config import FeishuConfig

# Load configs
feishu_config = FeishuConfig.from_env()
agent_config = Config.load("config.json")

# Create agent with multi-tenant
agent = Agent(config=agent_config, multitenant=True)

# Create Feishu channel
channel = FeishuChannel(agent, feishu_config)

# Start webhook server
await channel.start()
```

**Environment Variables**:

```bash
export FEISHU_APP_ID="cli_xxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"
export FEISHU_MULTITENANT="true"
export FEISHU_WORKSPACE="/path/to/workspace"
```

## GraphRAG Tools

### search_graph

Search knowledge graph for entities matching query.

```python
result = await agent._tools.execute(
    "graphrag_search_graph",
    {"query": "Machine Learning", "limit": 10}
)
```

### get_entity

Get detailed information about a specific entity.

```python
result = await agent._tools.execute(
    "graphrag_get_entity",
    {"entity_id": "entity_1"}
)
```

### query_relationships

Query relationships between entities.

```python
result = await agent._tools.execute(
    "graphrag_query_relationships",
    {"entity_id": "entity_1", "max_depth": 2}
)
```

### vector_search

Search entities by vector similarity (semantic search).

```python
result = await agent._tools.execute(
    "graphrag_vector_search",
    {"query_text": "Deep Learning", "top_k": 5}
)
```

## Directory Structure

```
FastReAct/
├── workspace/                    # Multi-tenant workspaces
│   ├── feishu_ou_aaa/           # User A workspace
│   │   ├── skills/              # User A skills
│   │   ├── config.json          # User A config
│   │   └── memory.json          # User A memory
│   └── feishu_ou_bbb/           # User B workspace
│       ├── skills/
│       └── config.json
├── skills/                       # Global skills
│   └── graphrag_workflow/
│       └── SKILL.md
├── examples/
│   ├── graph_rag_server.py      # GraphRAG MCP server
│   └── feishu_graphrag_bot.py   # Feishu bot example
└── config.json                   # Agent config
```

## Configuration

### MCP Config

```python
from fastreact import MCPConfig

mcp_config = MCPConfig(
    servers=[
        {
            "name": "graphrag",
            "command": "python3",
            "args": ["examples/graph_rag_server.py"]
        }
    ]
)
```

### Feishu Config

```python
from fastreact import FeishuConfig

feishu_config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="secret",
    enable_multitenant=True,
    base_workspace=Path.cwd() / "workspace",
)
```

### Agent Config

```python
from fastreact import Config

config = Config(
    llm=LLMConfig(model="gpt-4o-mini"),
    mcp=MCPConfig(servers=[...]),
)
```

## Testing

```bash
# Multi-tenant tests
pytest tests/unit/test_multitenant.py -v

# MCP structure tests
pytest tests/integration/test_mcp_structure.py -v

# GraphRAG tests (requires server)
pytest tests/integration/test_graphrag_mcp.py -v
```

## Examples

See `examples/` directory:

- `graph_rag_server.py` - GraphRAG MCP server implementation
- `feishu_graphrag_bot.py` - Complete Feishu bot with GraphRAG

## License

MIT
