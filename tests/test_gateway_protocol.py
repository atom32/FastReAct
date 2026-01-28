"""
测试 Gateway 协议系统
"""

import pytest
from pydantic import ValidationError
from fastreact.gateway.protocol import (
    RequestMessage, ResponseMessage, EventMessage,
    AgentRequest, SendRequest,
    ProtocolValidator, MessageBuilder, ErrorCode
)
import uuid


class TestRequestMessage:
    """测试请求消息"""

    def test_valid_agent_request(self):
        """测试有效的 Agent 请求"""
        req = RequestMessage(
            type="req",
            id="test-id",
            method="agent",
            params={"query": "What is the weather?"}
        )
        assert req.type == "req"
        assert req.method == "agent"
        assert req.params["query"] == "What is the weather?"

    def test_valid_send_request(self):
        """测试有效的 Send 请求"""
        req = RequestMessage(
            type="req",
            method="send",
            params={"message": "Hello"}
        )
        assert req.method == "send"
        assert req.params["message"] == "Hello"

    def test_valid_health_request(self):
        """测试有效的 Health 请求"""
        req = RequestMessage(
            type="req",
            method="health",
            params={}
        )
        assert req.method == "health"

    def test_invalid_agent_request_missing_query(self):
        """测试无效的 Agent 请求（缺少 query）"""
        # 测试 AgentRequest 类的验证
        with pytest.raises(ValidationError):
            AgentRequest(
                method="agent",
                params={}
            )

    def test_request_with_idempotency_key(self):
        """测试带幂等性密钥的请求"""
        req = RequestMessage(
            type="req",
            method="agent",
            params={"query": "test"},
            idempotency_key="unique-key-123"
        )
        assert req.idempotency_key == "unique-key-123"

    def test_auto_generate_id(self):
        """测试自动生成 ID"""
        req = RequestMessage(
            type="req",
            method="health",
            params={}
        )
        assert req.id is not None
        assert len(req.id) > 0


class TestResponseMessage:
    """测试响应消息"""

    def test_success_response(self):
        """测试成功响应"""
        res = ResponseMessage(
            type="res",
            id="test-id",
            ok=True,
            payload={"result": "test"}
        )
        assert res.ok is True
        assert res.payload["result"] == "test"
        assert res.error is None

    def test_error_response(self):
        """测试错误响应"""
        res = ResponseMessage(
            type="res",
            id="test-id",
            ok=False,
            error={
                "code": "TEST_ERROR",
                "message": "Test error message"
            }
        )
        assert res.ok is False
        assert res.error["code"] == "TEST_ERROR"
        assert res.payload is None

    def test_invalid_response_ok_with_error(self):
        """测试无效响应（ok=True 但有 error）"""
        with pytest.raises(ValidationError):
            ResponseMessage(
                type="res",
                id="test-id",
                ok=True,
                error={"code": "ERROR"}
            )

    def test_invalid_response_not_ok_without_error(self):
        """测试无效响应（ok=False 但没有 error）"""
        with pytest.raises(ValidationError):
            ResponseMessage(
                type="res",
                id="test-id",
                ok=False
            )


class TestEventMessage:
    """测试事件消息"""

    def test_valid_agent_event(self):
        """测试有效的 Agent 事件"""
        event = EventMessage(
            type="event",
            id="test-id",
            event="agent",
            payload={"agent": "coder", "status": "working"},
            seq=123,
            state_version=456
        )
        assert event.event == "agent"
        assert event.payload["agent"] == "coder"
        assert event.seq == 123
        assert event.state_version == 456

    def test_valid_presence_event(self):
        """测试有效的 Presence 事件"""
        event = EventMessage(
            type="event",
            event="presence",
            payload={"user_id": "user123"},
            seq=1,
            state_version=1
        )
        assert event.event == "presence"


class TestProtocolValidator:
    """测试协议验证器"""

    def test_validate_valid_request(self):
        """测试验证有效请求"""
        validator = ProtocolValidator()

        data = {
            "type": "req",
            "id": "test-id",
            "method": "agent",
            "params": {"query": "test"}
        }

        req = validator.validate_request(data)
        assert req.method == "agent"
        assert req.params["query"] == "test"

    def test_validate_invalid_request(self):
        """测试验证无效请求"""
        validator = ProtocolValidator()

        # 测试缺少必需字段的情况
        data = {
            "type": "req",
            # 缺少 "method"
            "params": {}
        }

        # 应该抛出 ValueError（包装了 ValidationError）
        with pytest.raises(ValueError):
            validator.validate_request(data)

    def test_validate_valid_response(self):
        """测试验证有效响应"""
        validator = ProtocolValidator()

        data = {
            "type": "res",
            "id": "test-id",
            "ok": True,
            "payload": {"result": "test"}
        }

        res = validator.validate_response(data)
        assert res.ok is True
        assert res.payload["result"] == "test"

    def test_validate_invalid_response(self):
        """测试验证无效响应"""
        validator = ProtocolValidator()

        data = {
            "type": "res",
            "id": "test-id",
            "ok": True,
            "error": {"code": "ERROR"}  # ok=True 不应有 error
        }

        with pytest.raises(ValueError):
            validator.validate_response(data)

    def test_validate_valid_event(self):
        """测试验证有效事件"""
        validator = ProtocolValidator()

        data = {
            "type": "event",
            "id": "test-id",
            "event": "presence",
            "payload": {},
            "seq": 1,
            "state_version": 1
        }

        event = validator.validate_event(data)
        assert event.event == "presence"
        assert event.seq == 1


class TestMessageBuilder:
    """测试消息构建器"""

    def test_create_request(self):
        """测试创建请求"""
        builder = MessageBuilder()

        req = builder.create_request(
            method="agent",
            params={"query": "test"}
        )

        assert req["type"] == "req"
        assert req["method"] == "agent"
        assert req["params"]["query"] == "test"
        assert "id" in req

    def test_create_request_with_custom_id(self):
        """测试创建请求（自定义 ID）"""
        builder = MessageBuilder()

        req = builder.create_request(
            method="agent",
            params={"query": "test"},
            request_id="custom-id"
        )

        assert req["id"] == "custom-id"

    def test_create_request_with_idempotency_key(self):
        """测试创建请求（带幂等性密钥）"""
        builder = MessageBuilder()

        req = builder.create_request(
            method="agent",
            params={"query": "test"},
            idempotency_key="unique-key"
        )

        assert req["idempotency_key"] == "unique-key"

    def test_create_success_response(self):
        """测试创建成功响应"""
        builder = MessageBuilder()

        res = builder.create_success_response(
            request_id="req-id",
            payload={"result": "test"}
        )

        assert res["type"] == "res"
        assert res["id"] == "req-id"
        assert res["ok"] is True
        assert res["payload"]["result"] == "test"
        assert "error" not in res

    def test_create_error_response(self):
        """测试创建错误响应"""
        builder = MessageBuilder()

        err = builder.create_error_response(
            request_id="req-id",
            error_code="TEST_ERROR",
            error_message="Test error"
        )

        assert err["type"] == "res"
        assert err["id"] == "req-id"
        assert err["ok"] is False
        assert err["error"]["code"] == "TEST_ERROR"
        assert err["error"]["message"] == "Test error"

    def test_create_error_response_with_details(self):
        """测试创建错误响应（带详情）"""
        builder = MessageBuilder()

        err = builder.create_error_response(
            request_id="req-id",
            error_code="TEST_ERROR",
            error_message="Test error",
            details={"field": "value"}
        )

        assert err["error"]["details"]["field"] == "value"

    def test_create_event(self):
        """测试创建事件"""
        builder = MessageBuilder()

        event = builder.create_event(
            event_type="presence",
            payload={"user_id": "user123"},
            seq=1,
            state_version=1
        )

        assert event["type"] == "event"
        assert event["event"] == "presence"
        assert event["payload"]["user_id"] == "user123"
        assert event["seq"] == 1
        assert event["state_version"] == 1


class TestErrorCode:
    """测试错误代码"""

    def test_error_codes_exist(self):
        """测试错误代码常量存在"""
        assert hasattr(ErrorCode, 'AUTH_FAILED')
        assert hasattr(ErrorCode, 'VALIDATION_ERROR')
        assert hasattr(ErrorCode, 'INTERNAL_ERROR')
        assert hasattr(ErrorCode, 'AGENT_ERROR')

    def test_error_code_values(self):
        """测试错误代码值"""
        assert ErrorCode.AUTH_FAILED == "AUTH_FAILED"
        assert ErrorCode.TOKEN_EXPIRED == "TOKEN_EXPIRED"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.UNKNOWN_METHOD == "UNKNOWN_METHOD"
        assert ErrorCode.AGENT_EXECUTION_FAILED == "AGENT_EXECUTION_FAILED"


@pytest.mark.asyncio
class TestDedupCache:
    """测试去重缓存"""

    async def test_check_and_store_first_time(self):
        """测试第一次存储"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        is_dup, value = await cache.check_and_store("key1", {"result": "test"})

        assert is_dup is False
        assert value == {"result": "test"}

    async def test_check_and_store_duplicate(self):
        """测试重复存储"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        # 第一次
        is_dup, value = await cache.check_and_store("key1", {"result": "first"})
        assert is_dup is False

        # 第二次（重复）
        is_dup, value = await cache.check_and_store("key1", {"result": "second"})
        assert is_dup is True
        assert value == {"result": "first"}  # 返回缓存的值

    async def test_get_and_set(self):
        """测试 get 和 set"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        # get 不存在的值
        value = await cache.get("key1")
        assert value is None

        # set 值
        await cache.set("key1", {"data": "test"})

        # get 存在的值
        value = await cache.get("key1")
        assert value == {"data": "test"}

    async def test_delete(self):
        """测试删除"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        assert result is True

        result = await cache.delete("key1")
        assert result is False

    async def test_clear(self):
        """测试清空"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    async def test_get_stats(self):
        """测试获取统计"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        await cache.check_and_store("key1", "value1")
        await cache.check_and_store("key1", "value2")  # 重复
        await cache.check_and_store("key2", "value3")

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["hits"] == 1
        assert stats["misses"] == 2

    async def test_cleanup_expired(self):
        """测试清理过期"""
        from fastreact.gateway.dedup import DedupCache
        from datetime import timedelta

        cache = DedupCache(ttl=1)  # 1 秒 TTL

        await cache.set("key1", "value1")

        import asyncio
        await asyncio.sleep(2)

        await cache.cleanup()

        value = await cache.get("key1")
        assert value is None

    async def test_get_size(self):
        """测试获取大小"""
        from fastreact.gateway.dedup import DedupCache

        cache = DedupCache(ttl=300)

        size = await cache.get_size()
        assert size == 0

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        size = await cache.get_size()
        assert size == 2
