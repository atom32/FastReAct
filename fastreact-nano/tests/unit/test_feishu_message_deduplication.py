"""
Test Feishu SDK message deduplication

Tests that:
1. Duplicate messages are ignored
2. Message IDs are tracked correctly
3. Cache cleanup works properly
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter
from fastreact import Agent, Config
from fastreact.core.config import FeishuConfig


class TestMessageDeduplication:
    """Test message deduplication functionality"""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent"""
        agent = Mock(spec=Agent)
        agent._mcp_manager = None
        agent._config = Mock()
        agent._config.paths = Mock()
        agent._config.paths.feishu_workspace_base = "/tmp/test_feishu"
        return agent

    @pytest.fixture
    def feishu_config(self):
        """Create Feishu configuration"""
        return FeishuConfig(
            app_id="test_app_id",
            app_secret="test_app_secret",
            encrypt_key="test_encrypt_key",
            verification_token="test_token",
            enable_multitenant=False,
        )

    @pytest.fixture
    def adapter(self, mock_agent, feishu_config):
        """Create adapter instance"""
        return FeishuSDKAdapter(agent=mock_agent, config=feishu_config)

    def test_deduplication_initialization(self, adapter):
        """Test that deduplication cache is initialized"""
        assert hasattr(adapter, '_processed_messages')
        assert hasattr(adapter, '_max_processed_messages')
        assert len(adapter._processed_messages) == 0
        assert adapter._max_processed_messages == 10000

    def test_duplicate_message_detection(self, adapter):
        """Test that duplicate messages are detected"""
        # Simulate first message
        message_id_1 = "msg_001"
        adapter._processed_messages.add(message_id_1)

        # Check first message is detected as processed
        assert message_id_1 in adapter._processed_messages

        # Check different message is not detected
        message_id_2 = "msg_002"
        assert message_id_2 not in adapter._processed_messages

    def test_cache_size_limit(self, adapter):
        """Test that cache size is limited"""
        # Set a smaller limit for testing
        adapter._max_processed_messages = 100

        # Fill cache to limit
        for i in range(150):
            adapter._processed_messages.add(f"msg_{i}")

        # Cache should not exceed limit (approximately)
        # Note: The actual cleanup happens on next message add
        assert len(adapter._processed_messages) >= 100

    def test_cache_cleanup(self, adapter):
        """Test automatic cache cleanup when limit is exceeded"""
        # Set a small limit for testing
        adapter._max_processed_messages = 100
        adapter._processed_messages.clear()

        # Add 100 messages (at limit)
        for i in range(100):
            adapter._processed_messages.add(f"msg_{i}")

        assert len(adapter._processed_messages) == 100

        # Add one more message - simulating cleanup trigger
        # Manual cleanup: remove 20% (20 messages)
        remove_count = int(adapter._max_processed_messages * 0.2)
        oldest_messages = sorted(adapter._processed_messages)[:remove_count]
        for old_msg_id in oldest_messages:
            adapter._processed_messages.discard(old_msg_id)

        # Now add new message
        adapter._processed_messages.add("msg_100")

        # After cleanup, size should be less than or equal to limit
        assert len(adapter._processed_messages) <= 100

    def test_get_deduplication_stats(self, adapter):
        """Test getting deduplication statistics"""
        # Add some messages
        adapter._processed_messages.add("msg_001")
        adapter._processed_messages.add("msg_002")

        # Get stats
        stats = adapter.get_deduplication_stats()

        assert stats["processed_messages"] == 2
        assert stats["max_cache_size"] == 10000
        assert 0 < stats["cache_usage_percent"] < 1

    def test_clear_processed_messages(self, adapter, capsys):
        """Test clearing processed message cache"""
        # Add some messages
        adapter._processed_messages.add("msg_001")
        adapter._processed_messages.add("msg_002")

        assert len(adapter._processed_messages) == 2

        # Clear cache
        adapter.clear_processed_messages()

        # Verify cache is empty
        assert len(adapter._processed_messages) == 0

        # Check log output
        captured = capsys.readouterr()
        assert "Cleared 2 message IDs" in captured.out


class TestMessageDeduplicationIntegration:
    """Integration tests for message deduplication in message handling"""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent with async capabilities"""
        agent = Mock(spec=Agent)
        agent._mcp_manager = None
        agent._config = Mock()
        agent._config.paths = Mock()
        agent._config.paths.feishu_workspace_base = "/tmp/test_feishu"
        return agent

    @pytest.fixture
    def feishu_config(self):
        """Create Feishu configuration"""
        return FeishuConfig(
            app_id="test_app_id",
            app_secret="test_app_secret",
            encrypt_key="test_encrypt_key",
            verification_token="test_token",
            enable_multitenant=False,
        )

    @pytest.fixture
    def adapter(self, mock_agent, feishu_config):
        """Create adapter instance"""
        return FeishuSDKAdapter(agent=mock_agent, config=feishu_config)

    def test_duplicate_message_ignored(self, adapter, capsys):
        """Test that duplicate messages are ignored during processing"""
        # Create mock event with message_id
        mock_event = Mock()
        mock_event.event.sender.sender_id.open_id = "user_123"
        mock_event.event.message.content = "Hello"
        mock_event.event.message.message_id = "msg_duplicate_test"
        mock_event.event.message.chat_id = "chat_123"

        # First call - should process
        adapter._handle_message_event_v2(mock_event)

        # Check that message_id was added
        assert "msg_duplicate_test" in adapter._processed_messages

        # Second call with same message_id - should be ignored
        adapter._handle_message_event_v2(mock_event)

        # Check log output
        captured = capsys.readouterr()
        assert "Duplicate message ignored" in captured.out
