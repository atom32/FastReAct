# FastReAct 系统流程说明

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web 前端   │  │  飞书 Bot    │  │  CLI/HTTP    │         │
│  │  (Next.js)   │  │   (Lark)     │  │  (API)       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                     WebSocket/HTTP                                │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gateway 统一入口                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         FastAPI Gateway (port 9000)                     │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │  /ws         │  │  /admin/*    │  │  /api/*      │  │    │
│  │  │  WebSocket   │  │  Admin API   │  │  HTTP API    │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  关键功能:                                                         │
│  • 用户识别 (user_key 提取)                                        │
│  • 多租户路由 (per-user Agent)                                    │
│  • Admin 监控 (只读 API)                                          │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Agent 层 (执行层)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  每个用户独立的 Agent 实例:                                        │
│  • Agent(user="web:user_a@example.com")                          │
│  • Agent(user="feishu:ou_123456")                                │
│  • Agent(user="web:user_b@example.com")                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  ReAct Core (大脑)                       │    │
│  │                                                          │    │
│  │  • 意图生成 (Prompt → LLM → Action)                     │    │
│  │  • 循环控制 (Steering/Followup)                         │    │
│  │  • 工具选择 (SKILL/MCP)                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  工具执行:                                                         │
│  • 4 个核心工具 (read, write, edit, exec)                       │
│  • SKILL 扩展                                                   │
│  • MCP 服务集成                                                 │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Workspace 层 (数据隔离)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  用户 Workspace 隔离:                                              │
│  ./workspaces/                                                    │
│  ├── web_user_a@example.com/    ← 用户 A 的独立空间              │
│  │   ├── config.json            ← 用户配置                      │
│  │   ├── memory.json            ← 对话记忆                      │
│  │   ├── skills/                ← 用户自定义 SKILL               │
│  │   └── files/                 ← 用户文件                      │
│  │                                                                  │
│  ├── web_user_b@example.com/    ← 用户 B 的独立空间              │
│  ├── feishu_ou_123456/          ← 飞书用户的独立空间             │
│  └── default/                   ← 单租户模式共享空间               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 完整请求流程

### 场景 1: Web 用户登录并提问

```
1. 用户操作
   ┌─────────────┐
   │ 浏览器访问   │
   │ localhost:  │
   │ 3000        │
   └──────┬──────┘
          │
          ▼
2. 用户登录
   输入: alice@example.com
          │
          ▼
3. WebSocket 连接
   ws://localhost:9000/ws?user_key=web:alice@example.com
          │
          ▼
4. Gateway 接收
   ┌─────────────────────────────────────┐
   │  Gateway (FastAPI)                  │
   │                                     │
   │  提取 user_key                      │
   │  验证格式 (channel:user_id)         │
   │  创建 Session                        │
   └──────────┬──────────────────────────┘
              │
              ▼
5. 创建用户专属 Agent
   ┌─────────────────────────────────────┐
   │  Agent(                              │
   │    user_key="web:alice@example.com" │
   │    multitenant=True                  │
   │  )                                  │
   └──────────┬──────────────────────────┘
              │
              ▼
6. 创建/加载用户 Workspace
   ./workspaces/web_alice@example.com/
          │
          ▼
7. 接收用户消息
   {"type": "query", "content": "帮我分析数据"}
          │
          ▼
8. ReAct 循环
   ┌─────────────────────────────────────┐
   │  ReAct Core                         │
   │                                     │
   │  Step 1: Think                      │
   │    → LLM 生成意图                   │
   │                                     │
   │  Step 2: Act                        │
   │    → 选择工具/ SKILL                │
   │    → 执行工具                       │
   │                                     │
   │  Step 3: Observe                    │
   │    → 观察结果                       │
   │    → 更新记忆                       │
   │                                     │
   │  Step 4: Decide                     │
   │    → 需要更多步骤? → 继续           │
   │    → 已完成? → 返回结果             │
   └──────────┬──────────────────────────┘
              │
              ▼
9. 返回结果
   {"type": "event", "content": "分析完成..."}
          │
          ▼
10. 前端显示
    渲染消息和事件流
```

### 场景 2: 飞书用户提问

```
1. 用户操作
   飞书 App 发送消息
          │
          ▼
2. 飞书服务器
   推送事件到 Webhook
          │
          ▼
3. Gateway 接收
   POST /webhook/feishu
          │
          ▼
4. 提取 user_key
   sender_id: "ou_1234567890"
   → user_key: "feishu:ou_1234567890"
          │
          ▼
5. 创建用户专属 Agent
   Agent(user_key="feishu:ou_1234567890")
          │
          ▼
6. 创建/加载 Workspace
   /var/fastreact/tenants/feishu/feishu_ou_1234567890/
          │
          ▼
7. ReAct 循环
   (同上)
          │
          ▼
8. 返回结果
   飞书 Card 消息
```

### 场景 3: Admin 监控

```
1. Admin 访问
   http://localhost:9000/admin
          │
          ▼
2. 身份验证
   输入 Admin API Key
          │
          ▼
3. 调用 Admin API
   GET /admin/sessions?admin_key=xxx
   GET /admin/users?admin_key=xxx
   GET /admin/metrics?admin_key=xxx
          │
          ▼
4. Gateway 处理
   验证 Admin API Key
          │
          ▼
5. 收集全局信息
   • 所有活跃会话
   • 所有用户列表
   • 系统性能指标
          │
          ▼
6. 返回只读数据
   (不包含用户聊天内容，保护隐私)
          │
          ▼
7. Admin 面板显示
   实时更新仪表盘
```

---

## 用户识别机制

### Web 用户

```
用户输入: alice@example.com
          │
          ▼
生成 user_key
  web:alice@example.com
          │
          ▼
WebSocket 连接
  ws://localhost:9000/ws?user_key=web:alice@example.com
          │
          ▼
Workspace 路径
  ./workspaces/web_alice@example.com/
```

### 飞书用户

```
飞书用户 ID: ou_1234567890
          │
          ▼
生成 user_key
  feishu:ou_1234567890
          │
          ▼
Workspace 路径
  /var/fastreact/tenants/feishu/feishu_ou_1234567890/
```

### CLI 用户（单租户）

```
CLI 启动
          │
          ▼
无 user_key
  (单租户模式)
          │
          ▼
Workspace 路径
  ./workspace/ (所有用户共享)
```

---

## 数据隔离保证

### 物理隔离
```
用户 A: ./workspaces/web_alice@example.com/
用户 B: ./workspaces/web_bob@example.com/
飞书:  /var/fastreact/tenants/feishu/feishu_ou_xxx/

✅ 完全独立的目录结构
```

### 逻辑隔离
```
Agent A: 只能访问用户 A 的 workspace
Agent B: 只能访问用户 B 的 workspace

✅ Agent 实例级别隔离
```

### 安全防护
```
路径验证: 防止 ../../../etc/passwd
字符过滤: 防止 user\0name
权限控制: Admin 只读，不泄露隐私

✅ 多层安全防护
```

---

## 配置与启动

### 1. 多租户模式（默认）

**配置** (`~/.fastreact/config.json`):
```json
{
  "gateway": {
    "enable_multitenant": true,
    "admin_api_key": "your-secret-key"
  }
}
```

**启动**:
```bash
python -m fastreact.adapters.gateway
```

**结果**:
- ✅ 每个用户独立 workspace
- ✅ 用户数据完全隔离
- ✅ Admin 可以监控所有用户

### 2. 单租户模式（Admin 专用）

**配置**:
```json
{
  "gateway": {
    "enable_multitenant": false,
    "admin_only": true
  }
}
```

**启动**:
```bash
python -m fastreact.adapters.gateway
```

**结果**:
- ✅ 所有用户共享 workspace
- ✅ 适合个人使用或 Admin 专用

### 3. 飞书 Bot（多租户）

**配置**:
```json
{
  "feishu": {
    "app_id": "your_app_id",
    "app_secret": "your_app_secret",
    "enable_multitenant": true
  }
}
```

**启动**:
```bash
python -m fastreact.adapters.feishu
```

**结果**:
- ✅ 每个飞书用户独立 workspace
- ✅ 支持飞书 Card 消息

---

## 工具与扩展

### SKILL 系统
```
用户可以添加自定义 SKILL:

./workspaces/web_alice@example.com/skills/
  ├── my_skill.py       ← 用户自定义 SKILL
  └── data.json         ← SKILL 数据

✅ 自动加载到用户的 Agent
```

### MCP 集成
```
用户可以配置 MCP 服务器:

~/.fastreact/mcp_servers.json
{
  "servers": [
    {
      "name": "database",
      "isolation": "per_user"  ← 每个 user 独立连接
    }
  ]
}

✅ 工具自动注入到用户对话
```

---

## 监控与管理

### Admin 面板
```
访问: http://localhost:9000/admin
功能:
  • 实时会话列表
  • 用户统计
  • 系统性能指标
  • CPU/内存监控
```

### 系统状态 API
```
GET /health
→ {"status": "healthy", "active_sessions": 5}

GET /api/status
→ {"multi_tenant": {"enabled": true}, "skills": [...], "mcp": [...]}
```

---

## 安全与隐私

### 用户数据保护
```
✅ Workspace 隔离 - 用户无法访问其他用户的数据
✅ Admin 只读 - Admin 只能看元数据，不能看聊天内容
✅ 路径验证 - 防止路径遍历攻击
✅ 字符过滤 - 防止特殊字符注入
```

### Admin API 安全
```
✅ API Key 认证 - X-Admin-Key header 或 admin_key query param
✅ 无认证拒绝 - 返回 401 Unauthorized
✅ 数据脱敏 - 只返回元数据，不返回用户内容
```

---

## 总结

### 当前系统特点

1. **原生多租户** - Gateway 默认支持多租户
2. **统一入口** - Gateway 作为主要启动方式
3. **Workspace 隔离** - 每个用户完全独立的数据空间
4. **灵活配置** - 支持多租户和单租户模式切换
5. **Admin 监控** - 只读监控，不泄露隐私

### 系统流程总结

```
用户 → Gateway → Agent(per-user) → ReAct Core → Tools/SKILLs → Workspace(per-user)
                                                                  ↑
                                                            数据完全隔离
```

### 启动方式

```bash
# 推荐：Gateway (多租户)
python -m fastreact.adapters.gateway

# 飞书 Bot (SDK 模式 - 推荐)
python -m fastreact.adapters.feishu_sdk

# 飞书 Bot (Webhook 模式 - 已废弃)
python -m fastreact.adapters.feishu

# 单租户模式
# 修改配置: gateway.enable_multitenant = false
python -m fastreact.adapters.gateway
```

---

**最后更新**: 2025-03-04
**系统版本**: FastReAct Nano v2.4.2
