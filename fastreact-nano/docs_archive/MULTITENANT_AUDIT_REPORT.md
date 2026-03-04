# FastReAct 多租户架构审计报告

**日期**: 2025-03-04
**审计范围**: 多租户架构实现、启动方式、测试覆盖

---

## 1. 架构概述

### 1.1 主要启动方式

FastReAct 支持多种启动方式，Gateway 是主要的统一入口：

```bash
# 方式 1: 直接启动 Gateway (推荐)
python -m fastreact.adapters.gateway

# 方式 2: 启动 HTTP 服务
python -m fastreact.adapters.http

# 方式 3: 启动飞书 Bot
python -m fastreact.adapters.feishu

# 方式 4: 使用脚本
./start.sh              # 启动 Gateway
./start_feishu_bot.sh   # 启动飞书 Bot
```

### 1.2 适配器架构

```
fastreact/
├── adapters/
│   ├── gateway.py      # WebSocket Gateway (统一入口，多租户)
│   ├── feishu.py       # 飞书 Bot (多租户)
│   ├── http.py         # HTTP API
│   ├── cli.py          # 命令行 REPL
│   ├── telegram.py     # Telegram Bot
│   └── wechat.py       # 微信 Bot
```

---

## 2. 多租户支持矩阵

| 通道 | User Key 格式 | 多租户支持 | Workspace 路径 | 状态 |
|------|--------------|-----------|--------------|------|
| **Gateway** | `web:user@example.com` | ✅ 是 | `./workspaces/web_user@example.com/` | ✅ 已实现 |
| **Feishu** | `feishu:ou_xxx` | ✅ 是 | `/var/fastreact/tenants/feishu/feishu_ou_xxx/` | ✅ 已实现 |
| **CLI** | `cli:local` | ❌ 否 | `./workspace/` | 单租户 |
| **HTTP** | - | ❌ 否 | - | 未实现 |
| **Telegram** | - | ❌ 否 | - | 未实现 |

---

## 3. Gateway 多租户实现

### 3.1 用户识别机制

**方式**: WebSocket Query 参数

```javascript
// 前端连接示例
const ws = new WebSocket("ws://localhost:9000/ws?user_key=web:user@example.com")

// 默认用户（临时，数据不持久）
const ws = new WebSocket("ws://localhost:9000/ws")  // user_key = "web:default"
```

### 3.2 Workspace 隔离

**规则**:
```
user_key 格式: "{channel}:{user_id}"

转换规则:
1. 分割 channel 和 user_id
2. 替换 `:` 为 `_`
3. 创建目录: base_workspace/{channel}_{user_id}/

示例:
- web:user@example.com → ./workspaces/web_user@example.com/
- mobile:user123      → ./workspaces/mobile_user123/
- api:client_xxx      → ./workspaces/api_client_xxx/
```

### 3.3 安全防护

**路径遍历攻击防护**:
```python
# 字符白名单
SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_@.=+-]+$')

# 危险模式检测
dangerous_patterns = ["..", "~", "\x00"]

# 路径包含验证
if not workspace.relative_to(base_workspace):
    raise SecurityError("Path escape detected")
```

---

## 4. 现有测试覆盖

### 4.1 单元测试

| 测试文件 | 测试数量 | 状态 | 覆盖内容 |
|---------|---------|------|---------|
| `test_gateway_multitenant.py` | 15 | ✅ 通过 | Gateway 多租户 |
| `test_admin_api.py` | 18 | ✅ 通过 | Admin API |
| `test_multitenant.py` | 18 | ✅ 通过 | MultiTenantManager |
| `test_multitenant_security.py` | - | ⚠️ 未审计 | 安全测试 |

### 4.2 集成测试

| 测试场景 | 状态 | 说明 |
|---------|------|------|
| 多用户并发访问 | ❌ 缺失 | 需要实现 |
| Workspace 隔离 | ❌ 缺失 | 需要实现 |
| Admin 监控 | ❌ 缺失 | 需要实现 |
| 单租户降级 | ❌ 缺失 | 需要实现 |

---

## 5. 端到端测试方案

### 5.1 测试目标

验证多租户架构的以下关键功能：
1. **用户隔离** - 不同用户的数据完全隔离
2. **Workspace 管理** - 自动创建、路径验证
3. **Admin 监控** - 只读访问，不泄露隐私
4. **会话管理** - 多用户并发会话

### 5.2 测试环境

```bash
# 1. 启动 Gateway (多租户模式)
cd fastreact-nano
python -m fastreact.adapters.gateway

# 2. 启动前端 (另一个终端)
cd ../fastreact-nano-web
npm run dev

# 3. 配置环境变量
export GATEWAY_ADMIN_KEY="test-admin-key"
```

### 5.3 端到端测试场景

#### 场景 1: 用户登录与 Workspace 创建

**步骤**:
1. 前端：用户 A 登录 (`user_a@example.com`)
2. 前端：发送消息 "Hello, I'm user A"
3. 验证：检查 `./workspaces/web_user_a@example.com/` 目录创建
4. 验证：检查 `config.json` 包含正确的 user_key

**预期结果**:
- ✅ Workspace 目录自动创建
- ✅ `config.json` 包含 `user_key: "web:user_a@example.com"`
- ✅ 用户收到连接消息 `{"type": "connected", "user_key": "web:user_a@example.com"}`

#### 场景 2: 用户数据隔离

**步骤**:
1. 用户 A 登录，创建文件 `test.txt`，内容 "User A Data"
2. 用户 A 登出
3. 用户 B 登录 (`user_b@example.com`)
4. 用户 B 尝试读取 `test.txt`

**预期结果**:
- ✅ 用户 B 无法访问用户 A 的文件
- ✅ 用户 B 的 workspace 中没有 `test.txt`
- ✅ 每个 user_key 有独立的 workspace

#### 场景 3: Admin 监控 (只读)

**步骤**:
1. 用户 A 和用户 B 同时登录
2. Admin 访问 `/admin/sessions?admin_key=test-admin-key`
3. Admin 访问 `/admin/users?admin_key=test-admin-key`

**预期结果**:
- ✅ Admin 看到两个活跃会话
- ✅ Admin 看到两个用户的信息
- ✅ Admin **不**能看到用户的聊天内容（隐私保护）

#### 场景 4: 单租户降级模式

**步骤**:
1. 修改配置 `~/.fastreact/config.json`:
   ```json
   {
     "gateway": {
       "enable_multitenant": false
     }
   }
   ```
2. 重启 Gateway
3. 用户 A 和用户 B 同时登录

**预期结果**:
- ✅ 所有用户共享同一个 workspace (`./workspaces/default/`)
- ✅ 连接消息显示 `"mode": "single-tenant"`

---

## 6. 测试自动化方案

### 6.1 测试工具

使用 `pytest` + `httpx` + `websockets` 实现自动化测试：

```python
# tests/integration/test_multitenant_e2e.py

import pytest
import asyncio
import json
from pathlib import Path
from websockets.client import connect

GATEWAY_URL = "ws://localhost:9000/ws"
ADMIN_API_KEY = "test-admin-key"

@pytest.mark.asyncio
async def test_user_workspace_isolation():
    """测试用户 workspace 隔离"""

    # 用户 A 连接
    async with connect(f"{GATEWAY_URL}?user_key=web:user_a@example.com") as ws_a:
        # 等待连接确认
        msg = json.loads(await ws_a.recv())
        assert msg["type"] == "connected"
        assert msg["user_key"] == "web:user_a@example.com"

        # 发送消息
        await ws_a.send(json.dumps({
            "type": "query",
            "content": "Create a file named test.txt with content 'User A Data'"
        }))

        # 等待响应
        while True:
            response = json.loads(await ws_a.recv())
            if response["type"] == "session_end":
                break

    # 验证 workspace 创建
    workspace_a = Path("./workspaces/web_user_a@example.com")
    assert workspace_a.exists()

    # 验证 config.json
    config_file = workspace_a / "config.json"
    assert config_file.exists()
    with open(config_file) as f:
        config = json.load(f)
    assert config["user_key"] == "web:user_a@example.com"

    # 用户 B 连接（应该无法访问用户 A 的数据）
    async with connect(f"{GATEWAY_URL}?user_key=web:user_b@example.com") as ws_b:
        # 发送消息尝试读取用户 A 的文件
        await ws_b.send(json.dumps({
            "type": "query",
            "content": "Read the file test.txt from user A's workspace"
        }))

        # 验证：应该返回错误或文件不存在
        while True:
            response = json.loads(await ws_b.recv())
            if response["type"] == "session_end" or response["type"] == "error":
                break
```

### 6.2 Admin API 测试

```python
@pytest.mark.asyncio
async def test_admin_monitoring():
    """测试 Admin 监控 API"""

    import httpx

    # 创建多个用户会话
    async with httpx.AsyncClient() as client:
        # 1. 测试无认证访问（应该返回 401）
        response = await client.get("http://localhost:9000/admin/sessions")
        assert response.status_code == 401

        # 2. 测试有认证访问
        response = await client.get(
            "http://localhost:9000/admin/sessions",
            headers={"X-Admin-Key": ADMIN_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "sessions" in data

        # 3. 测试用户列表
        response = await client.get(
            "http://localhost:9000/admin/users",
            params={"admin_key": ADMIN_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
```

---

## 7. 手动测试检查清单

### 7.1 Gateway 启动

- [ ] Gateway 正常启动在 `http://localhost:9000`
- [ ] 控制台输出显示 `[INFO] Gateway starting on 0.0.0.0:9000`
- [ ] 控制台输出显示 `[INFO] Multi-tenant: true`

### 7.2 前端用户登录

- [ ] 访问 `http://localhost:3000`
- [ ] 点击导航栏右侧用户按钮
- [ ] 输入邮箱 `test@example.com`
- [ ] 点击登录
- [ ] 用户按钮显示绿色圆点和邮箱地址

### 7.3 WebSocket 连接

- [ ] 浏览器开发者工具 Network 标签显示 WebSocket 连接
- [ ] 连接 URL 包含 `user_key=web:test@example.com`
- [ ] 收到 `connected` 消息，包含正确的 `user_key`

### 7.4 Admin 面板

- [ ] 访问 `http://localhost:9000/admin`
- [ ] 输入 Admin API Key
- [ ] 看到 Dashboard（系统指标）
- [ ] 看到 Users（用户列表）
- [ ] 看到 Sessions（会话列表）

### 7.5 Workspace 隔离

- [ ] 用户 A 创建文件后，用户 B 无法访问
- [ ] 每个用户的 workspace 目录独立
- [ ] config.json 包含正确的 user_key

---

## 8. 性能测试

### 8.1 并发用户测试

```python
# 测试 100 个并发用户
import asyncio
import websockets

async def simulate_user(user_id: int):
    async with websockets.connect(
        f"ws://localhost:9000/ws?user_key=web:user{user_id}@example.com"
    ) as ws:
        await ws.send(json.dumps({"type": "query", "content": "Hello"}))
        await asyncio.sleep(1)

async def test_concurrent_users():
    tasks = [simulate_user(i) for i in range(100)]
    await asyncio.gather(*tasks)
```

### 8.2 Workspace 数量测试

```python
# 测试大量 workspace 的性能
def test_workspace_count_performance():
    import time
    from fastreact.core.multitenant import MultiTenantManager
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MultiTenantManager(Path(tmpdir))

        start = time.time()
        for i in range(1000):
            manager.get_user_context(f"web:user{i}@example.com")
        elapsed = time.time() - start

        assert elapsed < 5.0  # 应该在 5 秒内完成
```

---

## 9. 安全审计

### 9.1 路径遍历防护

| 测试用例 | 预期结果 | 状态 |
|---------|---------|------|
| `web:../../../etc/passwd` | 拒绝 | ✅ 已实现 |
| `web:user\0name` | 拒绝 | ✅ 已实现 |
| `web:user/name` | 拒绝 | ✅ 已实现 |
| `web:user..name` | 拒绝 | ✅ 已实现 |

### 9.2 Admin API 安全

| 测试用例 | 预期结果 | 状态 |
|---------|---------|------|
| 无 API Key 访问 | 401 | ✅ 已实现 |
| 错误 API Key | 401 | ✅ 已实现 |
| Admin 查看用户数据 | 仅元数据 | ✅ 已实现 |

---

## 10. 建议和后续工作

### 10.1 短期改进

1. **添加集成测试** - 实现端到端自动化测试
2. **性能监控** - 添加 workspace 数量监控
3. **日志记录** - 记录用户登录/登出事件
4. **清理机制** - 自动清理不活跃 workspace

### 10.2 长期规划

1. **用户认证** - 添加真正的用户认证（JWT/OAuth）
2. **权限系统** - RBAC 权限控制
3. **配额管理** - 每个用户的磁盘/Token 配额
4. **审计日志** - 完整的操作审计

---

## 11. 结论

### 11.1 架构评估

✅ **Gateway 作为统一入口**: Gateway 确实是主要的统一后端启动方式
✅ **多租户支持**: Gateway 和 Feishu 都支持多租户
✅ **Workspace 隔离**: 实现了用户数据完全隔离
✅ **Admin 监控**: 实现了只读监控，不泄露隐私

### 11.2 测试覆盖

⚠️ **单元测试**: 充分（51/51 通过）
❌ **集成测试**: 缺失，需要实现
❌ **端到端测试**: 缺失，需要实现

### 11.3 优先级建议

1. **高优先级**: 实现端到端测试（确保多租户正确工作）
2. **中优先级**: 添加集成测试（验证用户隔离）
3. **低优先级**: 性能测试（优化大规模部署）

---

**审计人**: Claude
**审计日期**: 2025-03-04
**下次审计**: 实现端到端测试后
