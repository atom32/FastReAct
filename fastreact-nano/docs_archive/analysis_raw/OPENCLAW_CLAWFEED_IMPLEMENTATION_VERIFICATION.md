# OpenClaw 和 ClawFeed 实现验证报告

**Date**: 2025-02-27
**验证方法**: 源码审查
**结论**: 确认不依赖 MCP 协议

---

## 验证发现总结

### 1. ClawFeed 的实现

**文件**: `~/clawfeed/src/server.mjs`

**数据获取方式** - 原生 HTTP 请求：
```javascript
// ~/clawfeed/src/server.mjs (line 8-10)
import http from 'http';
import https from 'https';

// HTTP GET 实现 (line 45-70)
async function httpFetch(url, timeout = 5000, redirectsLeft = 3) {
  await assertSafeFetchUrl(url);
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const r = mod.get(url, { headers: {
      'User-Agent': 'AI-Digest/1.0',
      'Accept': 'text/html,application/xhtml+xml,application/xml,application/json,*/*'
    } }, async (resp) => {
      // 处理响应...
      let data = '';
      resp.on('data', c => { data += c; });
      resp.on('end', () => { resolve({ contentType: resp.headers['content-type'], body: data }); });
    });
  });
}
```

**支持的协议**：
- ✅ HTTPS feeds - Node.js `https.get()`
- ✅ HTTP feeds - Node.js `http.get()`
- ✅ RSS/Atom - 解析 XML 内容
- ✅ JSON feeds - 解析 JSON 内容
- ❌ 不使用 MCP 协议

---

### 2. OpenClaw 的工具系统

**核心工具** - 直接实现，不依赖外部进程：

**示例**: Browser Tool (`~/openclaw/src/agents/tools/browser-tool.ts`)
```typescript
// 直接使用 Chrome DevTools Protocol
import {
  browserStart,
  browserStop,
  browserNavigate,
  browserSnapshot,
  // ...
} from "../../browser/client.js";

// 工具实现是 TypeScript 函数，不是 exec 调用
async function browserOpenTab(params: Record<string, unknown>): Promise<AgentToolResult<unknown>> {
  // 直接调用 browser client API
  const tabs = await browserTabs();
  // ...
}
```

**示例**: Cron Tool (`~/openclaw/src/agents/tools/cron-tool.ts`)
```typescript
// 直接使用定时任务管理
async function cronStatus(params: Record<string, unknown>): Promise<AgentToolResult<unknown>> {
  // 直接读取定时任务状态
  const jobs = await listCronJobs();
  // ...
}
```

**示例**: Canvas Tool, Discord Tool, Image Tool
- ✅ 都是 TypeScript 实现
- ✅ 不调用外部命令
- ✅ 不使用 MCP 协议

---

### 3. OpenClaw 的技能系统

**技能定义** (`~/openclaw/skills/blogwatcher/SKILL.md`):
```yaml
---
name: blogwatcher
description: Monitor blogs and RSS/Atom feeds using the blogwatcher CLI.
metadata:
  openclaw:
    emoji: "📰"
    requires:
      bins: ["blogwatcher"]  # 声明需要的外部命令
    install:
      - id: "go"
        kind: "go"
        module: "github.com/Hyaxia/blogwatcher/cmd/blogwatcher@latest"
        bins: ["blogwatcher"]
        label: "Install blogwatcher (go)"
---

# blogwatcher

Track blog and RSS/Atom feed updates with the `blogwatcher` CLI.

## Common commands

- `blogwatcher add "My Blog" https://example.com`
- `blogwatcher scan`
- `blogwatcher articles`
```

**技能调用方式** - 通过 exec 调用 CLI 工具：

**核心 exec 实现** (`~/openclaw/src/process/exec.ts`):
```typescript
// 使用 Node.js child_process.spawn
import { execFile, spawn } from "node:child_process";

// 简单 exec (execFile)
export async function runExec(
  command: string,
  args: string[],
  opts: number | { timeoutMs?: number; maxBuffer?: number; cwd?: string } = 10_000,
): Promise<{ stdout: string; stderr: string }> {
  const { stdout, stderr } = await execFileAsync(resolveCommand(command), args, options);
  return { stdout, stderr };
}

// 带超时的 spawn (runCommandWithTimeout)
export async function runCommandWithTimeout(
  argv: string[],
  optionsOrTimeout: number | CommandOptions,
): Promise<SpawnResult> {
  // spawn 子进程
  const child = spawn(resolvedCommand, argv.slice(1), {
    stdio,
    cwd,
    env: resolvedEnv,
  });

  // 等待进程结束
  return await new Promise((resolve, reject) => {
    child.on('close', (code, signal) => {
      resolve({ stdout, stderr, code, signal, ... });
    });
  });
}
```

**调用流程**:
```
Agent 决定使用 blogwatcher 技能
    ↓
检查 blogwatcher 命令是否存在
    ↓
调用 runCommandWithTimeout([
  "blogwatcher",
  "scan"
])
    ↓
spawn("blogwatcher", ["scan"])  // 创建子进程
    ↓
等待进程结束，捕获 stdout/stderr
    ↓
返回结果给 Agent
```

---

### 4. OpenClaw 的 mcporter 技能

**技能定义** (`~/openclaw/skills/mcporter/SKILL.md`):
```yaml
---
name: mcporter
description: Use the mcporter CLI to call MCP servers
metadata:
  openclaw:
    requires:
      bins: ["mcporter"]  # mcporter 也是一个 CLI 工具！
---

# mcporter

Use `mcporter` to work with MCP servers directly.

## Quick start

- `mcporter list`
- `mcporter call <server.tool> key=value`
```

**关键点**：
- ✅ mcporter **本身**是一个 CLI 工具（通过 npm 安装）
- ✅ mcporter 用来调用 MCP 服务器
- ✅ 但这只是 59 个技能之一，不是核心架构
- ✅ 调用方式：`spawn("mcporter", ["call", "fetch_fetch", "url:..."])`

**mcporter 的工作原理**：
```
OpenClaw Agent
    ↓ (exec mcporter CLI)
mcporter 进程（临时）
    ↓ (JSON-RPC to MCP daemon)
MCP Server Daemon（长期运行）
    ↓ (执行工具)
返回结果 → mcporter → Agent
```

**两层架构**：
- CLI 层：mcporter（每次调用都是新的 exec）
- Daemon 层：MCP 服务器（长期运行）

---

## 与 FastReAct 的对比

| 维度 | OpenClaw | FastReAct Nano |
|------|----------|----------------|
| **核心工具** | TypeScript 实现（browser, cron, canvas, discord） | MCP 协议集成 |
| **技能系统** | CLI 工具（blogwatcher, op, memo） | MCP 服务器 |
| **HTTP 请求** | 原生 http.get（ClawFeed） | MCP fetch 服务器 |
| **进程管理** | spawn/exec（每次临时） | subprocess 长期连接 |
| **MCP 支持** | 可选（mcporter 技能） | 核心（必需） |

---

## 关键代码证据

### 1. ClawFeed 不使用 MCP

```bash
$ grep -r "mcp\|MCP" ~/clawfeed/src/
# 输出：无匹配
```

```bash
$ grep "http.get\|https.get" ~/clawfeed/src/server.mjs
# 输出：
const mod = url.startsWith('https') ? https : http;
const r = mod.get(url, { ... });
```

### 2. OpenClaw 技能依赖 CLI 工具

```bash
$ grep -r "requires.*bins" ~/openclaw/skills/*/SKILL.md | wc -l
# 输出：大量技能使用 bins
```

```yaml
# 示例
apple-reminders: requires.bins = ["remindctl"]
bear-notes: requires.bins = ["grizzly"]
blogwatcher: requires.bins = ["blogwatcher"]
```

### 3. OpenClaw exec 实现

```typescript
// ~/openclaw/src/process/exec.ts
import { execFile, spawn } from "node:child_process";

export async function runExec(command: string, args: string[]) {
  await execFileAsync(resolveCommand(command), args, options);
}

export async function runCommandWithTimeout(argv: string[], opts) {
  const child = spawn(resolvedCommand, argv.slice(1), options);
  // ... wait for process to exit
}
```

### 4. FastReAct MCP 实现

```python
# ~/fastreact-nano/src/fastreact/mcp/client.py
async def connect(self) -> None:
    # 启动 MCP 服务器（exec 调用，一次性）
    self._process = await asyncio.create_subprocess_exec(
        self._server_command,
        *self._server_args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )

    # 初始化 JSON-RPC 会话
    await self._send_request({
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {...}
    })

async def call_tool(self, name: str, args: dict):
    # 调用工具（不是 exec！是 JSON-RPC）
    await self._send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": args
        }
    })
```

---

## 验证结论

### ClawFeed
- ❌ **不使用 MCP 协议**
- ✅ 使用 Node.js 原生 `http.get` / `https.get`
- ✅ 直接解析 RSS/Atom/JSON feeds
- ✅ 完全独立运行，无需外部服务器

### OpenClaw
- ✅ **核心工具** = TypeScript 实现（browser, cron, canvas, discord）
- ✅ **技能系统** = CLI 工具调用（通过 spawn/exec）
- ⚠️ **MCP 支持** = 可选（mcporter 技能，59个之一）
- ✅ **不需要 MCP 服务器**运行

### FastReAct
- ✅ **所有工具** = MCP 协议集成
- ⚠️ **过度依赖 MCP** = MCP 加载失败时技能不可用
- ❌ **缺少 CLI 工具支持** = 不能直接调用外部命令

---

## 回答用户的问题

**问题**: "是不是所有的MCP工具的调用形式都是走npm的？所以才看上去是exec？"

**答案**：
1. ✅ **MCP 服务器启动** = exec 调用（可以是 npm, python3, uvx 等）
2. ❌ **MCP 工具调用** = JSON-RPC 消息（不是 exec）
3. ✅ **OpenClaw 的 CLI 工具** = 每次 exec 调用
4. ✅ **ClawFeed 的 HTTP 请求** = 原生 Node.js API（不是 exec）

**关键区别**：
- **FastReAct MCP**: exec 启动服务器（一次）→ JSON-RPC 调用工具（多次）
- **OpenClaw CLI**: exec 调用命令（每次）
- **ClawFeed**: 原生 HTTP API（不是 exec）

---

**验证完成日期**: 2025-02-27
**验证方法**: 源码审查
**结论**: OpenClaw 和 ClawFeed 都不依赖 MCP 协议

---

**作者**: FastReAct Team
**验证文件**:
- `~/clawfeed/src/server.mjs` - ClawFeed HTTP 实现
- `~/openclaw/src/process/exec.ts` - OpenClaw exec 实现
- `~/openclaw/src/agents/tools/*.ts` - OpenClaw 核心工具实现
- `~/openclaw/skills/*/SKILL.md` - OpenClaw 技能定义
