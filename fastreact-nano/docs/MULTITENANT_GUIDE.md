# FastReAct Nano 多租户与单租户完全指南

> Reference guide: this page contains historical gateway/Feishu framing. For the
> current headless service API, auth, policy, and MCP behavior, use
> [HEADLESS_SERVICE.md](HEADLESS_SERVICE.md), [security.md](security.md), and
> [MCP_CALLING_MECHANISM.md](MCP_CALLING_MECHANISM.md).
> `fastreact.adapters.gateway` is deprecated; use the HTTP/SSE service adapter.

**版本**: 2.4.2
**更新日期**: 2025-02-19

---

## 一、核心概念

### 1.1 什么是租户（Tenant）？

**租户** = 一个独立的用户或用户组，拥有：
- 独立的**工作区**（Workspace）
- 独立的**配置**（Config）
- 独立的**对话记忆**（Memory）
- 独立的**技能集**（Skills）
- 独立的**MCP 服务器**（可选）

### 1.2 单租户 vs 多租户

| 特性 | 单租户（Single-Tenant） | 多租户（Multi-Tenant） |
|------|----------------------|---------------------|
| **部署方式** | Gateway | Feishu Bot |
| **用户数量** | 1 个（所有用户共享） | N 个（每个用户独立） |
| **工作区位置** | `./workspaces/default/` | `/var/fastreact/tenants/feishu/{user_key}/` |
| **隔离性** | ❌ 无隔离（所有用户共享数据） | ✅ 完全隔离（每个用户独立数据） |
| **适用场景** | 个人开发、测试 | 企业部署、多用户 SaaS |
| **用户识别** | 无需识别 | 需要 user_key（如 "feishu:ou_xxx"） |
| **配置复杂度** | 简单 | 中等 |

---

## 二、架构对比

### 2.1 单租户架构（Gateway）

```
┌─────────────────────────────────────────────────────────────┐
│                    FastReAct Gateway                        │
│                  (FastAPI WebSocket Server)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Agent (multitenant=False)                     │
│  - 所有用户共享同一个 Agent 实例                             │
│  - 所有用户共享同一个工作区                                 │
│  - 所有用户共享同一个对话记忆                               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           共享工作区 (./workspaces/default/)                │
│  ├── config.json      (全局配置)                            │
│  ├── memory.json      (全局对话记忆)                        │
│  ├── skills/          (全局技能，无用户特定技能)            │
│  └── mcp_config.json  (全局 MCP 服务器)                     │
└─────────────────────────────────────────────────────────────┘
```

**特点**：
- ✅ 简单：无需用户识别
- ✅ 快速：共享资源，性能最优
- ❌ 无隔离：所有用户数据混在一起
- ❌ 无个性化：无法为不同用户配置不同技能

**典型使用场景**：
```python
# 启动 Gateway（单租户）
python3 -m fastreact.adapters.gateway

# 前端连接（所有用户共享同一个 Agent）
ws://localhost:9000/ws
```

### 2.2 多租户架构（Feishu）

```
┌─────────────────────────────────────────────────────────────┐
│                    Feishu Bot SDK                           │
│              (WebSocket Long Connection)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Agent (multitenant=True)                      │
│  - 动态识别用户（从消息中提取 user_key）                    │
│  - 为每个用户创建独立的 UserContext                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           MultiTenantManager                               │
│  - 管理 N 个用户的工作区                                     │
│  - 确保用户之间的隔离性                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ↓                       ↓
┌───────────────────────┐   ┌───────────────────────┐
│  User A Workspace     │   │  User B Workspace     │
│  feishu:ou_user_a/    │   │  feishu:ou_user_b/    │
│  ├── config.json      │   │  ├── config.json      │
│  ├── memory.json      │   │  ├── memory.json      │
│  ├── skills/          │   │  ├── skills/          │
│  │   └── custom_skill │   │  │   └── custom_skill │
│  └── mcp_config.json  │   │  └── mcp_config.json  │
└───────────────────────┘   └───────────────────────┘
```

**特点**：
- ✅ 隔离：每个用户有独立的工作区
- ✅ 个性化：每个用户可以有不同的技能和配置
- ✅ 安全：用户 A 无法访问用户 B 的数据
- ❌ 复杂：需要用户识别机制
- ❌ 资源：每个用户独立资源（内存、磁盘）

**典型使用场景**：
```python
# 启动 Feishu Bot（多租户）
python3 examples/feishu_sdk_bot.py

# 用户 A 发消息
用户 A: "帮我创建文件 test.txt"
→ user_key = "feishu:ou_user_a"
→ 工作区 = /var/fastreact/tenants/feishu/feishu_ou_user_a/
→ 文件创建在用户 A 的工作区

# 用户 B 发消息
用户 B: "帮我创建文件 test.txt"
→ user_key = "feishu:ou_user_b"
→ 工作区 = /var/fastreact/tenants/feishu/feishu_ou_user_b/
→ 文件创建在用户 B 的工作区（与用户 A 隔离）
```

---

## 三、User Key 机制

### 3.1 User Key 格式

**格式**：`{channel}:{user_id}`

**示例**：
```
feishu:ou_1234567890abcdef    # Feishu 用户
web:user@example.com          # Web 用户
cli:local                     # CLI 用户
```

**Channel**：来源渠道
- `feishu` - 飞书
- `web` - Web 应用
- `cli` - 命令行
- `slack` - Slack（未来支持）

**User ID**：用户唯一标识
- Feishu：`ou_xxx`（飞书用户 ID）
- Web：邮箱或用户名
- CLI：固定字符串 `local`

### 3.2 安全验证

**FastReAct 对 user_key 进行严格的安全验证**：

```python
# 1. 格式验证
if ":" not in user_key:
    raise ValueError("Invalid user_key format")

# 2. 字符白名单（防止路径遍历攻击）
SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_@.=+-]+$')
if not SAFE_PATTERN.match(channel):
    raise SecurityError("Unsafe characters in channel")

# 3. 路径遍历检测
if ".." in channel or ".." in user_id:
    raise SecurityError("Path traversal attempt detected")

# 4. 工作区边界检查
workspace = base_workspace / f"{channel}_{user_id}"
workspace = workspace.resolve()
if not workspace.relative_to(base_workspace):
    raise SecurityError("Workspace escape detected")
```

**保护措施**：
- ✅ 防止路径遍历攻击（`..`）
- ✅ 防止特殊字符注入（`\x00`, `~`）
- ✅ 确保工作区在 base_workspace 内
- ✅ user_id 安全化（`:` 替换为 `_`）

---

## 四、配置指南

### 4.1 单租户配置（Gateway）

**配置文件**：`~/.fastreact/config.json`

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-your-api-key"
  },
  "paths": {
    "gateway_workspace": "./workspaces/default"
  }
}
```

**启动方式**：
```bash
# 方式 1：直接启动
python3 -m fastreact.adapters.gateway

# 方式 2：通过 uvicorn
uvicorn fastreact.adapters.gateway:create_gateway_app --host 0.0.0.0 --port 9000

# 方式 3：自定义工作区
python3 -m fastreact.adapters.gateway --base-path ./my-workspace
```

**工作区结构**：
```
./workspaces/default/
├── config.json          # 全局配置
├── memory.json          # 全局对话记忆
├── skills/              # 全局技能（共享）
│   └── .gitkeep
└── mcp_config.json      # 全局 MCP 配置（可选）
```

### 4.2 多租户配置（Feishu）

**配置文件**：`~/.fastreact/config.json`

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-your-api-key"
  },
  "feishu": {
    "connection_mode": "sdk",
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "xxxxxxxxxxxxxxxx",
    "enable_multitenant": true
  },
  "paths": {
    "feishu_workspace_base": "/var/fastreact/tenants/feishu"
  }
}
```

**环境变量**（可选）：
```bash
export FEISHU_APP_ID=cli_xxxxxxxxx
export FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
export FEISHU_MULTITENANT=true
export FEISHU_BASE_WORKSPACE=/var/fastreact/tenants/feishu
```

**启动方式**：
```bash
python3 examples/feishu_sdk_bot.py
```

**工作区结构**：
```
/var/fastreact/tenants/feishu/
├── feishu_ou_user_a/          # 用户 A 的工作区
│   ├── config.json
│   ├── memory.json
│   ├── skills/
│   │   └── custom_skill/      # 用户 A 的自定义技能
│   └── mcp_config.json        # 用户 A 的 MCP 配置
├── feishu_ou_user_b/          # 用户 B 的工作区
│   ├── config.json
│   ├── memory.json
│   ├── skills/
│   └── mcp_config.json
└── feishu_ou_user_c/          # 用户 C 的工作区
    └── ...
```

---

## 五、代码示例

### 5.1 单租户使用

**场景**：个人开发助手

```python
from fastreact import Agent

# 1. 创建 Agent（单租户模式）
agent = Agent(multitenant=False)

# 2. 运行查询（无需 user_key）
async for event in agent.run_event_stream("帮我创建文件 test.txt"):
    if event.type == EventType.SESSION_END:
        print(f"结果: {event.content}")

# 文件创建在: ./workspaces/default/files/test.txt
```

**前端连接**：
```typescript
// 所有用户连接到同一个 WebSocket
const ws = new WebSocket('ws://localhost:9000/ws');

ws.send(JSON.stringify({
  type: 'query',
  content: '帮我创建文件 test.txt'
  // 注意：没有 user_key 字段
}));
```

### 5.2 多租户使用

**场景**：飞书机器人（企业内部）

```python
from fastreact import Agent
from fastreact.adapters.feishu_sdk import FeishuSDKBot

# 1. 创建 Agent（多租户模式）
agent = Agent(
    multitenant=True,
    base_workspace="/var/fastreact/tenants/feishu"
)

# 2. 创建 Feishu Bot
bot = FeishuSDKBot(
    agent=agent,
    app_id="cli_xxx",
    app_secret="xxx"
)

# 3. 启动 Bot（会自动识别用户）
bot.start()

# 用户 A 发消息时：
# user_key = "feishu:ou_user_a"
# 工作区 = /var/fastreact/tenants/feishu/feishu_ou_user_a/

# 用户 B 发消息时：
# user_key = "feishu:ou_user_b"
# 工作区 = /var/fastreact/tenants/feishu/feishu_ou_user_b/
```

**用户特定技能**：
```python
# 用户 A 的工作区
/var/fastreact/tenants/feishu/feishu_ou_user_a/
└── skills/
    └── my_custom_skill/      # 用户 A 的自定义技能
        ├── skill.json
        └── system_prompt.txt

# 用户 B 的工作区
/var/fastreact/tenants/feishu/feishu_ou_user_b/
└── skills/
    └── another_skill/        # 用户 B 的自定义技能
        ├── skill.json
        └── system_prompt.txt
```

**技能加载优先级**（多租户）：
```
1. 用户特定技能 (feishu_ou_user_a/skills/)
   ↓ (如果未找到)
2. 全局技能 (skills/builtin/)
   ↓ (如果未找到)
3. 社区技能 (skills/community/)
```

---

## 六、高级功能

### 6.1 动态用户识别

**场景**：Web 应用（需要登录）

```python
from fastreact import Agent

agent = Agent(multitenant=True)

# 用户登录后
async def handle_query(user_email: str, query: str):
    # 构造 user_key
    user_key = f"web:{user_email}"

    # 运行 Agent（会自动创建用户工作区）
    async for event in agent.run_event_stream(
        query,
        user_key=user_key  # 传递 user_key
    ):
        yield event

# 使用示例
# handle_query("alice@example.com", "创建文件")
# → 工作区: /var/fastreact/tenants/feishu/web_alice@example.com/
#
# handle_query("bob@example.com", "创建文件")
# → 工作区: /var/fastreact/tenants/feishu/web_bob@example.com/
```

### 6.2 用户配置管理

**读取用户配置**：
```python
from fastreact.core.multitenant import MultiTenantManager

manager = MultiTenantManager(Path("/var/fastreact/tenants/feishu"))

# 获取用户上下文
user_context = manager.get_user_context("feishu:ou_user_a")

# 读取用户配置
print(user_context.config)
# {
#   "user_key": "feishu:ou_user_a",
#   "channel": "feishu",
#   "user_id": "ou_user_a",
#   "preferences": {
#     "language": "zh-CN",
#     "timezone": "Asia/Shanghai"
#   }
# }
```

**更新用户配置**：
```python
# 更新用户配置
manager.update_user_config(
    "feishu:ou_user_a",
    {
        "preferences": {
            "language": "en-US",
            "timezone": "America/New_York"
        }
    }
)
```

### 6.3 用户特定 MCP 服务器

**配置**：`/var/fastreact/tenants/feishu/feishu_ou_user_a/mcp_config.json`

```json
{
  "servers": [
    {
      "name": "user_database",
      "command": "python3",
      "args": ["mcp_servers/user_db.py", "--user", "ou_user_a"],
      "isolation": "per_user"
    }
  ]
}
```

**效果**：用户 A 有自己的数据库 MCP Server，用户 B 无法访问。

---

## 七、迁移指南

### 7.1 从单租户迁移到多租户

**步骤 1**：备份现有工作区
```bash
cp -r workspaces/default workspaces/default.backup
```

**步骤 2**：创建用户工作区
```bash
# 为每个用户创建工作区
mkdir -p /var/fastreact/tenants/feishu/feishu_ou_user_a
mkdir -p /var/fastreact/tenants/feishu/feishu_ou_user_b

# 复制共享配置到每个用户（可选）
cp workspaces/default/config.json /var/fastreact/tenants/feishu/feishu_ou_user_a/
cp workspaces/default/config.json /var/fastreact/tenants/feishu/feishu_ou_user_b/
```

**步骤 3**：更新配置
```json
{
  "feishu": {
    "enable_multitenant": true
  },
  "paths": {
    "feishu_workspace_base": "/var/fastreact/tenants/feishu"
  }
}
```

**步骤 4**：重启服务
```bash
python3 examples/feishu_sdk_bot.py
```

---

## 八、最佳实践

### 8.1 何时使用单租户？

✅ **推荐场景**：
- 个人开发助手
- 测试环境
- PoC（概念验证）
- 所有用户共享同一数据集

❌ **不推荐场景**：
- 多用户生产环境
- 需要用户数据隔离
- 需要个性化配置

### 8.2 何时使用多租户？

✅ **推荐场景**：
- 企业部署（飞书机器人）
- SaaS 应用
- 需要用户数据隔离
- 需要用户个性化配置

❌ **不推荐场景**：
- 个人使用（资源浪费）
- 测试环境（复杂度高）

### 8.3 安全建议

1. **工作区隔离**：
   ```bash
   # 使用系统级目录（不是项目内）
   /var/fastreact/tenants/    # ✅ 好
   ./workspaces/              # ❌ 差（项目内）
   ```

2. **权限控制**：
   ```bash
   # 限制工作区权限
   chmod 700 /var/fastreact/tenants/feishu/feishu_ou_user_a
   ```

3. **磁盘配额**：
   ```bash
   # 为每个用户设置磁盘配额（防止占用过多空间）
   setquota -u ou_user_a 10G 12G 0 0 /var
   ```

4. **监控日志**：
   ```python
   # 记录用户操作（用于审计）
   import logging
   logger.info(f"User {user_key} performed action: {action}")
   ```

---

## 九、故障排查

### 9.1 单租户问题

**问题**：找不到工作区
```bash
# 检查工作区路径
ls -la ./workspaces/default/

# 检查配置
cat ~/.fastreact/config.json | grep gateway_workspace
```

**问题**：配置未生效
```bash
# 清除缓存
rm -rf workspaces/default/
rm -rf .fastreact/

# 重启
python3 -m fastreact.adapters.gateway
```

### 9.2 多租户问题

**问题**：用户工作区未创建
```bash
# 检查 base_workspace
ls -la /var/fastreact/tenants/feishu/

# 检查权限
ls -ld /var/fastreact/tenants/feishu/
# 应该是 drwxr-xr-x (755) 或更严格
```

**问题**：用户数据混乱
```bash
# 检查 user_key 格式
# 正确: feishu:ou_xxx
# 错误: feishu:ou:xxx (多余的冒号)

# 检查工作区命名
ls -la /var/fastreact/tenants/feishu/
# 应该是: feishu_ou_xxx (下划线，不是冒号)
```

**问题**：安全错误
```bash
# 检查 user_key 是否包含非法字符
# 只允许: a-zA-Z0-9_@.=+-
```

---

## 十、总结

### 核心区别

| 方面 | 单租户 | 多租户 |
|------|--------|--------|
| **复杂度** | 简单 | 中等 |
| **隔离性** | 无 | 完全隔离 |
| **适用** | 个人、测试 | 企业、SaaS |
| **工作区** | `./workspaces/default/` | `/var/fastreact/tenants/feishu/{user_key}/` |
| **配置** | 无需 user_key | 需要 user_key |

### 快速选择

```
是否需要多用户？
  ├─ 否 → 单租户（Gateway）
  └─ 是 → 是否需要数据隔离？
      ├─ 是 → 多租户（Feishu）
      └─ 否 → 单租户（Gateway）
```

---

**文档维护**：
- **作者**: Claude Code
- **最后更新**: 2025-02-19
- **版本**: 2.4.2
