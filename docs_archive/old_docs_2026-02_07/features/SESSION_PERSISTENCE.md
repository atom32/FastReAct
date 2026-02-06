# 会话持久化使用指南

> **Phase 1: 会话持久化** - SQLite 存储，重启不丢失数据

---

## 概述

FastReAct Gateway 现在支持会话持久化，使用 SQLite 数据库存储会话数据。

**主要特性**：
- ✅ **自动保存** - 每条消息自动保存到数据库
- ✅ **会话恢复** - 重启后自动恢复历史对话
- ✅ **高性能** - 异步 I/O，不阻塞主流程
- ✅ **零配置** - SQLite 内置，无需额外安装

---

## 快速开始

### 1. 安装依赖

```bash
pip install aiosqlite>=0.19.0
```

或安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 启动 Gateway

```bash
# Windows
set OPENAI_API_KEY=your-api-key
python scripts/run_gateway.py

# Linux/Mac
export OPENAI_API_KEY=your-api-key
python scripts/run_gateway.py
```

Gateway 会自动：
- 创建 `./data/sessions.db` 数据库文件
- 初始化表结构
- 开始自动保存会话

### 3. 测试持久化

1. 打开 `public/index.html`
2. 发送几条消息
3. 刷新页面（或重启 Gateway）
4. 使用相同的 session_id 连接
5. 历史消息会自动恢复

---

## 配置选项

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STORAGE_PATH` | `./data/sessions.db` | 数据库文件路径 |
| `AUTO_SAVE` | `true` | 是否自动保存会话 |

### 示例

```bash
# 自定义存储路径
export STORAGE_PATH=/var/lib/fastreact/sessions.db

# 禁用自动保存（仅内存）
export AUTO_SAVE=false
```

### 代码配置

```python
from fastreact import FastReAct
from fastreact.gateway import GatewayServer
from fastreact.storage import SQLiteSessionStorage

# 创建自定义存储
storage = SQLiteSessionStorage(
    db_path="./data/my_sessions.db"
)

# 创建 Gateway
gateway = GatewayServer(
    agent=FastReAct(...),
    storage=storage,
    storage_path="./data/sessions.db",  # 备选
    auto_save=True
)

# 启动时初始化
await gateway.startup()
```

---

## API 使用

### 基本用法

```python
from fastreact.storage import SQLiteSessionStorage

# 创建存储实例
storage = SQLiteSessionStorage("./data/sessions.db")
await storage.initialize()

# 保存会话
await storage.save_session("session_123", {
    "user_id": "user_456",
    "title": "研究人工智能",
    "messages": [
        {"role": "user", "content": "什么是 AI？"},
        {"role": "assistant", "content": "AI 是..."}
    ],
    "metadata": {"model": "gpt-4"}
})

# 加载会话
session = await storage.load_session("session_123")
print(session["title"])  # "研究人工智能"

# 列出会话
sessions = await storage.list_sessions(user_id="user_456", limit=10)
print(f"找到 {len(sessions)} 个会话")

# 删除会话
await storage.delete_session("session_123")

# 获取统计信息
stats = await storage.get_session_stats()
print(f"总会话数: {stats['total_sessions']}")
print(f"总消息数: {stats['total_messages']}")
```

### 高级用法

```python
# 添加单条消息
await storage.add_message("session_123", {
    "role": "user",
    "content": "继续刚才的话题",
    "metadata": {"timestamp": "2026-01-28T10:30:00"}
})

# 更新会话元数据
await storage.update_session_metadata("session_123", {
    "tags": ["AI", "研究"],
    "priority": "high"
})

# 清理旧会话（30天前）
deleted_count = await storage.cleanup_old_sessions(days=30)
print(f"清理了 {deleted_count} 个旧会话")

# 健康检查
is_healthy = await storage.health_check()
print(f"存储状态: {'健康' if is_healthy else '异常'}")
```

---

## 数据库结构

### 表结构

**sessions 表**：
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    metadata TEXT,  -- JSON 格式
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_active TIMESTAMP
)
```

**messages 表**：
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- user/assistant/system
    content TEXT NOT NULL,
    timestamp TIMESTAMP,
    metadata TEXT,  -- JSON 格式
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
)
```

### 索引

```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_last_active ON sessions(last_active DESC);
CREATE INDEX idx_messages_session_id ON messages(session_id, timestamp);
```

---

## 性能优化

### 1. 批量操作

```python
# ❌ 慢：逐条保存
for msg in messages:
    await storage.add_message(session_id, msg)

# ✅ 快：批量保存
await storage.save_session(session_id, {
    "messages": messages
})
```

### 2. 分页查询

```python
# 大数据集分页
page_size = 50
page = 0

while True:
    sessions = await storage.list_sessions(
        limit=page_size,
        offset=page * page_size
    )
    if not sessions:
        break
    process(sessions)
    page += 1
```

### 3. 定期清理

```python
import asyncio

async def cleanup_task():
    """定期清理旧会话"""
    while True:
        await asyncio.sleep(86400)  # 每天一次
        deleted = await storage.cleanup_old_sessions(days=30)
        print(f"清理了 {deleted} 个旧会话")
```

---

## 迁移指南

### 从内存存储迁移

如果你之前使用纯内存存储，现在可以无缝启用持久化：

**之前**：
```python
gateway = GatewayServer(agent)
```

**现在**：
```python
# 自动使用 SQLite（默认路径）
gateway = GatewayServer(agent)

# 或自定义路径
gateway = GatewayServer(agent, storage_path="./data/sessions.db")

# 启动时初始化
await gateway.startup()
```

**无需修改其他代码！**

---

## 故障排除

### 问题 1：数据库文件权限错误

**错误**：`PermissionError: [Errno 13] Permission denied: './data/sessions.db'`

**解决**：
```bash
# 确保数据目录存在并可写
mkdir -p ./data
chmod 755 ./data

# Windows
mkdir data
```

### 问题 2：数据库锁定

**错误**：`sqlite3.OperationalError: database is locked`

**解决**：
- SQLite 自动处理并发读取
- 写操作会排队等待
- 如果问题持续，检查是否有多个进程同时写入

### 问题 3：数据库损坏

**错误**：`DatabaseError: database disk image is malformed`

**解决**：
```bash
# SQLite 内置修复
sqlite3 sessions.db "PRAGMA integrity_check;"
sqlite3 sessions.db "VACUUM;"

# 或重新初始化
rm sessions.db  # 删除损坏的数据库
# 重启 Gateway 会自动创建新的
```

---

## 监控和维护

### 查看数据库大小

```bash
# Linux/Mac
du -h ./data/sessions.db

# Windows
dir data\sessions.db
```

### 数据库维护

```bash
# 打开数据库
sqlite3 ./data/sessions.db

# 查看表大小
SELECT
    'sessions' AS table_name,
    COUNT(*) AS row_count
FROM sessions
UNION ALL
SELECT
    'messages' AS table_name,
    COUNT(*) AS row_count
FROM messages;

# 退出
.quit
```

### 备份数据库

```bash
# 简单复制
cp ./data/sessions.db ./data/sessions.db.backup

# 或使用 SQLite 导出
sqlite3 ./data/sessions.db ".dump" > backup.sql
```

---

## 后续计划

### Phase 1 完成 ✅

- ✅ SQLite 存储
- ✅ 会话持久化
- ✅ 自动保存和恢复

### Phase 2 规划中

- [ ] PostgreSQL 支持（生产环境）
- [ ] Redis 缓存层
- [ ] 会话搜索
- [ ] 会话导出/导入

---

## 相关文档

- **[WEBSOCKET_GATEWAY.md](./WEBSOCKET_GATEWAY.md)** - Gateway 使用指南
- **[MOLTBOT_INSPRIED_ROADMAP.md](./MOLTBOT_INSPRIED_ROADMAP.md)** - 完整改进路线图

---

**完成时间**: 2026-01-28
**测试状态**: ✅ 15/15 通过
**向后兼容**: ✅ 完全兼容
**生产就绪**: ✅ 可用于生产环境（单机部署）
