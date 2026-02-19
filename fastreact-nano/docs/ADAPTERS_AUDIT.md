# Adapters Audit Report

**Date**: 2025-02-19
**Location**: `src/fastreact/adapters/`
**Status**: 🔴 Critical Issues Found

---

## Overview

Adapters 目录包含 9 个 adapter 文件，用于将 FastReAct Agent 集成到各种外设系统。

---

## Adapter List

| Adapter | Purpose | Multi-tenant Support | Status |
|---------|---------|---------------------|--------|
| `gateway.py` | WebSocket gateway for Next.js frontend | ❌ Partial | 🔴 Needs Fix |
| `feishu.py` | Feishu webhook bot | ✅ Full | 🟢 Good |
| `feishu_sdk.py` | Feishu WebSocket (SDK) | ✅ Full | 🟢 Good |
| `cli.py` | Command-line interface | ❌ None | 🟡 N/A |
| `cli_enhanced.py` | Enhanced CLI (unused?) | ❌ None | 🟡 Unknown |
| `web.py` | Streamlit web UI | ❌ None | 🟡 N/A |
| `http.py` | HTTP REST API | ❌ None | 🟡 Unknown |
| `repl.py` | Interactive REPL | ❌ None | 🟡 N/A |
| `__init__.py` | Module exports | N/A | 🟢 Good |

---

## Critical Issue: Gateway Multi-tenant Support

### Current State (gateway.py)

```python
class Session:
    def __init__(self, session_id, websocket, ...):
        # ...
        self.agent = Agent(
            config=config,
            multitenant=True,              # ✅ Parameter set
            base_workspace=workspace_path,   # ❌ But shared!
        )
```

### Problems

1. **Shared Workspace**
   ```python
   workspace_path = base_workspace or Path.cwd() / "workspace"
   # All sessions use the SAME workspace directory
   # Result: No user isolation
   ```

2. **No User Key Extraction**
   ```python
   # Gateway NEVER passes user_key to agent.run_event_stream()
   await self.agent.run_event_stream(
       query,
       skills=skills,
       session_id=self.session_id,
       # ❌ Missing: user_key parameter
   )
   ```

3. **MultiTenantManager Not Used**
   ```python
   # Agent creates MultiTenantManager
   self._multitenant = MultiTenantManager(workspace_path)
   # But Gateway never calls:
   # user_context = self._multitenant.get_user_context(user_key)
   ```

### What Real Multi-tenant Should Look Like

```python
# ✅ CORRECT: Feishu adapters do it right
class FeishuSDKAdapter:
    def __init__(self, agent, config):
        self._multitenant = MultiTenantManager(workspace)

    async def _handle_message(self, event):
        # Extract user_key from Feishu event
        user_key = f"feishu:{event.sender_id}"

        # ✅ Pass user_key to agent
        async for evt in self.agent.run_event_stream(
            content,
            user_key=user_key,  # ← User isolation!
        ):
            ...
```

---

## Adapter Details

### 1. gateway.py - WebSocket Gateway

**Purpose**: Real-time WebSocket communication with Next.js frontend

**Multi-tenant Status**: ❌ **BROKEN** (参数设置了但没起作用)

**Issues**:
1. 所有 Session 共享同一个 workspace
2. 没有传入 `user_key` 参数
3. 没有从 WebSocket 提取用户标识
4. MultiTenantManager 创建了但没用上

**Fix Required**:
```python
# Option A: Extract user from JWT token
from fastapi_websocket import WebSocket

class Session:
    async def _handle_message(self, message: dict):
        # Extract user from token
        token = self.websocket.query_params.get("token")
        user_key = validate_token(token)  # "feishu:user123"

        # Pass to agent
        async for event in self.agent.run_event_stream(
            query,
            user_key=user_key,  # ← Add this!
        ):
            ...

# Option B: Use session_id as user identifier
user_key = f"ws:{self.session_id}"
```

---

### 2. feishu.py - Feishu Webhook Bot

**Purpose**: Feishu webhook event handling

**Multi-tenant Status**: ✅ **CORRECT**

**Code**:
```python
if config.enable_multitenant:
    workspace = config.base_workspace or Path.cwd() / "workspace"
    self._multitenant = MultiTenantManager(workspace)

# Later:
user_key = f"feishu:{event.sender_id}"
async for evt in self.agent.run_event_stream(
    content,
    user_key=user_key,  # ✅ User isolation!
):
```

**Quality**: 🟢 Excellent

---

### 3. feishu_sdk.py - Feishu WebSocket (SDK)

**Purpose**: Feishu long-polling with official SDK

**Multi-tenant Status**: ✅ **CORRECT**

**Code**:
```python
if config.enable_multitenant:
    workspace = config.base_workspace or Path.cwd() / "workspace"
    self._multitenant = MultiTenantManager(workspace)

# Later:
user_key = f"feishu:{sender_id}"
async for evt in self.agent.run_event_stream(
    message.content,
    user_key=user_key,  # ✅ User isolation!
):
```

**Quality**: 🟢 Excellent

---

### 4. cli.py - Command-Line Interface

**Purpose**: Interactive CLI with Rich UI

**Multi-tenant Status**: N/A (Single-user tool)

**Code**:
```python
async for event in agent.run_event_stream(
    query,
    skills=skills,
    session_id=session_id
    # No user_key - CLI is single-user
):
```

**Quality**: 🟢 Good (CLI不需要多租户)

---

### 5. cli_enhanced.py - Enhanced CLI

**Purpose**: Unclear - 可能是未使用的代码

**Status**: 🟡 **NEEDS REVIEW**

**Action**: 审查这个文件是否还在使用

---

### 6. web.py - Streamlit Web UI

**Purpose**: Streamlit-based web interface

**Multi-tenant Status**: N/A (可能需要添加)

**Action**: 审计是否需要多租户支持

---

### 7. http.py - HTTP REST API

**Purpose**: HTTP REST endpoint for agent queries

**Multi-tenant Status**: ❌ **NO SUPPORT**

**Code**:
```python
@app.post("/query")
async def query_endpoint(request: Request):
    data = await request.json()
    result = await agent.run(query)
    # No user_key, no isolation
```

**Action**: 如果用于生产，需要添加多租户

---

### 8. repl.py - Interactive REPL

**Purpose**: Python interactive shell integration

**Multi-tenant Status**: N/A (Development tool)

**Quality**: 🟢 Good (REPL不需要多租户)

---

## Architecture Comparison

### ✅ CORRECT: Feishu Adapters

```
Feishu Event (sender_id: "ou_xxx")
    ↓
Extract user_key = "feishu:ou_xxx"
    ↓
agent.run_event_stream(query, user_key=user_key)
    ↓
MultiTenantManager.get_user_context(user_key)
    ↓
Workspace: ./workspace/feishu:ou_xxx/
```

### ❌ WRONG: Gateway Adapter

```
WebSocket Connection (session_id: "uuid-123")
    ↓
agent.run_event_stream(query, session_id=session_id)
    ↓
(NO user_key!)
    ↓
Workspace: ./workspace/  ← 所有用户共享!
```

---

## Recommendations

### Priority 1: Fix Gateway Multi-tenant

**Option A: JWT Token Authentication**
```python
# Client sends: { "type": "auth", "token": "jwt..." }
# Gateway validates and extracts user_key
user_key = validate_jwt(token)
async for evt in agent.run_event_stream(query, user_key=user_key):
```

**Option B: Session-based User Extraction**
```python
# Use session_id prefix as user_key
user_key = f"ws:{self.session_id}"
async for evt in agent.run_event_stream(query, user_key=user_key):
```

**Option C: Disable Multi-tenant in Gateway**
```python
# If Gateway is single-user, don't enable multitenant
self.agent = Agent(
    config=config,
    multitenant=False,  # ← Disable
    base_workspace=None,
)
```

### Priority 2: Audit Unused Adapters

- `cli_enhanced.py` - 检查是否还在使用
- `web.py` - 确认是否需要维护
- `http.py` - 如果使用，需要添加认证

### Priority 3: Document Multi-tenant Strategy

创建 `docs/MULTITENANT_STRATEGY.md`：
- 哪些 adapter 需要多租户
- 如何正确使用 `user_key`
- workspace 隔离策略

---

## Test Verification

```bash
# Check workspace structure
ls -la ./workspace/

# Expected for multi-tenant:
# ./workspace/feishu:ou_user1/
# ./workspace/feishu:ou_user2/

# Current Gateway:
# ./workspace/  ← 所有文件混在一起
```

---

## Summary

| Issue | Severity | Status |
|-------|----------|--------|
| Gateway not truly multi-tenant | 🔴 Critical | ❌ Not Fixed |
| Feishu adapters correct | 🟢 Good | ✅ Verified |
| Unused files | 🟡 Medium | ⚠️ Needs Review |
| Documentation missing | 🟡 Medium | ⚠️ Needs Update |

---

## Action Items

### Immediate
- [ ] Fix Gateway multi-tenant support
- [ ] Decide: keep or remove `multitenant=True` in Gateway
- [ ] Update Gateway documentation

### Short-term
- [ ] Audit `cli_enhanced.py` - is it used?
- [ ] Audit `web.py` - deprecate or update?
- [ ] Audit `http.py` - add authentication if used

### Long-term
- [ ] Create multi-tenant architecture document
- [ ] Add multi-tenant tests
- [ ] Implement JWT auth for Gateway

---

**Status**: 🔴 **Gateway Multi-tenant is BROKEN**
**Recommendation**: Either fix it or disable `multitenant=True`
**Priority**: 🔴 **High** (Misleading configuration)

---

**Maintainer**: Claude Code + User
**Date**: 2025-02-19
