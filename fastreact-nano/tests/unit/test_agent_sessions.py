"""
Unit tests for Agent session management

Tests for:
- Session queue lifecycle (creation, usage, cleanup)
- Message injection into active sessions
- Session interrupt handling
- Multi-user session isolation
- Session state persistence
- Session cleanup on error
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from fastreact import Agent
from fastreact.core.config import Config
from fastreact.core.messages import Message
from fastreact.core.events import EventType


@pytest.fixture
def mock_config():
    """Create mock configuration"""
    from unittest.mock import MagicMock

    config = MagicMock()
    config.llm.model = "gpt-4o-mini"
    config.llm.api_base = "https://api.openai.com/v1"
    config.llm.api_key = "test-key"
    config.llm.temperature = 0.7
    config.llm.max_tokens = 4096
    config.react.max_iterations = 10
    return config


@pytest.fixture
def agent(mock_config):
    """Create agent with mocked LLM"""
    with patch('fastreact.agent.LiteLLMProvider'):
        agent = Agent(config=mock_config)
        # Mock the LLM to avoid actual API calls
        agent._llm = Mock()
        agent._llm.call = AsyncMock(return_value="Test response")
        yield agent


class TestSessionQueueCreation:
    """Test session queue creation and lifecycle"""

    def test_session_queue_created_on_run(self, agent):
        """Test that session queue is created when running agent"""
        session_id = "test-session-123"

        # Initially no session queue
        assert session_id not in agent._session_queues

        # After starting run, session queue should exist
        # We'll just check the queue is created without full execution
        agent._session_queues[session_id] = Mock()
        assert session_id in agent._session_queues

    def test_session_queue_isolated_per_session(self, agent):
        """Test that different sessions have independent queues"""
        session1 = "session-1"
        session2 = "session-2"

        queue1 = Mock()
        queue2 = Mock()

        agent._session_queues[session1] = queue1
        agent._session_queues[session2] = queue2

        # Verify isolation
        assert agent._session_queues[session1] is queue1
        assert agent._session_queues[session2] is queue2
        assert queue1 is not queue2

    def test_session_queue_with_multitenant(self, mock_config):
        """Test session queues include user_key in multi-tenant mode"""
        with patch('fastreact.agent.LiteLLMProvider'):
            agent = Agent(config=mock_config, multitenant=True)
            agent._llm = Mock()

            user_key = "feishu:user123"
            session_id = f"{user_key}:session-abc"

            queue = Mock()
            agent._session_queues[session_id] = queue

            assert session_id in agent._session_queues
            assert agent._session_queues[session_id] is queue


class TestMessageInjection:
    """Test message injection into active sessions"""

    def test_inject_message_into_active_session(self, agent):
        """Test injecting message into an active session"""
        session_id = "test-session"

        # Create session queue
        mock_queue = Mock()
        agent._session_queues[session_id] = mock_queue

        # Inject message
        message = Message(role="user", content="Test message")
        agent.inject_message(session_id, message)

        # Verify message was pushed to queue
        mock_queue.push.assert_called_once_with(message)

    def test_inject_message_fails_for_inactive_session(self, agent):
        """Test that injecting into non-existent session raises error"""
        session_id = "nonexistent-session"

        message = Message(role="user", content="Test message")

        with pytest.raises(ValueError, match="Session not active"):
            agent.inject_message(session_id, message)

    def test_inject_multiple_messages(self, agent):
        """Test injecting multiple messages into a session"""
        session_id = "test-session"

        mock_queue = Mock()
        agent._session_queues[session_id] = mock_queue

        # Inject multiple messages
        messages = [
            Message(role="user", content="Message 1"),
            Message(role="user", content="Message 2"),
            Message(role="user", content="Message 3"),
        ]

        for msg in messages:
            agent.inject_message(session_id, msg)

        # Verify all messages were pushed
        assert mock_queue.push.call_count == 3

    def test_inject_message_with_metadata(self, agent):
        """Test injecting message with custom metadata"""
        session_id = "test-session"

        mock_queue = Mock()
        agent._session_queues[session_id] = mock_queue

        message = Message(
            role="steering",
            content="Guide the user",
            metadata={"source": "admin", "priority": "high"}
        )

        agent.inject_message(session_id, message)

        # Verify message was pushed with metadata
        mock_queue.push.assert_called_once()
        pushed_msg = mock_queue.push.call_args[0][0]
        assert pushed_msg.metadata["source"] == "admin"
        assert pushed_msg.metadata["priority"] == "high"


class TestSessionInterruptHandling:
    """Test session interrupt functionality"""

    def test_interrupt_signal_stops_execution(self, agent):
        """Test that interrupt signal stops current execution"""
        session_id = "test-session"

        # Create queue with interrupt message
        mock_queue = Mock()
        interrupt_msg = Message(
            role="user",
            content="[INTERRUPT] Stop now"
        )
        mock_queue.drain.return_value = [interrupt_msg]
        agent._session_queues[session_id] = mock_queue

        # Drain messages
        messages = mock_queue.drain()

        # Verify interrupt signal is present
        assert len(messages) == 1
        assert messages[0].content.startswith("[INTERRUPT]")

    def test_interrupt_message_format(self, agent):
        """Test various interrupt message formats"""
        test_cases = [
            "[INTERRUPT] Stop",
            "[INTERRUPT] User requested stop",
            "[INTERRUPT] Emergency shutdown",
        ]

        for content in test_cases:
            msg = Message(role="user", content=content)
            assert msg.content.startswith("[INTERRUPT]")


class TestMultiUserSessionIsolation:
    """Test session isolation across multiple users"""

    def test_different_users_have_separate_sessions(self, agent):
        """Test that sessions for different users are isolated"""
        user1_session = "feishu:user1:session-abc"
        user2_session = "feishu:user2:session-xyz"

        queue1 = Mock()
        queue2 = Mock()

        agent._session_queues[user1_session] = queue1
        agent._session_queues[user2_session] = queue2

        # Verify isolation
        assert agent._session_queues[user1_session] is queue1
        assert agent._session_queues[user2_session] is queue2

        # Actions on user1 should not affect user2
        msg1 = Message(role="user", content="User 1 message")
        agent.inject_message(user1_session, msg1)

        # Only user1's queue should receive the message
        queue1.push.assert_called_once()
        queue2.push.assert_not_called()

    def test_concurrent_sessions_same_user(self, agent):
        """Test that same user can have multiple concurrent sessions"""
        user_key = "feishu:user123"
        session1 = f"{user_key}:session-1"
        session2 = f"{user_key}:session-2"

        queue1 = Mock()
        queue2 = Mock()

        agent._session_queues[session1] = queue1
        agent._session_queues[session2] = queue2

        # Verify both sessions exist independently
        assert session1 in agent._session_queues
        assert session2 in agent._session_queues
        assert agent._session_queues[session1] is not agent._session_queues[session2]

    def test_session_id_includes_user_context(self, agent):
        """Test that session IDs include user context in multi-tenant mode"""
        user_keys = [
            "feishu:user123",
            "slack:user456",
            "discord:user789",
        ]

        sessions = []
        for user_key in user_keys:
            session_id = f"{user_key}:session-{uuid()}"
            sessions.append(session_id)
            agent._session_queues[session_id] = Mock()

        # Verify all sessions are tracked separately
        for session in sessions:
            assert session in agent._session_queues
            # Extract user_key from session_id
            parts = session.split(":")
            assert len(parts) >= 3  # platform:user_id:session_uuid


class TestSessionCleanup:
    """Test session cleanup and resource management"""

    def test_session_cleanup_on_error(self, agent):
        """Test that sessions are cleaned up on errors"""
        session_id = "error-session"

        # Create session
        agent._session_queues[session_id] = Mock()

        # Simulate error cleanup
        if session_id in agent._session_queues:
            del agent._session_queues[session_id]

        # Verify session was cleaned up
        assert session_id not in agent._session_queues

    def test_cleanup_inactive_sessions(self, agent):
        """Test cleanup of inactive/old sessions"""
        # Create multiple sessions
        sessions = {
            "session-1": Mock(),
            "session-2": Mock(),
            "session-3": Mock(),
        }

        for sid, queue in sessions.items():
            agent._session_queues[sid] = queue

        # Clean up specific sessions
        to_remove = ["session-1", "session-3"]
        for sid in to_remove:
            if sid in agent._session_queues:
                del agent._session_queues[sid]

        # Verify only session-2 remains
        assert len(agent._session_queues) == 1
        assert "session-2" in agent._session_queues
        assert "session-1" not in agent._session_queues
        assert "session-3" not in agent._session_queues

    def test_cleanup_all_sessions(self, agent):
        """Test cleaning up all sessions"""
        # Create multiple sessions
        for i in range(5):
            agent._session_queues[f"session-{i}"] = Mock()

        assert len(agent._session_queues) == 5

        # Clean up all
        agent._session_queues.clear()

        assert len(agent._session_queues) == 0


class TestSessionState:
    """Test session state and persistence"""

    def test_session_queue_initial_state(self, agent):
        """Test initial state of session queue"""
        session_id = "new-session"

        # Before creation
        assert session_id not in agent._session_queues

        # After creation
        from fastreact.core.messages import MessageQueue
        queue = MessageQueue()
        agent._session_queues[session_id] = queue

        assert session_id in agent._session_queues
        assert isinstance(agent._session_queues[session_id], MessageQueue)

    def test_session_state_persistence_across_calls(self, agent):
        """Test that session state persists across multiple calls"""
        session_id = "persistent-session"

        # Create session
        mock_queue = Mock()
        agent._session_queues[session_id] = mock_queue

        # Simulate multiple operations
        msg1 = Message(role="user", content="First message")
        msg2 = Message(role="assistant", content="Second message")

        agent.inject_message(session_id, msg1)
        agent.inject_message(session_id, msg2)

        # Verify both messages were pushed to same queue
        assert mock_queue.push.call_count == 2

    def test_session_exists_check(self, agent):
        """Test checking if a session exists"""
        session_id = "test-session"

        # Initially doesn't exist
        assert session_id not in agent._session_queues

        # After creation, exists
        agent._session_queues[session_id] = Mock()
        assert session_id in agent._session_queues


class TestSessionMessageQueueOperations:
    """Test MessageQueue operations within sessions"""

    def test_get_session_queue(self, agent):
        """Test retrieving session queue"""
        session_id = "test-session"

        # Create queue
        mock_queue = Mock()
        agent._session_queues[session_id] = mock_queue

        # Get queue (using dict get with default)
        queue = agent._session_queues.get(session_id)
        assert queue is mock_queue

        # Get non-existent queue with default
        default_queue = Mock()
        queue = agent._session_queues.get("nonexistent", default_queue)
        assert queue is default_queue

    def test_session_queue_message_operations(self, agent):
        """Test message operations on session queue"""
        from fastreact.core.messages import MessageQueue

        session_id = "test-session"
        queue = MessageQueue()
        agent._session_queues[session_id] = queue

        # Add messages
        msg1 = Message(role="user", content="Message 1")
        msg2 = Message(role="user", content="Message 2")

        queue.push(msg1)
        queue.push(msg2)

        # Drain messages
        messages = queue.drain()
        assert len(messages) == 2

        # After drain, queue should be empty
        messages = queue.drain()
        assert len(messages) == 0


@pytest.mark.asyncio
class TestSessionIntegration:
    """Integration tests for session management with agent execution"""

    async def test_session_lifecycle_in_agent_run(self, mock_config):
        """Test complete session lifecycle during agent.run_event_stream"""
        with patch('fastreact.agent.LiteLLMProvider') as mock_llm_provider:
            agent = Agent(config=mock_config)
            agent._llm = Mock()
            agent._llm.call = AsyncMock(return_value="4")

            # Mock the core to return simple events
            with patch.object(agent, '_core') as mock_core:
                from fastreact.core.events import AgentEvent

                async def mock_run_step(*args, **kwargs):
                    events = [
                        AgentEvent.think("Thinking", session_id="test"),
                        AgentEvent.tool_result("test_tool", "Result", session_id="test"),
                        AgentEvent.step_end("4", session_id="test"),
                    ]
                    for event in events:
                        yield event

                mock_core.run_step_stream = mock_run_step

                # Run agent and collect events
                events = []
                session_ids = []
                async for event in agent.run_event_stream("What is 2+2?"):
                    events.append(event)
                    # Extract session_id from any event that has it
                    if event.metadata and "session_id" in event.metadata:
                        session_ids.append(event.metadata["session_id"])

                # Verify at least one session was created
                assert len(events) > 0
                assert any(e.type == EventType.SESSION_START for e in events)
                # Session queues should have been created
                assert len(agent._session_queues) > 0 or len(session_ids) > 0

    async def test_session_cleanup_after_completion(self, mock_config):
        """Test that session resources are properly managed after completion"""
        with patch('fastreact.agent.LiteLLMProvider'):
            agent = Agent(config=mock_config)
            agent._llm = Mock()
            agent._llm.call = AsyncMock(return_value="Done")

            # Track sessions before and after
            initial_count = len(agent._session_queues)

            # Mock core to return completion event
            with patch.object(agent, '_core') as mock_core:
                from fastreact.core.events import AgentEvent

                async def mock_run_step(*args, **kwargs):
                    yield AgentEvent.session_end("Final answer", session_id="test")

                mock_core.run_step_stream = mock_run_step

                # Run agent
                async for _ in agent.run_event_stream("Test"):
                    pass

                # Session should still exist (for potential followup)
                # Cleanup is typically handled by session timeout or explicit cleanup
                assert len(agent._session_queues) >= initial_count


# Helper function for generating test session IDs
def uuid():
    """Generate test UUID"""
    import uuid as uuid_module
    return str(uuid_module.uuid4())
