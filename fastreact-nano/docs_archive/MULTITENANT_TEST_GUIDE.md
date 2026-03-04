# FastReAct 多租户端到端测试指南

## 快速验证

### 1. 快速功能验证（无需 Gateway）

```bash
cd fastreact-nano
python scripts/verify_multitenant.py
```

**预期输出**:
```
✓ 所有测试通过 (5/5)

下一步:
  1. 启动 Gateway: python -m fastreact.adapters.gateway
  2. 运行端到端测试: python tests/integration/test_multitenant_e2e.py
  3. 启动前端测试: cd ../fastreact-nano-web && npm run dev
```

### 2. 完整端到端测试（需要 Gateway）

#### 方式 1: 使用自动化脚本（推荐）

```bash
cd fastreact-nano
./scripts/test_e2e.sh
```

#### 方式 2: 手动执行

```bash
# Terminal 1: 启动 Gateway
cd fastreact-nano
export GATEWAY_ADMIN_KEY="test-admin-key"
python -m fastreact.adapters.gateway

# Terminal 2: 运行测试
cd fastreact-nano
python tests/integration/test_multitenant_e2e.py
```

---

## 测试场景说明

### 场景 1: 用户连接与 Workspace 创建

**测试内容**:
- 用户连接到 Gateway
- Workspace 自动创建
- Config 文件生成
- 子目录结构创建

**验证命令**:
```bash
# 检查生成的 Workspace
ls -la ./workspaces/

# 检查 Config 文件
cat ./workspaces/web_test_user@example.com/config.json
```

**预期结果**:
```json
{
  "user_key": "web:test_user@example.com",
  "channel": "web",
  "user_id": "test_user@example.com",
  "preferences": {
    "language": "zh-CN",
    "timezone": "Asia/Shanghai"
  }
}
```

### 场景 2: Workspace 隔离

**测试内容**:
- 用户 A 创建文件
- 用户 B 无法访问用户 A 的文件

**验证命令**:
```bash
# 检查用户 A 的 workspace
ls -la ./workspaces/web_user_a_isolation@example.com/

# 检查用户 B 的 workspace（应该没有 test.txt）
ls -la ./workspaces/web_user_b_isolation@example.com/
```

### 场景 3: Admin 监控 API

**测试内容**:
- Admin 无认证访问（应该 401）
- Admin 获取会话列表
- Admin 获取用户列表
- Admin 获取系统指标

**验证命令**:
```bash
# 1. 无认证访问（应该返回 401）
curl http://localhost:9000/admin/sessions

# 2. 有认证访问
curl "http://localhost:9000/admin/sessions?admin_key=test-admin-key"

# 3. 获取用户列表
curl "http://localhost:9000/admin/users?admin_key=test-admin-key"

# 4. 获取系统指标
curl "http://localhost:9000/admin/metrics?admin_key=test-admin-key"
```

**预期输出**:
```json
{
  "total": 2,
  "sessions": [
    {
      "session_id": "...",
      "user_key": "web:user_a_isolation@example.com",
      "created_at": "2025-03-04T...",
      "last_activity": "2025-03-04T...",
      "status": "active"
    }
  ]
}
```

### 场景 4: 并发用户

**测试内容**:
- 10 个用户同时连接
- 每个 user_key 有独立的 workspace

**验证命令**:
```bash
# 查看创建的 workspace 数量
ls -d ./workspaces/* | wc -l

# 应该看到至少 10 个不同的用户 workspace
```

---

## 前端测试流程

### 1. 启动前端

```bash
cd fastreact-nano-web
npm run dev
```

### 2. 用户登录流程

#### 步骤 1: 访问应用
1. 打开浏览器访问 `http://localhost:3000`
2. 看到聊天界面

#### 步骤 2: 用户登录
1. 点击导航栏右侧的用户按钮（显示 "Guest"）
2. 输入邮箱（例如 `alice@example.com`）
3. 点击登录

#### 步骤 3: 验证登录成功
- 用户按钮显示绿色圆点
- 显示邮箱地址 `alice@example.com`

#### 步骤 4: 验证 WebSocket 连接
1. 打开浏览器开发者工具（F12）
2. 切换到 Network 标签
3. 筛选 WebSocket 连接
4. 查看 WebSocket URL 包含 `user_key=web:alice@example.com`

#### 步骤 5: 验证 Workspace 创建
```bash
# 检查 Workspace 已创建
ls -la ./workspaces/web_alice@example.com/
```

### 3. Admin 面板测试

#### 步骤 1: 访问 Admin 面板
```bash
open http://localhost:9000/admin
```

#### 步骤 2: 登录
- 输入 Admin API Key: `test-admin-key`
- 点击登录

#### 步骤 3: 验证功能
- ✅ 看到 Dashboard（系统指标）
- ✅ 看到 Users（用户列表）
- ✅ 看到 Sessions（会话列表）
- ✅ 数据每 5 秒自动刷新

---

## 测试覆盖矩阵

| 测试类型 | 测试场景 | 自动化 | 手动 |
|---------|---------|--------|------|
| **单元测试** | MultiTenantManager | ✅ | - |
| **单元测试** | 安全验证 | ✅ | - |
| **单元测试** | Admin API | ✅ | - |
| **集成测试** | Workspace 隔离 | ✅ | - |
| **端到端测试** | 用户登录 | ✅ | ✅ |
| **端到端测试** | Admin 监控 | ✅ | ✅ |
| **端到端测试** | 并发用户 | ✅ | - |

---

## 故障排查

### 问题 1: 测试失败 - Gateway 未运行

**错误信息**:
```
[ERROR] 无法连接到 Gateway
```

**解决方法**:
```bash
cd fastreact-nano
python -m fastreact.adapters.gateway
```

### 问题 2: Admin API 返回 401

**错误信息**:
```
✗ Admin API 返回错误: 401
```

**解决方法**:
```bash
# 设置正确的 Admin API Key
export GATEWAY_ADMIN_KEY="test-admin-key"

# 或在配置文件中设置
# ~/.fastreact/config.json:
{
  "gateway": {
    "admin_api_key": "test-admin-key"
  }
}
```

### 问题 3: WebSocket 连接失败

**错误信息**:
```
✗ 连接失败: [Errno 61] Connection refused
```

**解决方法**:
1. 确认 Gateway 正在运行
2. 确认端口 9000 未被占用
3. 检查防火墙设置

### 问题 4: Workspace 未创建

**错误信息**:
```
✗ Workspace 不存在: ./workspaces/web_user@example.com
```

**解决方法**:
1. 确认多租户模式已启用
2. 确认用户已发送至少一条消息
3. 查看 Gateway 日志

---

## 性能基准

### 并发性能

| 用户数 | 预期耗时 | 内存占用 |
|-------|---------|---------|
| 10 | < 5s | ~200MB |
| 100 | < 30s | ~500MB |
| 1000 | < 5min | ~2GB |

### Workspace 操作性能

| 操作 | 预期耗时 |
|------|---------|
| 创建 Workspace | < 100ms |
| 加载 Config | < 50ms |
| 路径验证 | < 10ms |

---

## 下一步

### 当前已实现 ✅

1. ✅ Gateway 多租户支持
2. ✅ Workspace 自动创建与隔离
3. ✅ Admin 监控 API
4. ✅ 前端用户登录
5. ✅ 单租户降级模式

### 待实现 ⏳

1. ⏳ 用户认证（JWT/OAuth）
2. ⏳ 权限系统（RBAC）
3. ⏳ 配额管理（磁盘/Token）
4. ⏳ 审计日志
5. ⏳ Workspace 自动清理

---

## 文档索引

- **审计报告**: `docs_archive/MULTITENANT_AUDIT_REPORT.md`
- **测试说明**: `tests/integration/README.md`
- **配置示例**: `config.example.json`
- **架构文档**: `CLAUDE.md`

---

**最后更新**: 2025-03-04
**测试状态**: ✅ 所有测试通过
