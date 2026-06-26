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
├── src/                      # Core Python code
│   └── fastreact/
│       ├── core/             # ReAct engine, tools, events
│       ├── providers/        # LLM providers (litellm, etc.)
│       ├── mcp/              # MCP tool management
│       ├── skills/           # Skill discovery and loading
│       ├── adapters/         # HTTP/SSE and CLI adapters
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

### Local Single-Workspace Mode

**Use Case**: Development, testing, single-user deployments

**Workspace Location**: `~/FastReAct_workspaces/single/default/`

**Characteristics**:
- Runtime data is outside the project directory
- Single workspace for all users
- Skills loaded from `skills/builtin/`
- User-specific skills in `~/FastReAct_workspaces/single/default/skills/`
- MCP servers from `mcp_servers/config/`
- `paths.gateway_workspace` remains as a legacy explicit override

**Configuration** (`~/.fastreact/config.json`):
```json
{
  "paths": {
    "workspaces_root": "~/FastReAct_workspaces",
    "global_skills_dir": "./skills/builtin",
    "user_skills_template": "{user_workspace}/skills",
    "global_mcp_config": "./mcp_servers/config/shared.json"
  }
}
```

### Multi-Tenant Mode

**Use Case**: Production deployments, enterprise environments

**Workspace Location**: `~/FastReAct_workspaces/tenants/{tenant_key}/users/{safe_user_id}/`

**Characteristics**:
- Workspaces outside project directory
- Each user gets isolated workspace
- Skills loaded from `skills/builtin/` + user workspace
- User-specific MCP configurations supported
- Tenant defaults to the prefix before `:` in `user_key` unless an authenticated identity provides `tenant_key`

**Configuration** (`~/.fastreact/config.json`):
```json
{
  "paths": {
    "workspaces_root": "~/FastReAct_workspaces",
    "global_skills_dir": "./skills/builtin",
    "user_skills_template": "{user_workspace}/skills",
    "global_mcp_config": "./mcp_servers/config/shared.json",
    "user_mcp_config_template": "{user_workspace}/mcp_config.json"
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

### Local Single Workspace

```
~/FastReAct_workspaces/single/default/
├── config.json             # User configuration
├── memory.json             # Conversation history
├── skills/                 # User-specific skills (override global)
│   └── .gitkeep
└── mcp_config.json         # User-specific MCP servers (optional)
```

### Multi-Tenant Workspaces

```
~/FastReAct_workspaces/
└── tenants/
    └── acme/
        └── users/
            ├── sso_user_a/
            │   ├── config.json
            │   ├── memory.json
            │   ├── skills/
            │   └── mcp_config.json
            └── sso_user_b/
                └── ...
```

Legacy `paths.gateway_workspace` can still point to an explicit single
workspace for older deployments, but active multi-tenant layout is rooted at
`paths.workspaces_root`.

## Configuration Priority Order

For skills loading:
1. User workspace skills (`~/FastReAct_workspaces/tenants/{tenant}/users/{user}/skills/`)
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
export FASTREACT_WORKSPACES_ROOT="~/FastReAct_workspaces"
export FASTREACT_GATEWAY_WORKSPACE="~/FastReAct_workspaces/single/default"  # legacy override
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
└── src/
```

**Migration Steps**:
1. Existing skills automatically moved to `skills/builtin/`
2. Runtime workspace data should move outside the repo to `~/FastReAct_workspaces`
3. Legacy `paths.gateway_workspace` can be kept temporarily for single-workspace deployments
4. Multi-tenant deployments should adopt `tenants/{tenant}/users/{user}/`

## Best Practices

1. **Development**: Use local single-workspace mode with `~/FastReAct_workspaces/single/default/`
2. **Production**: Use multi-tenant mode with `~/FastReAct_workspaces/tenants/{tenant}/users/{user}/`
3. **Skills**: Add built-in skills to `skills/builtin/`
4. **Customization**: Add user skills to `{user_workspace}/skills/`
5. **MCP Servers**: Configure in `mcp_servers/config/` based on isolation needs

## See Also

- [MCP Servers README](../mcp_servers/README.md)
- [Skills and MCP Documentation](SKILLS_AND_MCP.md)
- [Configuration Reference](../README.md#configuration)
