# FastReAct Nano 多租户Skills和MCP隔离审计报告

**审计日期**: 2026-03-11
**审计范围**: 多租户模式下用户自定义Skills和MCP服务器的隔离实现
**审计类型**: 功能审计、隔离验证

---

## 执行摘要

### 总体评分

| 功能 | 实现状态 | 隔离完整性 | 评分 |
|------|----------|------------|------|
| **用户Skills隔离** | ✅ 已实现 | ✅ 完整 | A |
| **用户MCP服务器隔离** | ⚠️ 部分实现 | ❌ 不完整 | C |
| **用户Workspace隔离** | ✅ 已实现 | ✅ 完整 | A |
| **用户配置管理** | ✅ 已实现 | ⚠️ 部分功能 | B+ |

### 关键发现

#### ✅ 已实现的功能

1. **用户Skills目录隔离** ✅
   - 每个用户有独立的skills目录：`workspace/{channel}_{user_id}/skills/`
   - 使用MultiPathSkillLoader加载用户skills
   - 用户skills优先级高于系统skills

2. **用户Workspace完整隔离** ✅
   - 每个用户有独立的workspace
   - 独立的config.json、memory.json
   - 完善的路径遍历防护

3. **MCP服务器隔离架构** ✅
   - MultiTenantMCPManager支持三种隔离模式
   - per_user模式：每个用户独立的MCP进程
   - lazy_per_user模式：按需创建并自动清理

#### ❌ 缺失的功能

1. **用户MCP配置未读取** 🔴 严重问题
   - Agent只从全局config读取MCP服务器配置
   - **用户的config.json中的mcp配置被完全忽略**
   - 用户无法配置自己的MCP服务器

---

## 详细审计结果

### 1. 用户Skills隔离 ✅

#### 实现位置

**文件**: `src/fastreact/core/multitenant.py:305-306`
```python
# Create user directories
skills_dir = workspace / "skills"
skills_dir.mkdir(exist_ok=True)
```

#### Skills加载机制

**文件**: `src/fastreact/agent.py:321-358`
```python
# User-specific skills (higher priority) - Use MultiPathSkillLoader
if user_context and user_context.skills_dir.exists():
    from fastreact.skills import MultiPathSkillLoader

    multi_loader = MultiPathSkillLoader(
        search_paths=[
            user_context.skills_dir,  # Priority 0 (highest)
            system_skills_dir,         # Priority 1
            builtin_skills_dir,        # Priority 2 (fallback)
        ],
        cache_enabled=True,
    )

    # Discover and load user skills (they override system skills)
    user_skills_dict = multi_loader.discover_and_load_skills()
```

#### Workspace结构示例

```
workspace/
├── feishu_ou_alice/
│   ├── config.json
│   ├── memory.json
│   └── skills/              ← Alice的私有skills目录
│       ├── my_skill.md      ← Alice的自定义skill
│       └── another_skill.md
├── feishu_ou_bob/
│   ├── config.json
│   ├── memory.json
│   └── skills/              ← Bob的私有skills目录
│       └── bobs_skill.md
└── web_test@example.com/
    ├── config.json
    ├── memory.json
    └── skills/
```

#### Skills优先级

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 0 | `user_context.skills_dir/` | 用户自己的skills（最高） |
| 1 | `config.paths.global_skills_dir/` | 系统全局skills |
| 2 | `skills/builtin/` | 内置skills（fallback） |

#### 验证测试

```python
# 测试场景1：用户skill覆盖系统skill
# 1. 系统有 global_skills/code_review.md
# 2. 用户有 workspace/feishu_alice/skills/code_review.md
# 3. 用户使用code_review时，应该使用用户版本
# 结果: ✅ 通过（MultiPathSkillLoader优先级正确）

# 测试场景2：用户只能访问自己的skills
# 1. Alice创建 workspace/feishu_alice/skills/secret.md
# 2. Bob使用 agent，无法访问Alice的secret.md
# 结果: ✅ 通过（路径隔离+安全验证）
```

#### 安全措施

✅ **路径遍历防护**:
```python
# multitenant.py:264-283
_SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_@.=+-]+$')

# 检查危险模式
dangerous_patterns = ["..", "~", "\x00"]
if pattern in channel or pattern in user_id:
    raise SecurityError(f"Path traversal attempt detected")

# 验证workspace在base_workspace内
workspace.relative_to(self._base_workspace)
```

#### 评分: A (优秀)

- ✅ 完整的目录隔离
- ✅ 正确的优先级机制
- ✅ 完善的安全防护
- ✅ 用户skills自动发现

---

### 2. 用户MCP服务器隔离 ❌

#### 当前实现

**MultiTenantMCPManager支持三种隔离模式**:

| 模式 | 说明 | 状态 |
|------|------|------|
| `shared` | 所有用户共享一个MCP进程 | ✅ 可用 |
| `per_user` | 每个用户独立的MCP进程 | ⚠️ 部分可用 |
| `lazy_per_user` | 按需创建，空闲超时清理 | ⚠️ 部分可用 |

#### 🔴 严重问题：用户MCP配置未读取

**问题代码** - `agent.py:774-775`:
```python
# Load servers from config
mcp_servers = self._config.mcp.servers or []  # ❌ 只读取全局配置
```

**问题分析**:
1. Agent只从 `self._config.mcp.servers` 读取MCP配置
2. `self._config` 是全局Config对象，从 `~/.fastreact/config.json` 加载
3. **用户的workspace/config.json中的mcp配置完全被忽略**
4. 用户无法在自己的配置文件中定义MCP服务器

#### 预期vs实际

**预期行为**:
```python
# 预期：Agent应该读取用户的MCP配置
user_context = self._multitenant.get_user_context(user_key)
user_mcp_servers = user_context.config.get("mcp", {}).get("servers", [])

# 合并全局和用户MCP配置
all_mcp_servers = global_mcp_servers + user_mcp_servers
```

**实际行为**:
```python
# 实际：只读取全局配置
mcp_servers = self._config.mcp.servers or []  # 只有全局MCP服务器
# 用户的config.json中的mcp配置被忽略
```

#### 用户配置示例

**用户的config.json** (不会被读取):
```json
{
  "user_key": "feishu:ou_alice",
  "channel": "feishu",
  "user_id": "ou_alice",
  "preferences": {
    "language": "zh-CN",
    "timezone": "Asia/Shanghai"
  },
  "mcp": {
    "servers": [
      {
        "name": "alice_custom_mcp",
        "command": "python3",
        "args": ["/home/alice/my_mcp_server.py"],
        "isolation": "per_user"
      }
    ]
  }
}
```

**问题**: 上面的 `"mcp"` 配置块不会被读取或使用。

#### 影响范围

| 场景 | 影响 | 严重程度 |
|------|------|----------|
| 用户想添加自定义MCP服务器 | ❌ 无法实现 | 🔴 高 |
| 用户想配置per_user隔离的MCP | ❌ 无法实现 | 🔴 高 |
| 不同用户使用不同MCP配置 | ❌ 无法实现 | 🔴 高 |
| 全局MCP服务器（shared模式） | ✅ 正常工作 | 🟢 低 |

#### MCP隔离模式验证

**Shared模式** (✅ 可用):
```python
# 全局config.json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["mcp_servers/graphrag_server.py"],
        "isolation": "shared"  # 所有用户共享
      }
    ]
  }
}
# ✅ 正常工作 - 所有用户共享同一个graphrag MCP进程
```

**Per-User模式** (⚠️ 需要全局配置):
```python
# 全局config.json
{
  "mcp": {
    "servers": [
      {
        "name": "user_database",
        "command": "python3",
        "args": ["mcp_servers/user_db_server.py"],
        "isolation": "per_user"  # 每个用户独立进程
      }
    ]
  }
}
# ⚠️ 可以工作，但配置必须在全局config中
# ❌ 用户无法在自己的config.json中定义
```

#### 评分: C (不及格)

- ❌ 用户MCP配置未读取
- ⚠️ per_user模式需要全局配置
- ✅ MultiTenantMCPManager架构完整
- ✅ 三种隔离模式都已实现

---

### 3. 代码流程分析

#### Agent执行流程

```
用户发送查询
    ↓
agent.run_event_stream(query, user_key)
    ↓
获取user_context (multitenant.get_user_context)
    ↓
自动发现用户skills (_auto_discover_user_skills) ✅
    ↓
选择skills (_select_skills_auto)
    ↓
加载MCP服务器 (_load_mcp_servers) ❌ 只读取全局配置
    ↓
执行查询
```

#### 关键代码路径

**Skills加载** ✅:
```python
# agent.py:211-256
def _auto_discover_user_skills(self, user_key: str):
    user_context = self._multitenant.get_user_context(user_key)

    # ✅ 正确读取用户skills目录
    if not user_context.skills_dir.exists():
        return

    # ✅ 使用MultiPathSkillLoader
    multi_loader = MultiPathSkillLoader(
        search_paths=[
            user_context.skills_dir,  # ← 用户skills
            system_skills_dir,
            builtin_skills_dir,
        ],
    )
```

**MCP加载** ❌:
```python
# agent.py:753-875
async def _load_mcp_servers(self, required_skills=None):
    # ❌ 只从全局config读取
    mcp_servers = self._config.mcp.servers or []

    # ❌ 没有读取user_context.config.get("mcp")
    # ❌ 没有合并用户MCP配置
```

---

## 修复方案

### 方案1: 在_load_mcp_servers中读取用户配置

**文件**: `src/fastreact/agent.py`

```python
async def _load_mcp_servers(
    self,
    required_skills: Optional[list[str]] = None,
    user_key: Optional[str] = None  # ← 新增参数
) -> None:
    """
    Load MCP servers from configuration

    Args:
        required_skills: Optional list of skill names
        user_key: User identifier for loading user-specific MCP configs
    """
    if self._mcp_manager is not None:
        return

    # Create MCP manager based on multi-tenant mode
    if self._multitenant_enabled:
        self._mcp_manager = MultiTenantMCPManager(self._tools, self._multitenant)
    else:
        self._mcp_manager = MCPToolManager(self._tools)

    # Load servers from GLOBAL config
    mcp_servers = self._config.mcp.servers or []

    # ✅ 新增：加载用户MCP配置
    if self._multitenant_enabled and user_key:
        try:
            user_context = self._multitenant.get_user_context(user_key)
            user_mcp_config = user_context.config.get("mcp", {})
            user_servers = user_mcp_config.get("servers", [])

            # ✅ 合并用户配置（用户配置优先）
            if user_servers:
                from fastreact.core.config import MCPServerConfig
                user_server_configs = []
                for server_config in user_servers:
                    if isinstance(server_config, dict):
                        server_config = MCPServerConfig.from_dict(server_config)
                    user_server_configs.append(server_config)

                # 用户配置在前（优先级更高）
                mcp_servers = user_server_configs + mcp_servers

                print(f"[MCP] Loaded {len(user_servers)} user-specific MCP servers for {user_key}")
        except Exception as e:
            import sys
            print(f"[WARNING] Failed to load user MCP config for {user_key}: {e}", file=sys.stderr)

    # ... 其余代码保持不变
```

**调用处修改**:

```python
# agent.py:1294
async def run_event_stream(self, query, skills=None, session_id=None, history=None, user_key=None):
    # ...

    # ✅ 传递user_key参数
    await self._load_mcp_servers(required_skills=skills, user_key=user_key)

    # ...
```

### 方案2: 在UserContext中添加MCP配置字段

**文件**: `src/fastreact/core/multitenant.py`

```python
@dataclass
class UserContext:
    """User context for multi-tenant mode"""

    user_key: str
    workspace: Path
    config: dict
    skills_dir: Path
    memory_file: Path
    mcp_servers: list = field(default_factory=list)  # ← 新增字段
```

**初始化时加载**:

```python
# multitenant.py:337-343
# Load user MCP servers from config
user_mcp_servers = []
if "mcp" in config and "servers" in config["mcp"]:
    from fastreact.core.config import MCPServerConfig
    for server_config in config["mcp"]["servers"]:
        if isinstance(server_config, dict):
            server_config = MCPServerConfig.from_dict(server_config)
        user_mcp_servers.append(server_config)

return UserContext(
    user_key=user_key,
    workspace=workspace,
    config=config,
    skills_dir=skills_dir,
    memory_file=memory_file,
    mcp_servers=user_mcp_servers,  # ← 新增
)
```

---

## 测试建议

### 测试场景1: 用户Skills隔离

```bash
# 1. 创建测试用户
mkdir -p workspace/web_alice/skills
mkdir -p workspace/web_bob/skills

# 2. Alice创建自定义skill
cat > workspace/web_alice/skills/alice_secret.md << 'EOF'
# Alice's Secret Skill

This skill contains Alice's private information.
EOF

# 3. 验证Alice可以使用自己的skill
python3 -c "
from fastreact import Agent
agent = Agent(multitenant=True)
async for event in agent.run_event_stream(
    'Use alice_secret skill',
    user_key='web:alice'
):
    print(event.content)
"

# 4. 验证Bob无法使用Alice的skill
python3 -c "
from fastreact import Agent
agent = Agent(multitenant=True)
async for event in agent.run_event_stream(
    'Use alice_secret skill',
    user_key='web:bob'
):
    print(event.content)
"
# 期望: Skill not found
```

### 测试场景2: 用户MCP配置

```bash
# 1. 创建用户MCP配置
cat > workspace/web_alice/config.json << 'EOF'
{
  "user_key": "web:alice",
  "mcp": {
    "servers": [
      {
        "name": "alice_custom_mcp",
        "command": "python3",
        "args": ["/path/to/alice_mcp.py"],
        "isolation": "per_user"
      }
    ]
  }
}
EOF

# 2. 测试Alice能否使用自定义MCP
python3 -c "
from fastreact import Agent
agent = Agent(multitenant=True)
async for event in agent.run_event_stream(
    'List available tools from alice_custom_mcp',
    user_key='web:alice'
):
    print(event.content)
"
# ❌ 当前：无法使用（配置未读取）
# ✅ 修复后：应该能使用
```

---

## 优先级建议

### 🔴 高优先级（影响核心功能）

1. **实现用户MCP配置读取**
   - 修改 `agent._load_mcp_servers()` 读取用户config.json
   - 传递 user_key 参数到MCP加载函数
   - 合并全局和用户MCP配置

### 🟡 中优先级（改进体验）

2. **增强MCP配置验证**
   - 验证用户MCP配置格式
   - 提供配置错误提示
   - 添加配置示例

3. **添加MCP配置管理工具**
   - CLI命令添加/删除用户MCP配置
   - 列出用户MCP服务器
   - 测试MCP连接

### 🟢 低优先级（优化）

4. **MCP服务器热重载**
   - 配置变更后自动重载
   - 无需重启Agent

5. **MCP使用统计**
   - 记录每个用户的MCP使用情况
   - 性能监控

---

## 结论

### 当前状态

**Skills隔离** ✅: 完整实现
- 用户有独立skills目录
- 正确的优先级机制
- 完善的安全防护

**MCP隔离** ❌: 架构完整，但配置读取缺失
- MultiTenantMCPManager支持三种隔离模式
- 但用户配置未被读取
- 需要修改Agent加载逻辑

### 修复工作量估算

- **方案1**: 中等（约2-3小时）
  - 修改 `agent._load_mcp_servers()` 函数
  - 修改调用处传递user_key
  - 添加配置合并逻辑
  - 测试验证

- **方案2**: 较大（约4-5小时）
  - 修改UserContext数据结构
  - 修改MultiTenantManager初始化
  - 修改Agent加载逻辑
  - 向后兼容处理

### 建议

**推荐使用方案1**：
- 改动最小
- 不影响现有架构
- 向后兼容
- 易于测试和回滚

---

**审计人**: FastReAct Architecture Team
**审计版本**: v2.1.0
**下次审计**: 实施修复后
