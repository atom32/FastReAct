# FastReAct Nano - 简洁性 vs 功能性分析

**Date**: 2025-02-27
**主题**: 保持 Nano 特性的同时解决功能缺失

---

## FastReAct Nano 的核心价值

### 什么是 "Nano"？

**FastReAct Nano** 的定位应该是：
- ✅ **轻量级** - 最小依赖
- ✅ **简洁** - 核心功能清晰
- ✅ **健壮** - 工程质量高
- ✅ **可扩展** - 通过 MCP/Skills 扩展

**Nano 不等于功能少**，而是：
- 核心精简
- 扩展灵活
- 易于理解

---

## 简洁性的破坏因素

### 如果添加更多内建工具...

**会增加**：
- ❌ 代码行数（每个工具 ~300-500 行）
- ❌ 依赖库（httpx, pillow, schedule 等）
- ❌ 维护负担（bug 修复、更新）
- ❌ 测试复杂度
- ❌ 认知负担（用户需要学习的工具更多）

**会变成**：
- FastReAct "Medium" 或 "Full"
- 不再是 "Nano"

---

## 更好的方案：保持简洁 + 增强扩展

### 方案对比

| 方案 | 简洁性 | 功能性 | 复杂度 |
|------|--------|--------|--------|
| **A. 添加内建工具** | ❌ 破坏 | ✅ 完整 | ❌ 高 |
| **B. 改进 exec 工具** | ✅ 保持 | ✅ 灵活 | ✅ 低 |
| **C. Skills 机制** | ✅ 保持 | ✅ 可扩展 | ⚠️ 中 |
| **D. MCP 增强** | ✅ 保持 | ⚠️ 依赖 MCP | ⚠️ 中 |

---

## 推荐方案：增强 exec 工具

### 核心思路

**保持 4 个核心工具不变**：
1. ✅ exec - 执行命令
2. ✅ read_file - 读取文件
3. ✅ write_file - 写入文件
4. ✅ edit_file - 编辑文件

**通过 exec 工具实现所有功能**：
- HTTP 请求 → `python3 -c "import httpx; ..."`
- Web 搜索 → `python3 -c "import duckduckgo_search; ..."`
- 定时任务 → `python3 -c "import schedule; ..."`
- 图像处理 → `python3 -c "from PIL import Image; ..."`

---

### 实现：增强的 exec 工具

**当前问题**：
- ❌ exec 工具返回原始输出
- ❌ 需要手写 Python 代码
- ❌ 没有常用命令的快捷方式

**改进方案**：

#### 1️⃣ **预设命令模板**

```python
class ExecTool(Tool):
    """Enhanced exec tool with command templates"""

    # 常用命令模板
    TEMPLATES = {
        "http_get": 'python3 -c "import httpx; print(httpx.get(\'{url}\').text)"',
        "http_post": 'python3 -c "import httpx; print(httpx.post(\'{url}\', json={data}).text)"',
        "web_search": 'python3 -c "from duckduckgo_search import DDGS; print(DDGS().text(\'{query}\', max_results={limit}))"',
        "json_parse": 'python3 -c "import json; print(json.dumps(json.loads(\'{json}\'), indent=2))"',
        "base64_encode": 'python3 -c "import base64; print(base64.b64encode(b\'{text}\').decode())"',
        "base64_decode": 'python3 -c "import base64; print(base64.b64decode(b\'{text}\').decode())"',
    }

    async def execute(self, command: str, template: str = None, **kwargs):
        if template:
            # 使用预设模板
            command = self.TEMPLATES[template].format(**kwargs)

        # 执行命令
        # ...
```

**使用示例**：
```python
# Agent 调用
await exec_tool.execute(
    template="http_get",
    url="https://api.example.com"
)

# 等价于执行
# python3 -c "import httpx; print(httpx.get('https://api.example.com').text)"
```

---

#### 2️⃣ **Python 代码执行模式**

```python
class ExecTool(Tool):
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "python_code": {"type": "string"},  # 新增
                "template": {"type": "string"},    # 新增
            },
        }

    async def execute(self, command: str = None, python_code: str = None, template: str = None, **kwargs):
        if python_code:
            # 直接执行 Python 代码
            result = await self._exec_python(python_code, kwargs)
        elif template:
            # 使用模板
            command = self.TEMPLATES[template].format(**kwargs)
            result = await self._exec_command(command)
        else:
            # 原始命令
            result = await self._exec_command(command)

        return result

    async def _exec_python(self, code: str, context: dict):
        """执行 Python 代码"""
        import subprocess
        import json

        # 注入上下文
        full_code = f"""
import httpx
import json
from pathlib import Path

# 用户代码
{code}
"""

        result = subprocess.run(
            ["python3", "-c", full_code],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"[ERROR] {result.stderr}"

        return result.stdout
```

**使用示例**：
```python
# Agent 调用（简化）
await exec_tool.execute(
    python_code="""
resp = httpx.get('https://api.example.com')
data = resp.json()
print(json.dumps(data, indent=2))
"""
)
```

---

#### 3️⃣ **智能命令推荐**

```python
class ExecTool(Tool):
    PRESETS = {
        "fetch": {
            "description": "Fetch HTTP content",
            "template": "http_get",
            "params": ["url"]
        },
        "search": {
            "description": "Search the web",
            "template": "web_search",
            "params": ["query", "limit"]
        },
        "json_parse": {
            "description": "Parse JSON string",
            "template": "json_parse",
            "params": ["json"]
        },
    }

    def list_presets(self) -> dict:
        """列出所有预设命令"""
        return {
            name: {
                "description": info["description"],
                "params": info["params"]
            }
            for name, info in self.PRESETS.items()
        }
```

---

## 方案 B：零代码 Skills 机制

### 核心思路

**学习 OpenClaw Skills**，但更简单：

```yaml
# skills/web_fetch/SKILL.md
---
name: web_fetch
description: Fetch web content using httpx
template: python
requirements:
  python_packages: ["httpx"]
---

# Web Fetch

Use `exec` tool with Python:

\`\`\`python
import httpx
response = httpx.get('{url}')
print(response.text)
\`\`\`
```

**工作原理**：
1. Agent 加载技能时，检查 `requirements`
2. 如果满足要求，自动注册为可用技能
3. Agent 需要时，使用 SKILL.md 中的模板

**优点**：
- ✅ 零代码（只要写 Markdown）
- ✅ 不增加内建工具
- ✅ 保持 Nano 特性
- ✅ 易于扩展

---

## 方案 C：MCP 增强模式

### 核心思路

**不添加内建工具**，而是：
1. 改进 MCP 加载机制
2. 提供 MCP 服务器模板
3. 简化 MCP 服务器创建

**MCP 服务器模板**：

```python
# mcp_servers/templates/http_server.py
"""
Template for creating HTTP MCP servers
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx

app = Server("{SERVER_NAME}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="{TOOL_NAME}",
            description="{DESCRIPTION}",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                },
                "required": ["url"],
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            arguments["method"],
            arguments["url"]
        )
        return [TextContent(type="text", text=response.text)]
```

**生成命令**：
```bash
# 从模板创建 MCP 服务器
fastreact mcp create http-server \
  --name=my_http \
  --tool-name=http_fetch \
  --description="Fetch HTTP content"
```

---

## 最终推荐

### 保持 Nano 特性的最佳方案

**核心原则**：
1. ✅ **不增加内建工具** - 保持 4 个核心工具
2. ✅ **增强 exec 工具** - 添加模板和 Python 模式
3. ✅ **改进 Skills** - 零代码扩展机制
4. ✅ **优化 MCP** - 简化 MCP 服务器创建

---

### 具体实施步骤

**Phase 1：增强 exec 工具**（1 周）
1. ✅ 添加预设模板（http_get, web_search, json_parse）
2. ✅ 添加 Python 代码执行模式
3. ✅ 添加智能命令补全

**Phase 2：改进 Skills**（1 周）
1. ✅ 支持模板声明
2. ✅ 自动检查 requirements
3. ✅ 更好的技能文档

**Phase 3：优化 MCP**（1 周）
1. ✅ 提供 MCP 服务器模板
2. ✅ 提供生成工具
3. ✅ 改进错误处理

---

## 对比总结

| 方案 | 保持 Nano | 功能性 | 实现难度 | 推荐度 |
|------|----------|--------|----------|--------|
| **添加内建工具** | ❌ 破坏 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| **增强 exec 工具** | ✅ 保持 | ⭐⭐⭐⭐ | ⭐⭐ | ✅ **推荐** |
| **零代码 Skills** | ✅ 保持 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ **推荐** |
| **MCP 增强** | ✅ 保持 | ⭐⭐⭐ | ⭐⭐ | ⚠️ 可选 |

---

## 结论

**FastReAct Nano 应该**：
- ✅ 保持 4 个核心工具不变
- ✅ 通过 exec 工具实现所有功能
- ✅ 学习 OpenClaw Skills 的零代码扩展
- ✅ 不盲目增加内建工具

**Nano 的哲学**：
> "Less is more, but extensible"

核心小，扩展强，才是 Nano 的正确打开方式。

---

**作者**: FastReAct Team
**状态**: 方案讨论中
**下一步**: 实施增强 exec 工具方案
