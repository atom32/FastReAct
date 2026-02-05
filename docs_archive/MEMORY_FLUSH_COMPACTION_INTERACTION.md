# Memory Flush 和 Progressive Compaction 配合机制详解

## 概述

Memory Flush 和 Progressive Compaction 是**分层防御**的关系，它们在不同阶段触发，使用不同的压缩策略，共同管理上下文窗口。

---

## 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│  每次迭代开始（_build_messages_context）                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  计算 Token 总数     │
            │  system + history    │
            │  + query             │
            └──────────┬───────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Stage 1: Memory Flush      │
         │  检查点: 50000 tokens       │
         │  (soft_threshold)          │
         └──────────┬──────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
    total_tokens < 50000   total_tokens >= 50000
        │                       │
        │                       ▼
        │              ┌────────────────────┐
        │              │ 执行 Memory Flush  │
        │              │ - 总结旧消息       │
        │              │ - 保留关键信息     │
        │              │ - 压缩比 ~30%      │
        │              └────────┬───────────┘
        │                       │
        │                       ▼
        │              更新 history（已压缩）
        │                       │
        └───────────────────────┼─────────────────┐
                                    │                 │
                                    ▼                 ▼
                         ┌────────────────────┐  ┌──────────────────────┐
                         │  Stage 2:          │  │  Stage 2:            │
                         │  Progressive       │  │  Progressive         │
                         │  Compaction        │  │  Compaction         │
                         │  检查点: 50000     │  │  检查点: 50000      │
                         │  (trigger_threshold)│  │  (trigger_threshold) │
                         └────────┬───────────┘  └──────────┬───────────┘
                                  │                          │
                                  │          再次计算 token    │
                                  │          （使用更新后的   │
                                  │          history）         │
                                  │                          │
                                  └──────────┬───────────────┘
                                             │
                                ┌────────────┴────────────┐
                                │                         │
                          total_tokens < 50000      total_tokens >= 50000
                                │                         │
                                │                         ▼
                                │              ┌────────────────────┐
                                │              │ 执行 Progressive   │
                                │              │ Compaction         │
                                │              │ - 多层压缩         │
                                │              │ - Level 1-3        │
                                │              │ - 压缩比 5%-50%     │
                                │              └────────┬───────────┘
                                │                       │
                                └───────────────────────┼─────────────────┐
                                                        │                 │
                                                        ▼                 ▼
                                              ┌────────────────┐  ┌────────────────┐
                                              │ 使用压缩后的  │  │ 继续正常处理   │
                                              │ history        │  │               │
                                              └────────────────┘  └────────────────┘
```

---

## 关键差异

| 特性 | Memory Flush | Progressive Compaction |
|------|-------------|----------------------|
| **触发阈值** | 50000 tokens (soft) | 50000 tokens (trigger) |
| **触发条件** | `total_tokens >= soft_trigger` | `total_tokens >= trigger_threshold` |
| **压缩策略** | 总结旧消息，保留结构 | 多层压缩，激进缩减 |
| **压缩级别** | 单一总结（~30%） | Level 1-3（5%-50%） |
| **执行时机** | Stage 1（先执行） | Stage 2（后执行） |
| **协同关系** | 第一道防线 | 第二道防线（更激进） |

---

## 配合场景

### 场景 1：对话正常增长（< 50000 tokens）

```
初始: 45000 tokens
  ↓
Memory Flush: 不触发
Progressive Compaction: 不触发
结果: 继续正常对话
```

### 场景 2：对话超过软阈值（50000 tokens）

```
初始: 52000 tokens
  ↓
Memory Flush: 触发
  - 总结前 30 条消息
  - 压缩到 ~15600 tokens
  ↓
更新后: ~17600 tokens
  ↓
Progressive Compaction: 不触发（< 50000）
结果: 使用总结后的历史继续
```

### 场景 3：Memory Flush 后仍超阈值（极端情况）

```
初始: 60000 tokens
  ↓
Memory Flush: 触发
  - 总结旧消息
  - 压缩到 ~18000 tokens
  ↓
更新后: ~28000 tokens（仍然 >= 50000? 不对，这里有问题）
```

**等等！让我重新检查逻辑...**

看代码第 806-808 行：
```python
trigger_threshold = context_config.compaction.trigger_threshold_tokens
if total_tokens >= trigger_threshold:
```

**关键发现**：两个机制的触发阈值**相同**（都是 50000），但执行顺序不同：

1. **Memory Flush 先执行**
2. **Progressive Compaction 后执行**，但**重新计算 token 数**

所以实际配合是：

```
初始: 60000 tokens
  ↓
Stage 1: Memory Flush 检查
  60000 >= 50000 → 触发
  ↓
执行 Memory Flush
  压缩到 ~18000 tokens
  ↓
更新 history
  ↓
Stage 2: Progressive Compaction 检查
  重新计算: 18000 < 50000 → 不触发
  ↓
结果: 使用 Memory Flush 的结果
```

**那 Progressive Compaction 什么时候触发？**

看第 806-808 行的逻辑：
- Progressive Compaction 使用**相同的阈值**检查
- 但它是在 Memory Flush **之后**检查
- 所以只有当 Memory Flush **压缩后**仍然 >= 50000 时才会触发

这种情况很少见，除非：
- Memory Flush 失败
- 或者配置的阈值不同（比如 Compaction 的阈值更低）

---

## 实际建议配置

### 推荐配置（当前默认）

```json
"context": {
  "memory_flush": {
    "enabled": true,
    "soft_threshold_tokens": 50000,
    "hard_threshold_tokens": 55000
  },
  "compaction": {
    "enabled": false,  // 默认关闭
    "trigger_threshold_tokens": 50000
  }
}
```

**理由**：
- Memory Flush 已经足够处理大多数情况
- Progressive Compaction 更激进，适合极端长对话
- 默认关闭 Compaction，按需启用

### 激进配置（适合超长对话）

```json
"context": {
  "memory_flush": {
    "enabled": true,
    "soft_threshold_tokens": 40000,   // 更早触发
    "hard_threshold_tokens": 45000
  },
  "compaction": {
    "enabled": true,
    "trigger_threshold_tokens": 45000  // 比 Memory Flush 硬阈值低
  }
}
```

**配合效果**：
```
40000 tokens: Memory Flush 开始工作
45000 tokens: Memory Flush 强制执行
45000 tokens: Progressive Compaction 检查
           如果 Memory Flush 后仍 >= 45000，则触发
```

---

## 实际例子

### 例子 1：正常对话（Memory Flush 处理）

```
Iteration 1-10: 正常对话
  history_tokens: 30000

Iteration 11: 继续对话
  history_tokens: 52000 → Memory Flush 触发
  执行: 总结前 40 条消息
  结果: history_tokens = 18000

Iteration 12+: 继续正常对话
  history_tokens: 18000 + 新消息
```

### 例子 2：极端对话（需要 Progressive Compaction）

假设配置：
```json
"memory_flush": {
  "soft_threshold_tokens": 50000
},
"compaction": {
  "enabled": true,
  "trigger_threshold_tokens": 48000  // 比 Memory Flush 低！
}
```

执行流程：
```
Iteration N: 53000 tokens
  ↓
Memory Flush: 触发（53000 >= 50000）
  压缩到 ~20000 tokens
  ↓
Progressive Compaction: 检查
  重新计算: 20000 < 48000 → 不触发
  ↓
结果: 使用 Memory Flush 结果
```

**要让 Progressive Compaction 触发**，需要：
1. Memory Flush 失败或效果不佳
2. 或者配置 Compaction 阈值 < Memory Flush 阈值

---

## 代码逻辑详解

### Memory Flush 触发（engine.py: 748-793）

```python
# 1. 计算 token
total_tokens = system_tokens + history_tokens + query_tokens

# 2. 检查触发条件
if self._memory_flush.should_trigger(
    current_tokens=total_tokens,
    context_window=self._llm_config.context_window,
    iteration=iteration,
):
    # 3. 执行 flush
    flush_metadata, updated_history = await self._memory_flush.flush_and_update_context(...)

    # 4. 更新 history（重要！）
    history = updated_history
```

### Progressive Compaction 触发（engine.py: 796-871）

```python
# 1. 重新计算 token（使用更新后的 history！）
total_tokens = system_tokens + history_tokens + query_tokens

# 2. 检查触发条件
if total_tokens >= context_config.compaction.trigger_threshold_tokens:
    # 3. 计算压缩级别
    excess_tokens = total_tokens - trigger_threshold
    if excess_tokens > 20000:
        target_level = 3  # Ultra-compressed
    elif excess_tokens > 10000:
        target_level = 2  # Compressed
    else:
        target_level = 1  # Single summary

    # 4. 执行压缩
    compaction_result = await self._compaction.compact(...)

    # 5. 替换整个 history 为压缩结果
    history = [compacted_message]
```

---

## 关键点总结

1. **执行顺序**：Memory Flush → Progressive Compaction
2. **依赖关系**：Compaction 使用 Memory Flush **更新后**的 history
3. **触发条件**：使用**相同阈值**检查，但分阶段
4. **压缩策略**：
   - Memory Flush: 保留结构，温和压缩（~30%）
   - Progressive Compaction: 激进压缩，可能完全替换历史（5%-50%）
5. **协同效果**：
   - Memory Flush 处理大部分情况
   - Progressive Compaction 处理极端情况（如果配置更低的阈值）

---

## 实际使用建议

### 对于大多数用户

**启用 Memory Flush，禁用 Progressive Compaction**：
```json
{
  "memory_flush": {"enabled": true},
  "compaction": {"enabled": false}
}
```

**理由**：
- Memory Flush 温和压缩，保留对话结构
- 适合大多数对话场景
- 总结质量高，信息损失小

### 对于超长对话场景

**同时启用两者，设置合理的阈值差**：
```json
{
  "memory_flush": {
    "enabled": true,
    "soft_threshold_tokens": 45000
  },
  "compaction": {
    "enabled": true,
    "trigger_threshold_tokens": 42000  // 比 Memory Flush 低
  }
}
```

**理由**：
- Memory Flush 处理中等长度对话
- Progressive Compaction 作为安全网，处理极端情况
- 阈值差确保两者不会同时触发

---

**结论**：Memory Flush 是主要机制，Progressive Compaction 是极端情况下的备用方案。两者通过分层阈值和执行顺序协同工作，确保上下文不会溢出。
