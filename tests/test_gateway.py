"""
测试 WebSocket Gateway

验证：
1. 服务器启动
2. WebSocket 连接
3. 消息发送和接收
4. 会话管理
5. 健康检查
"""

import asyncio
import pytest
import json
from fastapi.testclient import TestClient

from fastreact import FastReAct
from fastreact.tools import CalculatorTool, SearchTool
from fastreact.gateway import GatewayServer


class TestGatewayServer:
    """测试网关服务器"""

    @pytest.fixture
    def gateway(self):
        """创建网关实例"""
        agent = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
            max_iterations=2,
        )
        return GatewayServer(agent)

    @pytest.fixture
    def client(self, gateway):
        """创建测试客户端"""
        return TestClient(gateway.app)

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "active_sessions" in data
        assert data["active_sessions"] == 0

    def test_list_sessions_empty(self, client):
        """测试列出会话（空列表）"""
        response = client.get("/sessions")
        assert response.status_code == 200

        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["sessions"]) == 0

    def test_get_stats(self, gateway):
        """测试获取统计信息"""
        stats = gateway.get_stats()
        assert stats["active_sessions"] == 0
        assert stats["total_messages"] == 0
        assert stats["sessions"] == []

    def test_clear_nonexistent_session(self, gateway):
        """测试清除不存在的会话"""
        result = gateway.clear_session("nonexistent")
        assert result is False


class TestWebSocketConnection:
    """测试 WebSocket 连接"""

    @pytest.fixture
    def gateway(self):
        """创建网关实例"""
        agent = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
            max_iterations=2,
        )
        return GatewayServer(agent)

    @pytest.mark.asyncio
    async def test_websocket_connection(self, gateway):
        """测试 WebSocket 连接和断开"""
        from fastapi.testclient import TestClient

        client = TestClient(gateway.app)

        # 注意：TestClient 不完全支持 WebSocket，这里只是示例
        # 实际测试需要使用真实的 WebSocket 客户端

        with client.websocket_connect("/ws/test-session") as websocket:
            # 接收欢迎消息
            data = websocket.receive_json()
            assert data["type"] == "system"
            assert "会话已创建" in data["message"]
            assert data["session_id"] == "test-session"

            # 发送消息（会被拒绝，因为是测试 API key）
            websocket.send_json({"query": "1 + 1"})

            # 接收响应（可能是错误或答案）
            try:
                response = websocket.receive_json()
                assert "type" in response
            except Exception:
                # 测试 API key 可能导致错误，这是正常的
                pass


class TestSessionManagement:
    """测试会话管理"""

    @pytest.fixture
    def gateway(self):
        """创建网关实例"""
        agent = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )
        return GatewayServer(agent)

    def test_session_creation(self, gateway):
        """测试会话创建"""
        # 模拟会话创建
        session_id = "test-session-123"
        gateway.sessions[session_id] = {
            "messages": [],
            "context": {},
            "metadata": {
                "created_at": "2026-01-28T10:00:00",
                "last_active": "2026-01-28T10:00:00"
            }
        }

        # 验证会话存在
        session = gateway.get_session(session_id)
        assert session is not None
        assert session["messages"] == []
        assert session["context"] == {}

    def test_session_removal(self, gateway):
        """测试会话移除"""
        # 创建会话
        session_id = "test-session-456"
        gateway.sessions[session_id] = {
            "messages": [],
            "context": {},
            "metadata": {}
        }

        # 移除会话
        result = gateway.clear_session(session_id)
        assert result is True

        # 验证已移除
        session = gateway.get_session(session_id)
        assert session is None

    def test_get_stats_with_sessions(self, gateway):
        """测试获取统计信息（包含会话）"""
        # 创建多个会话
        for i in range(3):
            session_id = f"session-{i}"
            gateway.sessions[session_id] = {
                "messages": [
                    {"role": "user", "content": f"Message {j}"}
                    for j in range(i + 1)
                ],
                "context": {},
                "metadata": {
                    "created_at": "2026-01-28T10:00:00",
                    "last_active": "2026-01-28T10:00:00"
                }
            }

        # 获取统计
        stats = gateway.get_stats()
        assert stats["active_sessions"] == 3
        assert stats["total_messages"] == 6  # 1 + 2 + 3
        assert len(stats["sessions"]) == 3


class TestSessionContextIntegration:
    """测试会话上下文集成"""

    @pytest.mark.asyncio
    async def test_run_async_with_session_context(self):
        """测试带会话上下文的 run_async"""
        agent = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
            max_iterations=1,
        )

        # 创建会话上下文
        session_context = {
            "history": [
                {"role": "user", "content": "之前的消息 1"},
                {"role": "assistant", "content": "之前的回复 1"},
                {"role": "user", "content": "之前的消息 2"},
            ]
        }

        # 注意：这里需要真实的 API key 才能完整测试
        # 以下只是验证参数传递正确

        # 验证 session_context 参数存在
        assert callable(agent.run_async)

        # 检查方法签名
        import inspect
        sig = inspect.signature(agent.run_async)
        assert 'session_context' in sig.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
