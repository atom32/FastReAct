# FastReAct 工具系统分析与改进建议

**Date**: 2025-02-27
**主题**: 内建工具数量分析

---

## 当前状况

### FastReAct 内建工具（4 个）

```python
src/fastreact/tools/
├── exec_tool.py      # 执行 shell 命令
├── read_file.py      # 读取文件
├── write_file.py     # 写入文件
└── edit_file.py      # 编辑文件（基于字符串替换）
```

**特点**：
- ✅ 基础文件操作完备
- ✅ exec 工具灵活（可以调用任何命令）
- ❌ **工具数量太少**（只有 4 个）
- ❌ 缺少常见的高级功能
- ❌ 过度依赖 MCP 服务器

---

### OpenClaw 内建工具（10+ 个）

```typescript
src/agents/tools/
├── browser-tool.ts       # 浏览器控制
├── canvas-tool.ts        # A2UI 视觉工作区
├── cron-tool.ts          # 定时任务管理
├── exec-tool.ts          # Shell 命令执行
├── sessions-*.ts         # 会话管理（5 个工具）
├── message-tool.ts       # 消息发送（多渠道）
├── image-tool.ts         # 图像处理
├── nodes-tool.ts         # 远程节点管理
└── ...
```

**工具分组**：
- `group:runtime` - exec, bash, process
- `group:fs` - read, write, edit, apply_patch
- `group:sessions` - sessions_list, sessions_history, sessions_send, sessions_spawn, session_status
- `group:memory` - memory_search, memory_get
- `group:web` - web_search, web_fetch
- `group:ui` - browser, canvas
- `group:automation` - cron, gateway
- `group:messaging` - message
- `group:nodes` - nodes

---

## 问题分析

### 1. 工具数量对比

| 项目 | 内建工具数量 | 扩展方式 |
|------|--------------|----------|
| **FastReAct** | 4 个 | MCP 服务器 |
| **OpenClaw** | 10+ 个 | Skills（零代码）+ Tools（TS） + Plugins |

**差距**：FastReAct 的工具数量不到 OpenClaw 的一半

---

### 2. 缺失的关键工具

#### 🔴 高优先级（严重影响使用）

**1. HTTP/Web 请求工具**
- **现状**：依赖 MCP fetch 服务器
- **问题**：MCP 加载失败时无法使用
- **影响**：news_aggregator 等技能完全不可用
- **建议**：创建 `http_tool.py`

```python
class HttpTool(Tool):
    """HTTP GET/POST requests using httpx"""

    @property
    def name(self) -> str:
        return "http_request"

    async def execute(self, url: str, method: str = "GET", ...):
        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(url)
            elif method == "POST":
                resp = await client.post(url, json=data)
            return resp.text
```

**2. 搜索工具**
- **现状**：无搜索能力
- **问题**：Agent 无法搜索网络信息
- **影响**：信息获取能力受限
- **建议**：创建 `search_tool.py`

```python
class SearchTool(Tool):
    """Web search using duckduckgo or brave API"""

    @property
    def name(self) -> str:
        return "web_search"

    async def execute(self, query: str, limit: int = 5):
        # 使用 duckduckgo 或 brave search API
        results = search_web(query, limit)
        return format_results(results)
```

**3. 会话管理工具**
- **现状**：会话管理逻辑在 Agent 内部
- **问题**：无法直接管理会话
- **影响**：多会话场景受限
- **建议**：创建 `session_tool.py`

```python
class SessionTool(Tool):
    """Session management"""

    @property
    def name(self) -> str:
        return "session_manage"

    async def execute(self, action: str, session_id: str = None):
        if action == "list":
            return list_sessions()
        elif action == "history":
            return get_history(session_id)
        elif action == "delete":
            return delete_session(session_id)
```

---

#### 🟡 中优先级（增强功能）

**4. 定时任务工具**
- **现状**：无定时任务
- **问题**：无法调度定期任务
- **影响**：自动化能力受限
- **建议**：创建 `schedule_tool.py`

```python
class ScheduleTool(Tool):
    """Schedule and manage cron-like tasks"""

    @property
    def name(self) -> str:
        return "schedule"

    async def execute(self, action: str, task: dict = None):
        if action == "add":
            return add_scheduled_task(task)
        elif action == "list":
            return list_tasks()
        elif action == "remove":
            return remove_task(task_id)
```

**5. 内存搜索工具**
- **现状**：依赖外部记忆系统
- **问题**：无法搜索历史对话
- **影响**：上下文检索受限
- **建议**：创建 `memory_tool.py`

```python
class MemoryTool(Tool):
    """Search and manage conversation memory"""

    @property
    def name(self) -> str:
        return "memory_search"

    async def execute(self, query: str, session_id: str = None):
        # 搜索本地 memory.json
        results = search_memory(query, session_id)
        return format_results(results)
```

**6. 图像处理工具**
- **现状**：无图像处理
- **问题**：无法处理图像
- **影响**：多模态能力受限
- **建议**：创建 `image_tool.py`

```python
class ImageTool(Tool):
    """Basic image operations"""

    @property
    def name(self) -> str:
        return "image_process"

    async def execute(self, action: str, image_path: str, **kwargs):
        if action == "resize":
            return resize_image(image_path, kwargs["size"])
        elif action == "convert":
            return convert_format(image_path, kwargs["format"])
        elif action == "info":
            return get_image_info(image_path)
```

---

#### 🟢 低优先级（锦上添花）

**7. 数据库工具**
- SQLite 查询和操作
- 可能会被 SQL 注入风险

**8. 文件系统工具**
- 目录遍历
- 文件搜索
- 已经有 read/write/edit，优先级较低

**9. Git 操作工具**
- Git 常用命令封装
- 可以通过 exec_tool 实现

**10. 浏览器工具**
- 需要复杂的依赖（Playwright/Selenium）
- 体积大，不适合内建
- 建议通过 MCP 提供

---

## 改进方案

### 方案 A：最小化方案（推荐）

**只添加最关键的工具**：
1. ✅ `http_tool.py` - HTTP 请求（解决 MCP 依赖问题）
2. ✅ `search_tool.py` - Web 搜索（增强信息获取）
3. ✅ `session_tool.py` - 会话管理（多会话支持）

**工作量**：1-2 周
**优点**：
- ✅ 快速实现
- ✅ 解决最紧迫的问题
- ✅ 不增加太多维护负担

---

### 方案 B：中等方案

**添加常用工具**：
1. ✅ 方案 A 的 3 个工具
2. ✅ `schedule_tool.py` - 定时任务
3. ✅ `memory_tool.py` - 内存搜索
4. ✅ `image_tool.py` - 图像处理

**工作量**：3-4 周
**优点**：
- ✅ 功能更全面
- ✅ 覆盖更多场景
- ✅ 仍然可控

---

### 方案 C：完整方案

**参考 OpenClaw 的完整工具集**：
1. ✅ 方案 B 的 6 个工具
2. ✅ `database_tool.py` - SQLite 操作
3. ✅ `filesystem_tool.py` - 高级文件操作
4. ✅ `git_tool.py` - Git 操作封装
5. ✅ `browser_mcp.py` - 浏览器 MCP 服务器（不内建）

**工作量**：6-8 周
**优点**：
- ✅ 功能最全面
- ✅ 对标 OpenClaw
**缺点**：
- ❌ 工作量大
- ❌ 维护成本高

---

## 工具设计原则

### 1. **核心工具 vs MCP 工具**

**应该内建的工具**：
- ✅ 基础且常用（HTTP、搜索、会话）
- ✅ 无需复杂依赖
- ✅ 性能敏感
- ✅ 稳定性要求高

**应该通过 MCP 提供的工具**：
- ✅ 需要复杂依赖（浏览器、SSH）
- ✅ 语言相关（TypeScript/Go 工具）
- ✅ 可选功能
- ✅ 第三方集成

---

### 2. **工具 vs Skill**

**使用工具**：
- ✅ 通用功能（HTTP、搜索、文件操作）
- ✅ 需要高性能
- ✅ 需要类型安全

**使用 Skill**：
- ✅ 领域特定（新闻聚合、代码审查）
- ✅ 复杂的工作流
- ✅ 需要多步推理

---

## 实现优先级

### Phase 1：立即实现（1-2 周）

**目标**：解决 MCP 依赖问题

1. **http_tool.py** - HTTP 请求
   - GET/POST/PUT/DELETE
   - 支持 headers、timeout
   - 使用 httpx 库

2. **search_tool.py** - Web 搜索
   - DuckDuckGo（免费）
   - 或 Brave Search API
   - 返回结构化结果

3. **session_tool.py** - 会话管理
   - list - 列出会话
   - history - 获取历史
   - delete - 删除会话

---

### Phase 2：短期实现（3-4 周）

**目标**：增强功能

4. **schedule_tool.py** - 定时任务
   - add/remove/list
   - 使用 Python schedule 库
   - 后台线程执行

5. **memory_tool.py** - 内存搜索
   - search - 搜索历史
   - get - 获取记忆
   - 基于 memory.json

6. **image_tool.py** - 图像处理
   - resize/convert/info
   - 使用 Pillow 库
   - 基础功能

---

### Phase 3：长期考虑（按需）

**目标**：完善生态

7. **database_tool.py** - SQLite
8. **filesystem_tool.py** - 高级文件操作
9. **git_tool.py** - Git 操作

---

## 与 OpenClaw 的对比

### OpenClaw 的策略

**分层扩展**：
1. **Skills**（零代码）- CLI 工具集成
2. **Tools**（TypeScript）- 核心功能
3. **Plugins**（TypeScript）- 复杂扩展

**关键优势**：
- ✅ Skills 可以快速扩展（无需编译）
- ✅ Tools 提供核心功能（高性能）
- ✅ Plugins 支持复杂场景

---

### FastReAct 应该学习的

**1. 简化扩展机制**

参考 OpenClaw 的 Skills，创建类似的机制：

```yaml
# skills/http-fetch/SKILL.md
---
name: http_fetch
description: Fetch HTTP content using httpx
requirements:
  python_packages: ["httpx"]
---
```

**2. 分层工具体系**

- **Core Tools**（内建）- 4 个基础 + HTTP/搜索/会话
- **Extended Tools**（MCP）- 浏览器、SSH 等
- **Skills**（工作流）- 新闻聚合、代码审查等

**3. 工具分组**

参考 OpenClaw 的 tool groups：
- `group:runtime` - exec
- `group:fs` - read/write/edit
- `group:web` - http/search
- `group:sessions` - session_manage
- `group:automation` - schedule

---

## 建议的工具结构

```
src/fastreact/tools/
├── core/                      # 核心工具（内建）
│   ├── __init__.py
│   ├── exec_tool.py           # Shell 命令
│   ├── read_file.py           # 读取文件
│   ├── write_file.py          # 写入文件
│   └── edit_file.py           # 编辑文件
│
├── web/                       # Web 工具（新增）
│   ├── __init__.py
│   ├── http_tool.py           # HTTP 请求
│   └── search_tool.py         # Web 搜索
│
├── session/                   # 会话工具（新增）
│   ├── __init__.py
│   └── session_tool.py       # 会话管理
│
├── automation/                # 自动化工具（新增）
│   ├── __init__.py
│   └── schedule_tool.py      # 定时任务
│
├── memory/                    # 记忆工具（新增）
│   ├── __init__.py
│   └── memory_tool.py        # 内存搜索
│
└── media/                     # 媒体工具（新增）
    ├── __init__.py
    └── image_tool.py         # 图像处理
```

---

## 总结

### 当前问题

1. ❌ **工具太少** - 只有 4 个基础工具
2. ❌ **过度依赖 MCP** - HTTP/搜索都通过 MCP
3. ❌ **扩展不便** - 添加新工具需要写代码

### 改进建议

1. ✅ **短期**：添加 3 个核心工具（HTTP、搜索、会话）
2. ✅ **中期**：添加 3 个增强工具（定时、记忆、图像）
3. ✅ **长期**：考虑 Skills 机制（零代码扩展）

### 优先级

**🔴 立即实现**：
- `http_tool.py` - 解决 MCP 依赖
- `search_tool.py` - 增强信息获取
- `session_tool.py` - 多会话支持

**🟡 短期实现**：
- `schedule_tool.py`
- `memory_tool.py`
- `image_tool.py`

**🟢 长期考虑**：
- Skills 机制
- 更复杂的工具

---

**作者**: FastReAct Team
**状态**: 建议阶段
**下一步**: 实现方案 A（最小化方案）
