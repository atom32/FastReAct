# MCP能力添加改进方案

**日期**: 2025-02-24
**状态**: 提案

---

## 当前流程的问题

### 现状
添加MCP能力需要手动完成5个步骤：
1. 创建MCP server文件
2. 编写server代码（继承SimpleMCPServer）
3. 手动编辑`~/.fastreact/config.json`
4. （可选）创建对应的SKILL
5. 重启Gateway服务

### 问题汇总

| 问题 | 影响 | 严重性 | 优先级 |
|------|------|--------|--------|
| **配置分散** | server文件和配置分离，难以管理 | 中 | P2 |
| **手动编辑** | JSON格式错误、路径错误 | 高 | P1 |
| **无验证** | 配置错误只能在运行时发现 | 高 | P1 |
| **无模板** | 每次都要从头写server代码 | 中 | P2 |
| **无自动化** | 没有命令行工具 | 中 | P2 |

---

## 改进方案

### 方案A: MCP Server模板生成器 (P1, 高价值)

**目标**: 提供MCP server脚手架生成工具

**实现**: CLI命令 `fastreact add-mcp`

```bash
# 使用方式
fastreact add-mcp my_server --description "My custom MCP server"

# 自动生成：
# - mcp_servers/builtin/my_server.py (模板代码)
# - skills/builtin/my_server_workflow/SKILL.md (SKILL模板)
# - 并提示更新 config.json
```

**生成代码模板**:
```python
# mcp_servers/builtin/my_server.py
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

**同时生成SKILL模板**:
```markdown
---
name: my_server_workflow
description: Guide for using my custom MCP server tools
tags: [custom, my_server]
version: 1.0.0
mcp_servers: [my_server]
recommended_tools: [my_server_my_tool]
---

# My Server Workflow Skill

## When to Use

Use this skill when...
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
# [ERROR] timeserver: Command 'uvx' not found in PATH
# [WARNING] my_server: No associated SKILL found
```

**验证检查项**:
- [ ] 配置文件存在且JSON格式正确
- [ ] server文件存在
- [ ] command命令可用（在PATH中）
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

### 方案D: 统一配置管理 (P2, 中价值)

**目标**: 配置文件与server文件放在一起

**当前**:
```
mcp_servers/builtin/my_server.py     # server代码
~/.fastreact/config.json              # server配置
skills/builtin/my_workflow/SKILL.md   # SKILL定义
```

**改进后**:
```
mcp_servers/builtin/my_server/
├── server.py              # server代码
├── config.json            # server配置
├── SKILL.md               # SKILL定义（可选）
└── README.md              # 文档
```

**优点**:
- 配置与代码在一起，易于维护
- 可以单独启用/禁用每个server
- 支持从`mcp_servers/builtin/`自动发现所有server

**加载逻辑**:
```python
# 扫描builtin目录
for server_dir in mcp_servers/builtin/*/:
    config = server_dir/config.json
    if config.get("enabled", True):
        load_server(config)
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

### Phase 1: 立即改进 (1-2天)
1. ✅ **方案A**: MCP Server模板生成器
   - 添加`fastreact add-mcp`命令
   - 生成server代码模板
   - 生成SKILL模板
   - 打印配置提示

2. ✅ **方案B**: 配置验证工具
   - 添加`fastreact validate-mcp`命令
   - 验证配置文件
   - 验证server文件
   - 验证命令可用性

### Phase 2: 中期改进 (3-5天)
3. **方案D**: 统一配置管理
   - 重构目录结构
   - 自动发现server
   - 更新文档

4. **方案C**: 热重载支持
   - 配置文件监控
   - 动态加载机制
   - API端点

### Phase 3: 长期改进 (可选)
5. **方案E**: MCP Marketplace集成
   - 前端UI
   - server仓库
   - 自动安装

---

## 快速实现方案A: CLI模板生成器

### 代码实现

**文件**: `src/fastreact/cli/mcp_commands.py`

```python
"""
FastReAct CLI - MCP Server Commands
"""

import click
from pathlib import Path
from typing import Optional

@click.group()
def mcp():
    """MCP server management commands"""
    pass

@mcp.command()
@click.argument("name")
@click.option("--description", "-d", default="Custom MCP server", help="Server description")
@click.option("--isolation", "-i", type=click.Choice(["shared", "per_user", "lazy_per_user"]), default="shared", help="Isolation mode")
@click.option("--with-skill", is_flag=True, help="Generate SKILL template")
def add(name: str, description: str, isolation: str, with_skill: bool):
    """Add a new MCP server"""

    # 1. Generate server code
    server_path = Path.cwd() / "mcp_servers" / "builtin" / f"{name}_server.py"

    if server_path.exists():
        click.echo(f"[ERROR] Server already exists: {server_path}")
        return

    # Template code
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
    asyncio.run(server.run())
'''

    server_path.write_text(template)
    click.echo(f"[OK] Created: {server_path}")

    # 2. Generate SKILL template
    if with_skill:
        skill_path = Path.cwd() / "skills" / "builtin" / f"{name}_workflow"
        skill_path.mkdir(parents=True, exist_ok=True)

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

        (skill_path / "SKILL.md").write_text(skill_template)
        click.echo(f"[OK] Created: {skill_path / 'SKILL.md'}")

    # 3. Print configuration instructions
    click.echo("\n[INFO] Add this to ~/.fastreact/config.json:")
    click.echo(f'''{{
  "mcp": {{
    "servers": [
      {{
        "name": "{name}",
        "command": "python3",
        "args": ["mcp_servers/builtin/{name}_server.py"],
        "isolation": "{isolation}",
        "description": "{description}",
        "associated_skill": "{with_skill and f"{name}_workflow" or "null"}"
      }}
    ]
  }}
}}''')

    click.echo("\n[INFO] Then restart Gateway:")
    click.echo("  pkill -f 'fastreact.adapters.gateway'")
    click.echo("  python3 -m fastreact.adapters.gateway")

@mcp.command()
def validate():
    """Validate MCP server configuration"""
    import json
    from pathlib import Path

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
        command = server.get("command")
        args = server.get("args", [])

        # Check server file
        if args and args[0].startswith("mcp_servers/"):
            server_path = Path.cwd() / args[0]
            if server_path.exists():
                click.echo(f"[OK] {name}: Server file exists")
            else:
                click.echo(f"[ERROR] {name}: Server file not found: {server_path}")

        # Check command availability
        import shutil
        if command and not shutil.which(command):
            click.echo(f"[WARNING] {name}: Command '{command}' not found in PATH")
        else:
            click.echo(f"[OK] {name}: Command '{command}' available")

    click.echo("[DONE] Validation complete")

# Register commands
from fastreact.cli import main
main.add_command(mcp)
```

---

## 总结

### 当前状态
- 添加MCP能力需要**手动完成多个步骤**
- 配置分散，容易出错
- 无验证工具

### 改进后
- ✅ `fastreact add-mcp my_server` - 自动生成模板
- ✅ `fastreact validate-mcp` - 验证配置
- ✅ （可选）统一配置管理
- ✅ （可选）热重载支持

### 优先级
1. **P1**: 模板生成器 + 配置验证（1-2天）
2. **P2**: 统一配置管理（3-5天）
3. **P3**: 热重载 + Marketplace（可选）

---

**文档版本**: 1.0
**维护者**: FastReAct Team
