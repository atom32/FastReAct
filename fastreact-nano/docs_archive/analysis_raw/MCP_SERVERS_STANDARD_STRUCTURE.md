# MCP Servers 标准目录结构

**日期**: 2025-02-19
**状态**: 已整理

---

## 问题

**之前的混乱状态**：
```
examples/
  ├── graph_rag_server.py     ← 散落在这里
  └── file_mcp_server.py      ← 散落在这里

mcp_servers/
  ├── builtin/
  │   └── timeserver/           ← 只有这一个
  └── config/
```

**问题**：
- MCP server 位置不统一
- 难以管理和维护
- 不符合项目重组后的标准结构

---

## 标准目录结构（整理后）

```
fastreact-nano/
├── mcp_servers/                    ← MCP servers 统一管理目录
│   ├── README.md                   ← MCP server 开发指南
│   │
│   ├── builtin/                    ← 内置 MCP servers
│   │   ├── graph_rag_server.py    ← GraphRAG knowledge graph
│   │   ├── filesystem_server.py   ← Filesystem operations
│   │   └── timeserver/             ← Time server
│   │       ├── src/
│   │       └── README.md
│   │
│   └── config/                     ← MCP server 配置示例
│       ├── shared.json.example      ← Shared 模式示例
│       └── per_user.json.example    ← Per-user 模式示例
│
├── skills/builtin/                 ← SKILL 定义（与 MCP 对应）
│   └── graphrag_workflow/
│       └── SKILL.md
│
└── ~/.fastreact/config.json         ← 实际使用的配置
```

---

## MCP Servers 清单

### 1. GraphRAG Server

**文件**: `mcp_servers/builtin/graph_rag_server.py`

**功能**: 知识图谱搜索和查询
- 搜索实体（文本匹配）
- 获取实体详情
- 查询关系网络
- 向量语义搜索
- 创建新实体

**配置** (`~/.fastreact/config.json`):
```json
{
  "name": "graphrag",
  "command": "python3",
  "args": ["mcp_servers/builtin/graph_rag_server.py"],
  "isolation": "lazy_per_user",
  "idle_timeout": 300,
  "max_instances": 10,
  "description": "Knowledge graph search with GraphRAG",
  "associated_skill": "graphrag_workflow"
}
```

**提供的工具**（5个）:
- `graphrag_search_graph`
- `graphrag_get_entity`
- `graphrag_query_relationships`
- `graphrag_vector_search`
- `graphrag_create_entity`

**Mock 数据**: 10个实体（AI、ML、DL、NLP、CV等）+ 17条关系

---

### 2. Filesystem Server

**文件**: `mcp_servers/builtin/filesystem_server.py`

**功能**: 文件系统操作（备用/示例）
- 提供增强的文件操作功能
- 与内置工具（read_file, write_file）互补

**状态**: 未在 `config.json` 中启用（内置工具已足够）

---

### 3. Time Server

**文件**: `mcp_servers/builtin/timeserver/`

**功能**: 获取当前时间
- 提供当前时间和日期信息

**配置** (`~/.fastreact/config.json`):
```json
{
  "name": "timeserver",
  "command": "uvx",
  "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
  "isolation": "shared",
  "description": "Current time and date information"
}
```

**提供的工具**（1个）:
- `timeserver_get-current-time`

---

## 配置管理

### 生产配置

**位置**: `~/.fastreact/config.json`

**当前启用的 MCP servers**:
1. graphrag (lazy_per_user)
2. timeserver (shared)

### 示例配置

**位置**: `mcp_servers/config/`

**shared.json.example**:
```json
{
  "servers": [
    {
      "name": "timeserver",
      "command": "uvx",
      "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
      "isolation": "shared"
    }
  ]
}
```

**per_user.json.example**:
```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "{user_workspace}"],
      "isolation": "per_user"
    }
  ]
}
```

---

## 添加新的 MCP Server

### 步骤

1. **创建 MCP server 文件**
   ```bash
   touch mcp_servers/builtin/my_server.py
   ```

2. **继承 SimpleMCPServer**
   ```python
   from fastreact.mcp.server import SimpleMCPServer

   class MyMCPServer(SimpleMCPServer):
       def __init__(self):
           super().__init__()
           self._register_tools()

       def _register_tools(self):
           self.register_tool(
               name="my_tool",
               description="My tool description",
               input_schema={...}
           )

       async def handle_tool_call(self, name, arguments):
           # Handle tool calls
           pass
   ```

3. **更新配置文件**
   ```bash
   # 编辑 ~/.fastreact/config.json
   {
     "mcp": {
       "servers": [
         {
           "name": "my_server",
           "command": "python3",
           "args": ["mcp_servers/builtin/my_server.py"],
           "isolation": "shared"
         }
       ]
     }
   }
   ```

4. **（可选）创建对应的 SKILL**
   ```bash
   mkdir -p skills/builtin/my_workflow
   touch skills/builtin/my_workflow/SKILL.md
   ```

5. **重启 Gateway**
   ```bash
   pkill -f "fastreact.adapters.gateway"
   python3 -m fastreact.adapters.gateway
   ```

---

## MCP Server 命名规范

### 文件命名

**格式**: `{name}_server.py`

**示例**:
- `graph_rag_server.py` (内置 Python 实现)
- `filesystem_server.py` (内置 Python 实现)
- `timeserver/` (外部包，使用 uvx)

### 配置命名

**格式**: 简短、描述性的小写名称

**示例**:
- `graphrag`
- `timeserver`
- `filesystem`

### 工具命名

**格式**: `{server_name}_{tool_name}`

**示例**:
- `graphrag_search_graph`
- `timeserver_get-current-time`

---

## 隔离模式 (Isolation Modes)

### shared

**描述**: 所有用户共享同一个 MCP server 实例

**适用场景**:
- 无状态的 MCP server
- 轻量级 server（如 timeserver）

**示例**:
```json
{
  "name": "timeserver",
  "isolation": "shared"
}
```

### lazy_per_user

**描述**: 按需创建，每个用户一个实例，闲置超时后关闭

**适用场景**:
- 有状态的 MCP server（如 GraphRAG）
- 需要用户隔离但不想常驻内存

**示例**:
```json
{
  "name": "graphrag",
  "isolation": "lazy_per_user",
  "idle_timeout": 300
}
```

### per_user

**描述**: 每个用户独立的实例，常驻内存

**适用场景**:
- 需要持久连接的 MCP server
- 每用户独立配置

**示例**:
```json
{
  "name": "filesystem",
  "isolation": "per_user"
}
```

---

## 验证

### 检查 MCP Servers

```bash
# 查看 API
curl http://localhost:9000/api/mcp/servers

# 查看工具
curl http://localhost:9000/api/tools
```

### 测试 GraphRAG

```bash
# 直接测试 MCP server
cd /Users/xudawei/FastReAct/fastreact-nano
python3 mcp_servers/builtin/graph_rag_server.py

# 通过 Agent 测试
python3 -c "
from fastreact import Agent
import asyncio

async def test():
    agent = Agent()
    await agent._load_mcp_servers()
    result = await agent._tools.execute('graphrag_search_graph', {'query': 'AI'}, None)
    print(result)

asyncio.run(test())
"
```

---

## 总结

### 整理前

- MCP servers 散落在 `examples/` 下
- 位置不统一，难以管理
- 不符合标准项目结构

### 整理后

- ✅ 所有 MCP servers 统一在 `mcp_servers/builtin/` 下
- ✅ 配置文件在 `mcp_servers/config/` 下（示例）
- ✅ 实际配置在 `~/.fastreact/config.json` 中
- ✅ 清晰的命名规范和目录结构
- ✅ 易于维护和扩展

### 下一步

- [ ] 添加更多 MCP servers 到 `builtin/`
- [ ] 创建 MCP server 开发模板
- [ ] 添加 MCP server 测试框架
- [ ] 完善 MCP server 文档

---

**维护者**: Claude Code
**日期**: 2025-02-19
**版本**: 2.4.2
