# FastReAct Nano vs OpenClaw - 功能缺失分析

**Date**: 2025-02-27
**Status**: ⚠️ Critical Findings

---

## 🔍 核心问题

用户反馈：**"no workaround!"**

当前情况：
- ❌ Agent 说："无法访问新闻"、"没有网页浏览或API调用功能"
- ❌ 技能选择成功，但工具调用失败
- ❌ MCP fetch 服务器未加载

---

## 📊 功能对比：FastReAct Nano vs OpenClaw

### OpenClaw 的工具系统

**特点**：
1. **内置工具（First-class Tools）**:
   - `browser` - 专用Chrome/Chromium浏览器控制
   - `canvas` - A2UI视觉工作区
   - `exec` - shell命令执行
   - `cron` - 定时任务
   - `sessions` - 会话管理

2. **外部CLI工具集成**:
   - 技能（如blogwatcher）依赖外部CLI工具
   - SKILL.md中明确标注：
     ```yaml
     metadata:
       requires:
         bins: ["blogwatcher"]  # 需要外部命令
     ```

3. **工具发现机制**:
   - Agent可以调用**任何系统命令**
   - 无需MCP协议
   - 直接通过exec工具执行

### FastReAct Nano 的工具系统

**特点**：
1. **基于MCP协议的工具**:
   - MCP服务器通过stdio提供工具
   - 需要预先配置和加载
   - JSON-RPC协议通信

2. **内置工具**:
   - `exec` - shell命令执行（存在但不稳定）
   - `read_file` - 文件读取
   - `write_file` - 文件写入
   - `edit_file` - 文件编辑

3. **工具发现机制**:
   - 需要MCP服务器预先加载
   - 工具注册到ToolRegistry
   - Agent只能看到已注册的工具

---

## ❌ 根本原因分析

### 问题1: MCP服务器加载失败

**现象**：
```
[OK] MCP server 'filesystem' (stdio) registered and ready
```
**缺少**：`fetch` MCP服务器

**原因**：
1. MCP SDK依赖缺失（已安装 `mcp` 包）
2. fetch_server.py可能有问题
3. Gateway的MCP加载逻辑可能只加载了filesystem

### 问题2: exec工具限制

**现象**：
- Agent尝试调用`fetch_fetch`命令
- 结果：`fetch_fetch: command not found`

**原因**：
- Agent期望有一个名为`fetch_fetch`的命令
- 但实际没有这个命令
- exec工具只能执行系统命令，不能调用MCP工具

### 问题3: 工具系统设计差异

**OpenClaw**:
```python
# Agent可以直接调用任何命令
tool = exec_tool()
result = await tool.execute(command="curl https://api.example.com")
```

**FastReAct**:
```python
# Agent需要MCP工具已注册
# 如果MCP服务器未加载，工具不可用
tool = mcp_manager.get_tool("fetch_fetch")
if not tool:
    return "[ERROR] Tool not available"
```

---

## 🚨 Critical Finding

**OpenClaw的"魔法"**：
- 技能（如blogwatcher）**不需要**MCP服务器
- 技能直接调用**外部CLI工具**
- Agent通过`exec`工具执行这些命令

**FastReAct的限制**：
- ❌ 技能依赖MCP服务器
- ❌ MCP服务器加载失败时，技能完全无法使用
- ❌ 没有机制让技能直接调用外部CLI工具

---

## 📝 应该在CLAUDE.md中明确说明的规则

### Rule #1: MCP依赖性 ⚠️ CRITICAL

**当前状态**：
- 技能（SKILL.md）中声明的`mcp_servers`必须已加载
- 如果MCP服务器加载失败，技能完全无法使用
- 没有fallback机制

**应该明确说明**：
```markdown
## MCP服务器依赖规则

### ⚠️ CRITICAL: MCP服务器必须可用

**技能的MCP依赖**：
- 技能的`mcp_servers`字段中列出的服务器必须成功加载
- 如果MCP服务器加载失败，技能将**完全无法使用**
- Agent会返回"工具不可用"错误

**检查MCP服务器状态**：
```bash
# 检查Gateway日志
grep "MCP server.*registered" /tmp/gateway.log

# 应该看到：
# [OK] MCP server 'fetch' (stdio) registered and ready
# [OK] MCP server 'filesystem' (stdio) registered and ready
```

**当前限制**：
- ❌ 如果MCP服务器加载失败，没有fallback机制
- ❌ 技能不能直接调用外部CLI工具
- ❌ Agent无法使用未注册的工具
```

### Rule #2: exec工具的限制 ⚠️ IMPORTANT

**当前状态**：
- `exec`工具只能执行系统命令
- 不能调用MCP工具
- 命令必须在$PATH中或使用完整路径

**应该明确说明**：
```markdown
## exec工具使用规则

### 可用的场景

✅ **可以**：
- 执行系统命令：`ls`, `cat`, `python3`, `curl`
- 管道操作：`cat file.txt | grep pattern`
- 重定向：`echo "text" > output.txt`
- Python脚本：`python3 -c "print('hello')"`

❌ **不可以**：
- 调用MCP工具（如`fetch_fetch`）
- 使用不存在的命令
- 执行需要交互的命令

### 示例

**正确使用**：
```python
# Agent调用
tool = exec_tool()
result = await tool.execute(command="python3 -c 'import httpx; print(httpx.get(\"https://api.example.com\").text)'")
```

**错误使用**：
```python
# Agent尝试调用不存在的MCP工具
tool = exec_tool()
result = await tool.execute(command="fetch_fetch --url https://...")
# 错误：fetch_fetch: command not found
```
```

### Rule #3: 技能开发的最佳实践 ✅ RECOMMENDED

**当前状态**：
- 技能过度依赖MCP服务器
- 没有fallback机制

**应该明确说明**：
```markdown
## 技能开发最佳实践

### 方案A: 使用MCP服务器（推荐用于复杂功能）

**适用场景**：
- 需要复杂的状态管理
- 需要专用协议（如SSH、数据库）
- 需要跨语言集成

**步骤**：
1. 创建MCP服务器（`mcp_servers/builtin/`）
2. 在技能中声明：`mcp_servers: [fetch]`
3. 确保`recommended_tools`与MCP工具名匹配

**风险**：
- ⚠️ MCP服务器加载失败时，技能不可用
- ⚠️ 需要调试stdio通信

### 方案B: 使用exec工具（推荐用于简单功能）

**适用场景**：
- 简单的HTTP请求（如clawfeed）
- 系统命令调用
- 快速原型开发

**步骤**：
1. 不声明`mcp_servers`
2. 在技能说明中明确说明如何使用exec工具
3. 提供完整的命令示例

**优势**：
- ✅ 不依赖MCP服务器
- ✅ 立即可用
- ✅ 调试简单

**示例**：
```yaml
---
name: simple_fetch
description: Simple HTTP fetch using exec tool
tags: [http, fetch, 简单获取]
# 不声明mcp_servers
---

## Instructions

Use `exec` tool with Python to fetch data:

```bash
python3 -c "
import httpx
resp = httpx.get('https://api.example.com')
print(resp.text)
"
```
```

### 方案C: 混合方案（最灵活）

**适用场景**：
- 主要功能用exec工具
- 特殊功能用MCP服务器

**示例**：
```yaml
---
name: hybrid_skill
description: Hybrid skill with exec and MCP
tags: [hybrid, 混合]
mcp_servers: [database]  # 只用于数据库
recommended_tools: [exec, database_query]
---

## Instructions

### HTTP requests (use exec)
Use `exec` tool with Python:

```bash
python3 -c "import httpx; print(httpx.get('https://...').text)"
```

### Database queries (use MCP)
Use `database_query` MCP tool:

```json
{"sql": "SELECT * FROM news"}
```
```
```

---

## 🔧 当前建议的修复方案

### 短期修复（立即可用）

**修改news_aggregator技能**：
1. ✅ 移除`mcp_servers`依赖
2. ✅ 明确说明使用`exec`工具
3. ✅ 提供完整的Python示例

**优点**：
- ✅ 立即可用，不依赖MCP
- ✅ 与openclaw的blogwatcher模式类似
- ✅ 调试简单

### 长期修复（更好的架构）

**目标**：让exec工具可以调用外部CLI工具（如openclaw）

**实现**：
1. 在SKILL.md中添加`requires.bins`字段
2. Agent检查`requires.bins`中的命令是否可用
3. Agent使用exec工具调用这些命令

**示例**：
```yaml
---
name: news_aggregator_v2
description: News aggregation using external tools
tags: [news, 聚合]
requires:
  bins: [curl, python3]  # 声明需要的外部命令
---

## Instructions

Use `exec` tool to fetch data:

### Method 1: curl
```bash
curl -s https://hacker-news.firebaseio.com/v0/topstories.json
```

### Method 2: Python + httpx
```bash
python3 -c "
import httpx
print(httpx.get('https://...').text)
"
```
```

---

## 📊 总结

### 当前状态
- ✅ 技能自动选择：正常工作
- ❌ 工具执行：MCP服务器加载问题
- ❌ 用户体验：Agent说"无法访问"

### 与OpenClaw的差距
| 功能 | OpenClaw | FastReAct Nano |
|------|----------|-----------------|
| **外部CLI工具** | ✅ 原生支持 | ❌ 需要通过MCP或exec |
| **工具可用性** | ✅ 系统$PATH中的命令都可用 | ❌ 只有已注册工具可用 |
| **技能依赖** | ✅ 外部CLI工具 | ⚠️ MCP服务器（可能失败） |
| **Fallback** | ✅ 多个选项 | ❌ 无fallback |

### 建议规则

**CLAUDE.md应添加**：
1. ✅ **MCP依赖性规则** - 说明MCP加载失败的影响
2. ✅ **exec工具限制** - 说明什么能做什么，不能做什么
3. ✅ **技能开发最佳实践** - 提供三种方案（MCP、exec、混合）
4. ✅ **与OpenClaw的差距** - 明确说明功能限制

---

---

## 重大发现 (2025-02-27 更新)

**通过代码审查确认**：
- ❌ **ClawFeed 不使用 MCP** - 直接使用 Node.js 原生 `http.get` / `https.get`
- ❌ **OpenClaw 技能不依赖 MCP** - 直接调用外部 CLI 工具
- ✅ OpenClaw 只有一个 `mcporter` 技能支持 MCP（59个技能之一，非必需）

**详细分析**：参见 `docs/OPENCLAW_NO_MCP_FINDINGS.md`

**关键代码证据**：

```javascript
// ClawFeed 直接使用原生 HTTP (~/clawfeed/src/server.mjs)
const mod = url.startsWith('https') ? https : http;
const r = mod.get(url, { headers: {
  'User-Agent': 'AI-Digest/1.0',
  'Accept': 'text/html,application/xhtml+xml,application/xml'
} }, async (resp) => {
  // 处理响应...
});
```

```yaml
# OpenClaw 技能直接调用 CLI 工具 (~/openclaw/skills/blogwatcher/SKILL.md)
name: blogwatcher
description: Monitor blogs using the blogwatcher CLI
metadata:
  openclaw:
    requires:
      bins: ["blogwatcher"]  # 声明需要的外部命令
```

**结论**：
- FastReAct 的 MCP 依赖是**架构设计选择**，不是技术必需
- 可以通过 exec 工具实现类似 OpenClaw 的功能
- news_aggregator 已修改为使用 exec 工具（不依赖 MCP）

---

**作者**: FastReAct Team
**创建日期**: 2025-02-27
**最后更新**: 2025-02-27 (添加 OpenClaw 代码审查发现)
**严重程度**: ⚠️ Critical - 影响核心功能
**状态**: 已理解差异，已提供替代方案
