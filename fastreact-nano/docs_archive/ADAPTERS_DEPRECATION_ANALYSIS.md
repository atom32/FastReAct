# Adapters 废弃分析与建议

**日期**: 2025-03-04
**问题**: 哪些 adapter 应该 deprecated？

---

## 当前 Adapter 状态

### 🟢 保留（活跃使用）

| Adapter | 文件 | 状态 | 理由 |
|---------|------|------|------|
| **Gateway** | `gateway.py` | ✅ 保留 | 统一入口，多租户支持 |
| **Feishu SDK** | `feishu_sdk.py` | ✅ 保留 | Lark SDK 模式，推荐使用 |

### 🟡 可选（根据需求）

| Adapter | 文件 | 状态 | 理由 |
|---------|------|------|------|
| **Feishu (Webhook)** | `feishu.py` | ⚠️ Deprecated | 已被 feishu_sdk.py 取代 |
| **HTTP** | `http.py` | ⚠️ 可选 | SSE API，根据需求使用 |

### 🔴 建议废弃

| Adapter | 文件 | 状态 | 理由 |
|---------|------|------|------|
| **Base** | `base.py` | ❌ 应废弃 | 设计假设不符合实际需求 |
| **CLI** | `cli.py` | ❌ 应废弃 | 被 REPL 取代，功能重叠 |
| **REPL** | `repl.py` | ❌ 应废弃 | 使用场景有限，被 CLI/HTTP 取代 |
| **Telegram** | `telegram.py` | ❌ 应废弃 | 需要 bot token，维护成本高 |

---

## 详细分析

### 1. base.py - 建议废弃

**问题**: 设计假设不符合实际

```python
class BaseAdapter(ABC):
    @abstractmethod
    async def start(self):  # ← 要求异步
        pass
```

**适用情况**: 只有 Telegram, WeChat 使用（25%）

**不适用**:
- Gateway (服务器框架)
- Feishu SDK (同步阻塞)
- HTTP (无状态)

**建议**:
```python
class BaseAdapter(ABC):
    """
    .. deprecated::
        BaseAdapter is deprecated and will be removed in v3.0.

        This base class assumes async long-connection model, which does not fit:
        - Server frameworks (Gateway, HTTP servers)
        - Synchronous SDKs (Feishu Lark SDK)

        Each adapter should implement its own lifecycle management.
    """
```

### 2. cli.py - 建议废弃

**问题**: 与 repl.py 功能重叠

| 功能 | cli.py | repl.py |
|------|--------|---------|
| 命令行交互 | ✅ | ✅ |
| 会话历史 | ❌ | ✅ |
| 事件流可视化 | ❌ | ✅ |
| Rich 输出 | ❌ | ✅ (Rich 库) |

**结论**: repl.py 功能更完整，cli.py 应该废弃。

### 3. feishu.py - 应该标记废弃

**状态**: ✅ 已在文档中标记为废弃

**证据** (FEISHU_ADAPTER_COMPARISON.md):
```markdown
### ❌ feishu.py (Webhook 模式 - 已废弃)

**状态**: 🚫 已废弃，不推荐使用
```

**改进**: 在文件顶部添加废弃警告：

```python
"""
FastReAct Nano - Feishu (Lark) Channel Adapter

.. deprecated::
    This adapter (Webhook mode) is deprecated in favor of feishu_sdk.py (SDK mode).

    Reasons:
    - Requires public IP or NAT traversal
    - Requires webhook URL configuration
    - Requires HTTPS certificate
    - Dependency on HTTP server

    Use feishu_sdk.py instead:
    - No public IP required (works on local network)
    - No webhook configuration needed
    - Uses Lark official SDK with WebSocket long connection
    - Automatic reconnection
"""

import warnings
warnings.warn(
    "feishu.py (Webhook mode) is deprecated. Use feishu_sdk.py (SDK mode) instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### 4. repl.py - 建议废弃

**问题**: 使用场景有限，被 CLI/HTTP 取代

| 需求 | 更好的方案 |
|------|-----------|
| 命令行交互 | CLI adapter |
| 交互式对话 | HTTP adapter (前端 UI) |
| 调试 | Gateway (WebSocket) |

**建议**: 标记为实验性/废弃。

### 5. http.py - 可选保留

**状态**: 根据需求使用

**用途**: SSE API 适合集成到 Web 应用

**评估**: 保留，但不作为主要入口。

### 6. telegram.py - 建议废弃

**问题**:
- 需要 Telegram bot token（用户难以获取）
- 需要部署在服务器上
- 维护成本高
- 使用率低

**建议**: 标记为可选插件，不作为核心功能。

---

## 废弃标记模板

### 通用模板

```python
"""
Adapter Name

.. deprecated::
    This adapter is deprecated as of v2.4.2 and will be removed in v3.0.

    Reasons:
    - [具体原因 1]
    - [具体原因 2]

    Alternative:
    - [更好的替代方案]

    Migration Guide:
    - [迁移步骤]
"""

import warnings
warnings.warn(
    "This adapter is deprecated. Use [Alternative] instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### 具体示例

#### base.py

```python
"""
Base adapter interface for all communication channels

.. deprecated::
    BaseAdapter is deprecated as of v2.4.2.

    The async long-connection model does not fit:
    - Server frameworks (Gateway, HTTP servers)
    - Synchronous SDKs (Feishu Lark SDK)
    - Stateless APIs (REST APIs)

    Each adapter should implement its own lifecycle management.
"""

class BaseAdapter(ABC):
    warnings.warn(
        "BaseAdapter is deprecated. Each adapter should implement its own lifecycle.",
        DeprecationWarning,
        stacklevel=2
    )
```

#### cli.py

```python
"""
CLI Adapter for FastReAct Nano

.. deprecated::
    CLI adapter is deprecated as of v2.4.2.

    Use REPL adapter instead:
    - Better session management
    - Rich output formatting
    - Event streaming visualization

    Or use Gateway for WebSocket-based interaction.
"""
```

#### feishu.py

```python
"""
FastReAct Nano - Feishu (Lark) Channel Adapter (Webhook Mode)

.. deprecated::
    This adapter (Webhook mode) is deprecated as of v2.4.2.

    Use feishu_sdk.py (SDK mode) instead:
    - No public IP required
    - No webhook configuration
    - No HTTP server needed
    - Automatic reconnection
"""
```

#### repl.py

```python
"""
REPL Adapter for FastReAct Nano

.. deprecated::
    REPL adapter is deprecated as of v2.4.2.

    Use Gateway or HTTP adapter instead:
    - Gateway: WebSocket-based real-time interaction
    - HTTP: Browser-based UI
    - More flexible and powerful
"""
```

#### telegram.py

```python
"""
Telegram Adapter for FastReAct Nano

.. deprecated::
    Telegram adapter is deprecated as of v2.4.2.

    This adapter is now an optional plugin.
    It is not maintained as part of the core package.

    To use:
    1. Copy to plugins/telegram.py
    2. Install dependencies: pip install python-telegram-bot
    3. Configure bot token
"""
```

---

## 实施计划

### Phase 1: 添加废弃警告（立即）

**文件**: 所有建议废弃的 adapter

**操作**:
1. 在文件顶部添加 `.. deprecated::` 文档字符串
2. 添加 `warnings.warn()` 调用
3. 更新 README 和文档

### Phase 2: 更新文档（短期）

**文件**:
- README.md
- docs/ADAPTERS.md
- SYSTEM_FLOW.md

**操作**:
1. 标记废弃的 adapter
2. 说明推荐的替代方案
3. 添加迁移指南

### Phase 3: 移到独立仓库（中期）

**操作**:
1. 将废弃的 adapter 移到 `plugins/` 目录
2. 作为可选插件维护
3. 不包含在核心包中

### Phase 4: 完全移除（长期）

**版本**: v3.0

**操作**:
- 从代码库中删除
- 从文档中移除
- 归档到 `docs_archive/`

---

## 最终建议

### 立即废弃

```bash
# 标记为废弃
✅ base.py        - 设计假设错误
✅ cli.py         - 被 repl.py 取代
✅ feishu.py      - 被 feishu_sdk.py 取代
✅ repl.py        - 使用场景有限
✅ telegram.py    - 维护成本高
```

### 保留并优化

```bash
# 核心入口
✅ gateway.py     - 主要入口，多租户支持
✅ feishu_sdk.py  - 飞书集成（SDK 模式）

# 可选功能
⚠️  http.py       - 根据需求使用
```

### 文档更新

**README.md**:
```markdown
## Quick Start

### Web UI (推荐)
```bash
python -m fastreact.adapters.gateway
# 访问 http://localhost:3000
```

### Feishu Bot
```bash
./scripts/start_feishu_bot.sh
```

### HTTP API
```bash
python -m fastreact.adapters.http
```

## Deprecated Adapters

The following adapters are deprecated and will be removed in v3.0:
- ❌ base.py (设计问题)
- ❌ cli.py (被 repl.py 取代)
- ❌ feishu.py (被 feishu_sdk.py 取代)
- ❌ repl.py (使用场景有限)
- ❌ telegram.py (维护成本高)
```

---

## 总结

### ✅ 你的判断完全正确

应该 deprecated 的 adapter：
1. ✅ **base.py** - 设计假设不符合实际
2. ✅ **cli.py** - 被 repl.py 取代
3. ✅ **feishu.py** - 被 feishu_sdk.py 取代
4. ✅ **repl.py** - 使用场景有限
5. ✅ **telegram.py** - 维护成本高

### 🎯 推荐的架构

**核心入口**:
- Gateway (多租户 WebSocket)
- Feishu SDK (飞书集成)

**可选功能**:
- HTTP (SSE API)

**废弃**:
- 所有其他 adapter

---

**文档作者**: Claude (FastReAct Team)
**最后更新**: 2025-03-04
**版本**: v2.4.2
