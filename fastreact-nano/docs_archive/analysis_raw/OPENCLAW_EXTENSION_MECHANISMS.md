# OpenClaw vs FastReAct - 扩展能力对比

**Date**: 2025-02-27
**主题**: 如何添加新能力/功能

---

## OpenClaw 的扩展机制

OpenClaw 有 **3 种扩展方式**，根据复杂度选择：

---

### 1️⃣ **Skills（技能）** - 最简单

**用途**: 教 Agent 如何使用外部 CLI 工具

**文件格式**: SKILL.md (YAML frontmatter + markdown)

**示例** (`~/openclaw/skills/blogwatcher/SKILL.md`):
```yaml
---
name: blogwatcher
description: Monitor blogs and RSS/Atom feeds using the blogwatcher CLI
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

**工作原理**:
1. OpenClaw 检查 `blogwatcher` 命令是否存在（通过 `requires.bins`）
2. 如果不存在，提示用户安装（通过 `install` 规格）
3. Agent 需要时，通过 `exec` 工具调用命令
4. 每次调用都是新的 `spawn("blogwatcher", ["scan"])`

**适用场景**:
- ✅ 简单的 CLI 工具集成
- ✅ 不需要复杂状态管理
- ✅ 快速原型开发

**优点**:
- ✅ 非常简单 - 只需要写 Markdown 文件
- ✅ 不需要编写代码
- ✅ 可以通过 ClawHub 分享

**缺点**:
- ❌ 依赖外部 CLI 工具
- ❌ 每次调用都有启动开销
- ❌ 无法保持长期连接

---

### 2️⃣ **Tools（工具）** - 中等复杂度

**用途**: 实现内置的核心功能（浏览器、画布、定时任务等）

**文件格式**: TypeScript 文件（`src/agents/tools/*.ts`）

**示例** (`~/openclaw/src/agents/tools/browser-tool.ts`):
```typescript
import {
  browserStart,
  browserStop,
  browserNavigate,
  browserSnapshot,
} from "../../browser/client.js";

const BrowserToolSchema = Type.Object({
  action: stringEnum(["open_tab", "navigate", "snapshot", ...]),
  url: Type.Optional(Type.String()),
  // ...
});

async function browserOpenTab(params: Record<string, unknown>) {
  // 直接调用 browser client API
  const tabs = await browserTabs();
  return {
    content: [{ type: "text", text: JSON.stringify(tabs) }],
  };
}

export const browserTool: AnyAgentTool = {
  name: "browser",
  schema: BrowserToolSchema,
  handler: async (params, context) => {
    // 根据 action 分发到不同函数
    const action = params.action as string;
    if (action === "open_tab") return browserOpenTab(params);
    // ...
  },
};
```

**工作原理**:
1. 工具是 TypeScript 函数
2. 直接调用内部 API（不是 exec）
3. 无需外部依赖
4. 编译时类型检查

**适用场景**:
- ✅ 核心功能（浏览器、画布、定时任务）
- ✅ 需要类型安全
- ✅ 需要高性能（无进程启动开销）

**优点**:
- ✅ 类型安全（TypeScript）
- ✅ 无外部依赖
- ✅ 性能好（直接 API 调用）
- ✅ 易于调试

**缺点**:
- ❌ 需要编写 TypeScript 代码
- ❌ 需要重新编译部署
- ❌ 更新需要发布新版本

**内置工具列表**:
- `browser` - Chrome/Chromium 浏览器控制
- `canvas` - A2UI 视觉工作区
- `cron` - 定时任务管理
- `exec` - shell 命令执行
- `sessions_*` - 会话管理
- `message` - 消息发送（多渠道）
- `image` - 图像处理
- `nodes` - 远程节点管理

---

### 3️⃣ **Plugins（插件）** - 最复杂

**用途**: 扩展 Gateway 功能，添加新工具、RPC 方法、HTTP 处理器

**文件格式**: TypeScript 模块 + `openclaw.plugin.json`

**示例结构**:
```
my-plugin/
├── package.json
├── openclaw.plugin.json    # 插件清单
├── src/
│   ├── index.ts            # 插件入口
│   ├── tools.ts           # 自定义工具
│   └── skills/            # 技能目录
│       └── my-skill/
│           └── SKILL.md
└── README.md
```

**插件清单** (`openclaw.plugin.json`):
```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "My custom plugin",
  "author": "Your Name",
  "minOpenclawVersion": "2025.1.0",
  "skills": ["src/skills/my-skill"],
  "config": {
    "schema": {
      "type": "object",
      "properties": {
        "apiKey": { "type": "string" }
      }
    }
  }
}
```

**插件入口** (`src/index.ts`):
```typescript
import type { PluginContext } from "@openclaw/plugin";

export default async function register(api: PluginContext) {
  // 注册 Gateway RPC 方法
  api.gateway.registerMethod("my_method", async (params) => {
    return { result: "ok" };
  });

  // 注册 HTTP 处理器
  api.gateway.addHandler("GET", "/my-endpoint", async (req) => {
    return { status: 200, body: "Hello" };
  });

  // 注册 Agent 工具
  api.tools.register({
    name: "my_tool",
    schema: { /* ... */ },
    handler: async (params, context) => {
      return { content: [{ type: "text", text: "Result" }] };
    },
  });

  // 注册 CLI 命令
  api.cli.registerCommand("my-cmd", async (args) => {
    console.log("My command");
  });

  // 启动后台服务
  api.background.start(async () => {
    // 长期运行的服务
  });
}
```

**插件安装**:
```bash
# 从 npm 安装
openclaw plugins install @openclaw/voice-call

# 启用插件
openclaw plugins enable voice-call

# 配置插件（~/.openclaw/openclaw.json）
{
  plugins: {
    entries: {
      "voice-call": {
        enabled: true,
        config: {
          phoneNumber: "+1234567890"
        }
      }
    }
  }
}
```

**适用场景**:
- ✅ 复杂的功能扩展
- ✅ 需要后台服务
- ✅ 需要自定义 RPC/HTTP 端点
- ✅ 第三方集成（Microsoft Teams, Matrix, Nostr 等）

**优点**:
- ✅ 完整的扩展能力
- ✅ 可以添加工具、RPC、HTTP 处理器
- ✅ 可以包含技能
- ✅ 通过 npm 分发

**缺点**:
- ❌ 最复杂
- ❌ 需要深入了解 OpenClaw 内部
- ❌ 需要编写 TypeScript 代码

**官方插件**:
- `@openclaw/voice-call` - 语音通话
- `@openclaw/msteams` - Microsoft Teams 集成
- `@openclaw/matrix` - Matrix 协议
- `@openclaw/zalouser` - Zalo Personal

---

## 扩展方式对比

| 维度 | Skills | Tools | Plugins |
|------|--------|-------|---------|
| **复杂度** | 低（Markdown） | 中（TypeScript） | 高（TypeScript） |
| **文件位置** | `skills/*/SKILL.md` | `src/agents/tools/*.ts` | `extensions/*` |
| **代码需求** | 无（只要 Markdown） | TypeScript | TypeScript |
| **重新编译** | 不需要 | 需要 | 不需要（运行时加载） |
| **分发方式** | ClawHub / git | npm（核心） | npm |
| **更新方式** | 热加载 | 发布新版本 | npm install |
| **适用场景** | CLI 工具集成 | 核心功能 | 复杂扩展 |
| **性能** | 中（spawn 开销） | 高（直接 API） | 高（直接 API） |

---

## FastReAct 的扩展机制

FastReAct 主要依赖 **MCP 协议**：

### MCP 服务器

**文件格式**: Python/TypeScript/任何语言（stdio 或 HTTP）

**示例** (`mcp_servers/builtin/fetch_server/server.py`):
```python
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("fetch-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="fetch_fetch",
            description="Fetch HTTP content",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "timeout": {"type": "number"}
                },
                "required": ["url"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "fetch_fetch":
        # 实现逻辑
        result = httpx.get(arguments["url"]).text
        return [TextContent(type="text", text=result)]
```

**配置** (`mcp_servers/config/shared.json`):
```json
{
  "servers": [
    {
      "name": "fetch",
      "command": "python3",
      "args": ["mcp_servers/builtin/fetch_server/server.py"],
      "isolation": "shared"
    }
  ]
}
```

**优点**:
- ✅ 语言无关（Python, TypeScript, Go, Rust 等）
- ✅ 标准化协议（JSON-RPC）
- ✅ 社区生态（npm MCP 服务器）
- ✅ 进程隔离

**缺点**:
- ❌ 需要实现 MCP 协议
- ❌ 依赖 MCP 服务器加载
- ❌ 调试复杂（stdio 通信）

---

## 如何选择扩展方式

### OpenClaw 决策树

```
需要添加新功能？
    ↓
是否是简单的 CLI 工具集成？
    ├─ 是 → 使用 Skills（SKILL.md）
    │        - blogwatcher, 1password, apple-notes 等
    │
    └─ 否 → 是否需要长期运行的服务？
        ├─ 是 → 使用 Plugins
        │        - Microsoft Teams, Matrix, Voice Call
        │
        └─ 否 → 是否是核心功能？
            ├─ 是 → 使用 Tools（TypeScript）
            │        - browser, canvas, cron
            │
            └─ 否 → 考虑 Skills（如果可以用 CLI 实现）
```

### FastReAct 决策树

```
需要添加新功能？
    ↓
是否有现成的 MCP 服务器？
    ├─ 是 → 直接使用（npm 或 Python）
    │        - @modelcontextprotocol/server-filesystem
    │        - mcp-server-sqlite
    │
    └─ 否 → 是否需要复杂状态管理？
        ├─ 是 → 编写 MCP 服务器
        │        - Python + mcp SDK
        │
        └─ 否 → 使用 exec 工具
             - python3 -c "..."
```

---

## 具体示例

### 示例 1: 添加 HTTP 请求功能

**OpenClaw**:
```yaml
# skills/http-fetch/SKILL.md
---
name: http_fetch
description: Fetch HTTP content using curl CLI
metadata:
  openclaw:
    requires:
      bins: ["curl"]
---

# HTTP Fetch

Use `curl` to fetch HTTP content:

\`\`\`bash
curl -s https://example.com
\`\`\`
```

**FastReAct**:
```python
# mcp_servers/builtin/fetch_server/server.py
from mcp.server import Server
import httpx

app = Server("fetch-server")

@app.call_tool()
async def fetch_fetch(name, arguments):
    result = httpx.get(arguments["url"]).text
    return [TextContent(type="text", text=result)]
```

---

### 示例 2: 添加浏览器控制功能

**OpenClaw**:
```typescript
// src/agents/tools/browser-tool.ts
export const browserTool: AnyAgentTool = {
  name: "browser",
  schema: BrowserToolSchema,
  handler: async (params, context) => {
    if (params.action === "navigate") {
      await browserNavigate(params.url);
      return { content: [{ type: "text", text: "Navigated" }] };
    }
  },
};
```

**FastReAct**:
```python
# 需要找到或实现浏览器 MCP 服务器
# 例如：chrome-devtools-mcp（npm）
```

---

### 示例 3: 添加定时任务功能

**OpenClaw**:
```typescript
// src/agents/tools/cron-tool.ts
export const cronTool: AnyAgentTool = {
  name: "cron",
  schema: CronToolSchema,
  handler: async (params, context) => {
    if (params.action === "add") {
      await createCronJob(params.job);
      return { content: [{ type: "text", text: "Job created" }] };
    }
  },
};
```

**FastReAct**:
```python
# 需要实现 schedule MCP 服务器
# 或使用 Python 的 schedule 库 + exec 工具
```

---

## 总结

### OpenClaw 的扩展哲学

**分层设计**:
1. **Skills** - 最外层，零代码，通过 CLI 工具扩展
2. **Tools** - 中间层，TypeScript，核心功能
3. **Plugins** - 最内层，完整扩展能力

**关键特点**:
- ✅ **灵活性** - 三种方式覆盖不同复杂度
- ✅ **渐进式** - 从简单到复杂
- ✅ **生态友好** - ClawHub 分享技能
- ✅ **不依赖 MCP** - 直接实现或通过 CLI 工具

### FastReAct 的扩展哲学

**标准化**:
- ✅ **MCP 协议** - 统一的扩展标准
- ✅ **语言无关** - 任何语言都可以实现
- ✅ **进程隔离** - 稳定性更好

**关键特点**:
- ✅ **标准化** - MCP 协议
- ✅ **生态丰富** - npm MCP 服务器
- ✅ **类型安全** - JSON Schema
- ⚠️ **过度依赖** - MCP 加载失败时功能不可用

---

**作者**: FastReAct Team
**参考资料**:
- OpenClaw Skills: `~/openclaw/docs/tools/skills.md`
- OpenClaw Tools: `~/openclaw/docs/tools/index.md`
- OpenClaw Plugins: `~/openclaw/docs/tools/plugin.md`
