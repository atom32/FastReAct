# FastReAct Nano Directory Structure

This document explains the standard directory structure for FastReAct Nano v2.4+.

## Top-Level Directories

```
fastreact-nano/
├── skills/                    # Global SKILL definitions
│   ├── builtin/              # Built-in skills (git_workflow, code_review, etc.)
│   ├── community/            # Community-contributed skills
│   └── custom/               # User-defined skills (gitignored)
│
├── mcp_servers/              # Global MCP server configurations
│   ├── builtin/              # Built-in MCP server implementations
│   ├── config/               # MCP server configuration files
│   │   ├── shared.json       # Shared mode servers (single instance)
│   │   └── per_user.json     # Per-user mode servers (isolated)
│   └── README.md             # MCP server development guide
│
├── workspaces/               # User workspaces (Gateway single-tenant)
│   └── default/              # Default Gateway workspace
│       ├── config.json       # User configuration
│       ├── memory.json       # Conversation memory
│       └── skills/           # User-specific skills (override global)
│
├── src/                      # Core Python code
│   └── fastreact/
│       ├── core/             # ReAct engine, tools, events
│       ├── providers/        # LLM providers (litellm, etc.)
│       ├── mcp/              # MCP tool management
│       ├── skills/           # Skill discovery and loading
│       ├── adapters/         # Gateway, Feishu adapters
│       └── agent.py          # Main Agent orchestration
│
├── examples/                 # Example code and demos
│   ├── async/                # Async/await examples
│   ├── decorators/           # Decorator examples
│   ├── basics/               # Basic Python examples
│   ├── algorithms/           # Algorithm implementations
│   ├── advanced/             # Advanced usage examples
│   ├── demos/                # FastReAct demos
│   └── testing/              # Testing utilities
│
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
│
├── deploy/                   # Deployment configurations
│   ├── docker/               # Dockerfiles
│   └── kubernetes/           # K8s manifests
│
├── docs/                     # User documentation
│   └── DIRECTORY_STRUCTURE.md  # This file
│
├── docs_archive/             # Historical documentation
│   ├── testing/              # Test suite history
│   ├── implementation/       # Feature development history
│   ├── deployment/           # Deployment history
│   └── async/                # Async documentation
│
├── fastreact-nano-web/       # Next.js 14 frontend
│   ├── app/                  # Next.js app router pages
│   ├── components/           # React components
│   └── package.json          # Frontend dependencies
│
├── README.md                 # Main documentation
├── GETTING_STARTED.md        # Quick start guide
├── QUICKSTART.md             # Installation guide
├── CLAUDE.md                 # Development rules
├── CHANGELOG.md              # Version history
└── LICENSE                   # MIT License
```

## Single-Tenant vs Multi-Tenant Deployment

### Gateway (Single-Tenant Mode)

**Use Case**: Development, testing, single-user deployments

**Workspace Location**: `./workspaces/default/`

**Characteristics**:
- All resources within the project directory
- Single workspace for all users
- Skills loaded from `skills/builtin/`
- User-specific skills in `workspaces/default/skills/`
- MCP servers from `mcp_servers/config/`

**Configuration** (`~/.fastreact/config.json`):
```json
{
  "adapter": "gateway",
  "paths": {
    "gateway_workspace": "./workspaces/default",
    "global_skills_dir": "./skills/builtin",
    "user_skills_template": "{user_workspace}/skills",
    "global_mcp_config": "./mcp_servers/config/shared.json"
  }
}
```

### Feishu (Multi-Tenant Mode)

**Use Case**: Production deployments, enterprise environments

**Workspace Location**: `/var/fastreact/tenants/feishu/{user_id}/`

**Characteristics**:
- Workspaces outside project directory (system-level)
- Each user gets isolated workspace
- Skills loaded from `skills/builtin/` + user workspace
- User-specific MCP configurations supported
- Centralized management via Feishu bot

**Configuration** (`~/.fastreact/config.json`):
```json
{
  "adapter": "feishu",
  "feishu": {
    "enable_multitenant": true
  },
  "paths": {
    "global_skills_dir": "./skills/builtin",
    "user_skills_template": "{user_workspace}/skills",
    "global_mcp_config": "./mcp_servers/config/shared.json",
    "user_mcp_config_template": "{user_workspace}/mcp_config.json",
    "feishu_workspace_base": "/var/fastreact/tenants/feishu"
  }
}
```

## Skills Directory Structure

### Global Skills (`skills/builtin/`)

Built-in skills included with FastReAct:

```
skills/builtin/
├── git_workflow/           # Git operations (commit, push, pull)
├── code_review/            # Code review and analysis
├── file_ops/               # File system operations
├── github_integration/     # GitHub API integration
└── graphrag_workflow/      # GraphRAG knowledge search
```

### Community Skills (`skills/community/`)

Community-contributed skills (managed via git):

```
skills/community/
├── .gitkeep                # Placeholder for git tracking
└── (future contributions)
```

### Custom Skills (`skills/custom/`)

User-defined skills (not in git):

```
skills/custom/
├── .gitkeep                # Placeholder for git tracking
└── (user additions - gitignored)
```

## MCP Servers Directory Structure

### Built-in Servers (`mcp_servers/builtin/`)

Custom MCP server implementations:

```
mcp_servers/builtin/
└── .gitkeep                # Placeholder for future servers
```

### Server Configurations (`mcp_servers/config/`)

**`shared.json`** - Shared mode servers:
- Single instance for all users
- Stateless operations
- Read-only resources
- Example: GraphRAG knowledge search

**`per_user.json`** - Per-user mode servers:
- Isolated instance per user
- User-specific resources
- Sensitive operations
- Example: Filesystem operations

## Workspace Directory Structure

### Gateway Workspace

```
workspaces/default/
├── config.json             # User configuration
├── memory.json             # Conversation history
├── skills/                 # User-specific skills (override global)
│   └── .gitkeep
└── mcp_config.json         # User-specific MCP servers (optional)
```

### Feishu Multi-Tenant Workspaces

```
/var/fastreact/tenants/feishu/
├── ou_user_a/
│   ├── config.json
│   ├── memory.json
│   ├── skills/
│   └── mcp_config.json
├── ou_user_b/
│   └── ...
└── ou_user_c/
    └── ...
```

## Configuration Priority Order

For skills loading:
1. User workspace skills (`workspaces/{user}/skills/`)
2. Global built-in skills (`skills/builtin/`)
3. Community skills (`skills/community/`)

For MCP servers:
1. User MCP config (`{user_workspace}/mcp_config.json`)
2. Per-user config (`mcp_servers/config/per_user.json`)
3. Shared config (`mcp_servers/config/shared.json`)

## Environment Variables

Override paths with environment variables:

```bash
# Skills directories
export FASTRACT_SKILLS_DIR="./skills/builtin"
export FASTRACT_USER_SKILLS_TEMPLATE="{user_workspace}/skills"

# MCP servers
export FASTRACT_MCP_CONFIG="./mcp_servers/config/shared.json"
export FASTRACT_USER_MCP_CONFIG_TEMPLATE="{user_workspace}/mcp_config.json"

# Workspaces
export FASTRACT_GATEWAY_WORKSPACE="./workspaces/default"
export FEISHU_BASE_WORKSPACE="/var/fastreact/tenants/feishu"
```

## Migration Guide

### From v2.3 to v2.4+

**Old Structure**:
```
fastreact-nano/
├── skills/                 # All skills in one place
└── workspace/              # Single workspace (old name)
```

**New Structure**:
```
fastreact-nano/
├── skills/
│   └── builtin/           # Built-in skills moved here
└── workspaces/            # Renamed from workspace/
    └── default/           # Default workspace
```

**Migration Steps**:
1. Existing skills automatically moved to `skills/builtin/`
2. `workspace/` renamed to `workspaces/`
3. User-specific configs updated automatically
4. No manual intervention required

## Best Practices

1. **Development**: Use Gateway mode with `workspaces/default/`
2. **Production**: Use Feishu mode with `/var/fastreact/tenants/`
3. **Skills**: Add built-in skills to `skills/builtin/`
4. **Customization**: Add user skills to `workspaces/{user}/skills/`
5. **MCP Servers**: Configure in `mcp_servers/config/` based on isolation needs

## See Also

- [MCP Servers README](../mcp_servers/README.md)
- [Skills and MCP Documentation](SKILLS_AND_MCP.md)
- [Configuration Reference](../README.md#configuration)
