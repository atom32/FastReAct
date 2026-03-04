# Feishu Adapter 架构审计报告

**审计日期**: 2025-03-04
**审计范围**: feishu.py vs feishu_sdk.py

---

## 两个 Adapter 的区别

### ❌ feishu.py (Webhook 模式 - 已废弃)

**文件**: `src/fastreact/adapters/feishu.py`

**特点**:
- 使用 FastAPI 创建 Webhook 服务器
- 需要公网 IP 或内网穿透
- 需要配置 Webhook URL
- 依赖 HTTP 请求接收事件

**架构**:
```
飞书服务器 → HTTP Webhook → FastAPI 服务器 → 处理消息
```

**缺点**:
- ❌ 需要公网 IP（或内网穿透）
- ❌ 需要配置 Webhook URL
- ❌ 需要服务器公网证书
- ❌ 依赖 HTTP 服务器

**状态**: 🚫 已废弃，不推荐使用

---

### ✅ feishu_sdk.py (SDK 模式 - 推荐)

**文件**: `src/fastreact/adapters/feishu_sdk.py`

**特点**:
- 使用 Lark 官方 SDK (`lark-oapi`)
- WebSocket 长连接模式
- **无需公网 IP**
- 自动重连
- 事件驱动

**架构**:
```
飞书服务器 ←→ WebSocket 长连接 ←→ Lark SDK → 处理消息
```

**优点**:
- ✅ **无需公网 IP**（内网即可）
- ✅ 无需配置 Webhook URL
- ✅ 无需 HTTP 服务器
- ✅ 自动重连机制
- ✅ 官方 SDK 支持

**状态**: ✅ 推荐使用，已验证可用

---

## 启动方式对比

### feishu.py (Webhook 模式)

```bash
python -m fastreact.adapters.feishu

# 输出:
[INFO] Feishu Bot Configuration:
  - Connection mode: sdk
  - Multi-tenant: True
  - Host: 0.0.0.0
  - Port: 8001
  - Webhook path: /webhook/feishu
[INFO] Starting Uvicorn server...
```

**配置要求**:
```json
{
  "feishu": {
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "your_app_secret",
    "encrypt_key": "your_encrypt_key",
    "verification_token": "your_verification_token",
    "connection_mode": "sdk",
    "enable_multitenant": true
  }
}
```

### feishu_sdk.py (SDK 模式)

```bash
python -m fastreact.adapters.feishu_sdk

# 输出:
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_xxxxxxxxx
[INFO] Multi-tenant: True
[INFO] Auto-reconnect: True
[INFO] Loaded 3 MCP servers
[INFO] Available skills: [...]
```

**配置要求**:
```json
{
  "feishu": {
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "your_app_secret",
    "connection_mode": "sdk",
    "enable_multitenant": true,
    "auto_reconnect": true,
    "log_level": "info"
  }
}
```

**注意**: SDK 模式**不需要** `encrypt_key` 和 `verification_token`（这些是 Webhook 模式需要的）

---

## 依赖关系

### feishu.py 依赖
```
fastapi
uvicorn
cryptography (HMAC 验证)
```

### feishu_sdk.py 依赖
```
lark-oapi>=1.5.0
httpx
```

---

## 架构对比

### feishu.py (Webhook 模式)

```
┌─────────────────────────────────────────┐
│  飞书服务器                                 │
│  (主动推送事件到 Webhook)                 │
└────────────┬────────────────────────────┘
             │ HTTP POST
             ▼
┌─────────────────────────────────────────┐
│  FastAPI Webhook 服务器                   │
│  (监听 0.0.0.0:8001)                      │
│                                           │
│  • 验证 Webhook 签名                        │
│  • 解析事件                               │
│  • 调用 Agent 处理                         │
│  • 返回 HTTP 响应                         │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Agent (per-user)                         │
│  • Workspace 隔离                          │
│  • ReAct 循环                              │
└─────────────────────────────────────────┘
```

### feishu_sdk.py (SDK 模式) ✅

```
┌─────────────────────────────────────────┐
│  飞书服务器                                 │
│  (保持 WebSocket 长连接)                   │
└────────────┬────────────────────────────┘
             │ WebSocket
             ▼
┌─────────────────────────────────────────┐
│  Lark SDK 客户端                         │
│  (自动管理连接和重连)                     │
│                                           │
│  • 接收事件 (事件驱动)                     │
│  • 发送消息                               │
│  • 自动重连                                │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  FeishuSDKAdapter                         │
│  • 事件处理器                             │
│  • 用户识别 (feishu:user_id)             │
│  • 多租户路由                              │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Agent (per-user)                         │
│  • Workspace 隔离                          │
│  • ReAct 循环                              │
└─────────────────────────────────────────┘
```

---

## 多租户支持对比

### feishu.py 多租户实现

**User Key 格式**: `feishu:ou_xxxxxxxxx`

**Workspace 路径**:
```
/var/fastreact/tenants/feishu/feishu_ou_xxxxxxxxx/
```

**实现**:
```python
# 从飞书事件中提取 sender_id
sender_id = event.sender.sender_id
user_key = f"feishu:{sender_id}"

# 创建用户专属 Agent
agent = Agent(config=config)
agent_session = agent.create_session(user_key=user_key)
```

### feishu_sdk.py 多租户实现

**User Key 格式**: `feishu:ou_xxxxxxxxx`

**Workspace 路径**:
```
/var/fastreact/tenants/feishu/feishu_ou_xxxxxxxxx/
```

**实现**:
```python
class FeishuSDKAdapter:
    def __init__(self, agent, config):
        # 多租户管理器
        if config.enable_multitenant:
            workspace = config.base_workspace or agent._config.paths.feishu_workspace_base
            self._multitenant = MultiTenantManager(workspace)

    def _handle_message_event(self, event):
        # 从飞书事件中提取 sender_id
        sender_id = event.sender.sender_id
        user_key = f"feishu:{sender_id}"

        # 创建用户专属会话
        session = self.agent.get_or_create_session(user_key=user_key)
```

**完全相同！** 两个 adapter 的多租户实现逻辑相同。

---

## 启动验证

### 验证 feishu_sdk.py 正在运行

```bash
ps aux | grep feishu_sdk
```

**输出**:
```
ning  38023  ... python -m fastreact.adapters.feishu_sdk
```

### 验证 WebSocket 连接

启动后会看到：
```
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_xxxxxxxxx
[INFO] Multi-tenant: True
[INFO] Auto-reconnect: True
[INFO] Loaded 3 MCP servers
[INFO] MCP Manager initialized
[INFO] Available skills: [...]
```

---

## 配置迁移

### 从 feishu.py 迁移到 feishu_sdk.py

**之前 (feishu.py)**:
```json
{
  "feishu": {
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "your_app_secret",
    "encrypt_key": "your_encrypt_key",
    "verification_token": "your_verification_token",
    "connection_mode": "sdk",
    "enable_multitenant": true
  }
}
```

**之后 (feishu_sdk.py)**:
```json
{
  "feishu": {
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "your_app_secret",
    "connection_mode": "sdk",
    "enable_multitenant": true,
    "auto_reconnect": true,
    "log_level": "info"
  }
}
```

**变更**:
- ❌ 移除 `encrypt_key`（SDK 模式不需要）
- ❌ 移除 `verification_token`（SDK 模式不需要）
- ✅ 添加 `auto_reconnect`（SDK 自动重连）
- ✅ 添加 `log_level`（日志级别控制）

---

## 系统状态

### 当前运行的服务

```
✅ Gateway:        port 9000  (WebSocket 多租户)
✅ Feishu SDK:    WebSocket  (Lark SDK, 长连接)
⏸️ 前端:         port 3000  (可选)
```

### 多租户架构

```
Gateway 用户
  → ws://localhost:9000/ws?user_key=web:alice@example.com
  → Workspace: /Users/ning/workspaces/web_alice@example.com/

飞书用户
  → 飞书客户端
  → WebSocket 长连接 (Lark SDK)
  → Workspace: /var/fastreact/tenants/feishu/feishu_ou_xxxxxxxxx/
```

---

## 总结

### 推荐使用 feishu_sdk.py ✅

**原因**:
1. ✅ 使用 Lark 官方 SDK
2. ✅ WebSocket 长连接（稳定）
3. ✅ 无需公网 IP
4. ✅ 无需 Webhook URL
5. ✅ 自动重连机制
6. ✅ 内网即可运行

### 废弃 feishu.py ❌

**原因**:
1. ❌ 需要 FastAPI 服务器
2. ❌ 需要公网 IP 或内网穿透
3. ❌ 配置复杂
4. ❌ 维护成本高

---

**审计结论**:

✅ **feishu_sdk.py 是正确的选择**
- 架构更优
- 配置更简单
- 无需公网暴露
- 更易维护

❌ **feishu.py 应该废弃**
- 仅用于特殊场景（已有 Webhook 基础设施）
- 不推荐新项目使用

---

**审计人**: Claude
**审计日期**: 2025-03-04
**推荐使用**: feishu_sdk.py
