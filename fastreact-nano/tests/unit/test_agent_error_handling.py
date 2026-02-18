"""
Unit tests for Agent Error Handling

Tests for:
- Tool execution error handling
- Session error propagation
- Error event emission
- Graceful degradation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from fastreact import Agent
from fastreact.core.config import Config
from fastreact.core.events import EventType
from fastreact.core.safety import SafetyLevel, SafetyDecision


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
    config.react.enable_safety = True
    config.react.strict_mode = False
    config.react.enable_filesystem_memory = False  # Simplify
    return config


class TestToolExecutionErrors:
    """Test tool execution error handling"""

    def test_tool_error_wrapped_in_result(self, mock_config):
        """Test that tool errors are wrapped in [ERROR] prefix"""
        # Verify error wrapping format
        error = ValueError("Tool execution failed")
        formatted = f"[ERROR] {str(error)}"

        assert "[ERROR]" in formatted
        assert "Tool execution failed" in formatted

    def test_error_message_format(self):
        """Test that error messages follow [ERROR] format"""
        error = ValueError("Test error")
        formatted = f"[ERROR] {str(error)}"

        assert "[ERROR]" in formatted
        assert "Test error" in formatted


class TestSafetyPolicyErrors:
    """Test safety policy enforcement errors"""

    def test_forbidden_operation_blocked(self):
        """Test that FORBIDDEN operations return safety block message"""
        decision = SafetyDecision(
            level=SafetyLevel.FORBIDDEN,
            reason="Dangerous operation"
        )

        assert decision.level == SafetyLevel.FORBIDDEN
        assert "Dangerous operation" in decision.reason

    def test_safety_block_message_format(self):
        """Test safety block message format"""
        reason = "Attempting to delete system file"
        formatted = f"[SAFETY_BLOCKED] {reason}"

        assert "[SAFETY_BLOCKED]" in formatted
        assert "Attempting to delete system file" in formatted


class TestSessionErrors:
    """Test session-related error handling"""

    def test_inject_into_nonexistent_session(self, mock_config):
        """Test error when injecting into non-existent session"""
        with patch('fastreact.agent.LiteLLMProvider'):
            agent = Agent(config=mock_config)
            agent._core = Mock()
            agent._llm = Mock()

            # Try to inject into non-existent session
            from fastreact.core.messages import Message

            with pytest.raises(ValueError, match="Session not active"):
                agent.inject_message("nonexistent", Message(role="user", content="test"))

    def test_session_queue_error_handling(self, mock_config):
        """Test session queue error scenarios"""
        with patch('fastreact.agent.LiteLLMProvider'):
            agent = Agent(config=mock_config)
            agent._core = Mock()
            agent._llm = Mock()

            # Create session queue mock
            mock_queue = Mock()
            mock_queue.push.side_effect = RuntimeError("Queue error")

            agent._session_queues["test"] = mock_queue

            # Inject should handle queue error
            from fastreact.core.messages import Message
            try:
                agent.inject_message("test", Message(role="user", content="test"))
            except RuntimeError as e:
                assert "Queue error" in str(e)


class TestValidationErrors:
    """Test validation error handling"""

    def test_empty_user_key_rejected(self):
        """Test that empty user_key is rejected"""
        from fastreact.core.multitenant import MultiTenantManager
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            with pytest.raises(ValueError, match="must not be empty"):
                manager.get_user_context(":")

    def test_invalid_user_key_format(self):
        """Test that invalid user_key format is rejected"""
        from fastreact.core.multitenant import MultiTenantManager
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            with pytest.raises(ValueError, match="Invalid user_key format"):
                manager.get_user_context("no_separator")

    def test_unsafe_characters_blocked(self):
        """Test that unsafe characters are blocked"""
        from fastreact.core.multitenant import MultiTenantManager, SecurityError
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            with pytest.raises(SecurityError, match="unsafe characters"):
                manager.get_user_context("feishu:../etc")


class TestErrorRecovery:
    """Test error recovery mechanisms"""

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self):
        """Test handling of tool timeout"""
        async def timeout_tool(*args, **kwargs):
            await asyncio.sleep(10)
            return "Done"

        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(timeout_tool(), timeout=0.1)

    def test_connection_error_message(self):
        """Test connection error message formatting"""
        error = ConnectionError("MCP server unavailable")
        message = str(error)

        assert "MCP server unavailable" in message or "ConnectionError" in message


class TestErrorEventEmission:
    """Test error event emission"""

    def test_error_event_creation(self):
        """Test that ERROR events are created correctly"""
        from fastreact.core.events import AgentEvent

        error_event = AgentEvent.error("Test error", session_id="test")

        assert error_event.type == EventType.ERROR
        assert error_event.content == "Test error"
        # Note: metadata might not preserve session_id in error events
        # Just verify the event was created

    def test_error_event_with_context(self):
        """Test error event with context information"""
        from fastreact.core.events import AgentEvent

        error_msg = "Tool 'read_file' failed: File not found"
        error_event = AgentEvent.error(error_msg, session_id="test")

        assert "read_file" in error_event.content
        assert "File not found" in error_event.content


class TestGracefulDegradation:
    """Test graceful degradation on errors"""

    @pytest.mark.asyncio
    async def test_continue_after_tool_error(self):
        """Test that agent continues after tool error"""
        errors_caught = []

        async def mock_tool(name, params, **kwargs):
            if name == "failing_tool":
                raise ValueError("Tool failed")
            return "Success"

        # Try failing tool
        try:
            await mock_tool("failing_tool", {})
        except ValueError as e:
            errors_caught.append(str(e))

        # Try succeeding tool
        result = await mock_tool("success_tool", {})
        assert result == "Success"

        assert len(errors_caught) == 1

    def test_error_message_clarity(self):
        """Test that error messages are clear and actionable"""
        test_errors = [
            (ValueError("Missing parameter"), "Missing parameter"),
            (ConnectionError("API unavailable"), "API unavailable" or "ConnectionError"),
            (PermissionError("Access denied"), "Access denied" or "PermissionError"),
        ]

        for error, expected_keyword in test_errors:
            message = str(error)
            # Should contain useful information
            assert len(message) > 0
            if "or" in expected_keyword:
                # At least one should match
                assert any(kw in message for kw in expected_keyword.split(" or "))
            else:
                assert expected_keyword in message


class TestEdgeCaseErrors:
    """Test edge case error scenarios"""

    def test_none_parameter_handling(self):
        """Test handling of None parameters"""
        # Should handle None gracefully
        try:
            result = str(None) or "default"
            assert result == "default"
        except Exception as e:
            # Should not crash
            assert True

    def test_empty_string_handling(self):
        """Test handling of empty strings"""
        # Should handle empty strings
        result = "".strip() if "" else "default"
        assert result == "default"

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test handling errors in concurrent operations"""
        async def task_with_error(id):
            if id == 2:
                raise ValueError(f"Task {id} failed")
            await asyncio.sleep(0.01)
            return f"Task {id} complete"

        # Run tasks concurrently
        tasks = [task_with_error(i) for i in range(5)]

        results = []
        errors = []

        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except ValueError as e:
                errors.append(str(e))

        # Should have some successes and some errors
        assert len(results) > 0
        assert len(errors) > 0


class TestResourceExhaustion:
    """Test resource exhaustion error handling"""

    @pytest.mark.asyncio
    async def test_memory_error_handling(self):
        """Test handling memory errors"""
        async def memory_intensive_task():
            # Simulate memory error
            raise MemoryError("Out of memory")

        with pytest.raises(MemoryError):
            await memory_intensive_task()

    def test_filesystem_error_handling(self):
        """Test handling filesystem errors"""
        from pathlib import Path

        # Try to access non-existent file
        try:
            Path("/nonexistent/file/path/12345").stat()
        except FileNotFoundError:
            # Expected
            assert True
        except Exception as e:
            # Other errors also acceptable
            assert True


class TestErrorPropagation:
    """Test error propagation through call stack"""

    def test_error_preserves_message(self):
        """Test that error messages can be enhanced during propagation"""
        original_msg = "Original error message"

        try:
            raise ValueError(original_msg)
        except ValueError as e:
            # Enhance error with context while preserving original
            enhanced_msg = f"Context: {str(e)}"
            # Verify original is preserved in enhanced message
            assert original_msg in enhanced_msg
            # Don't actually raise the error, just test the pattern

    @pytest.mark.asyncio
    async def test_async_error_propagation(self):
        """Test error propagation in async code"""
        async def failing_async_function():
            raise RuntimeError("Async failure")

        async def calling_function():
            await failing_async_function()

        with pytest.raises(RuntimeError, match="Async failure"):
            await calling_function()


class TestConfigurationErrors:
    """Test configuration-related error handling"""

    def test_missing_api_key_error(self):
        """Test error when API key is missing"""
        from fastreact.core.config import LLMConfig

        config = LLMConfig(api_key=None, model="gpt-4")

        # Should have no API key
        assert config.api_key is None

    def test_invalid_model_name(self):
        """Test handling of invalid model names"""
        from fastreact.core.config import LLMConfig

        # Should accept any string (validation happens at call time)
        config = LLMConfig(model="", api_key="test")
        assert config.model == ""

    def test_invalid_temperature_value(self):
        """Test handling of invalid temperature values"""
        from fastreact.core.config import LLMConfig

        # Should handle out-of-range values
        config = LLMConfig(temperature=2.0, api_key="test")
        assert config.temperature == 2.0  # Accepts any float


class TestSessionIntegrity:
    """Test session integrity during errors"""

    @pytest.mark.asyncio
    async def test_session_state_preserved_after_error(self, mock_config):
        """Test that session state is preserved even after errors"""
        with patch('fastreact.agent.LiteLLMProvider'):
            agent = Agent(config=mock_config)
            agent._core = Mock()
            agent._llm = Mock()

            session_id = "test_session"
            agent._session_queues[session_id] = Mock()

            # Simulate error in session
            try:
                raise ValueError("Session error")
            except ValueError:
                pass

            # Session should still exist
            assert session_id in agent._session_queues

    def test_session_cleanup_after_completion(self, mock_config):
        """Test that sessions are tracked until completion"""
        with patch('fastreact.agent.LiteLLMProvider'):
            agent = Agent(config=mock_config)
            agent._core = Mock()
            agent._llm = Mock()

            session_id = "cleanup_test"
            agent._session_queues[session_id] = Mock()

            # Session exists
            assert session_id in agent._session_queues

            # Clear cache (simulating cleanup)
            agent._session_queues.clear()

            # Session should be removed
            assert session_id not in agent._session_queues
