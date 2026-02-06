# Context Window 配置对比与说明

> 更新日期: 2025-02-01

## 问题发现

对比 Moltbot 和 FastReAct 的配置，发现 FastReAct 的 token 预算设置过于保守。

---

## Moltbot 配置参考

### 不同模型的 Context Window

| 模型 | Context Window | Max Tokens | 预留 Token |
|------|----------------|------------|------------|
| MiniMax | **200,000** | 8,192 | 20,000 |
| Moonshot (Kimi) | **256,000** | 8,192 | 20,000 |
| Kimi Code | **262,144** | 32,768 | 20,000 |
| Qwen | **128,000** | 8,192 | 20,000 |
| Ollama | **128,000** | 8,192 | 20,000 |

### 关键配置

```typescript
// 硬性限制
CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000    // 最小值
CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000  // 警告阈值

// 默认预留
DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR = 20_000

// 压缩比例
BASE_CHUNK_RATIO = 0.4    // 40% for chunks
MIN_CHUNK_RATIO = 0.15    // 15% minimum
SAFETY_MARGIN = 1.2       // 20% buffer
```

---

## FastReAct 配置变更

### 修改前（过于保守）

| 配置项 | 旧值 | 说明 |
|--------|------|------|
| `max_history_messages` | 50 | 消息数量限制 |
| `max_history_tokens` | 4,000 | **仅 6.25%** 的 64k window |
| `reserve_tokens` | 2,048 | 预留给响应 |
| `system_prompt_tokens` | 1,000 | 系统 prompt 预估 |
| GPT-4 context window | 8,192 | **过时**（旧版 GPT-4） |

**问题**:
- 只用了 6.25% 的 context window 给历史消息
- GPT-4 配置过时（GPT-4o/GPT-4-turbo 都是 128k）
- 与 Moltbot 相比太保守

### 修改后（合理配置）

| 配置项 | 新值 | 变化 | 说明 |
|--------|------|------|------|
| `max_history_messages` | 200 | **4x** | 支持更长对话 |
| `max_history_tokens` | 24,000 | **6x** | **37.5%** 的 64k window |
| `reserve_tokens` | 12,000 | **6x** | 预留足够空间给响应 |
| `system_prompt_tokens` | 2,000 | **2x** | 更复杂的系统 prompt |
| GPT-4o context window | 128,000 | - | 更新到最新模型 |
| Memory Flush 软阈值 | 40,000 | - | 适应更大 context |
| Memory Flush 硬阈值 | 50,000 | - | 适应更大 context |

---

## Token 预算分析（以 DeepSeek V3 为例）

### 修改前

```
Context Window:  64,000 tokens
─────────────────────────────────────
History:          4,000 (6.25%)  ← 太少
System:           1,000 (1.56%)
Reserve:          2,048 (3.20%)  ← 不够
Response (max):   8,192 (12.8%)
─────────────────────────────────────
Used:            15,240 (23.8%)
Unused:          48,760 (76.2%)  ← 浪费！
```

### 修改后

```
Context Window:  64,000 tokens
─────────────────────────────────────
History:         24,000 (37.5%)  ← 合理
System:           2,000 (3.125%)
Reserve:         12,000 (18.75%) ← 充足
Query:              ~500 (0.8%)
Response (max):   8,192 (12.8%)
─────────────────────────────────────
Used:            46,692 (73.0%)
Unused:          17,308 (27.0%)  ← 合理余量
```

**利用率提升**: 23.8% → **73.0%** (+207%)

---

## 不同模型的推荐配置

### 128k Context Window (GPT-4o, Claude 3.5 Sonnet, etc.)

```json
{
  "context": {
    "max_history_messages": 400,
    "max_history_tokens": 50000,
    "reserve_tokens": 25000,
    "system_prompt_tokens": 3000,
    "memory_flush": {
      "soft_threshold_tokens": 80000,
      "hard_threshold_tokens": 90000
    }
  }
}
```

**预算分配**:
- History: 50,000 (39%)
- Reserve: 25,000 (19.5%)
- System: 3,000 (2.3%)
- Response: ~16,000 (12.5%)
- **Total**: ~94,000 (73.5%)

### 200k Context Window (Claude 3.5 Sonnet, o1, etc.)

```json
{
  "context": {
    "max_history_messages": 600,
    "max_history_tokens": 80000,
    "reserve_tokens": 40000,
    "system_prompt_tokens": 4000,
    "memory_flush": {
      "soft_threshold_tokens": 130000,
      "hard_threshold_tokens": 150000
    }
  }
}
```

### 256k Context Window (Kimi, Moonshot, etc.)

```json
{
  "context": {
    "max_history_messages": 800,
    "max_history_tokens": 100000,
    "reserve_tokens": 50000,
    "system_prompt_tokens": 5000,
    "memory_flush": {
      "soft_threshold_tokens": 170000,
      "hard_threshold_tokens": 190000
    }
  }
}
```

---

## 配置原则总结

### 1. 按比例分配

Moltbot 的经验:
- **History**: 30-50% of context window
- **Reserve**: 15-25% of context window
- **System**: 2-5% of context window
- **Response**: 10-15% of context window (max_tokens)

### 2. 动态调整

根据不同模型的 context window 按比例调整，不要用固定值。

### 3. 安全边际

- **Safety Margin**: 1.2 (20% buffer)
- 避免顶格使用 context window

### 4. Memory Flush 阈值

```python
soft_threshold = context_window * 0.6  # 60% 时触发
hard_threshold = context_window * 0.75 # 75% 时强制
```

---

## 更新文件清单

- [x] `config.json` - 更新默认配置
- [x] `src/fastreact/context/config.py` - 更新默认值和模型映射
- [x] 添加主流模型的 context window 映射

---

## 参考资源

- Moltbot: `D:\moltbot\src\agents\pi-settings.ts`
- Moltbot: `D:\moltbot\src\agents\compaction.ts`
- OpenAI Models: https://platform.openai.com/docs/models
- Anthropic Models: https://docs.anthropic.com/en/docs/about-claude/models

---

**最后更新**: 2025-02-01
**维护者**: FastReAct Team
