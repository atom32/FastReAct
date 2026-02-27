# OpenClaw 和 ClawFeed 不使用 MCP！

**Date**: 2025-02-27
**Status**: CONFIRMED - 关键发现！

---

## 研究结论

### 1. ClawFeed 的实现

**ClawFeed 使用原生 HTTP 请求**，不是 MCP：

```javascript
// ~/clawfeed/src/server.mjs
const mod = url.startsWith('https') ? https : http;
const r = mod.get(url, { headers: {
  'User-Agent': 'AI-Digest/1.0',
  'Accept': 'text/html,application/xhtml+xml,application/xml,application/json,*/*'
} }, async (resp) => {
  // Handle response...
});
```

**数据源**：
- ✅ RSS/Atom feeds - 直接 HTTP GET 请求
- ✅ HackerNews API - 直接 HTTP GET 请求
- ✅ Twitter/X - 直接 HTTP GET 请求
- ✅ GitHub Trending - 直接 HTTP GET 请求

**特点**：
- ❌ 不使用 MCP 协议
- ❌ 不需要 MCP 服务器
- ✅ 直接使用 Node.js 原生 `http.get` / `https.get`
- ✅ 完全独立运行

---

### 2. OpenClaw 的技能系统

**OpenClaw 技能直接调用外部 CLI 工具**：

**示例技能**：
```yaml
# ~/openclaw/skills/blogwatcher/SKILL.md
name: blogwatcher
description: Monitor blogs and RSS/Atom feeds using the blogwatcher CLI
metadata:
  openclaw:
    requires:
      bins: ["blogwatcher"]  # 需要 blogwatcher 命令
```

**Agent 调用方式**：
```bash
# Agent 直接调用 CLI 工具
blogwatcher add "My Blog" https://example.com
blogwatcher scan
blogwatcher articles
```

**更多示例**：
- `1password` → 调用 `op` CLI
- `apple-notes` → 调用 `memo` CLI
- `apple-reminders` → 调用 `remindctl` CLI
- `bear-notes` → 调用 `grizzly` CLI

---

### 3. OpenClaw 的 MCP 支持

**OpenClaw 有一个 `mcporter` 技能**，但这只是它的 59 个技能之一：

```yaml
# ~/openclaw/skills/mcporter/SKILL.md
name: mcporter
description: Use the mcporter CLI to call MCP servers directly
metadata:
  openclaw:
    requires:
      bins: ["mcporter"]  # 需要 mcporter CLI
```

**关键点**：
- ✅ OpenClaw **可以**使用 MCP（通过 mcporter 技能）
- ✅ 但这不是必需的，只是**可选功能**
- ✅ 大部分技能直接使用 CLI 工具，不需要 MCP

---

## 与 FastReAct 的对比

| 维度 | OpenClaw + ClawFeed | FastReAct Nano |
|------|---------------------|----------------|
| **数据获取** | 原生 HTTP 请求 | MCP 服务器 |
| **工具集成** | CLI 工具 (直接调用) | MCP 协议 |
| **技能依赖** | 外部 CLI 命令 | MCP 服务器 |
| **失败处理** | 命令不存在时提示安装 | MCP 加载失败时技能不可用 |
| **灵活性** | 高（任何命令都可以） | 低（只有 MCP 工具） |

---

## 核心差异

### OpenClaw 的"魔法"

**技能定义**：
```yaml
requires:
  bins: ["blogwatcher"]  # 声明需要的外部命令
```

**Agent 行为**：
1. 检查 `blogwatcher` 命令是否在 `$PATH` 中
2. 如果不存在，提示用户安装
3. 如果存在，直接通过 `exec` 工具调用

**示例调用**：
```bash
# Agent 调用 blogwatcher 技能
exec_tool(command="blogwatcher scan")
exec_tool(command="blogwatcher articles")
```

### FastReAct 的限制

**技能定义**：
```yaml
mcp_servers: [fetch]  # 声明需要的 MCP 服务器
recommended_tools: [fetch_fetch]  # 声明需要的工具
```

**Agent 行为**：
1. 检查 `fetch` MCP 服务器是否已加载
2. 如果未加载，技能**完全无法使用**
3. 如果已加载，调用 `fetch_fetch` 工具

**问题**：
- ❌ MCP 服务器加载失败时，没有 fallback
- ❌ 不能直接调用外部 CLI 工具
- ❌ 技能过度依赖 MCP 服务器

---

## FastReAct 的当前问题

### 问题 1: MCP 配置加载混乱

**Config.load() 优先级**：
```python
default_paths = [
    Path.home() / ".fastreact" / "config.json",  # 最高优先级
    Path.cwd() / ".fastreact" / "config.json",
    Path.cwd() / "config.json",
]
```

**导致**：
- `~/.fastreact/config.json` 覆盖项目配置
- `mcp_servers/config/shared.json` 被忽略
- 用户不清楚哪个配置文件生效

### 问题 2: 技能与 MCP 强耦合

**news_aggregator 技能**：
```yaml
mcp_servers: [fetch]
recommended_tools: [fetch_fetch]
```

**结果**：
- 如果 fetch MCP 服务器未加载 → Agent 说"无法访问新闻"
- 没有使用 exec 工具的 fallback 方案
- 技能不能独立工作

### 问题 3: 缺少 CLI 工具支持

**OpenClaw 有**：
```yaml
requires:
  bins: ["blogwatcher"]  # 声明需要的外部命令
```

**FastReAct 缺少**：
- ❌ 没有 `requires.bins` 字段
- ❌ Agent 不能检查外部命令是否存在
- ❌ Agent 不能直接调用 CLI 工具

---

## 建议修复方案

### 方案 A: 让 news_aggregator 使用 exec 工具 ✅ (已完成)

**修改前**：
```yaml
mcp_servers: [fetch]
recommended_tools: [fetch_fetch]
```

**修改后** (已在 SKILL.md 中更新)：
```yaml
# 不依赖 MCP 服务器
# 使用 exec 工具 + Python 代码
```

**Agent 调用**：
```bash
# 使用 Python httpx 获取数据
python3 -c "
import httpx
resp = httpx.get('https://hacker-news.firebaseio.com/v0/topstories.json')
print(resp.json())
"
```

**优点**：
- ✅ 立即可用，不依赖 MCP
- ✅ 与 OpenClaw 的 blogwatcher 模式类似
- ✅ 调试简单

### 方案 B: 实现 requires.bins 字段

**SKILL.md 格式**：
```yaml
---
name: news_aggregator_v2
description: News aggregation using external tools
requires:
  bins: [curl, python3]  # 声明需要的外部命令
---
```

**Agent 行为**：
```python
# 检查命令是否存在
import shutil
for bin_name in skill.requires.bins:
    if not shutil.which(bin_name):
        return f"[ERROR] Required command '{bin_name}' not found. Please install it first."

# 使用 exec 工具调用
tool = exec_tool()
result = await tool.execute(command="python3 -c '...'")
```

### 方案 C: 配置文件优先级调整

**建议优先级**：
```python
default_paths = [
    Path.cwd() / ".fastreact" / "config.json",  # 项目配置优先
    Path.cwd() / "mcp_servers" / "config" / "shared.json",  # MCP 共享配置
    Path.home() / ".fastreact" / "config.json",  # 用户配置（追加）
]
```

**合并策略**：
- 项目配置：定义必需的 MCP 服务器
- 用户配置：覆盖 LLM API key、个人设置
- 结果：项目配置 + 用户配置合并

---

## 验证命令

**检查 OpenClaw 技能依赖 CLI**：
```bash
grep -r "requires.*bins" ~/openclaw/skills/*/SKILL.md | wc -l
# 输出: 大量技能使用 bins
```

**检查 ClawFeed 不使用 MCP**：
```bash
grep -r "mcp\|MCP" ~/clawfeed/src/
# 输出: 无 MCP 相关代码
```

**检查 ClawFeed 使用原生 HTTP**：
```bash
grep "http.get\|https.get" ~/clawfeed/src/server.mjs
# 输出: 大量原生 HTTP 请求
```

---

## 结论

1. **OpenClaw 不依赖 MCP** - 它的技能系统直接调用 CLI 工具
2. **ClawFeed 不使用 MCP** - 它直接使用 Node.js 原生 HTTP 请求
3. **FastReAct 过度依赖 MCP** - 这是架构设计问题，不是 bug

**建议**：
- ✅ 短期：使用 exec 工具实现技能（已完成）
- ✅ 中期：实现 requires.bins 字段支持 CLI 工具
- ✅ 长期：调整配置文件优先级和合并策略

---

**作者**: FastReAct Team
**验证方法**: 代码审查
**影响**: 架构理解
