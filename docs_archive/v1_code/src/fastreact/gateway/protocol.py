"""
Gateway 协议系统

使用 Pydantic 实现类型化的 WebSocket 协议：
- Request Message（请求消息）
- Response Message（响应消息）
- Event Message（事件消息）

提供消息验证、构建和去重功能。
"""

from typing import Literal, Optional, Any, Dict, List
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


# ====== 消息类型定义 ======

class MessageType(BaseModel):
    """消息类型基类"""
    type: Literal["req", "res", "event"]
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


# ====== 请求消息 ======

class AgentRequest(BaseModel):
    """Agent 执行请求"""
    method: Literal["agent"] = "agent"
    params: Dict[str, Any] = Field(..., description="Agent 参数")

    @field_validator("params")
    @classmethod
    def validate_params(cls, v):
        if "query" not in v and "task" not in v:
            raise ValueError("params must contain 'query' or 'task'")
        return v


class SendRequest(BaseModel):
    """发送消息请求"""
    method: Literal["send"] = "send"
    params: Dict[str, Any] = Field(..., description="发送参数")

    @field_validator("params")
    @classmethod
    def validate_params(cls, v):
        if "message" not in v:
            raise ValueError("params must contain 'message'")
        return v


class HealthRequest(BaseModel):
    """健康检查请求"""
    method: Literal["health"] = "health"
    params: Dict[str, Any] = {}


class SessionsListRequest(BaseModel):
    """列出会话请求"""
    method: Literal["sessions.list"] = "sessions.list"
    params: Dict[str, Any] = {}


class RequestMessage(MessageType):
    """请求消息

    Args:
        type: 消息类型 "req"
        id: 请求ID（UUID）
        method: 方法名称（agent, send, health, sessions.list）
        params: 方法参数
        idempotency_key: 幂等性密钥（可选，用于重试）

    Example:
        {
            "type": "req",
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "method": "agent",
            "params": {"query": "What is the weather?"},
            "idempotency_key": "optional-dedupe-key"
        }
    """
    type: Literal["req"] = "req"
    method: Literal["agent", "send", "health", "sessions.list"]
    params: Dict[str, Any]
    idempotency_key: Optional[str] = Field(None, description="幂等性密钥，用于重试和去重")


# ====== 响应消息 ======

class ResponseMessage(MessageType):
    """响应消息

    Args:
        type: 消息类型 "res"
        id: 对应的请求ID
        ok: 是否成功
        payload: 响应数据（成功时）
        error: 错误信息（失败时）

    Example (Success):
        {
            "type": "res",
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "ok": true,
            "payload": {"result": "The weather is sunny"}
        }

    Example (Error):
        {
            "type": "res",
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "ok": false,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid parameters",
                "details": {}
            }
        }
    """
    type: Literal["res"] = "res"
    ok: bool
    payload: Optional[Any] = None
    error: Optional[Dict[str, Any]] = Field(None, description="错误信息")

    @model_validator(mode="after")
    def validate_ok_error(self) -> "ResponseMessage":
        if self.ok and self.error is not None:
            raise ValueError("Cannot have both ok=True and error")

        if not self.ok and self.error is None:
            raise ValueError("Must provide error when ok=False")

        return self


# ====== 事件消息 ======

class AgentEvent(BaseModel):
    """Agent 事件"""
    event: Literal["agent"] = "agent"
    payload: Dict[str, Any]


class PresenceEvent(BaseModel):
    """在线状态事件"""
    event: Literal["presence"] = "presence"
    payload: Dict[str, Any]


class TickEvent(BaseModel):
    """心跳事件"""
    event: Literal["tick"] = "tick"
    payload: Dict[str, Any]


class ShutdownEvent(BaseModel):
    """关闭事件"""
    event: Literal["shutdown"] = "shutdown"
    payload: Dict[str, Any]


class EventMessage(MessageType):
    """事件消息

    Args:
        type: 消息类型 "event"
        event: 事件类型（agent, presence, tick, shutdown）
        payload: 事件数据
        seq: 序列号
        state_version: 状态版本号

    Example:
        {
            "type": "event",
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "event": "agent",
            "payload": {"agent": "coder", "status": "working"},
            "seq": 123,
            "state_version": 456
        }
    """
    type: Literal["event"] = "event"
    event: Literal["agent", "presence", "tick", "shutdown"]
    payload: Dict[str, Any]
    seq: int
    state_version: int


# ====== 协议验证器 ======

class ProtocolValidator:
    """协议验证器

    提供消息验证功能，确保消息符合协议规范。

    Usage:
        validator = ProtocolValidator()

        # 验证请求
        try:
            request = validator.validate_request(data)
        except ValueError as e:
            print(f"Invalid request: {e}")

        # 验证响应
        try:
            response = validator.validate_response(data)
        except ValueError as e:
            print(f"Invalid response: {e}")
    """

    @staticmethod
    def validate_request(data: Dict) -> RequestMessage:
        """验证请求消息

        Args:
            data: 待验证的数据字典

        Returns:
            验证后的 RequestMessage 对象

        Raises:
            ValueError: 验证失败
        """
        try:
            return RequestMessage(**data)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Invalid request: {error_msg}")
            raise ValueError(f"Invalid request: {error_msg}")

    @staticmethod
    def validate_response(data: Dict) -> ResponseMessage:
        """验证响应消息

        Args:
            data: 待验证的数据字典

        Returns:
            验证后的 ResponseMessage 对象

        Raises:
            ValueError: 验证失败
        """
        try:
            return ResponseMessage(**data)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Invalid response: {error_msg}")
            raise ValueError(f"Invalid response: {error_msg}")

    @staticmethod
    def validate_event(data: Dict) -> EventMessage:
        """验证事件消息

        Args:
            data: 待验证的数据字典

        Returns:
            验证后的 EventMessage 对象

        Raises:
            ValueError: 验证失败
        """
        try:
            return EventMessage(**data)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Invalid event: {error_msg}")
            raise ValueError(f"Invalid event: {error_msg}")


# ====== 消息构建器 ======

class MessageBuilder:
    """消息构建器

    提供便捷的消息构建方法。

    Usage:
        builder = MessageBuilder()

        # 创建请求
        req = builder.create_request(
            method="agent",
            params={"query": "test"},
            idempotency_key="key123"
        )

        # 创建成功响应
        res = builder.create_success_response(
            request_id="req-id",
            payload={"result": "test"}
        )

        # 创建错误响应
        err = builder.create_error_response(
            request_id="req-id",
            error_code="TEST_ERROR",
            error_message="Test error"
        )
    """

    @staticmethod
    def create_request(
        method: str,
        params: Dict,
        request_id: str = None,
        idempotency_key: str = None
    ) -> Dict:
        """创建请求消息

        Args:
            method: 方法名称
            params: 方法参数
            request_id: 请求ID（可选，自动生成UUID）
            idempotency_key: 幂等性密钥（可选）

        Returns:
            请求消息字典
        """
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
        """创建成功响应

        Args:
            request_id: 对应的请求ID
            payload: 响应数据

        Returns:
            响应消息字典
        """
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
        """创建错误响应

        Args:
            request_id: 对应的请求ID
            error_code: 错误代码
            error_message: 错误消息
            details: 额外错误详情（可选）

        Returns:
            错误响应消息字典
        """
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
        state_version: int,
        event_id: str = None
    ) -> Dict:
        """创建事件消息

        Args:
            event_type: 事件类型
            payload: 事件数据
            seq: 序列号
            state_version: 状态版本号
            event_id: 事件ID（可选，自动生成UUID）

        Returns:
            事件消息字典
        """
        return {
            "type": "event",
            "id": event_id or str(uuid.uuid4()),
            "event": event_type,
            "payload": payload,
            "seq": seq,
            "state_version": state_version
        }


# ====== 错误代码定义 ======

class ErrorCode:
    """标准错误代码"""

    # 认证错误
    AUTH_FAILED = "AUTH_FAILED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"

    # 验证错误
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    INVALID_PARAMS = "INVALID_PARAMS"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # 协议错误
    UNKNOWN_METHOD = "UNKNOWN_METHOD"
    INVALID_MESSAGE_TYPE = "INVALID_MESSAGE_TYPE"
    PROTOCOL_VIOLATION = "PROTOCOL_VIOLATION"

    # 服务器错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_INITIALIZED = "NOT_INITIALIZED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # 会话错误
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # Agent 错误
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"

    # 工具错误
    TOOL_ERROR = "TOOL_ERROR"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
