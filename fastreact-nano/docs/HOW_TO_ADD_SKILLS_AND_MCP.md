# 如何添加 Skill 和 MCP

**适用场景**: 新机器部署后，添加自定义功能

**重要**: 首次使用需要配置用户技能目录！

---

## 前置步骤：配置用户技能目录

**只需执行一次：**

```bash
# 方法 1: 使用配置脚本（推荐）
python3 -c "
import json
from pathlib import Path
config_path = Path.home() / '.fastreact/config.json'
with open(config_path) as f:
    config = json.load(f)
if 'paths' not in config:
    config['paths'] = {}
config['paths']['user_skills_dir'] = str(Path.home() / '.fastreact/skills')
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print('[OK] 用户技能目录已配置')
"

# 方法 2: 手动编辑
nano ~/.fastreact/config.json

# 添加以下内容：
{
  "paths": {
    "user_skills_dir": "/Users/你的用户名/.fastreact/skills"
  }
}
```

**验证配置：**

```bash
cat ~/.fastreact/config.json | grep -A 2 "paths"
# 应该看到:
# "paths": {
#   "user_skills_dir": "/Users/xxx/.fastreact/skills"
# }
```

---

## 方法 1: 添加 Skill (推荐 - 最简单)

### 步骤 1: 创建 Skill 目录

```bash
mkdir -p ~/.fastreact/skills/my_tool
```

### 步骤 2: 创建 SKILL.md

```bash
cat > ~/.fastreact/skills/my_tool/SKILL.md << 'EOF'
---
name: http_operations
description: HTTP 请求操作工具
tags: [http, api, web]
---

# HTTP 操作

使用 exec 工具执行 curl 命令：

```bash
# GET 请求
curl -s https://api.example.com/data

# POST 请求
curl -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' https://api.example.com
```
EOF
```

### 步骤 3: 立即可用

```bash
# Skill 会自动被发现
fastreact "使用 http_operations 获取 API 数据"
```

---

## 方法 2: 添加 MCP 服务器 (适合复杂集成)

### 步骤 1: 创建 MCP 服务器

```bash
mkdir -p ~/.fastreact/mcp_servers/my_server
```

### 步骤 2: 编写 server.py

```python
# ~/.fastreact/mcp_servers/my_server/server.py
from fastreact.mcp.server import SimpleMCPServer

class MyMCPServer(SimpleMCPServer):
    def __init__(self):
        super().__init__()
        self._register_tools()

    def _register_tools(self):
        self.register_tool(
            name="my_tool",
            description="My custom tool",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        )

    async def handle_tool_call(self, name, args):
        if name == "my_tool":
            return f"Result: {args['query']}"
        return "Unknown tool"

async def main():
    server = MyMCPServer()
    await server.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 步骤 3: 配置到 ~/.fastreact/config.json

```bash
# 编辑配置文件
nano ~/.fastreact/config.json
```

添加以下内容：

```json
{
  "mcp": {
    "servers": [
      {
        "name": "my_server",
        "command": "python3",
        "args": ["~/.fastreact/mcp_servers/my_server/server.py"],
        "isolation": "shared"
      }
    ]
  }
}
```

### 步骤 4: 测试

```bash
fastreact "使用 my_tool 工具查询 hello"
```

---

## 方法 3: 使用现有的 MCP 服务器 (最省事)

### 使用 npm 官方服务器

```bash
# 编辑 ~/.fastreact/config.json
cat >> ~/.fastreact/config.json << 'EOF'
{
  "mcp": {
    "servers": [
      {
        "name": "fetch",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "isolation": "shared"
      },
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/.fastreact/workspace"],
        "isolation": "shared"
      }
    ]
  }
}
EOF
```

---

## 配置文件位置

### 用户级配置 (推荐)

**位置**: `~/.fastreact/config.json`

**优先级**: 最高

**用途**: 个人开发、测试

### 项目级配置

**位置**: `./fastreact-nano/.fastreact/config.json`

**优先级**: 中等

**用途**: 项目特定配置

---

## 验证安装

### 检查 Skill 是否加载

```bash
fastreact "列出所有可用的 skills"
```

### 检查 MCP 服务器是否加载

```python
python3 -c "
import asyncio
from fastreact import Agent

async def check():
    agent = Agent()
    await agent._load_mcp_servers()
    tools = agent._tools.list_all()
    mcp_tools = [t for t in tools if '_' in t]
    print(f'MCP Tools: {len(mcp_tools)}')
    for t in mcp_tools[:5]:
        print(f'  - {t}')
    await agent.close_mcp_servers()

asyncio.run(check())
"
```

---

## 常见问题

### Q: Skill 添加后不生效？

**A**: 检查以下几点：
1. SKILL.md 文件格式是否正确（frontmatter 必须完整）
2. 文件路径是否在 `~/.fastreact/skills/` 或配置的 skills 目录
3. 重启 Agent

### Q: MCP 服务器启动失败？

**A**: 检查：
1. Python 脚本是否有执行权限
2. 依赖是否安装 (`pip install` 所需包)
3. server.py 是否有 `if __name__ == "__main__"` 入口
4. 手动运行测试：`python3 server.py`

### Q: 如何调试 Skill？

**A**: 使用诊断脚本：

```bash
python3 scripts/diagnose_skill_selection.py "你的查询"
```

---

## 推荐的 Skills

### HTTP 操作

```bash
mkdir -p ~/.fastreact/skills/http
cat > ~/.fastreact/skills/http/SKILL.md << 'EOF'
---
name: http
description: HTTP 请求工具
tags: [http, api, web]
---
使用 curl 进行 HTTP 请求：
\`\`\`bash
curl -s https://api.example.com
\`\`\`
EOF
```

### 数据库操作

```bash
mkdir -p ~/.fastreact/skills/database
cat > ~/.fastreact/skills/database/SKILL.md << 'EOF'
---
name: database
description: SQLite 数据库操作
tags: [database, sql, sqlite]
---
使用 sqlite3 命令：
\`\`\`bash
sqlite3 database.db "SELECT * FROM users"
\`\`\`
EOF
```

---

**总结**: 优先使用 Skill（Markdown），复杂需求用 MCP（Python），两者配合使用最佳！
