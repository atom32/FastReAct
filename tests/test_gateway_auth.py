"""
测试 Gateway 认证系统
"""

import pytest
from fastreact.gateway.auth import GatewayAuth
import jwt


class TestGatewayAuth:
    """测试 GatewayAuth 类"""

    def test_no_auth_development_mode(self):
        """测试开发模式（无认证）"""
        auth = GatewayAuth()
        assert auth.has_auth is False

    def test_static_token_auth(self):
        """测试静态 token 认证"""
        auth = GatewayAuth(token="test-token-123")

        class DummyWebSocket:
            async def close(self, code, reason):
                pass

        ws = DummyWebSocket()

        # 正确的 token
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, token="test-token-123"
        )
        assert authenticated is True
        assert user_id == "static_token"
        assert metadata["mode"] == "static_token"

        # 错误的 token
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, token="wrong-token"
        )
        assert authenticated is False
        assert user_id is None

    def test_password_auth(self):
        """测试密码认证"""
        auth = GatewayAuth(password="test-password")

        class DummyWebSocket:
            async def close(self, code, reason):
                pass

        ws = DummyWebSocket()

        # 正确的密码
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, password="test-password"
        )
        assert authenticated is True
        assert user_id == "password"
        assert metadata["mode"] == "password"

        # 错误的密码
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, password="wrong-password"
        )
        assert authenticated is False

    def test_jwt_generation_and_verification(self):
        """测试 JWT 生成和验证"""
        auth = GatewayAuth()

        # 生成 token
        token = auth.generate_token("user123", expires_in=3600)

        assert isinstance(token, str)
        assert len(token) > 0

        # 验证 token
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "user123"
        assert "exp" in payload
        assert "iat" in payload

    def test_jwt_expiration(self):
        """测试 JWT 过期"""
        auth = GatewayAuth()

        # 生成已过期的 token
        token = auth.generate_token("user123", expires_in=-1)

        # 验证应该失败
        payload = auth.verify_token(token)
        assert payload is None

    def test_jwt_auth_via_websocket(self):
        """测试通过 WebSocket 使用 JWT 认证"""
        # 使用空的 static_token 来启用 JWT 认证（但需要 has_auth=True）
        auth = GatewayAuth(token="dummy", enable_jwt=True)

        class DummyWebSocket:
            async def close(self, code, reason):
                pass

        ws = DummyWebSocket()

        # 生成有效 token（使用真实的 secret）
        token = auth.generate_token("user123", expires_in=3600)

        # 使用 token 认证
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, token=token
        )
        assert authenticated is True
        assert user_id == "user123"
        assert metadata["mode"] == "jwt"

        # 使用过期 token
        expired_token = auth.generate_token("user123", expires_in=-1)
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, token=expired_token
        )
        assert authenticated is False

    def test_api_key_auth(self):
        """测试 API 密钥认证"""
        api_keys = {
            "key123": {"user_id": "user1", "name": "Test Key"},
            "key456": {"user_id": "user2", "name": "Prod Key"}
        }
        auth = GatewayAuth(api_keys=api_keys)

        class DummyWebSocket:
            async def close(self, code, reason):
                pass

        ws = DummyWebSocket()

        # 有效的 API key
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, api_key="key123"
        )
        assert authenticated is True
        assert user_id == "user1"
        assert metadata["name"] == "Test Key"

        # 无效的 API key
        authenticated, user_id, metadata = auth.authenticate_websocket(
            ws, api_key="invalid-key"
        )
        assert authenticated is False

    def test_session_management(self):
        """测试会话管理"""
        auth = GatewayAuth()

        # 创建会话
        session_id = auth.create_session("user123", metadata={"ip": "127.0.0.1"})
        assert session_id is not None
        assert len(session_id) > 0

        # 验证会话
        assert auth.validate_session(session_id) is True
        assert auth.validate_session("nonexistent") is False

        # 获取会话
        session = auth.get_session(session_id)
        assert session is not None
        assert session["user_id"] == "user123"
        assert session["metadata"]["ip"] == "127.0.0.1"

        # 撤销会话
        result = auth.revoke_session(session_id)
        assert result is True
        assert auth.validate_session(session_id) is False

        # 再次撤销应该失败
        result = auth.revoke_session(session_id)
        assert result is False

    def test_list_sessions(self):
        """测试列出会话"""
        auth = GatewayAuth()

        # 创建多个会话
        session1 = auth.create_session("user1")
        session2 = auth.create_session("user2")
        session3 = auth.create_session("user1")

        # 列出所有会话
        sessions = auth.list_sessions()
        assert len(sessions) == 3

        # 过滤特定用户
        user1_sessions = auth.list_sessions(user_id="user1")
        assert len(user1_sessions) == 2
        assert all(s["user_id"] == "user1" for s in user1_sessions)

    def test_cleanup_expired_sessions(self):
        """测试清理过期会话"""
        auth = GatewayAuth()

        # 创建会话
        session_id = auth.create_session("user123")

        # 清理（会话未过期，不应删除）
        count = auth.cleanup_expired_sessions(max_age_hours=24)
        assert count == 0
        assert auth.validate_session(session_id) is True

        # 手动设置 created_at 为过去
        import datetime
        from datetime import timedelta
        auth.active_sessions[session_id]["created_at"] = datetime.datetime.utcnow() - timedelta(hours=25)

        # 清理（应该删除过期会话）
        count = auth.cleanup_expired_sessions(max_age_hours=24)
        assert count == 1
        assert auth.validate_session(session_id) is False

    def test_api_key_management(self):
        """测试 API 密钥管理"""
        auth = GatewayAuth()

        # 添加 API key
        auth.add_api_key("key123", "user1", name="Test Key")
        assert "key123" in auth.api_keys
        assert auth.api_keys["key123"]["user_id"] == "user1"

        # 移除 API key
        result = auth.remove_api_key("key123")
        assert result is True
        assert "key123" not in auth.api_keys

        # 移除不存在的 key
        result = auth.remove_api_key("nonexistent")
        assert result is False

    def test_get_stats(self):
        """测试获取统计信息"""
        # 无认证
        auth1 = GatewayAuth()
        stats1 = auth1.get_stats()
        assert stats1["has_auth"] is False
        assert stats1["active_sessions"] == 0

        # 有认证
        auth2 = GatewayAuth(token="test", password="pass")
        auth2.create_session("user1")
        auth2.create_session("user2")

        stats2 = auth2.get_stats()
        assert stats2["has_auth"] is True
        assert stats2["auth_methods"]["static_token"] is True
        assert stats2["auth_methods"]["password"] is True
        assert stats2["active_sessions"] == 2


@pytest.mark.asyncio
class TestGatewayAuthAsync:
    """测试异步功能"""

    async def test_close_unauthorized(self):
        """测试关闭未授权连接"""
        auth = GatewayAuth(token="test-token")

        class MockWebSocket:
            def __init__(self):
                self.closed = False
                self.code = None
                self.reason = None

            async def close(self, code, reason):
                self.closed = True
                self.code = code
                self.reason = reason

        ws = MockWebSocket()
        await auth.close_unauthorized(ws, "Test reason")

        assert ws.closed is True
        assert ws.code == 1008  # WS_1008_POLICY_VIOLATION
        assert ws.reason == "Test reason"
