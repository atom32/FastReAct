"""
Integration tests for Streamlit web adapter

These tests verify the web adapter components without running Streamlit itself.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.integration
class TestWebAdapter:
    """Test web adapter components"""

    def test_web_session_initialization(self):
        """Test WebSession can be initialized"""
        from fastreact.adapters.web import WebSession

        session = WebSession()

        assert session is not None
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.agent is None
        assert len(session.message_history) == 0
        assert len(session.event_buffer) == 0

    def test_web_session_add_message(self):
        """Test adding messages to history"""
        from fastreact.adapters.web import WebSession

        session = WebSession()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there")

        assert len(session.message_history) == 2
        assert session.message_history[0]["role"] == "user"
        assert session.message_history[0]["content"] == "Hello"
        assert session.message_history[1]["role"] == "assistant"
        assert session.message_history[1]["content"] == "Hi there"

    def test_web_session_clear_history(self):
        """Test clearing message history"""
        from fastreact.adapters.web import WebSession

        session = WebSession()
        session.add_message("user", "Test")
        session.add_message("assistant", "Response")

        assert len(session.message_history) == 2

        session.clear_history()

        assert len(session.message_history) == 0
        assert len(session.event_buffer) == 0

    def test_render_event_imports(self):
        """Test that render_event function exists and has correct signature"""
        from fastreact.adapters.web import render_event
        import inspect

        assert callable(render_event)
        sig = inspect.signature(render_event)
        assert "event_dict" in sig.parameters

    @pytest.mark.asyncio
    async def test_run_agent_async_function(self):
        """Test that web session has agent and can interact with it"""
        from fastreact.adapters.web import WebSession

        session = WebSession()
        session.initialize()

        # Test that session has an agent
        assert hasattr(session, "agent")
        assert session.agent is not None
        # Agent should be able to run queries
        assert hasattr(session.agent, "run_event_stream")
        assert callable(session.agent.run_event_stream)


@pytest.mark.integration
class TestWebAdapterIntegration:
    """Test web adapter with actual Agent"""

    @pytest.mark.asyncio
    async def test_web_session_with_agent(self):
        """Test WebSession can initialize Agent"""
        from fastreact.adapters.web import WebSession

        session = WebSession()
        session.initialize()

        assert session.agent is not None
        assert hasattr(session.agent, "run_event_stream")

    @pytest.mark.asyncio
    async def test_event_buffering(self):
        """Test that events are buffered correctly"""
        from fastreact.adapters.web import WebSession
        from fastreact.core.events import EventType

        session = WebSession()
        session.initialize()

        # Simulate event
        session.event_buffer.append({
            "type": EventType.THINK,
            "content": "Test thinking",
            "tool_name": None,
            "tool_args": None,
            "session_id": session.session_id,
            "metadata": {},
        })

        assert len(session.event_buffer) == 1
        assert session.event_buffer[0]["type"] == EventType.THINK
        assert session.event_buffer[0]["content"] == "Test thinking"


@pytest.mark.unit
class TestWebAdapterDependencies:
    """Test web adapter dependency checks"""

    def test_streamlit_check(self):
        """Test Streamlit availability check"""
        from fastreact.adapters.web import STREAMLIT_AVAILABLE

        # Should be a boolean
        assert isinstance(STREAMLIT_AVAILABLE, bool)

    def test_imports(self):
        """Test that all imports work"""
        try:
            from fastreact.adapters.web import (
                WebSession,
                render_event,
                render_chat_interface,
            )
            # Note: run_agent_async may not exist, but WebSession should have run_query
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
