# Moltbot 研究与 FastReAct 改进方案

> 基于 Moltbot (https://github.com/moltbot/moltbot) 架构分析的详细改进方案

**创建时间**: 2026-01-28
**版本**: v1.0
**状态**: Phase 1 完成，Phase 2 规划中

---

## 目录

1. [Moltbot 架构核心要点](#1-moltbot-架构核心要点)
2. [FastReAct vs Moltbot 对比](#2-fastreact-vs-moltbot-对比)
3. [改进方案总览](#3-改进方案总览)
4. [P0 优先级改进](#4-p0-优先级改进)
5. [P1 优先级改进](#5-p1-优先级改进)
6. [P2 优先级改进](#6-p2-优先级改进)
7. [实施路线图](#7-实施路线图)
8. [架构决策记录](#8-架构决策记录)

---

## 1. Moltbot 架构核心要点

### 1.1 Gateway-Centric Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Messaging Channels                │
│  WhatsApp │ Telegram │ Slack │ Discord │ iMessage   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Gateway (Single Long-Lived Process)    │
│  • WebSocket Control Plane (ws://127.0.0.1:18789)  │
│  • Channel Connections Manager                     │
│  • Session Management                               │
│  • Event Bus (presence, health, agent events)       │
│  • Canvas Host (HTTP file server on port 18793)     │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
       ▼           ▼           ▼
  ┌────────┐  ┌──────┐  ┌──────────┐
  │Pi Agent│  │ CLI  │  │WebChat UI│
  │ (RPC)  │  │      │  │          │
  └────────┘  └──────┘  └──────────┘
```

**核心设计理念**：
- **单一控制平面** - Gateway 是所有连接的中心
- **WebSocket 通信协议** - 类型化的 JSON 协议
- **事件驱动** - 推送式更新，而非轮询
- **有状态会话** - 持久化存储 + 内存缓存

### 1.2 Wire Protocol 设计

**请求格式**：
```json
{
  "type": "req",
  "id": "unique-id",
  "method": "agent|send|health|node.invoke",
  "params": { /* method-specific */ }
}
```

**响应格式**：
```json
{
  "type": "res",
  "id": "unique-id",
  "ok": true/false,
  "payload": { /* response data */ }
}
```

**事件格式**：
```json
{
  "type": "event",
  "event": "agent|presence|tick|shutdown",
  "payload": { /* event data */ },
  "seq": 123,
  "stateVersion": 456
}
```

**关键特性**：
- ✅ **幂等性密钥** - 安全重试副作用操作
- ✅ **TypeBox schemas** - 协议类型定义和代码生成
- ✅ **JSON Schema 验证** - 所有入站帧验证
- ✅ **短期去重缓存** - 重放保护

### 1.3 安全模型

**多层安全**：
1. **Gateway 认证** - Token 或密码
2. **DM 配对** - 默认需要配对码
3. **白名单访问** - 显式批准
4. **会话沙箱** - Docker 容器隔离非主会话
5. **设备配对** - Node 需要显式批准
6. **Tailscale 集成** - 安全远程访问

**沙箱配置示例**：
```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "mode": "non-main",
        "allowlist": [
          "bash", "process", "read", "write",
          "sessions_list", "sessions_send"
        ],
        "denylist": [
          "browser", "canvas", "nodes", "cron"
        ]
      }
    }
  }
}
```

### 1.4 Node 系统

设备通过 **Node** 角色连接，暴露本地能力：

```json
{
  "role": "node",
  "client": {
    "id": "device-id",
    "displayName": "My iPhone",
    "deviceFamily": "ios",
    "mode": "node"
  },
  "caps": {
    "camera": true,
    "canvas": true,
    "screenRecording": true
  },
  "commands": [
    "canvas.push",
    "camera.snap",
    "screen.record",
    "location.get"
  ]
}
```

### 1.5 多智能体路由

**路由配置**：
```json
{
  "agents": {
    "routing": {
      "channels": {
        "whatsapp:+1234567890": "research-agent",
        "discord:guild-id:channel-id": "code-agent"
      },
      "patterns": {
        "research|analyze|report": "research-agent",
        "code|debug|api": "code-agent"
      }
    }
  }
}
```

**会话类型**：
- **Main Session** - 直接 DM，完整工具访问
- **Group Sessions** - 每个群组隔离，默认提及门控
- **Per-Agent Sessions** - 每个智能体独立会话上下文

---

## 2. FastReAct vs Moltbot 对比

### 2.1 功能对比矩阵

| 功能类别 | Moltbot | FastReAct (当前) | 差距 |
|---------|---------|-----------------|------|
| **核心架构** |
| WebSocket Gateway | ✅ | ✅ | 相似 |
| 多通道支持 | ✅ 50+ | ⚠️ 仅 WebChat | **重大** |
| 单一控制平面 | ✅ | ✅ | 相似 |
| 事件驱动协议 | ✅ | ⚠️ 基础 | 中等 |
| **会话管理** |
| 持久化会话 | ✅ SQLite/Redis | ✅ SQLite | 相似 |
| 多智能体会话 | ✅ | ✅ | 相似 |
| 会话隔离 | ✅ | ⚠️ 基础 | 中等 |
| **多智能体系统** |
| 智能体路由 | ✅ | ✅ | 相似 |
| 智能体通信 | ✅ sessions_* | ✅ | 相似 |
| 专用智能体 | ✅ | ✅ | 相似 |
| **工具与技能** |
| 工具注册表 | ✅ | ✅ | 相似 |
| 内置工具 | ✅ 20+ | ⚠️ 11 | 中等 |
| 技能系统 | ✅ | ❌ | **重大** |
| **安全** |
| DM 配对 | ✅ | ❌ | **重大** |
| 沙箱 | ✅ Docker | ❌ | **重大** |
| 认证 | ✅ Token/密码 | ❌ | **关键** |
| **DevOps** |
| 健康检查 | ✅ | ⚠️ 基础 | 中等 |
| 日志 | ✅ 结构化 | ✅ 结构化 | 相似 |
| 指标 | ✅ | ❌ | **重大** |

### 2.2 架构优势对比

**Moltbot 优势**：
1. **成熟度** - 生产就绪，60,000+ GitHub stars
2. **Gateway 协议** - 类型化协议与代码生成
3. **Node 系统** - 优雅的设备本地能力暴露
4. **安全** - 从第一天起就有的综合安全模型
5. **多平台** - 原生配套应用 (macOS/iOS/Android)

**FastReAct 优势**：
1. **简洁性** - 核心引擎 < 600 行 vs Moltbot 的复杂性
2. **纯 ReACT** - 专注于推理循环而非功能
3. **异步优先** - 从头开始用 asyncio 构建
4. **去重** - 请求去重（Moltbot 没有）
5. **学习友好** - 清晰的代码结构，适合教育

### 2.3 关键差异

| 方面 | Moltbot | FastReAct | 分析 |
|-----|---------|-----------|------|
| **设计哲学** | 功能全面、生产就绪 | 简洁优雅、教育价值 | 不同定位 |
| **协议** | 强类型、代码生成 | 简单 JSON | Moltbot 更健壮 |
| **存储** | 插拔式（SQLite/Redis） | SQLite | 相似 |
| **多智能体** | 路由 + 配对 | 路由 + 绑定 | FastReAct 更简单 |
| **安全** | 多层、默认安全 | 需添加 | FastReAct 需改进 |
| **部署** | Docker Compose | 灵活 | FastReAct 更轻量 |

---

## 3. 改进方案总览

### 3.1 设计原则

**保持 FastReAct 的优势**：
- ✅ 代码简洁性
- ✅ 纯 ReACT 专注
- ✅ 异步优先架构
- ✅ 教育价值

**采纳 Moltbot 的生产特性**：
- ✅ 类型化协议
- ✅ 安全机制
- ✅ 多通道支持
- ✅ 监控和指标

**策略**：**渐进式增强**，不破坏现有 API

### 3.2 优先级矩阵

```
高影响力
  │
  │  [P0] Gateway 认证    [P1] Telegram/Slack
  │  [P0] 类型化协议      [P1] Docker 沙箱
  │
  │──────────────────────────────►
  │                              实施难度
  │
  │  [P2] Cron 调度器       [P2] 指标系统
  │  [P2] Webhook 支持      [P2] 技能系统
  │
  ▼
低影响力
```

### 3.3 Phase 1 完成项 ✅

- ✅ SQLite 持久化存储
- ✅ 多智能体系统（ResearchAgent, CodeAgent, CreativeAgent, GeneralAgent）
- ✅ 智能体路由器（关键词自动分类）
- ✅ 会话绑定
- ✅ Agent-to-Agent 通信工具
- ✅ 完整测试覆盖

---

## 4. P0 优先级改进

### 4.1 Gateway 认证系统

**目标**：保护 Gateway 免受未授权访问

**实现方案**：

```python
# src/fastreact/gateway/auth.py

import os
import jwt
from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import WebSocket, status
import secrets

class GatewayAuth:
    """Gateway 认证系统"""

    def __init__(
        self,
        token: Optional[str] = None,
        password: Optional[str] = None,
        jwt_secret: Optional[str] = None,
        enable_jwt: bool = True
    ):
        self.static_token = token or os.getenv("GATEWAY_TOKEN")
        self.password = password or os.getenv("GATEWAY_PASSWORD")
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET", secrets.token_hex(32))
        self.enable_jwt = enable_jwt

        # 会话存储
        self.active_sessions: Dict[str, Dict] = {}

    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """生成 JWT token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[Dict]:
        """验证 JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def authenticate_websocket(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """认证 WebSocket 连接"""

        # 开发模式：无认证
        if not self.static_token and not self.password and not self.enable_jwt:
            return True, None

        # 检查静态 token
        if self.static_token and token == self.static_token:
            return True, "static_token"

        # 检查密码
        if self.password and password == self.password:
            return True, "password"

        # 检查 JWT token
        if self.enable_jwt and token:
            payload = self.verify_token(token)
            if payload:
                return True, payload.get("user_id")

        # 检查 API key
        if api_key:
            # 可以从配置中验证 API key
            return True, "api_key"

        return False, None

    async def close_unauthorized(self, websocket: WebSocket, reason: str = "Unauthorized"):
        """关闭未授权连接"""
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=reason
        )

    def create_session(self, user_id: str, metadata: Dict = None) -> str:
        """创建会话"""
        session_id = secrets.token_urlsafe(16)
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """验证会话"""
        return session_id in self.active_sessions

    def revoke_session(self, session_id: str) -> bool:
        """撤销会话"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
```

**Gateway 集成**：

```python
# src/fastreact/gateway/server.py

class GatewayServer:
    def __init__(
        self,
        agent: FastReAct,
        auth: GatewayAuth = None,
        storage: SessionStorage = None
    ):
        self.agent = agent
        self.auth = auth or GatewayAuth()
        self.storage = storage

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        session_id: str,
        token: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        # 认证
        authenticated, auth_method = self.auth.authenticate_websocket(
            websocket, token, password, api_key
        )

        if not authenticated:
            await self.auth.close_unauthorized(websocket)
            return

        await websocket.accept()

        # 记录认证方法
        logger.info(f"WebSocket connection authenticated via {auth_method}")

        # ... 其余连接处理
```

**测试策略**：

```python
# tests/test_gateway_auth.py

import pytest
from fastreact.gateway.auth import GatewayAuth

def test_static_token_auth():
    """测试静态 token 认证"""
    auth = GatewayAuth(token="test-token")
    assert auth.authenticate_websocket(None, token="test-token")[0] is True
    assert auth.authenticate_websocket(None, token="wrong-token")[0] is False

def test_password_auth():
    """测试密码认证"""
    auth = GatewayAuth(password="test-password")
    assert auth.authenticate_websocket(None, password="test-password")[0] is True

def test_jwt_generation():
    """测试 JWT 生成和验证"""
    auth = GatewayAuth()

    token = auth.generate_token("user123", expires_in=3600)
    payload = auth.verify_token(token)

    assert payload is not None
    assert payload["user_id"] == "user123"

def test_jwt_expiration():
    """测试 JWT 过期"""
    auth = GatewayAuth()

    # 生成已过期的 token
    token = auth.generate_token("user123", expires_in=-1)
    payload = auth.verify_token(token)

    assert payload is None

def test_session_management():
    """测试会话管理"""
    auth = GatewayAuth()

    session_id = auth.create_session("user123", {"ip": "127.0.0.1"})
    assert auth.validate_session(session_id) is True

    auth.revoke_session(session_id)
    assert auth.validate_session(session_id) is False
```

**收益**：
- ✅ 生产环境安全
- ✅ 多租户支持
- ✅ 审计和合规
- ✅ JWT 支持无状态认证

---

### 4.2 类型化协议系统

**目标**：健壮的协议定义和验证

**实现方案**：

```python
# src/fastreact/gateway/protocol.py

from typing import Literal, Optional, Any, Dict, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

# ====== 消息类型 ======

class MessageType(BaseModel):
    """消息类型基类"""
    type: Literal["req", "res", "event"]
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# ====== 请求消息 ======

class AgentRequest(BaseModel):
    """Agent 请求"""
    method: Literal["agent"] = "agent"
    params: Dict[str, Any] = Field(..., description="Agent 参数")

    @validator('params')
    def validate_params(cls, v):
        if 'query' not in v:
            raise ValueError("params must contain 'query'")
        return v

class SendRequest(BaseModel):
    """发送消息请求"""
    method: Literal["send"] = "send"
    params: Dict[str, Any] = Field(..., description="发送参数")

    @validator('params')
    def validate_params(cls, v):
        if 'message' not in v:
            raise ValueError("params must contain 'message'")
        return v

class HealthRequest(BaseModel):
    """健康检查请求"""
    method: Literal["health"] = "health"
    params: Dict[str, Any] = {}

class RequestMessage(MessageType):
    """请求消息"""
    type: Literal["req"] = "req"
    method: Literal["agent", "send", "health", "sessions.list"]
    params: Dict[str, Any]
    idempotency_key: Optional[str] = None

# ====== 响应消息 ======

class ResponseMessage(MessageType):
    """响应消息"""
    type: Literal["res"] = "res"
    ok: bool
    payload: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    @validator('error')
    def validate_error(cls, v, values):
        if values.get('ok') and v is not None:
            raise ValueError("Cannot have both ok=True and error")
        if not values.get('ok') and v is None:
            raise ValueError("Must provide error when ok=False")
        return v

# ====== 事件消息 ======

class AgentEvent(BaseModel):
    """Agent 事件"""
    event: Literal["agent"]
    payload: Dict[str, Any]

class PresenceEvent(BaseModel):
    """在线状态事件"""
    event: Literal["presence"]
    payload: Dict[str, Any]

class TickEvent(BaseModel):
    """心跳事件"""
    event: Literal["tick"]
    payload: Dict[str, Any]

class ShutdownEvent(BaseModel):
    """关闭事件"""
    event: Literal["shutdown"]
    payload: Dict[str, Any]

class EventMessage(MessageType):
    """事件消息"""
    type: Literal["event"] = "event"
    event: Literal["agent", "presence", "tick", "shutdown"]
    payload: Dict[str, Any]
    seq: int
    state_version: int

# ====== 协议验证器 ======

class ProtocolValidator:
    """协议验证器"""

    @staticmethod
    def validate_request(data: Dict) -> RequestMessage:
        """验证请求消息"""
        try:
            return RequestMessage(**data)
        except Exception as e:
            raise ValueError(f"Invalid request: {str(e)}")

    @staticmethod
    def validate_response(data: Dict) -> ResponseMessage:
        """验证响应消息"""
        try:
            return ResponseMessage(**data)
        except Exception as e:
            raise ValueError(f"Invalid response: {str(e)}")

    @staticmethod
    def validate_event(data: Dict) -> EventMessage:
        """验证事件消息"""
        try:
            return EventMessage(**data)
        except Exception as e:
            raise ValueError(f"Invalid event: {str(e)}")

# ====== 消息构建器 ======

class MessageBuilder:
    """消息构建器"""

    @staticmethod
    def create_request(
        method: str,
        params: Dict,
        request_id: str = None,
        idempotency_key: str = None
    ) -> Dict:
        """创建请求消息"""
        return {
            "type": "req",
            "id": request_id or str(uuid.uuid4()),
            "method": method,
            "params": params,
            "idempotency_key": idempotency_key
        }

    @staticmethod
    def create_success_response(
        request_id: str,
        payload: Any = None
    ) -> Dict:
        """创建成功响应"""
        return {
            "type": "res",
            "id": request_id,
            "ok": True,
            "payload": payload
        }

    @staticmethod
    def create_error_response(
        request_id: str,
        error_code: str,
        error_message: str,
        details: Dict = None
    ) -> Dict:
        """创建错误响应"""
        return {
            "type": "res",
            "id": request_id,
            "ok": False,
            "error": {
                "code": error_code,
                "message": error_message,
                "details": details or {}
            }
        }

    @staticmethod
    def create_event(
        event_type: str,
        payload: Dict,
        seq: int,
        state_version: int
    ) -> Dict:
        """创建事件消息"""
        return {
            "type": "event",
            "event": event_type,
            "payload": payload,
            "seq": seq,
            "state_version": state_version
        }
```

**去重缓存**：

```python
# src/fastreact/gateway/dedup.py

from typing import Dict, Optional, Any
import asyncio
from datetime import datetime, timedelta

class DedupCache:
    """短期去重缓存（防止重放攻击）"""

    def __init__(self, ttl: int = 300):  # 5 分钟 TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self._lock = asyncio.Lock()

    async def check_and_store(
        self,
        key: str,
        value: Any = None
    ) -> tuple[bool, Optional[Any]]:
        """检查并存储键

        Returns:
            (is_duplicate, stored_value)
        """
        async with self._lock:
            now = datetime.utcnow()

            # 清理过期条目
            await self._cleanup_expired(now)

            # 检查是否存在
            if key in self.cache:
                entry = self.cache[key]
                return True, entry.get("value")

            # 存储新条目
            self.cache[key] = {
                "value": value,
                "created_at": now
            }

            return False, value

    async def _cleanup_expired(self, now: datetime):
        """清理过期条目"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if (now - entry["created_at"]).total_seconds() > self.ttl
        ]

        for key in expired_keys:
            del self.cache[key]

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self.cache.clear()
```

**Gateway 集成**：

```python
# src/fastreact/gateway/server.py

from .protocol import ProtocolValidator, MessageBuilder
from .dedup import DedupCache

class GatewayServer:
    def __init__(self, agent: FastReAct):
        self.agent = agent
        self.validator = ProtocolValidator()
        self.builder = MessageBuilder()
        self.dedup = DedupCache(ttl=300)

    async def handle_message(
        self,
        session_id: str,
        data: Dict
    ) -> Dict:
        """处理消息"""

        try:
            # 验证消息
            message = self.validator.validate_request(data)

            # 检查幂等性
            if message.idempotency_key:
                is_dup, cached_result = await self.dedup.check_and_store(
                    message.idempotency_key
                )
                if is_dup:
                    return cached_result

            # 路由到处理器
            if message.method == "agent":
                result = await self._handle_agent(message.params)
            elif message.method == "health":
                result = await self._handle_health()
            else:
                raise ValueError(f"Unknown method: {message.method}")

            # 构建响应
            response = self.builder.create_success_response(
                message.id,
                result
            )

            # 缓存响应（用于幂等性）
            if message.idempotency_key:
                await self.dedup.check_and_store(
                    message.idempotency_key,
                    response
                )

            return response

        except Exception as e:
            # 构建错误响应
            return self.builder.create_error_response(
                data.get("id", "unknown"),
                error_code="VALIDATION_ERROR",
                error_message=str(e)
            )
```

**测试策略**：

```python
# tests/test_gateway_protocol.py

import pytest
from pydantic import ValidationError
from fastreact.gateway.protocol import (
    RequestMessage, ResponseMessage, EventMessage,
    ProtocolValidator, MessageBuilder
)

def test_request_validation():
    """测试请求验证"""
    validator = ProtocolValidator()

    # 有效请求
    valid_req = {
        "type": "req",
        "id": "test-id",
        "method": "agent",
        "params": {"query": "test"}
    }
    req = validator.validate_request(valid_req)
    assert req.method == "agent"

    # 无效请求（缺少 params）
    invalid_req = {
        "type": "req",
        "id": "test-id",
        "method": "agent"
    }
    with pytest.raises(ValueError):
        validator.validate_request(invalid_req)

def test_response_validation():
    """测试响应验证"""
    validator = ProtocolValidator()

    # 成功响应
    valid_res = {
        "type": "res",
        "id": "test-id",
        "ok": True,
        "payload": {"result": "test"}
    }
    res = validator.validate_response(valid_res)
    assert res.ok is True

    # 错误响应
    error_res = {
        "type": "res",
        "id": "test-id",
        "ok": False,
        "error": {"code": "ERROR", "message": "Test error"}
    }
    res = validator.validate_response(error_res)
    assert res.ok is False

    # 无效响应（ok=True 但有 error）
    invalid_res = {
        "type": "res",
        "id": "test-id",
        "ok": True,
        "error": {"code": "ERROR"}
    }
    with pytest.raises(ValueError):
        validator.validate_response(invalid_res)

def test_message_builder():
    """测试消息构建"""
    builder = MessageBuilder()

    # 创建请求
    req = builder.create_request(
        method="agent",
        params={"query": "test"}
    )
    assert req["type"] == "req"
    assert req["method"] == "agent"

    # 创建成功响应
    res = builder.create_success_response(
        request_id="test-id",
        payload={"result": "test"}
    )
    assert res["ok"] is True
    assert res["payload"]["result"] == "test"

    # 创建错误响应
    err = builder.create_error_response(
        request_id="test-id",
        error_code="TEST_ERROR",
        error_message="Test error"
    )
    assert err["ok"] is False
    assert err["error"]["code"] == "TEST_ERROR"
```

**收益**：
- ✅ 类型安全
- ✅ 自动验证
- ✅ 文档即代码
- ✅ 防止重放攻击

---

## 5. P1 优先级改进

### 5.1 多通道集成框架

**目标**：支持 Telegram, Slack, Discord 等主流消息平台

**架构设计**：

```
┌─────────────────────────────────────────────────────┐
│              Channel Abstraction Layer              │
└──────────────────┬──────────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
      ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Telegram │ │  Slack   │ │ Discord  │
│ Channel  │ │ Channel  │ │ Channel  │
└──────────┘ └──────────┘ └──────────┘
      │            │            │
      └────────────┼────────────┘
                   ▼
          ┌────────────────┐
          │    Gateway     │
          │  (WebSocket)   │
          └────────────────┘
```

**基础抽象**：

```python
# src/fastreact/channels/base.py

from abc import ABC, abstractmethod
from typing import Dict, Optional, Callable
import asyncio

class Channel(ABC):
    """通道基类"""

    def __init__(
        self,
        name: str,
        gateway_url: str = "ws://localhost:8080",
        config: Dict = None
    ):
        self.name = name
        self.gateway_url = gateway_url
        self.config = config or {}
        self.running = False
        self.message_handler: Optional[Callable] = None

    @abstractmethod
    async def start(self):
        """启动通道"""
        pass

    @abstractmethod
    async def stop(self):
        """停止通道"""
        pass

    @abstractmethod
    async def send_message(
        self,
        user_id: str,
        message: str,
        **kwargs
    ):
        """发送消息给用户"""
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息"""
        pass

    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self.message_handler = handler

    async def _forward_to_gateway(
        self,
        user_id: str,
        message: str,
        metadata: Dict = None
    ):
        """转发消息到 Gateway"""
        if self.message_handler:
            await self.message_handler(
                channel=self.name,
                user_id=user_id,
                message=message,
                metadata=metadata or {}
            )
```

**Telegram 通道**：

```python
# src/fastreact/channels/telegram.py

import os
import logging
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from .base import Channel

logger = logging.getLogger(__name__)

class TelegramChannel(Channel):
    """Telegram 通道"""

    def __init__(
        self,
        bot_token: str = None,
        gateway_url: str = "ws://localhost:8080",
        config: Dict = None
    ):
        super().__init__("telegram", gateway_url, config)
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        self.bot = Bot(token=self.bot_token)
        self.application = None

    async def start(self):
        """启动 Telegram bot"""
        try:
            self.application = Application.builder().token(self.bot_token).build()

            # 添加命令处理器
            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("help", self._cmd_help))
            self.application.add_handler(CommandHandler("agent", self._cmd_agent))

            # 添加消息处理器
            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    self._handle_message
                )
            )

            # 启动应用
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            self.running = True
            logger.info("Telegram channel started")

        except Exception as e:
            logger.error(f"Failed to start Telegram channel: {e}")
            raise

    async def stop(self):
        """停止 Telegram bot"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        self.running = False
        logger.info("Telegram channel stopped")

    async def send_message(
        self,
        user_id: str,
        message: str,
        parse_mode: str = "Markdown",
        **kwargs
    ):
        """发送消息给用户"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息"""
        try:
            chat = await self.bot.get_chat(user_id)
            return {
                "id": str(chat.id),
                "username": chat.username,
                "first_name": chat.first_name,
                "last_name": chat.last_name,
                "type": chat.type
            }
        except Exception as e:
            logger.error(f"Failed to get Telegram user info: {e}")
            return {}

    # ====== 命令处理器 ======

    async def _cmd_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """处理 /start 命令"""
        await update.message.reply_text(
            "👋 Welcome to FastReAct Bot!\n\n"
            "Available commands:\n"
            "/help - Show help\n"
            "/agent <name> - Switch agent\n\n"
            "Just send me a message to start!"
        )

    async def _cmd_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """处理 /help 命令"""
        await update.message.reply_text(
            "📖 *FastReAct Bot Help*\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/agent <name> - Switch to a specific agent\n\n"
            "Agents:\n"
            "• `researcher` - Research and analysis\n"
            "• `coder` - Programming and debugging\n"
            "• `creator` - Content creation\n"
            "• `general` - General assistance\n\n"
            "Just send any message to start chatting!",
            parse_mode="Markdown"
        )

    async def _cmd_agent(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """处理 /agent 命令"""
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Usage: /agent <name>\n\n"
                "Available agents: researcher, coder, creator, general"
            )
            return

        agent_name = context.args[0]

        # 转发到 Gateway（用于切换智能体）
        await self._forward_to_gateway(
            user_id=str(update.effective_user.id),
            message=f"/switch_agent {agent_name}",
            metadata={"command": "agent", "agent_name": agent_name}
        )

    # ====== 消息处理器 ======

    async def _handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """处理文本消息"""
        user_id = str(update.effective_user.id)
        message = update.message.text

        # 转发到 Gateway
        await self._forward_to_gateway(
            user_id=user_id,
            message=message,
            metadata={
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "message_id": update.message.message_id
            }
        )
```

**Slack 通道**：

```python
# src/fastreact/channels/slack.py

import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .base import Channel

logger = logging.getLogger(__name__)

class SlackChannel(Channel):
    """Slack 通道"""

    def __init__(
        self,
        bot_token: str = None,
        app_token: str = None,
        gateway_url: str = "ws://localhost:8080",
        config: Dict = None
    ):
        super().__init__("slack", gateway_url, config)
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.app_token = app_token or os.getenv("SLACK_APP_TOKEN")

        if not self.bot_token or not self.app_token:
            raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN are required")

        self.app = App(token=self.bot_token)
        self.handler = None

    async def start(self):
        """启动 Slack bot"""
        try:
            # 注册事件处理器
            self.app.event("app_mention")(self._handle_app_mention)
            self.app.event("message")(self._handle_message)
            self.app.command("/agent")(self._cmd_agent)

            # 启动 Socket Mode 处理器
            self.handler = SocketModeHandler(self.app, self.app_token)
            await self.handler.connect_async()

            self.running = True
            logger.info("Slack channel started")

        except Exception as e:
            logger.error(f"Failed to start Slack channel: {e}")
            raise

    async def stop(self):
        """停止 Slack bot"""
        if self.handler:
            await self.handler.close()
        self.running = False
        logger.info("Slack channel stopped")

    async def send_message(
        self,
        user_id: str,
        message: str,
        channel: str = None,
        **kwargs
    ):
        """发送消息给用户"""
        try:
            target = channel or user_id
            await self.app.client.chat_postMessage(
                channel=target,
                text=message
            )
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")

    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息"""
        try:
            user = await self.app.client.users_info(user=user_id)
            return {
                "id": user["user"]["id"],
                "name": user["user"]["name"],
                "real_name": user["user"]["real_name"],
                "email": user["user"].get("profile", {}).get("email")
            }
        except Exception as e:
            logger.error(f"Failed to get Slack user info: {e}")
            return {}

    # ====== 事件处理器 ======

    async def _handle_app_mention(self, context):
        """处理应用提及"""
        event = context.event
        user_id = event["user"]
        text = event.get("text", "")
        channel = event["channel"]

        # 移除机器人提及
        message = text.replace(f"<@{context.bot_user_id}>", "").strip()

        # 转发到 Gateway
        await self._forward_to_gateway(
            user_id=user_id,
            message=message,
            metadata={
                "channel": channel,
                "event_type": "app_mention"
            }
        )

    async def _handle_message(self, context):
        """处理直接消息"""
        event = context.event
        channel_type = event.get("channel_type")

        # 只处理 DM
        if channel_type != "im":
            return

        user_id = event["user"]
        message = event.get("text", "")
        channel = event["channel"]

        # 转发到 Gateway
        await self._forward_to_gateway(
            user_id=user_id,
            message=message,
            metadata={
                "channel": channel,
                "event_type": "message"
            }
        )

    async def _cmd_agent(self, ack, body, respond):
        """处理 /agent 命令"""
        await ack()

        agent_name = body.get("text", "").strip()
        if not agent_name:
            await respond("Usage: /agent <name>")
            return

        # 转发到 Gateway
        await self._forward_to_gateway(
            user_id=body["user_id"],
            message=f"/switch_agent {agent_name}",
            metadata={
                "command": "agent",
                "agent_name": agent_name
            }
        )
```

**通道管理器**：

```python
# src/fastreact/channels/manager.py

from typing import Dict, List
from .base import Channel
from .telegram import TelegramChannel
from .slack import SlackChannel

class ChannelManager:
    """通道管理器"""

    def __init__(self, gateway_url: str = "ws://localhost:8080"):
        self.gateway_url = gateway_url
        self.channels: Dict[str, Channel] = {}

    def register_channel(self, channel: Channel):
        """注册通道"""
        channel.set_message_handler(self._handle_channel_message)
        self.channels[channel.name] = channel

    async def start_channel(self, name: str):
        """启动通道"""
        if name in self.channels:
            await self.channels[name].start()

    async def stop_channel(self, name: str):
        """停止通道"""
        if name in self.channels:
            await self.channels[name].stop()

    async def start_all(self):
        """启动所有通道"""
        for channel in self.channels.values():
            await channel.start()

    async def stop_all(self):
        """停止所有通道"""
        for channel in self.channels.values():
            await channel.stop()

    async def send_to_channel(
        self,
        channel_name: str,
        user_id: str,
        message: str,
        **kwargs
    ):
        """发送消息到指定通道"""
        if channel_name in self.channels:
            await self.channels[channel_name].send_message(
                user_id, message, **kwargs
            )

    async def _handle_channel_message(
        self,
        channel: str,
        user_id: str,
        message: str,
        metadata: Dict
    ):
        """处理通道消息（转发到 Gateway）"""
        # 这里会通过 WebSocket 连接到 Gateway
        # 实现将在 Gateway 集成部分完成
        logger.info(f"Message from {channel}:{user_id}: {message}")
```

**测试策略**：

```python
# tests/test_channels.py

import pytest
from fastreact.channels.manager import ChannelManager

@pytest.mark.asyncio
class TestChannels:
    """测试通道功能"""

    async def test_channel_registration(self):
        """测试通道注册"""
        manager = ChannelManager()

        # 创建 mock 通道
        class MockChannel(Channel):
            async def start(self): pass
            async def stop(self): pass
            async def send_message(self, user_id, message, **kwargs): pass
            async def get_user_info(self, user_id): return {}

        channel = MockChannel("test")
        manager.register_channel(channel)

        assert "test" in manager.channels

    async def test_send_to_channel(self):
        """测试发送到通道"""
        manager = ChannelManager()

        # 创建 spy 通道
        class SpyChannel(Channel):
            def __init__(self):
                super().__init__("spy")
                self.messages = []

            async def start(self): pass
            async def stop(self): pass
            async def send_message(self, user_id, message, **kwargs):
                self.messages.append((user_id, message))
            async def get_user_info(self, user_id): return {}

        channel = SpyChannel()
        manager.register_channel(channel)

        await manager.send_to_channel("spy", "user123", "Hello!")

        assert len(channel.messages) == 1
        assert channel.messages[0] == ("user123", "Hello!")
```

**收益**：
- ✅ 多平台支持
- ✅ 统一接口
- ✅ 易于扩展
- ✅ 用户体验提升

---

### 5.2 Docker 沙箱系统

**目标**：安全的代码执行环境

**实现方案**：

```python
# src/fastreact/sandbox/docker.py

import docker
import logging
from typing import Dict, Optional, List
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class DockerSandbox:
    """Docker 沙箱管理器"""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()  # 测试连接
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError("Docker is not available")

        # 容器池
        self.containers: Dict[str, docker.models.containers.Container] = {}

        # 配置
        self.image_map = {
            "python": "python:3.11-slim",
            "javascript": "node:18-alpine",
            "bash": "bash:5.2",
            "java": "openjdk:17-slim"
        }

        self.default_limits = {
            "memory": "512m",
            "cpu_period": 100000,
            "cpu_quota": 50000,  # 50% CPU
            "network_disabled": True
        }

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        stdin: str = None,
        allowlist: List[str] = None,
        denylist: List[str] = None
    ) -> Dict:
        """在沙箱中执行代码"""

        # 选择镜像
        image = self.image_map.get(language, "python:3.11-slim")

        # 构建命令
        if language == "python":
            command = self._build_python_command(code)
        elif language == "javascript":
            command = self._build_node_command(code)
        elif language == "bash":
            command = ["bash", "-c", code]
        else:
            return {
                "success": False,
                "error": f"Unsupported language: {language}"
            }

        # 安全检查
        if denylist:
            for keyword in denylist:
                if keyword in code:
                    return {
                        "success": False,
                        "error": f"Blocked keyword: {keyword}"
                    }

        try:
            # 运行容器
            result = self.client.containers.run(
                image,
                command=command,
                stdin_open=True,
                environment=self._get_environment(language),
                **self.default_limits,
                timeout=timeout,
                remove=True,
                stdout=True,
                stderr=True,
                detach=False
            )

            output = result.decode("utf-8") if isinstance(result, bytes) else result

            return {
                "success": True,
                "output": output,
                "language": language,
                "timestamp": datetime.utcnow().isoformat()
            }

        except docker.errors.ContainerError as e:
            return {
                "success": False,
                "error": f"Container error: {e.stderr.decode('utf-8')}",
                "exit_code": e.exit_status
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _build_python_command(self, code: str) -> List[str]:
        """构建 Python 执行命令"""
        # 使用 -c 参数执行代码
        return ["python", "-c", code]

    def _build_node_command(self, code: str) -> List[str]:
        """构建 Node.js 执行命令"""
        return ["node", "-e", code]

    def _get_environment(self, language: str) -> Dict[str, str]:
        """获取环境变量"""
        env = {
            "PYTHONUNBUFFERED": "1",
            "NODE_ENV": "production"
        }

        # 语言特定环境变量
        if language == "python":
            env["PYTHONDONTWRITEBYTECODE"] = "1"

        return env

    async def create_sandbox(
        self,
        session_id: str,
        language: str = "python",
        persist: bool = False
    ) -> str:
        """创建持久化沙箱容器"""

        image = self.image_map.get(language, "python:3.11-slim")

        try:
            container = self.client.containers.run(
                image,
                command=["tail", "-f", "/dev/null"],  # 保持容器运行
                detach=True,
                remove=not persist,
                name=f"sandbox_{session_id[:8]}",
                **self.default_limits
            )

            self.containers[session_id] = container

            logger.info(f"Created sandbox container: {container.id}")
            return container.id

        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise

    async def execute_in_sandbox(
        self,
        session_id: str,
        code: str,
        language: str = "python"
    ) -> Dict:
        """在持久化沙箱中执行代码"""

        if session_id not in self.containers:
            return {
                "success": False,
                "error": "Sandbox not found"
            }

        container = self.containers[session_id]

        try:
            # 构建命令
            if language == "python":
                command = ["python", "-c", code]
            else:
                command = ["bash", "-c", code]

            # 执行命令
            result = container.exec_run(command)

            output = result.output.decode("utf-8") if result.output else ""

            return {
                "success": result.exit_code == 0,
                "output": output,
                "exit_code": result.exit_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def destroy_sandbox(self, session_id: str):
        """销毁沙箱容器"""

        if session_id in self.containers:
            try:
                container = self.containers[session_id]
                container.stop(timeout=5)
                container.remove()
                del self.containers[session_id]
                logger.info(f"Destroyed sandbox for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to destroy sandbox: {e}")

    async def cleanup(self):
        """清理所有沙箱容器"""
        for session_id in list(self.containers.keys()):
            await self.destroy_sandbox(session_id)

    def get_stats(self) -> Dict:
        """获取沙箱统计信息"""
        return {
            "active_containers": len(self.containers),
            "supported_languages": list(self.image_map.keys()),
            "memory_limit": self.default_limits["memory"],
            "cpu_limit": "50%"
        }
```

**工具集成**：

```python
# src/fastreact/tools/sandbox.py

from ..core.tool import Tool
from ..sandbox.docker import DockerSandbox
import json

class ExecuteCodeTool(Tool):
    """在 Docker 沙箱中执行代码"""

    def __init__(self, sandbox: DockerSandbox):
        self.sandbox = sandbox
        super().__init__()

    def _get_description(self):
        return "Execute code in a secure Docker sandbox"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash"],
                    "description": "Programming language",
                    "default": "python"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30
                }
            },
            "required": ["code"]
        }

    async def execute_async(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30
    ) -> str:
        result = await self.sandbox.execute_code(
            code=code,
            language=language,
            timeout=timeout
        )

        return json.dumps(result, ensure_ascii=False, indent=2)
```

**测试策略**：

```python
# tests/test_sandbox.py

import pytest
from fastreact.sandbox.docker import DockerSandbox

@pytest.mark.asyncio
class TestDockerSandbox:
    """测试 Docker 沙箱"""

    @pytest.fixture
    async def sandbox(self):
        """创建沙箱实例"""
        try:
            sandbox = DockerSandbox()
            yield sandbox
        except RuntimeError:
            pytest.skip("Docker not available")

    async def test_execute_python_code(self, sandbox):
        """测试执行 Python 代码"""
        result = await sandbox.execute_code(
            code="print('Hello, World!')",
            language="python"
        )

        assert result["success"] is True
        assert "Hello, World!" in result["output"]

    async def test_execute_javascript_code(self, sandbox):
        """测试执行 JavaScript 代码"""
        result = await sandbox.execute_code(
            code="console.log('Hello from Node!');",
            language="javascript"
        )

        assert result["success"] is True
        assert "Hello from Node!" in result["output"]

    async def test_code_timeout(self, sandbox):
        """测试代码超时"""
        result = await sandbox.execute_code(
            code="import time; time.sleep(100)",
            language="python",
            timeout=2
        )

        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    async def test_denylist(self, sandbox):
        """测试拒绝列表"""
        result = await sandbox.execute_code(
            code="import os; os.system('rm -rf /')",
            language="python",
            denylist=["os.system", "subprocess"]
        )

        assert result["success"] is False
        assert "Blocked" in result["error"]
```

**收益**：
- ✅ 安全隔离
- ✅ 资源限制
- ✅ 支持多语言
- ✅ 防止恶意代码

---

## 6. P2 优先级改进

### 6.1 Cron 调度器

**目标**：支持定时任务和自动化

**实现方案**：

```python
# src/fastreact/scheduler/cron.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Dict, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class CronScheduler:
    """Cron 任务调度器"""

    def __init__(self, gateway=None):
        self.scheduler = AsyncIOScheduler()
        self.gateway = gateway
        self.jobs: Dict[str, Dict] = {}

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("Cron scheduler started")

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("Cron scheduler stopped")

    async def add_cron_job(
        self,
        job_id: str,
        task: str,
        hour: int = None,
        minute: int = None,
        day: str = None,
        day_of_week: str = None,
        session_id: str = None
    ):
        """添加 Cron 任务"""

        async def job_func():
            logger.info(f"Executing cron job: {job_id}")
            if self.gateway:
                await self.gateway.handle_message(
                    session_id or job_id,
                    {"query": task}
                )

        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day=day,
            day_of_week=day_of_week
        )

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=job_id,
            replace_existing=True
        )

        self.jobs[job_id] = {
            "type": "cron",
            "task": task,
            "trigger": trigger,
            "session_id": session_id
        }

        logger.info(f"Added cron job: {job_id}")

    async def add_interval_job(
        self,
        job_id: str,
        task: str,
        seconds: int = 3600,
        session_id: str = None
    ):
        """添加间隔任务"""

        async def job_func():
            logger.info(f"Executing interval job: {job_id}")
            if self.gateway:
                await self.gateway.handle_message(
                    session_id or job_id,
                    {"query": task}
                )

        trigger = IntervalTrigger(seconds=seconds)

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=job_id,
            replace_existing=True
        )

        self.jobs[job_id] = {
            "type": "interval",
            "task": task,
            "seconds": seconds,
            "session_id": session_id
        }

        logger.info(f"Added interval job: {job_id}")

    def remove_job(self, job_id: str):
        """移除任务"""
        self.scheduler.remove_job(job_id)
        if job_id in self.jobs:
            del self.jobs[job_id]
        logger.info(f"Removed job: {job_id}")

    def list_jobs(self) -> Dict:
        """列出所有任务"""
        return {
            "jobs": [
                {
                    "id": job_id,
                    **job_data
                }
                for job_id, job_data in self.jobs.items()
            ],
            "count": len(self.jobs)
        }

    def get_job_info(self, job_id: str) -> Optional[Dict]:
        """获取任务信息"""
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job_id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
        return None
```

### 6.2 指标收集系统

**目标**：监控和可观测性

**实现方案**：

```python
# src/fastreact/metrics/collector.py

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """指标收集器"""

    def __init__(self, port: int = 9090):
        # 请求计数器
        self.request_counter = Counter(
            'fastreact_requests_total',
            'Total requests',
            ['method', 'status']
        )

        # 响应时间直方图
        self.response_time = Histogram(
            'fastreact_response_time_seconds',
            'Response time',
            ['method']
        )

        # 活跃会话
        self.active_sessions = Gauge(
            'fastreact_active_sessions',
            'Active sessions'
        )

        # Agent 执行计数
        self.agent_executions = Counter(
            'fastreact_agent_executions_total',
            'Agent executions',
            ['agent_name', 'status']
        )

        # Tool 使用计数
        self.tool_usage = Counter(
            'fastreact_tool_usage_total',
            'Tool usage',
            ['tool_name', 'status']
        )

        self.port = port

    def start_server(self):
        """启动指标服务器"""
        start_http_server(self.port)
        logger.info(f"Metrics server started on port {self.port}")

    def record_request(self, method: str, status: str):
        """记录请求"""
        self.request_counter.labels(method=method, status=status).inc()

    def record_response_time(self, method: str, duration: float):
        """记录响应时间"""
        self.response_time.labels(method=method).observe(duration)

    def update_active_sessions(self, count: int):
        """更新活跃会话数"""
        self.active_sessions.set(count)

    def record_agent_execution(self, agent_name: str, status: str):
        """记录 Agent 执行"""
        self.agent_executions.labels(
            agent_name=agent_name,
            status=status
        ).inc()

    def record_tool_usage(self, tool_name: str, status: str):
        """记录工具使用"""
        self.tool_usage.labels(
            tool_name=tool_name,
            status=status
        ).inc()

# 使用上下文管理器
class RequestTimer:
    """请求计时器"""

    def __init__(self, collector: MetricsCollector, method: str):
        self.collector = collector
        self.method = method
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.collector.record_response_time(self.method, duration)
```

---

## 7. 实施路线图

### 7.1 Phase 1: 安全与协议 (2-3 周)

**Week 1-2: Gateway 认证**
- [ ] 实现 GatewayAuth 类
- [ ] 支持 static token, password, JWT
- [ ] 会话管理
- [ ] WebSocket 集成
- [ ] 单元测试
- [ ] 文档编写

**Week 2-3: 类型化协议**
- [ ] 定义 Pydantic 模型
- [ ] 实现 ProtocolValidator
- [ ] 实现 MessageBuilder
- [ ] 实现 DedupCache
- [ ] Gateway 集成
- [ ] 单元测试

**里程碑**：
- ✅ Gateway 受密码保护
- ✅ 所有消息经过验证
- ✅ 防重放攻击

### 7.2 Phase 2: 多通道支持 (3-4 周)

**Week 4-5: Telegram & Slack**
- [ ] 实现 Channel 基类
- [ ] 实现 TelegramChannel
- [ ] 实现 SlackChannel
- [ ] 实现 ChannelManager
- [ ] Gateway 集成
- [ ] 端到端测试

**Week 6: Discord & 其他**
- [ ] 实现 DiscordChannel
- [ ] 优化通道抽象
- [ ] 错误处理
- [ ] 性能优化

**里程碑**：
- ✅ 支持 3+ 主流平台
- ✅ 统一消息接口
- ✅ 生产可用

### 7.3 Phase 3: 沙箱与自动化 (2-3 周)

**Week 7-8: Docker 沙箱**
- [ ] 实现 DockerSandbox
- [ ] 持久化容器
- [ ] 安全限制
- [ ] 工具集成
- [ ] 全面测试

**Week 9: Cron & Webhooks**
- [ ] 实现 CronScheduler
- [ ] 实现 WebhookHandler
- [ ] 任务管理 API
- [ ] 测试与文档

**里程碑**：
- ✅ 安全代码执行
- ✅ 定时任务支持
- ✅ Webhook 集成

### 7.4 Phase 4: 可观测性 (1-2 周)

**Week 10: 指标与监控**
- [ ] 实现 MetricsCollector
- [ ] Prometheus 集成
- [ ] 性能仪表板
- [ ] 告警规则

**里程碑**：
- ✅ Prometheus 端点
- ✅ 关键指标追踪
- ✅ 可视化仪表板

---

## 8. 架构决策记录

### 8.1 为什么选择 Pydantic 而非 TypeBox?

**决策**：使用 Pydantic 进行协议验证

**理由**：
1. FastReAct 是 Python 项目，Pydantic 原生支持
2. Pydantic 与 FastAPI 无缝集成
3. 类型提示 + 运行时验证
4. 自动生成 JSON Schema

**权衡**：
- ❌ 失去了跨语言代码生成能力
- ✅ 更简单的开发体验
- ✅ 更好的 Python 生态集成

### 8.2 为什么使用 SQLite 而非 Redis?

**决策**：默认使用 SQLite，可选 Redis

**理由**：
1. 零配置，单文件部署
2. Windows 友好（当前开发环境）
3. 足够的性能（< 1000 并发）
4. 易于备份和迁移

**权衡**：
- ❌ 不支持分布式部署
- ✅ 简单性优先
- ✅ 可以后续添加 Redis 适配器

### 8.3 为什么采用渐进式增强?

**决策**：保持核心简洁，功能通过插件添加

**理由**：
1. FastReAct 的价值在于简洁和教育性
2. 不希望变成 Moltbot 的复制品
3. 渐进式增强降低风险
4. 用户可以选择需要的功能

**权衡**：
- ❌ 功能增加可能影响简洁性
- ✅ 保持核心清晰
- ✅ 灵活的架构

---

## 9. 总结

### 9.1 关键收获

**从 Moltbot 学到的**：
1. **单一控制平面** - Gateway 架构扩展性更好
2. **类型化协议** - 使用 schemas 和验证增强健壮性
3. **会话持久化** - 生产环境的关键需求
4. **多智能体路由** - 任务专业化的基础
5. **安全优先** - 从第一天开始考虑安全

**FastReAct 保持的优势**：
1. **代码简洁性** - 易于理解和修改
2. **纯 ReACT** - 专注于推理质量
3. **去重机制** - 节省成本和延迟
4. **异步优先** - 更好的负载性能
5. **学习友好** - 清晰的结构适合教育

### 9.2 推荐策略

**保持 FastReAct 的简洁性**，同时**采纳 Moltbot 的生产特性**：

- ✅ 不过度工程化核心引擎
- ✅ 将持久化存储作为一个层添加
- ✅ 将多智能体作为扩展实现
- ✅ 保持协议简单但类型化
- ✅ 逐步添加安全功能

### 9.3 预期成果

通过遵循此路线图，FastReAct 可以在 **2-3 个月内**达到生产就绪状态，同时保持其教育价值和代码质量。

---

**参考资源**：
- [Moltbot GitHub](https://github.com/moltbot/moltbot)
- [Moltbot 文档](https://docs.molt.bot)
- [FastReAct 仓库](https://github.com/your-username/fastreact)

**最后更新**: 2026-01-28
**下一步**: 开始实施 P0 - Gateway 认证系统
