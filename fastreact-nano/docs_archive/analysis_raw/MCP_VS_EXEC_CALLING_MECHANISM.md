# MCP 调用机制 vs Exec 直接调用

**Date**: 2025-02-27
**Topic**: MCP 工具的实际调用方式

---

## 核心观察

**用户的观察**：
> "是不是所有的MCP工具的调用形式都是走npm的？所以才看上去是exec？"

**答案**：
- ✅ **MCP 服务器启动** = exec（创建子进程）
- ❌ **MCP 工具调用** = JSON-RPC 消息（不是 exec）
- ⚠️ **OpenClaw 的 CLI 工具** = 直接 exec（每次调用都是新的 exec）

---

## 调用机制对比

### 1. MCP 工具的调用机制

**两阶段调用**：

**阶段 1: 启动 MCP 服务器（exec 调用）**
```python
# FastReAct 启动 MCP 服务器
await asyncio.create_subprocess_exec(
    "python3",  # 命令：可以是 python3, npx, uvx, bunx, mcporter
    "mcp_servers/builtin/fetch_server/server.py",  # 参数
    stdin=PIPE,
    stdout=PIPE,
    stderr=PIPE
)
# 这是一次 exec 调用，启动一个长期运行的子进程
```

**阶段 2: 调用 MCP 工具（JSON-RPC 消息）**
```python
# FastReAct 调用 MCP 工具（不是 exec！）
await self._send_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",  # JSON-RPC 方法
    "params": {
        "name": "fetch_fetch",
        "arguments": {
            "url": "https://hacker-news.firebaseio.com/v0/topstories.json"
        }
    }
})
# 通过 stdin/stdout 发送 JSON 消息，不是 exec
```

**流程图**：
```
FastReAct Agent
    ↓ (exec 启动，一次性)
MCP Server 子进程（长期运行）
    ↓ (JSON-RPC over stdio)
MCP 工具执行（在子进程内）
    ↓ (JSON-RPC 响应)
返回结果给 Agent
```

**特点**：
- ✅ 服务器启动 = exec（一次性）
- ✅ 工具调用 = JSON-RPC（多次）
- ✅ 长期连接，避免重复启动开销

---

### 2. OpenClaw CLI 工具的调用机制

**直接 exec 调用**：
```bash
# OpenClaw Agent 每次调用都是新的 exec
exec_tool(command="blogwatcher scan")
exec_tool(command="blogwatcher articles")
exec_tool(command="op read 'password'")
```

**流程图**：
```
OpenClaw Agent
    ↓ (exec 调用)
CLI 工具进程（临时）
    ↓ (执行并退出)
返回结果给 Agent
```

**特点**：
- ✅ 每次调用 = 新的 exec
- ❌ 无长期连接
- ❌ 每次调用都有启动开销

---

### 3. mcporter CLI 的调用机制

**mcporter 是特殊的** - 它是一个 CLI 工具，但用来调用 MCP 服务器：

**阶段 1: mcporter 启动 MCP 服务器（exec）**
```bash
# 通过 mcporter 启动 MCP 服务器
mcporter daemon start
# 这会启动一个长期运行的 MCP 服务器进程
```

**阶段 2: mcporter 调用 MCP 工具（exec + JSON-RPC）**
```bash
# 每次调用都是新的 exec
mcporter call linear.list_issues team=ENG limit:5
# mcporter 进程启动 → 发送 JSON-RPC → 返回结果 → 退出
```

**流程图**：
```
OpenClaw Agent
    ↓ (exec 调用 mcporter)
mcporter CLI（临时）
    ↓ (JSON-RPC to daemon)
MCP Server Daemon（长期运行）
    ↓ (执行工具)
返回结果 → mcporter → Agent
```

**特点**：
- ✅ MCP daemon = 长期运行
- ✅ mcporter CLI = 每次 exec
- ⚠️ 两层架构

---

## 关键区别总结

| 维度 | MCP (FastReAct) | CLI 工具 (OpenClaw) | mcporter |
|------|-----------------|-------------------|----------|
| **启动方式** | exec (一次性) | exec (每次) | exec (每次) |
| **工具调用** | JSON-RPC (消息) | exec (每次) | JSON-RPC (通过daemon) |
| **进程生命周期** | 长期运行 | 临时 | CLI临时，daemon长期 |
| **通信协议** | stdio/HTTP | 命令行参数 | stdio/HTTP |
| **启动开销** | 一次 | 每次调用 | 每次 (CLI部分) |

---

## FastReAct 的 MCP 调用示例

**配置**：
```json
{
  "name": "fetch",
  "command": "python3",
  "args": ["mcp_servers/builtin/fetch_server/server.py"]
}
```

**启动过程**：
```python
# Agent 初始化时（一次性）
await asyncio.create_subprocess_exec(
    "python3",  # exec 调用
    "mcp_servers/builtin/fetch_server/server.py",
    stdin=PIPE,
    stdout=PIPE,
    stderr=PIPE
)
# 子进程启动，等待 JSON-RPC 请求
```

**工具调用过程**：
```python
# Agent 调用工具（多次，不需要 exec）
await mcp_client.call_tool(
    "fetch_fetch",
    {"url": "https://hacker-news.firebaseio.com/v0/topstories.json"}
)
# 发送 JSON-RPC 消息到子进程的 stdin
# 从子进程的 stdout 读取响应
```

**实际传输的数据**：
```json
// 发送到 stdin
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "fetch_fetch",
    "arguments": {
      "url": "https://hacker-news.firebaseio.com/v0/topstories.json"
    }
  }
}

// 从 stdout 读取
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[123, 456, 789, ...]"
      }
    ]
  }
}
```

---

## 为什么用户觉得"看上去是 exec"？

**原因**：
1. ✅ MCP 服务器确实是通过 exec 启动的
2. ✅ 启动命令可以是：`npx`, `python3`, `uvx`, `bunx`, `mcporter`
3. ✅ 从进程树看，确实是子进程

**但实际上**：
- ❌ MCP 工具调用不是 exec
- ✅ MCP 工具调用是 JSON-RPC 消息
- ✅ 一次 exec 启动，多次 JSON-RPC 调用

---

## MCP 服务器的启动命令

**常见的启动命令**：

```json
// Python MCP 服务器
{
  "command": "python3",
  "args": ["mcp_servers/builtin/fetch_server/server.py"]
}

// npm MCP 服务器
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "{user_workspace}"]
}

// uvx MCP 服务器
{
  "command": "uvx",
  "args": ["--from", "@builtin/timeserver", "mcp-timeserver"]
}

// bunx MCP 服务器
{
  "command": "bunx",
  "args": ["--silent", "./my-mcp-server.ts"]
}

// mcporter CLI（特殊）
{
  "command": "mcporter",
  "args": ["call", "fetch_fetch", "url:https://..."]
}
```

**共同点**：
- ✅ 都是通过 `asyncio.create_subprocess_exec()` 启动
- ✅ 都是通过 stdio 进行 JSON-RPC 通信
- ✅ 都是长期运行的子进程

---

## 结论

1. **MCP 服务器启动** = exec 调用（一次性）
   - 通过 `asyncio.create_subprocess_exec()` 创建子进程
   - 子进程长期运行，等待 JSON-RPC 请求

2. **MCP 工具调用** = JSON-RPC 消息（多次）
   - 通过 stdin/stdout 发送 JSON 消息
   - 不是 exec 调用

3. **OpenClaw CLI 工具** = exec 调用（每次）
   - 每次调用都是新的 exec
   - 工具执行完立即退出

4. **mcporter 的特殊性**：
   - 作为一个 CLI 工具，通过 exec 调用
   - 但它内部使用 JSON-RPC 与 MCP daemon 通信
   - 两层架构：CLI（临时）+ daemon（长期）

**用户的观察正确性**：
- ✅ MCP 服务器启动 = exec（正确）
- ❌ MCP 工具调用 = exec（不正确，是 JSON-RPC）
- ✅ "看上去像 exec" = 因为子进程（正确）

---

**作者**: FastReAct Team
**验证方法**: 代码审查 + FastReAct MCP client 实现
**影响**: 理解 MCP 调用机制的关键
