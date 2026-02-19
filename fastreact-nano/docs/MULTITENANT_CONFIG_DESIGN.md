# 多租户配置管理方案

**版本**: 2.4.2
**日期**: 2025-02-19
**状态**: 设计阶段

---

## 🎯 问题定义

### 单租户 vs 多租户配置需求

| 层面 | 单租户 | 多租户 |
|------|--------|--------|
| **配置位置** | `~/.fastreact/config.json` | `~/.fastreact/config.json` + `{user_workspace}/config.json` |
| **MCP 服务器** | 全局统一 | 全局共享 + 用户特定 |
| **SKILL** | 全局统一 | 全局 + 用户自定义 |
| **用户数** | 1 个（所有用户共享） | N 个（每用户独立） |
| **配置冲突** | ❌ 无冲突 | ✅ 需要优先级机制 |

### 用户场景示例

**用户 A** (GitHub 开发者):
- 需要：GitHub MCP server
- 不需要：数据库 MCP server
- 自定义 SKILL：github_workflow

**用户 B** (数据分析师):
- 不需要：GitHub MCP server
- 需要：PostgreSQL MCP server
- 自定义 SKILL：data_analysis

---

## 🏗️ 配置架构设计

### 双层配置系统

```
┌─────────────────────────────────────────────────────────────┐
│                    配置层级                                     │
└─────────────────────────────────────────────────────────────┘

【全局配置层】(Global)
位置: ~/.fastreact/config.json
适用: 所有用户
内容:
  - LLM 配置（可被用户配置覆盖）
  - 全局 MCP 服务器（shared 模式）
  - 系统级设置

【用户配置层】(User-Specific)
位置: {user_workspace}/config.json
适用: 单个用户
内容:
  - 用户特定 LLM 配置（覆盖全局）
  - 用户 MCP 服务器（per_user 模式）
  - 用户偏好设置
```

### MCP 服务器优先级

```
1. 用户特定 MCP 服务器 (per_user)
   ↓
2. 全局共享 MCP 服务器 (shared)
   ↓
3. 内置工具 (read_file, write_file, exec)
```

**示例**:

**全局配置** (`~/.fastreact/config.json`):
```json
{
  "mcp": {
    "servers": [
      {
        "name": "timeserver",
        "command": "uvx",
        "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
        "isolation": "shared",
        "description": "Time server for everyone"
      }
    ]
  }
}
```

**用户 A 配置** (`/var/fastreact/tenants/feishu/feishu_ou_user_a/config.json`):
```json
{
  "mcp": {
    "servers": [
      {
        "name": "github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_user_a_token"
        },
        "isolation": "per_user",
        "description": "GitHub for user A only"
      }
    ]
  }
}
```

**用户 A 的实际可用 MCP**:
1. `github` (用户特定)
2. `timeserver` (全局共享)

**用户 B 配置** (`/var/fastreact/tenants/feishu/feishu_ou_user_b/config.json`):
```json
{
  "mcp": {
    "servers": [
      {
        "name": "postgres",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"],
        "isolation": "per_user",
        "description": "PostgreSQL for user B only"
      }
    ]
  }
}
```

**用户 B 的实际可用 MCP**:
1. `postgres` (用户特定)
2. `timeserver` (全局共享)

---

## 🔧 实现方案

### 方案 A: 配置合并（推荐）

**设计思想**: Agent 在运行时合并全局和用户配置

**实现**: `src/fastreact/agent.py`

```python
class Agent:
    def __init__(self, ...):
        # 加载全局配置
        self._config = Config.load()  # ~/.fastreact/config.json

    async def _load_mcp_servers(self, user_context: UserContext = None):
        """加载 MCP 服务器（支持多租户）"""
        servers = []

        # 1. 加载全局配置
        servers.extend(self._config.mcp.servers)

        # 2. 加载用户特定配置（多租户）
        if user_context:
            user_config_path = user_context.workspace / "config.json"
            if user_config_path.exists():
                user_config = Config.load(user_config_path)
                servers.extend(user_config.mcp.servers)

        # 3. 去重（按服务器名称）
        unique_servers = {}
        for server in servers:
            if server.name not in unique_servers:
                unique_servers[server.name] = server

        # 4. 加载 MCP 服务器
        for server in unique_servers.values():
            await self._mcp_manager.add_server(server)
```

**优先级处理**:
- 如果全局和用户都有同名服务器 → 使用用户配置（用户优先）
- 如果服务器名称不同 → 同时加载

---

### 方案 B: 配置覆盖（备选）

**设计思想**: 用户配置完全覆盖全局配置

**实现**:

```python
# 用户配置文件
{
  "mcp": {
    "override_global": true,  # 完全覆盖全局
    "servers": [...]
  }
}
```

**优点**:
- ✅ 用户完全控制
- ✅ 逻辑简单

**缺点**:
- ❌ 用户必须手动配置所有内容
- ❌ 无法继承全局配置

---

## 🎯 Gateway (单租户) 暂时方案

### 当前状态

**配置**: `~/.fastreact/config.json`
- ✅ 所有用户共享
- ✅ 统一管理
- ✅ 简单直接

**用户 A** 通过前端问 "有哪些工具？"
→ Agent 回答基于全局配置

**用户 B** 通过前端问 "有哪些工具？"
→ Agent 回答基于同一个全局配置

**一致性**: ✅ 所有用户看到相同的工具

---

## 🚀 Feishu (多租户) 实现计划

### Phase 1: 基础架构（当前）

**现状**:
- ✅ MultiTenantManager 已实现
- ✅ 用户工作区隔离
- ⏸️ 用户特定 MCP 配置 **待实现**

**配置结构**:
```
/var/fastreact/tenants/feishu/
├── feishu_ou_user_a/
│   ├── config.json          ← 用户 A 的配置
│   ├── memory.json
│   ├── skills/
│   └── mcp_config.json      ← 用户 A 的 MCP 配置（待实现）
├── feishu_ou_user_b/
│   ├── config.json
│   ├── memory.json
│   ├── skills/
│   └── mcp_config.json      ← 用户 B 的 MCP 配置（待实现）
```

### Phase 2: 配置加载（待实现）

**修改文件**: `src/fastreact/agent.py`

**方法**: 扩展 `_load_mcp_servers()` 支持用户配置

```python
async def _load_mcp_servers(self, user_context: UserContext = None):
    """加载 MCP 服务器（支持多租户）"""
    servers = []

    # 1. 全局配置
    servers.extend(self._config.mcp.servers)

    # 2. 用户特定配置（多租户）
    if user_context:
        # 检查用户配置文件
        user_config_path = user_context.workspace / "mcp_config.json"
        if user_config_path.exists():
            try:
                import json
                with open(user_config_path, "r") as f:
                    user_config = json.load(f)

                # 解析 MCP 服务器配置
                if "mcp" in user_config and "servers" in user_config["mcp"]:
                    for server_data in user_config["mcp"]["servers"]:
                        server = MCPServerConfig.from_dict(server_data)
                        servers.append(server)
            except Exception as e:
                print(f"[WARNING] Failed to load user MCP config: {e}")

    # 3. 去重和加载
    # ... (同方案 A)
```

### Phase 3: 配置 UI（前端）

**前端页面**: `/admin` → "MCP 配置"

**功能**:
- 查看当前用户的 MCP 配置
- 添加/删除 MCP 服务器
- 测试 MCP 服务器连接
- 查看服务器状态

---

## 📋 配置文件格式规范

### 全局配置 (`~/.fastreact/config.json`)

```json
{
  "llm": { ... },
  "mcp": {
    "servers": [
      {
        "name": "timeserver",
        "command": "uvx",
        "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
        "isolation": "shared",
        "description": "Time server (all users)"
      }
    ]
  }
}
```

### 用户配置 (`{user_workspace}/mcp_config.json`)

```json
{
  "mcp": {
    "servers": [
      {
        "name": "github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
        },
        "isolation": "per_user",
        "description": "GitHub (user-specific)"
      }
    ]
  }
}
```

---

## 🧪 测试场景

### 场景 1: 用户 A 和用户 B 有不同 MCP 服务器

**设置**:
- 全局: timeserver
- 用户 A: github
- 用户 B: postgres

**验证**:
```
用户 A: "有哪些工具？"
→ 回答: github, timeserver

用户 B: "有哪些工具？"
→ 回答: postgres, timeserver
```

### 场景 2: 用户 A 添加新 MCP 服务器

**操作**: 用户 A 在前端添加 `filesystem` MCP

**验证**:
```
用户 A: "有哪些工具？"
→ 回答: github, filesystem, timeserver
```

### 场景 3: 全局添加新 MCP 服务器

**操作**: 管理员在 `~/.fastreact/config.json` 添加 `slack` MCP

**验证**:
```
用户 A: "有哪些工具？"
→ 回答: github, slack, timeserver

用户 B: "有哪些工具？"
→ 回答: postgres, slack, timeserver
```

---

## 🚧 实现检查清单

### 当前状态 (Gateway 单租户)
- [x] 全局配置统一 (`~/.fastreact/config.json`)
- [x] 示例配置隔离 (`.example` 后缀)
- [ ] Agent 通过 API 获取状态（而非读取文件）
- [ ] 配置优先级文档

### 待实现 (Feishu 多租户)
- [ ] 用户工作区创建 `mcp_config.json`
- [ ] Agent 加载用户 MCP 配置
- [ ] 配置去重和优先级处理
- [ ] 前端 MCP 配置 UI
- [ ] 配置验证和测试

---

## 💡 设计原则

### 1. 单一数据源（重要！）

**原则**: Agent 应该通过内部 API 获取状态，而不是读取配置文件

**当前问题**:
```python
# ❌ 错误：Agent 读取配置文件
read_file("mcp_servers/config/per_user.json")
→ 产生"能力幻觉"
```

**正确实现**:
```python
# ✅ 正确：Agent 通过内部 API 获取状态
mcp_servers = self._mcp_manager.list_servers()
available_tools = self._tools.list_all()
→ 无幻觉
```

### 2. 配置继承和覆盖

**全局配置**: 基础配置，所有用户共享
**用户配置**: 覆盖全局，满足个性化需求

**优先级**: 用户 > 全局

### 3. 配置隔离

**用户配置位置**: `{user_workspace}/mcp_config.json`
**隔离级别**: 每用户独立配置
**安全**: 用户 A 无法访问用户 B 的配置

---

## 📚 相关文档

- **`docs/CONFIG_FILE_LOCATIONS.md`** - 配置文件位置
- **`docs/MULTITENANT_GUIDE.md`** - 多租户指南
- **`docs/CAPABILITY_HALLUCINATION_FIX.md`** - AI 幻觉修复
- **`docs/SKILLS_AND_MCP.md`** - SKILL 和 MCP 架构

---

## 🎯 总结

### 单租户（Gateway）- 当前方案
- ✅ 配置位置: `~/.fastreact/config.json`
- ✅ 所有用户共享
- ✅ 简单直接

### 多租户（Feishu）- 待实现
- ⏸️ 全局配置: `~/.fastreact/config.json`
- ⏸️ 用户配置: `{user_workspace}/mcp_config.json`
- ⏸️ 优先级: 用户 > 全局
- ⏸️ 隔离: 每用户独立

### 关键问题
- ❌ **Gateway 单租户**: 无需特殊处理（已解决）
- ⚠️ **Feishu 多租户**: 需要实现用户特定 MCP 配置（待 Phase 2）

---

**维护者**: Claude Code + User
**设计日期**: 2025-02-19
**版本**: 2.4.2
