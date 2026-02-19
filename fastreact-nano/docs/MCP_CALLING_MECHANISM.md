# FastReAct Nano MCP 调用机制详解

**版本**: 2.4.2
**更新日期**: 2025-02-19

---

## 一、MCP 调用机制概述

### 1.1 通信方式

FastReAct Nano **只使用 STDIO (标准输入输出)** 方式与 MCP Server 通信，**不使用 HTTP/SSE**。

**为什么只用 STDIO？**
- ✅ **简单可靠**：不需要网络配置，直接启动子进程
- ✅ **隔离性好**：每个 MCP Server 是独立进程，崩溃不影响主程序
- ✅ **本地优先**：适合本地文件操作、数据库访问等场景
- ❌ **不支持远程**：如果要调用远程 MCP Server，需要通过 SSH 隧道或 Agent

### 1.2 架构层级

```
┌─────────────────────────────────────────────────────────────┐
│                     FastReAct Agent                         │
│  (决策层：决定调用哪个 MCP Tool)                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCPToolManager                            │
│  (管理层：管理 MCP Server 生命周期)                          │
│  - 启动/停止 MCP Server 进程                                 │
│  - 监控 Server 健康状态 (Zombie 检测)                        │
│  - 自动重启崩溃的 Server (Resurrection)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  SimpleMCPClient                            │
│  (通信层：通过 STDIO 与 Server 通信)                         │
│  - JSON-RPC 协议                                             │
│  - stdin 发送请求                                           │
│  - stdout 接收响应                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              MCP Server (子进程)                             │
│  (执行层：实际干活的服务器)                                  │
│  - 从 stdin 读取 JSON-RPC 请求                              │
│  - 调用实际的系统/API                                        │
│  - 向 stdout 输出 JSON-RPC 响应                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、MCP Server 通信协议

### 2.1 启动流程

```python
# 1. MCPToolManager 启动 MCP Server (作为子进程)
server_command = "python3"
server_args = ["examples/file_mcp_server.py"]

# 2. SimpleMCPClient 创建子进程
process = await asyncio.create_subprocess_exec(
    server_command,
    *server_args,
    stdin=asyncio.subprocess.PIPE,   # ✅ 用 stdin 发送请求
    stdout=asyncio.subprocess.PIPE,  # ✅ 从 stdout 读取响应
    stderr=asyncio.subprocess.PIPE,  # ✅ 错误输出
)
```

### 2.2 JSON-RPC 通信

**初始化握手**：
```json
// Client → Server (通过 stdin)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "fastreact-nano",
      "version": "2.4.2"
    }
  }
}

// Server → Client (通过 stdout)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "file-server",
      "version": "1.0.0"
    },
    "capabilities": {}
  }
}
```

**工具调用**：
```json
// Client → Server (调用 read_file)
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "path": "config.json"
    }
  }
}

// Server → Client (返回结果)
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"api_key\": \"sk-xxx\"}"
      }
    ]
  }
}
```

---

## 三、当前可用的 MCP Server

### 3.1 示例 MCP Server

项目中有**示例实现**，但**默认不启用**：

#### 1. `examples/file_mcp_server.py`

**功能**：文件操作 MCP Server
- `read_file` - 读取文件
- `write_file` - 写入文件
- `list_dir` - 列出目录
- `file_info` - 获取文件元数据

**状态**：✅ 可用（需要手动配置）

**配置方式**：
```json
{
  "mcp": {
    "servers": [
      {
        "name": "file_operations",
        "command": "python3",
        "args": ["examples/file_mcp_server.py", "--base-path", "./allowed"],
        "isolation": "shared",
        "description": "File operations (sandboxed)"
      }
    ]
  }
}
```

#### 2. 官方 MCP Servers (通过 NPM)

这些是 Model Context Protocol 官方提供的 Servers：

**GitHub**：
```json
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
  },
  "isolation": "shared"
}
```

**Filesystem**：
```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
  "isolation": "per_user"
}
```

**PostgreSQL**：
```json
{
  "name": "postgres",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/db"],
  "isolation": "shared"
}
```

**Web Search** (Brave):
```json
{
  "name": "web_search",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-brave-search"],
  "env": {
    "BRAVE_API_KEY": "your-api-key"
  },
  "isolation": "shared"
}
```

### 3.2 默认状态

**重要**：FastReAct Nano **默认不启用任何 MCP Server**！

**原因**：
- MCP Server 需要外部依赖（NPM 包、API 密钥等）
- 不是所有用户都需要 MCP 功能
- 让用户自己选择需要的 Server

**如何启用**：
1. 编辑 `~/.fastreact/config.json` 或项目根目录的 `config.json`
2. 在 `mcp.servers` 数组中添加需要的 Server 配置
3. 重启 FastReAct

---

## 四、MCP Server 开发指南

### 4.1 创建自定义 MCP Server

**步骤 1**：创建 Python 脚本

```python
#!/usr/bin/env python3
"""My Custom MCP Server"""

import asyncio
from fastreact.mcp.server import SimpleMCPServer

class MyMCPServer(SimpleMCPServer):
    def __init__(self):
        super().__init__()

        # 注册工具
        self.register_tool(
            name="my_tool",
            description="My custom tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                },
                "required": ["param1"],
            },
        )

    async def call_tool(self, name: str, arguments: dict) -> str:
        """工具调用逻辑"""
        if name == "my_tool":
            # 在这里调用实际的系统/API
            result = do_something(arguments["param1"])
            return result
        else:
            raise ValueError(f"Unknown tool: {name}")

async def main():
    server = MyMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**步骤 2**：配置到 FastReAct

```json
{
  "mcp": {
    "servers": [
      {
        "name": "my_custom_server",
        "command": "python3",
        "args": ["path/to/my_server.py"],
        "isolation": "shared",
        "description": "My custom MCP server"
      }
    ]
  }
}
```

### 4.2 与实际系统对接

**场景 1：操作数据库**
```python
async def call_tool(self, name: str, arguments: dict) -> str:
    if name == "query_database":
        import sqlite3
        conn = sqlite3.connect("my_database.db")
        cursor = conn.cursor()
        cursor.execute(arguments["sql"])
        result = cursor.fetchall()
        conn.close()
        return str(result)
```

**场景 2：调用外部 API**
```python
async def call_tool(self, name: str, arguments: dict) -> str:
    if name == "get_weather":
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.weather.com/{arguments['city']}"
            )
            return response.text
```

**场景 3：操作游戏引擎**
```python
async def call_tool(self, name: str, arguments: dict) -> str:
    if name == "update_monster_stats":
        # 读取游戏配置
        with open("game_data/monsters.json") as f:
            monsters = json.load(f)

        # 修改数据
        for monster in monsters:
            monster["hp"] *= 2

        # 保存
        with open("game_data/monsters.json", "w") as f:
            json.dump(monsters, f)

        return f"Updated {len(monsters)} monsters"
```

---

## 五、多租户隔离机制

### 5.1 Isolation Modes

FastReAct 支持 3 种隔离模式：

#### 1. `shared` - 全局共享
```json
{
  "name": "web_search",
  "isolation": "shared"
}
```
- **特点**：所有用户共享一个 MCP Server 进程
- **适用**：无状态工具（搜索、计算器）
- **性能**：最优（只启动一次）

#### 2. `per_user` - 每用户隔离
```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "{user_workspace}"],
  "isolation": "per_user"
}
```
- **特点**：每个用户有独立的 MCP Server 进程
- **适用**：有状态工具（文件系统、数据库）
- **性能**：每用户启动一次

#### 3. `lazy_per_user` - 按需创建
```json
{
  "name": "database",
  "isolation": "lazy_per_user",
  "idle_timeout": 300,
  "max_instances": 10
}
```
- **特点**：活跃用户创建进程，空闲后回收
- **适用**：平衡性能和隔离
- **性能**：动态调整

### 5.2 模板变量

**可用变量**：
- `{user_workspace}` - 用户工作区路径
- `{user_id}` - 用户 ID
- `{tenant_id}` - 租户 ID

**使用示例**：
```json
{
  "name": "filesystem",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "{user_workspace}/files"
  ]
}
```

---

## 六、故障排查

### 6.1 MCP Server 无法启动

**检查 1**：命令路径
```bash
# 手动测试 MCP Server 是否能启动
python3 examples/file_mcp_server.py
```

**检查 2**：依赖是否安装
```bash
# 如果使用 NPM MCP Server
npx -y @modelcontextprotocol/server-github --help

# 如果使用 Python MCP Server
pip install mcp
```

**检查 3**：权限问题
```bash
# 确保 Python 脚本有执行权限
chmod +x examples/file_mcp_server.py
```

### 6.2 工具调用失败

**常见原因**：
1. **参数不匹配**：检查 `input_schema` 和实际调用参数
2. **Server 崩溃**：查看 MCP Server 的 stderr 输出
3. **超时**：默认 30 秒，复杂操作可能需要更长时间

**调试方法**：
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 七、与 Gemini 解释的对比

### Gemini 说的两种方式

1. **STDIO** - ✅ FastReAct 使用这个
2. **HTTP (SSE)** - ❌ FastReAct 不支持

### 为什么 FastReAct 不用 HTTP？

**设计哲学**：
- FastReAct 是**本地 AI Agent 系统**，不是云服务
- MCP Server 作为**本地工具扩展**，不需要远程访问
- STDIO 更简单、更可靠、更安全

**如果需要远程 MCP Server**：
1. 使用 SSH 隧道：`ssh -L 3000:remote:3000 user@server`
2. 使用 Agent 模式：在远程机器运行 FastReAct，本地通过 WebSocket 连接
3. 等待社区贡献 HTTP/SSE 支持（欢迎 PR！）

---

## 八、总结

### 核心要点

1. **FastReAct 只用 STDIO 方式**与 MCP Server 通信
2. **默认不启用任何 MCP Server**，需要手动配置
3. **有示例 Server**（`examples/file_mcp_server.py`），可以直接使用
4. **支持官方 NPM MCP Servers**（GitHub、Filesystem、PostgreSQL 等）
5. **多租户隔离**：支持 shared / per_user / lazy_per_user 三种模式

### 快速开始

```bash
# 1. 配置 MCP Server
cat > ~/.fastreact/config.json << 'EOF'
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-your-key"
  },
  "mcp": {
    "servers": [
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/yourname/projects"],
        "isolation": "per_user"
      }
    ]
  }
}
EOF

# 2. 启动 FastReAct
python3 -m fastreact.adapters.gateway

# 3. 在前端或 API 中使用
# Agent 会自动加载 MCP Server 的工具
```

---

**文档维护**：
- **作者**: Claude Code
- **最后更新**: 2025-02-19
- **版本**: 2.4.2
