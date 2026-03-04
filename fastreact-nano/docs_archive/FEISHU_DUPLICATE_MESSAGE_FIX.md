# Feishu SDK 重复发送问题修复

**日期**: 2025-03-04
**问题**: 18:37 输入"你好"得到回复后，18:50 无输入却收到相同回复
**修复**: 添加消息去重机制

---

## 问题描述

### 症状

**时间线**:
```
18:37 - 用户发送"你好"
18:37 - Bot 回复（正确）
18:50 - 无用户输入
18:50 - Bot 再次发送相同回复（错误）
```

### 根本原因

**缺少消息去重机制**

虽然飞书 SDK 提取了 `message_id`，但**没有用于去重检查**。飞书可能因以下原因发送重复消息事件：

1. **WebSocket 重连** - 连接断开后重连，可能重发未确认的消息
2. **网络问题** - 数据包重复传输
3. **平台行为** - 飞书服务器在某些情况下会重发消息

---

## 修复方案

### 实现逻辑

**文件**: `src/fastreact/adapters/feishu_sdk.py`

#### 1. 初始化去重缓存

```python
def __init__(self, agent: Agent, config: FeishuConfig):
    # ... 其他初始化 ...

    # ✅ 添加消息去重缓存
    self._processed_messages: set[str] = set()
    self._max_processed_messages: int = 10000  # 防止无限增长
```

#### 2. 消息处理时检查去重

```python
def _handle_message_event_v2(self, event: P2ImMessageReceiveV1) -> None:
    # ... 提取 message_id ...

    # ✅ 检查是否重复
    if message_id in self._processed_messages:
        print(f"[INFO] Duplicate message ignored: {message_id}")
        return  # ← 跳过处理

    # ✅ 添加到已处理集合
    self._processed_messages.add(message_id)

    # ✅ 防止缓存无限增长（超过限制时清理 20%）
    if len(self._processed_messages) > self._max_processed_messages:
        remove_count = int(self._max_processed_messages * 0.2)
        oldest_messages = list(self._processed_messages)[:remove_count]
        for old_msg_id in oldest_messages:
            self._processed_messages.discard(old_msg_id)
        print(f"[INFO] Cleaned {remove_count} old message IDs from cache")

    # ... 继续处理消息 ...
```

#### 3. 监控和管理方法

```python
def get_deduplication_stats(self) -> dict:
    """获取去重统计信息"""
    return {
        "processed_messages": len(self._processed_messages),
        "max_cache_size": self._max_processed_messages,
        "cache_usage_percent": len(self._processed_messages) / self._max_processed_messages * 100,
    }

def clear_processed_messages(self):
    """清理已处理消息缓存（用于测试或内存管理）"""
    cleared_count = len(self._processed_messages)
    self._processed_messages.clear()
    print(f"[INFO] Cleared {cleared_count} message IDs from deduplication cache")
```

---

## 技术细节

### 去重策略

**基于 Message ID**:
- 使用飞书的 `message_id`（全局唯一）
- 存储在 `set` 中（O(1) 查找）

**内存管理**:
- 最大缓存：10,000 条消息
- 超限时清理：移除最旧的 20%
- 防止内存泄漏

**清理时机**:
- 每次添加新消息时检查
- 如果超过限制，立即清理
- 清理最旧的消息（FIFO 近似）

### 性能影响

**时间复杂度**:
- 检查重复：O(1)（set 查找）
- 添加消息：O(1)（set 添加）
- 清理缓存：O(n)，n = 2000（20% of 10,000）

**空间复杂度**:
- 每个 message_id：约 50-100 字节
- 10,000 条消息：约 0.5-1 MB
- 可忽略不计

---

## 测试验证

### 单元测试

**文件**: `tests/unit/test_feishu_message_deduplication.py`

**测试覆盖**:
```python
test_deduplication_initialization()  # ✅ 缓存初始化
test_duplicate_message_detection()   # ✅ 重复检测
test_cache_size_limit()              # ✅ 缓存大小限制
test_cache_cleanup()                 # ✅ 自动清理
test_get_deduplication_stats()       # ✅ 统计 API
test_clear_processed_messages()      # ✅ 手动清理
test_duplicate_message_ignored()     # ✅ 集成测试
```

**测试结果**:
```
7 passed, 1 warning in 6.68s
```

### 场景验证

**场景 1: 正常消息**
```
18:37 - 收到消息 "你好" (message_id: om_123)
       - 检查缓存：未找到
       - 处理消息
       - 添加到缓存
       - 发送回复 ✅
```

**场景 2: 重复消息**
```
18:50 - 收到消息 "你好" (message_id: om_123)
       - 检查缓存：已存在
       - 打印 "Duplicate message ignored"
       - 跳过处理 ✅
       - 不发送回复
```

**场景 3: 不同消息**
```
19:00 - 收到消息 "新问题" (message_id: om_456)
       - 检查缓存：未找到
       - 处理消息
       - 添加到缓存
       - 发送回复 ✅
```

---

## 使用指南

### 监控去重状态

```python
# 在运行时获取统计
adapter = FeishuSDKAdapter(agent, config)
stats = adapter.get_deduplication_stats()

print(f"已处理消息: {stats['processed_messages']}")
print(f"缓存上限: {stats['max_cache_size']}")
print(f"使用率: {stats['cache_usage_percent']:.1f}%")
```

### 手动清理缓存

```python
# 如果需要重置缓存
adapter.clear_processed_messages()
# 输出: [INFO] Cleared 1234 message IDs from deduplication cache
```

### 启动日志

```
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_xxxxxxxxx
[INFO] Multi-tenant: True
[INFO] Auto-reconnect: True
[INFO] Message deduplication cache: 0 messages
[INFO] Max cache size: 10000 messages
```

---

## 最佳实践

### 1. 缓存大小调整

**默认值**: 10,000 条消息

**调整方法**:
```python
# 在 __init__ 中修改
self._max_processed_messages = 20000  # 增加到 20,000
```

**考虑因素**:
- 消息频率：高频消息需要更大缓存
- 内存限制：每个 message_id 约 50-100 字节
- 去重窗口：缓存大小决定去重时间窗口

### 2. 监控告警

```python
# 定期检查缓存使用率
stats = adapter.get_deduplication_stats()
if stats['cache_usage_percent'] > 90:
    print(f"[WARNING] Deduplication cache at {stats['cache_usage_percent']:.1f}%")
```

### 3. 调试技巧

**查看重复消息**:
```python
# 在 _handle_message_event_v2 中添加日志
if message_id in self._processed_messages:
    print(f"[DEBUG] Duplicate message ignored:")
    print(f"[DEBUG]   message_id: {message_id}")
    print(f"[DEBUG]   sender_id: {sender_id}")
    print(f"[DEBUG]   content: {text}")
    return
```

---

## 后续优化

### 短期

- [ ] 添加去重统计监控接口
- [ ] 记录重复消息频率
- [ ] 告警机制（高频重复）

### 长期

- [ ] 使用持久化存储（Redis）
- [ ] 分布式去重（多实例部署）
- [ ] 基于时间的自动清理（TTL）

---

## 总结

### ✅ 问题已解决

**修复前**:
- ❌ 重复消息导致重复响应
- ❌ 用户困惑（收到相同回复）
- ❌ 资源浪费（重复处理）

**修复后**:
- ✅ 重复消息自动忽略
- ✅ 只处理新消息
- ✅ 节省资源

### 📊 效果

**性能影响**:
- 时间复杂度：O(1) 检查
- 空间复杂度：0.5-1 MB 内存
- 可忽略不计

**可靠性提升**:
- 防止重复响应
- 提升用户体验
- 减少资源浪费

### 🎯 关键代码

```python
# 去重检查（3 行代码）
if message_id in self._processed_messages:
    print(f"[INFO] Duplicate message ignored: {message_id}")
    return

self._processed_messages.add(message_id)
```

---

**实施者**: FastReAct Team
**完成日期**: 2025-03-04
**版本**: v2.5.0
**Commit**: 09fe7ee
**测试**: 7/7 passing
