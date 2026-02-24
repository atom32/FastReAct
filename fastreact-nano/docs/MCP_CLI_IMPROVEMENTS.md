# MCP能力添加改进方案

**日期**: 2025-02-24
**状态**: 提案 (部分已实现 v2.4.2)
**最后更新**: 2025-02-24

---

## 实现状态 (v2.4.2)

### ✅ 已实现

| 方案 | 状态 | 说明 |
|------|------|------|
| **方案D: 统一配置管理** | ✅ 完成 | 标准目录结构 + 魔法路径 |
| **魔法路径支持** | ✅ 完成 | `@builtin/` 自动解析 |
| **HTTP 传输** | ✅ 完成 | stdio + HTTP 双传输 |
| **凭证管理** | ✅ 完成 | 环境变量优先级 |

### ⏳ 待实现

| 方案 | 优先级 | 工作量 | 状态 |
|------|--------|--------|------|
| **方案A: MCP模板生成器** | P1 | 1-2天 | 待实现 |
| **方案B: 配置验证工具** | P1 | 1天 | 待实现 |
| **方案C: 热重载支持** | P2 | 3-5天 | 待实现 |
| **方案E: Marketplace集成** | P3 | 1周 | 待实现 |

---

## 当前流程

### 现状 (v2.4.2 改进后)

添加MCP能力现在需要以下步骤：
1. 创建MCP server目录（标准结构）
2. 编写server代码（继承SimpleMCPServer）
3. （可选）编辑`~/.fastreact/config.json`（支持魔法路径）
4. （可选）创建对应的SKILL
5. 重启Gateway服务

**改进点**：
- ✅ 标准目录结构：`mcp_servers/builtin/{name}/server.py`
- ✅ 魔法路径简化配置：`@builtin/{name}/server.py`
- ✅ 凭证安全分离：`credentials.json` + 环境变量

### 剩余问题

| 问题 | 影响 | 严重性 | 优先级 |
|------|------|--------|--------|
| **手动编写代码** | 每次都要从头写server代码 | 中 | P1 |
| **无验证工具** | 配置错误只能在运行时发现 | 高 | P1 |
| **无模板生成** | 没有脚手架代码生成 | 中 | P1 |
| **需要重启** | 添加server需要重启Gateway | 低 | P2 |

---

## 未实现方案详情

### 方案A: MCP Server模板生成器 (P1, 高价值)

**目标**: 提供MCP server脚手架生成工具

**实现**: CLI命令 `fastreact add-mcp`

```bash
# 使用方式
fastreact add-mcp my_server --description "My custom MCP server"

# 自动生成：
# - mcp_servers/builtin/my_server/server.py (模板代码)
# - mcp_servers/builtin/my_server/config.json (元数据)
# - mcp_servers/builtin/my_server/README.md (文档)
# - skills/builtin/my_server_workflow/SKILL.md (SKILL模板，可选)
```

**生成代码模板**:
```python
# mcp_servers/builtin/my_server/server.py
"""
FastReAct Nano - My Server MCP Server

MCP server for custom functionality.
"""

from fastreact.mcp.server import SimpleMCPServer
from typing import Any, Dict

class MyMCPServer(SimpleMCPServer):
    """My custom MCP server"""

    def __init__(self):
        super().__init__()
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools"""
        self.register_tool(
            name="my_tool",
            description="Description of what this tool does",
            input_schema={
                "type": "object",
                "properties": {
                    "param": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param"]
            }
        )

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle tool execution"""
        if name == "my_tool":
            return f"Result: {arguments.get('param', '')}"
        return f"[ERROR] Unknown tool: {name}"

if __name__ == "__main__":
    import asyncio
    server = MyMCPServer()
    asyncio.run(server.run())
```

---

### 方案B: 配置验证工具 (P1, 高价值)

**目标**: 在启动前验证MCP配置

**实现**: CLI命令 `fastreact validate-mcp`

```bash
# 验证配置
fastreact validate-mcp

# 输出示例：
# [OK] MCP config loaded from ~/.fastreact/config.json
# [OK] graphrag: Server file exists
# [OK] graphrag: Python syntax valid
# [OK] graphrag: Transport = stdio
# [WARNING] timeserver: Command 'uvx' not found in PATH
# [WARNING] my_server: No associated SKILL found
```

**验证检查项**:
- [ ] 配置文件存在且JSON格式正确
- [ ] server文件存在
- [ ] transport字段有效（stdio/http）
- [ ] stdio: command命令可用（在PATH中）
- [ ] http: URL格式正确
- [ ] Python文件语法正确
- [ ] （可选）对应的SKILL文件存在

---

### 方案C: 热重载支持 (P2, 中价值)

**目标**: 无需重启Gateway即可添加MCP server

**实现**:
1. 监控`~/.fastreact/config.json`变化
2. 自动加载新配置
3. 动态注册新MCP工具

**API端点**:
```bash
# 手动触发重载
curl -X POST http://localhost:9000/api/mcp/reload

# 响应
{
  "status": "success",
  "reloaded_servers": ["my_server"],
  "errors": []
}
```

---

### 方案E: MCP Marketplace集成 (P3, 低价值)

**目标**: 从前端直接安装MCP server

**实现**: 前端`/marketplace`页面
1. 浏览可用的MCP servers
2. 一键安装到本地
3. 自动配置和启用

---

## 推荐实施顺序

### Phase 1: CLI工具改进 (1-2天)
1. **方案A**: MCP Server模板生成器
   - 添加`fastreact add-mcp`命令
   - 生成server代码模板
   - 生成config.json和README.md
   - 生成SKILL模板（可选）

2. **方案B**: 配置验证工具
   - 添加`fastreact validate-mcp`命令
   - 验证配置文件
   - 验证server文件
   - 验证命令可用性

### Phase 2: 中期改进 (3-5天)
3. **方案C**: 热重载支持
   - 配置文件监控
   - 动态加载机制
   - API端点

### Phase 3: 长期改进 (可选)
4. **方案E**: MCP Marketplace集成
   - 前端UI
   - server仓库
   - 自动安装

---

## 快速实现: CLI模板生成器

### 代码实现

**文件**: `src/fastreact/cli/mcp_commands.py`

```python
"""
FastReAct CLI - MCP Server Commands
"""

import click
from pathlib import Path
from typing import Optional
import json

@click.group()
def mcp():
    """MCP server management commands"""
    pass

@mcp.command()
@click.argument("name")
@click.option("--description", "-d", default="Custom MCP server", help="Server description")
@click.option("--isolation", "-i",
              type=click.Choice(["shared", "per_user", "lazy_per_user"]),
              default="shared", help="Isolation mode")
@click.option("--with-skill", is_flag=True, help="Generate SKILL template")
@click.option("--transport", "-t",
              type=click.Choice(["stdio", "http"]),
              default="stdio", help="Transport type")
def add(name: str, description: str, isolation: str, with_skill: bool, transport: str):
    """Add a new MCP server with standard directory structure"""

    # 1. Create server directory
    server_dir = Path.cwd() / "mcp_servers" / "builtin" / name
    server_dir.mkdir(parents=True, exist_ok=True)

    server_file = server_dir / "server.py"

    # 2. Generate server code
    if transport == "stdio":
        template = f'''"""
FastReAct Nano - {name.title()} MCP Server

{description}
"""

from fastreact.mcp.server import SimpleMCPServer
from typing import Any, Dict

class {name.title().replace("_", "")}MCPServer(SimpleMCPServer):
    """{name.title()} MCP server"""

    def __init__(self):
        super().__init__()
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools"""
        self.register_tool(
            name="{name}_tool",
            description="Description of what this tool does",
            input_schema={{
                "type": "object",
                "properties": {{
                    "param": {{
                        "type": "string",
                        "description": "Parameter description"
                    }}
                }},
                "required": ["param"]
            }}
        )

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle tool execution"""
        if name == "{name}_tool":
            return f"Result: {{arguments.get('param', '')}}"
        return f"[ERROR] Unknown tool: {{name}}"

if __name__ == "__main__":
    import asyncio
    server = {name.title().replace("_", "")}MCPServer()
    asyncio.run(server.run()
'''
    else:
        template = f'''"""
FastReAct Nano - {name.title()} HTTP MCP Server

{description}

HTTP MCP server for {name} functionality.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from typing import Any, Dict
import json

app = FastAPI(title="{name.title()} MCP Server")

@app.post("/message")
async def handle_message(request: Request):
    """Handle JSON-RPC messages"""
    data = await request.json()

    if data.get("method") == "tools/list":
        return JSONResponse({{"jsonrpc": "2.0", "id": data.get("id"), "result": {{
            "tools": [
                {{
                    "name": "{name}_tool",
                    "description": "Description of what this tool does",
                    "inputSchema": {{
                        "type": "object",
                        "properties": {{
                            "param": {{"type": "string", "description": "..."}}
                        }},
                        "required": ["param"]
                    }}
                }}
            ]
        }}})

    return JSONResponse({{"jsonrpc": "2.0", "id": data.get("id"), "error": "Unknown method"}})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
'''

    server_file.write_text(template)
    click.echo(f"[OK] Created: {server_file}")

    # 3. Generate config.json
    config_data = {
        "name": name,
        "version": "1.0.0",
        "description": description,
        "transport": transport,
        "author": "FastReAct Nano",
        "license": "MIT"
    }

    if transport == "stdio":
        config_data["command"] = "python3"
        config_data["args"] = [f"@builtin/{name}/server.py"]

    config_file = server_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    click.echo(f"[OK] Created: {config_file}")

    # 4. Generate README.md
    readme = f'''# {name.title()} MCP Server

{description}

## Installation

Add to `~/.fastreact/config.json`:

```json
{{
  "mcp": {{
    "servers": [
      {{
        "name": "{name}",
        "transport": "{transport}",
        {"command": "python3","args": ["@builtin/{name}/server.py"] if transport == "stdio" else "url": "http://localhost:8000"},
        "isolation": "{isolation}"
      }}
    ]
  }}
}}
```

## Tools

- `{name}_tool`: Description of what this tool does

## Usage

```
fastreact "使用{name}工具..."
```

---

**Generated by**: `fastreact add-mcp {name}`
**Date**: {datetime.now().strftime("%Y-%m-%d")}
'''

    readme_file = server_dir / "README.md"
    readme_file.write_text(readme)
    click.echo(f"[OK] Created: {readme_file}")

    # 5. Generate SKILL template
    if with_skill:
        skill_dir = Path.cwd() / "skills" / "builtin" / f"{name}_workflow"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_template = f'''---
name: {name}_workflow
description: Guide for using {name} MCP server tools
tags: [{name}, custom]
version: 1.0.0
mcp_servers: [{name}]
recommended_tools: [{name}_tool]
---

# {name.title()} Workflow Skill

## Quick Start

中文示例：
- "使用{name}工具..."

English Examples：
- "Use {name} tool..."

## When to Use

Use {name} tools when you need to...

## Tool Guide

### {name}_tool

**Use for**: ...

**Example queries**:
- "..."
'''

        (skill_dir / "SKILL.md").write_text(skill_template)
        click.echo(f"[OK] Created: {skill_dir / 'SKILL.md'}")

    # 6. Print configuration instructions
    click.echo("\n[INFO] Server files created successfully!")
    click.echo("\n[INFO] Add this to ~/.fastreact/config.json:")
    click.echo(f'''{{
  "mcp": {{
    "servers": [
      {{
        "name": "{name}",
        "transport": "{transport}",
        {"command": "python3","args": ["@builtin/{name}/server.py"] if transport == "stdio" else "url": "http://localhost:8000"},
        "isolation": "{isolation}",
        "description": "{description}",
        "associated_skill": "{with_skill and f"{name}_workflow" or "null"}"
      }}
    ]
  }}
}}''')

    click.echo("\n[INFO] Then restart Gateway (if running):")
    click.echo("  pkill -f 'fastreact.adapters.gateway'")
    click.echo("  python3 -m fastreact.adapters.gateway")


@mcp.command()
def validate():
    """Validate MCP server configuration"""
    import shutil
    import json

    config_paths = [
        Path.home() / ".fastreact" / "config.json",
        Path.cwd() / ".fastreact" / "config.json",
    ]

    config_path = next((p for p in config_paths if p.exists()), None)
    if not config_path:
        click.echo("[ERROR] MCP config not found")
        return

    with open(config_path) as f:
        config = json.load(f)

    servers = config.get("mcp", {}).get("servers", [])
    click.echo(f"[INFO] Validating {len(servers)} MCP servers...")

    for server in servers:
        name = server.get("name")
        transport = server.get("transport", "stdio")
        command = server.get("command")
        args = server.get("args", [])

        click.echo(f"\n{name} (transport={transport}):")

        # Check transport-specific validation
        if transport == "stdio":
            # Check server file
            if args:
                # Resolve magic paths
                from fastreact.mcp import MCPToolManager
                from fastreact.core.tools import ToolRegistry
                from fastreact.core import Credentials

                registry = ToolRegistry()
                creds = Credentials.load()
                manager = MCPToolManager(registry, credentials=creds)

                for arg in args:
                    resolved = manager._resolve_magic_path(arg)
                    server_path = Path.cwd() / resolved

                    if server_path.exists():
                        click.echo(f"  [OK] Server file exists: {resolved}")
                    else:
                        click.echo(f"  [ERROR] Server file not found: {resolved}")

            # Check command availability
            if command:
                if shutil.which(command):
                    click.echo(f"  [OK] Command '{command}' available")
                else:
                    click.echo(f"  [WARNING] Command '{command}' not found in PATH")

        elif transport == "http":
            url = server.get("url")
            if url:
                click.echo(f"  [OK] HTTP URL: {url}")
            else:
                click.echo(f"  [ERROR] HTTP transport requires 'url' field")

        # Check auth token reference
        auth_ref = server.get("auth_token_ref")
        if auth_ref:
            from fastreact.core import Credentials
            creds = Credentials.load()
            token = creds.get_auth_token(auth_ref)
            if token:
                click.echo(f"  [OK] Auth token found: {auth_ref}")
            else:
                click.echo(f"  [WARNING] Auth token not found: {auth_ref}")

    click.echo("\n[DONE] Validation complete")

# Register commands
from fastreact.cli import main
main.add_command(mcp)
```

---

## 总结

### 已完成 (v2.4.2)
- ✅ 统一目录结构 (`mcp_servers/builtin/{name}/`)
- ✅ 魔法路径支持 (`@builtin/`)
- ✅ HTTP 传输支持
- ✅ 凭证管理分离

### 待实现
- ⏳ `fastreact add-mcp` - 模板生成器
- ⏳ `fastreact validate-mcp` - 配置验证
- ⏳ 热重载支持
- ⏳ Marketplace 集成

### 优先级
1. **P1**: 模板生成器 + 配置验证（1-2天）
2. **P2**: 热重载支持（3-5天）
3. **P3**: Marketplace 集成（可选）

---

**文档版本**: 2.0
**最后更新**: 2025-02-24
**维护者**: FastReAct Team
