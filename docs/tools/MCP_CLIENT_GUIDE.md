# MCP Client 集成指南

FastReAct 现在支持 **MCP (Model Context Protocol)** Client 功能，可以连接和使用外部 MCP Servers 提供的工具。

## 什么是 MCP？

MCP (Model Context Protocol) 是 Anthropic 开发的开放协议，用于标准化 LLM 应用与外部工具的连接。可以把它理解为 "AI 工具调用的 USB 接口"。

### MCP 的核心概念

- **Resources**: 类似 REST API 的 GET 端点，提供数据访问
- **Tools**: 类似 REST API 的 POST 端点，执行操作
- **Prompts**: 可重用的提示模板

### 为什么要使用 MCP？

1. **标准化**: 统一的工具调用协议
2. **生态丰富**: 官方和社区提供大量 MCP Servers
3. **易于集成**: 一个配置文件即可连接多个服务
4. **安全性**: 标准化的授权和认证机制

---

## 快速开始

### 1. 安装依赖

```bash
# MCP SDK 已包含在依赖中
pip install -e .
```

### 2. 创建 MCP 配置文件

在项目根目录创建 `mcp_servers.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/files"
      ]
    }
  }
}
```

### 3. 使用 MCP Client

```python
import asyncio
from fastreact import FastReAct
from fastreact.tools import MCPClientManager

async def main():
    # 1. 创建 MCP Client Manager
    mcp_manager = MCPClientManager("mcp_servers.json")

    # 2. 连接所有服务器
    await mcp_manager.connect_all()

    # 3. 获取所有 MCP 工具
    mcp_tools = await mcp_manager.get_all_tools()

    print(f"加载了 {len(mcp_tools)} 个 MCP 工具")

    # 4. 创建 FastReAct 引擎（包含 MCP 工具）
    engine = FastReAct(
        api_key="your-openai-api-key",
        tools=mcp_tools,  # 添加 MCP 工具
    )

    # 5. 运行 ReACT 循环
    response = await engine.run(
        "请读取 examples 目录下的文件列表"
    )

    print(response)

    # 6. 清理连接
    await mcp_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 配置 MCP 服务器

### 支持的传输方式

#### 1. stdio 传输（本地进程）

适合连接本地运行的 MCP Servers（通过命令行启动）。

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
      "env": {
        "CUSTOM_VAR": "value"
      }
    }
  }
}
```

#### 2. Streamable HTTP 传输

适合连接远程 MCP Servers（生产环境推荐）。

```json
{
  "mcpServers": {
    "my-http-server": {
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer token123"
      }
    }
  }
}
```

---

## 官方 MCP Servers

### 1. Filesystem Server

文件系统操作工具。

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
  }
}
```

### 2. GitHub Server

GitHub 仓库操作工具。

```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "ghp_xxxxx"
    }
  }
}
```

### 3. Postgres Server

PostgreSQL 数据库操作工具。

```json
{
  "postgres": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-postgres",
      "postgresql://user:password@localhost:5432/dbname"
    ]
  }
}
```

### 4. Memory Server

内存存储工具（持久化上下文）。

```json
{
  "memory": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-memory"]
  }
}
```

### 5. Brave Search Server

网络搜索工具。

```json
{
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your_api_key"
    }
  }
}
```

### 6. Slack Server

Slack 集成工具。

```json
{
  "slack": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_TOKEN": "xoxb-xxxxx",
      "SLACK_CHANNELS": "channel1,channel2"
    }
  }
}
```

---

## 高级用法

### 手动添加服务器

```python
from fastreact.tools import MCPClientManager

manager = MCPClientManager()

# 添加 stdio 服务器
manager.add_server("filesystem", {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
})

# 添加 HTTP 服务器
manager.add_server("remote-api", {
    "url": "http://localhost:8080/mcp",
    "headers": {"Authorization": "Bearer token"}
})

await manager.connect_all()
```

### 使用上下文管理器

```python
from fastreact.tools import MCPClientManager

async with MCPClientManager("mcp_servers.json").auto_connect():
    tools = await manager.get_all_tools()
    # 在此上下文中使用工具
    # 自动处理连接和断开
```

### 获取特定服务器的工具

```python
# 只获取 filesystem 服务器的工具
fs_tools = await manager.get_server_tools("filesystem")

print(f"Filesystem tools: {[t.name for t in fs_tools]}")
```

### 检查服务器状态

```python
# 列出所有服务器
servers = manager.list_servers()
print(f"配置的服务器: {servers}")

# 检查连接状态
status = manager.get_server_status()
print(f"连接状态: {status}")
# 输出: {"filesystem": True, "github": False, ...}
```

### 保存配置

```python
manager = MCPClientManager()

# 动态添加服务器
manager.add_server("new-server", {...})

# 保存到文件
manager.save_config("mcp_servers_updated.json")
```

---

## 完整示例

### 示例 1: 文件系统 + GitHub 集成

```python
import asyncio
from fastreact import FastReAct
from fastreact.tools import MCPClientManager

async def main():
    # 创建 MCP Manager
    mcp_manager = MCPClientManager()

    # 添加服务器
    mcp_manager.add_server("filesystem", {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./project"]
    })

    mcp_manager.add_server("github", {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": "your_token"}
    })

    # 连接并获取工具
    await mcp_manager.connect_all()

    mcp_tools = await mcp_manager.get_all_tools()
    print(f"加载工具: {[t.name for t in mcp_tools]}")

    # 创建 FastReAct 引擎
    engine = FastReAct(
        api_key="your-openai-api-key",
        tools=mcp_tools,
    )

    # 执行任务
    response = await engine.run(
        "请读取 project 目录下的 README.md，"
        "然后在 GitHub 上创建一个 issue 来跟踪发现的 bug"
    )

    print(response)

    # 清理
    await mcp_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 2: 数据库查询 + 分析

```python
import asyncio
from fastreact import FastReAct
from fastreact.tools import MCPClientManager

async def main():
    mcp_manager = MCPClientManager()

    # 连接 Postgres 数据库
    mcp_manager.add_server("postgres", {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-postgres",
            "postgresql://user:password@localhost:5432/analytics"
        ]
    })

    await mcp_manager.connect_all()

    # 获取数据库工具
    db_tools = await mcp_manager.get_server_tools("postgres")

    # 创建引擎
    engine = FastReAct(
        api_key="your-openai-api-key",
        tools=db_tools,
    )

    # 分析数据
    response = await engine.run(
        "查询过去 7 天的销售数据，"
        "计算总收入和平均订单价值，"
        "并生成一份简单的分析报告"
    )

    print(response)

    await mcp_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 3: 混合使用 MCP 和原生工具

```python
import asyncio
from fastreact import FastReAct
from fastreact.tools import (
    MCPClientManager,
    CalculatorTool,
    SearchTool,
)

async def main():
    # MCP 工具
    mcp_manager = MCPClientManager("mcp_servers.json")
    await mcp_manager.connect_all()
    mcp_tools = await mcp_manager.get_all_tools()

    # 原生工具
    native_tools = [CalculatorTool(), SearchTool()]

    # 合并所有工具
    all_tools = native_tools + mcp_tools

    # 创建引擎
    engine = FastReAct(
        api_key="your-openai-api-key",
        tools=all_tools,
    )

    response = await engine.run(
        "搜索最新的人工智能发展报告，"
        "读取本地文件中的参考数据，"
        "进行计算分析，"
        "最后将结果保存到文件"
    )

    print(response)

    await mcp_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 错误处理

```python
import asyncio
from fastreact.tools import MCPClientManager

async def main():
    manager = MCPClientManager("mcp_servers.json")

    # 连接所有服务器
    results = await manager.connect_all()

    # 检查连接结果
    for server_name, success in results.items():
        if not success:
            print(f"警告: 无法连接到服务器 '{server_name}'")
            # 继续处理其他服务器...

    # 获取可用工具
    try:
        tools = await manager.get_all_tools()
        print(f"成功加载 {len(tools)} 个工具")
    except Exception as e:
        print(f"获取工具失败: {e}")
        return

    # 使用工具...

    await manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 最佳实践

### 1. 环境变量管理

不要在配置文件中硬编码敏感信息：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

在 Python 代码中替换环境变量：

```python
import os
import json

def load_config_with_env(config_path: str) -> dict:
    with open(config_path) as f:
        config = json.load(f)

    # 替换环境变量
    for server_config in config["mcpServers"].values():
        if "env" in server_config:
            for key, value in server_config["env"].items():
                if isinstance(value, str) and value.startswith("${"):
                    env_var = value[2:-1]  # 去掉 ${}
                    server_config["env"][key] = os.getenv(env_var, "")

    return config

# 使用
config = load_config_with_env("mcp_servers.json")
manager = MCPClientManager()
manager._connections = config  # 直接设置配置
```

### 2. 连接池管理

对于生产环境，建议使用上下文管理器确保连接正确释放：

```python
async with MCPClientManager("mcp_servers.json").auto_connect():
    # 使用工具
    pass
# 自动断开连接
```

### 3. 工具过滤

如果只需要特定服务器的工具：

```python
# 只加载 filesystem 工具
fs_tools = await manager.get_server_tools("filesystem")

engine = FastReAct(api_key="...", tools=fs_tools)
```

### 4. 错误重试

```python
import asyncio
from fastreact.tools import MCPClientManager

async def connect_with_retry(manager, max_retries=3):
    for attempt in range(max_retries):
        results = await manager.connect_all()

        # 检查是否全部成功
        if all(results.values()):
            return True

        # 等待后重试
        await asyncio.sleep(2 ** attempt)  # 指数退避

    return False
```

---

## 故障排查

### 问题 1: npx 命令找不到

**错误**: `Command not found: npx`

**解决**: 确保安装了 Node.js 和 npm:
```bash
# macOS
brew install node

# Ubuntu/Debian
sudo apt install nodejs npm

# Windows
# 从 https://nodejs.org 下载安装
```

### 问题 2: 连接超时

**错误**: `Timeout connecting to MCP server`

**解决**: 增加超时时间:
```python
manager = MCPClientManager(timeout=60.0)  # 60 秒
```

### 问题 3: 工具执行失败

**错误**: `Tool execution failed`

**解决**: 检查 MCP Server 日志，查看具体错误信息。

---

## 参考资源

- [MCP 官方规范](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Servers 列表](https://github.com/modelcontextprotocol/servers)
- [Real Python: MCP Client 教程](https://realpython.com/python-mcp-client/)

---

## 总结

通过 MCP Client 集成，FastReAct 现在可以：

✅ 连接 50+ 官方和社区 MCP Servers
✅ 访问文件系统、数据库、API 等外部资源
✅ 使用统一的标准协议管理工具
✅ 轻松扩展 Agent 的能力边界

开始使用 MCP Client，让你的 Agent 更强大！
