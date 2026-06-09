"""
Event Protocol Unit Tests

Tests for EventType enum, AgentEvent class, and event serialization.

Coverage: 210-line events.py module
Test Count: 25 tests
"""

import pytest
import json
import time
from typing import AsyncIterator
from fastreact.core.events import (
    EventType,
    AgentEvent,
    EventStream,
)


class TestEventType:
    """Test EventType enum"""

    def test_lifecycle_events_exist(self):
        """Test all lifecycle event types are defined"""
        assert EventType.SESSION_START.value == "session_start"
        assert EventType.SESSION_END.value == "session_end"
        assert EventType.ERROR.value == "error"

    def test_react_loop_events_exist(self):
        """Test all ReAct loop event types are defined"""
        assert EventType.THINK.value == "think"
        assert EventType.TOOL_CALL.value == "tool_call"
        assert EventType.TOOL_RESULT.value == "tool_result"

    def test_control_events_exist(self):
        """Test all control event types are defined"""
        assert EventType.STEP_END.value == "step_end"
        assert EventType.INTERRUPT.value == "interrupt"
        assert EventType.ASK_USER.value == "ask_user"

    def test_event_type_is_string_enum(self):
        """Test EventType is a string enum"""
        assert isinstance(EventType.SESSION_START, str)
        assert EventType.SESSION_START == "session_start"


class TestAgentEventCreation:
    """Test AgentEvent creation and initialization"""

    def test_event_creation_minimal(self):
        """Test creating event with minimal parameters"""
        event = AgentEvent(type=EventType.THINK, content="Test")
        assert event.type == EventType.THINK
        assert event.content == "Test"
        assert event.session_id == ""
        assert event.tool_name is None
        assert event.tool_args is None
        assert event.metadata == {}

    def test_event_creation_full(self):
        """Test creating event with all parameters"""
        event = AgentEvent(
            type=EventType.TOOL_CALL,
            content="Executing",
            session_id="test-session",
            tool_name="read_file",
            tool_args={"path": "test.txt"},
            metadata={"call_id": "123"},
        )
        assert event.type == EventType.TOOL_CALL
        assert event.content == "Executing"
        assert event.session_id == "test-session"
        assert event.tool_name == "read_file"
        assert event.tool_args == {"path": "test.txt"}
        assert event.metadata == {"call_id": "123"}

    def test_event_timestamp_default(self):
        """Test event gets timestamp by default"""
        before = time.time()
        event = AgentEvent(type=EventType.THINK)
        after = time.time()
        assert before <= event.timestamp <= after

    def test_event_metadata_none_handling(self):
        """Test event handles None metadata"""
        event = AgentEvent(type=EventType.THINK, metadata=None)
        assert event.metadata == {}


class TestAgentEventFactoryMethods:
    """Test AgentEvent factory methods"""

    def test_session_start_factory(self):
        """Test session_start factory method"""
        event = AgentEvent.session_start("Test query", "session-123")
        assert event.type == EventType.SESSION_START
        assert event.content == "Test query"
        assert event.session_id == "session-123"
        assert event.tool_name is None

    def test_session_end_factory(self):
        """Test session_end factory method"""
        event = AgentEvent.session_end("session-123", "Final answer")
        assert event.type == EventType.SESSION_END
        assert event.content == "Final answer"
        assert event.session_id == "session-123"

    def test_session_end_factory_empty_answer(self):
        """Test session_end factory with empty answer"""
        event = AgentEvent.session_end("session-123")
        assert event.type == EventType.SESSION_END
        assert event.content == ""

    def test_think_factory(self):
        """Test think factory method"""
        event = AgentEvent.think("Thinking...", "session-123", source="test")
        assert event.type == EventType.THINK
        assert event.content == "Thinking..."
        assert event.session_id == "session-123"
        assert event.metadata == {"source": "test"}

    def test_think_factory_without_metadata(self):
        """Test think factory without metadata"""
        event = AgentEvent.think("Thinking...", "session-123")
        assert event.type == EventType.THINK
        assert event.metadata == {}

    def test_tool_call_factory(self):
        """Test tool_call factory method"""
        event = AgentEvent.tool_call(
            "read_file",
            {"path": "test.txt"},
            "session-123",
            call_id="call-456"
        )
        assert event.type == EventType.TOOL_CALL
        assert event.tool_name == "read_file"
        assert event.tool_args == {"path": "test.txt"}
        assert event.session_id == "session-123"
        assert event.metadata == {"action": "calling", "call_id": "call-456"}

    def test_tool_result_factory(self):
        """Test tool_result factory method"""
        event = AgentEvent.tool_result("read_file", "File content", "session-123")
        assert event.type == EventType.TOOL_RESULT
        assert event.content == "File content"
        assert event.tool_name == "read_file"
        assert event.session_id == "session-123"
        assert event.metadata == {"action": "result"}

    def test_error_factory(self):
        """Test error factory method"""
        event = AgentEvent.error("Something went wrong", "session-123", "ValueError")
        assert event.type == EventType.ERROR
        assert event.content == "Something went wrong"
        assert event.session_id == "session-123"
        assert event.metadata == {"error_type": "ValueError"}

    def test_error_factory_default_type(self):
        """Test error factory with default error type"""
        event = AgentEvent.error("Error", "session-123")
        assert event.metadata == {"error_type": "Exception"}

    def test_ask_user_factory(self):
        """Test ask_user factory method"""
        event = AgentEvent.ask_user(
            "Dangerous operation",
            "exec",
            {"command": "rm file"},
            "session-123"
        )
        assert event.type == EventType.ASK_USER
        assert event.content == "Dangerous operation"
        assert event.tool_name == "exec"
        assert event.tool_args == {"command": "rm file"}
        assert event.session_id == "session-123"

    def test_step_end_factory(self):
        """Test step_end factory method"""
        event = AgentEvent.step_end("session-123", "Step complete", has_tool_calls=True)
        assert event.type == EventType.STEP_END
        assert event.content == "Step complete"
        assert event.session_id == "session-123"
        assert event.metadata == {"has_tool_calls": True}

    def test_step_end_factory_without_tool_calls(self):
        """Test step_end factory without tool calls"""
        event = AgentEvent.step_end("session-123", "Step complete")
        assert event.metadata == {"has_tool_calls": False}


class TestAgentEventSerialization:
    """Test AgentEvent serialization and deserialization"""

    def test_to_dict(self):
        """Test converting event to dictionary"""
        event = AgentEvent(
            type=EventType.TOOL_CALL,
            content="Test",
            session_id="session-123",
            tool_name="test_tool",
            tool_args={"arg": "value"},
            metadata={"key": "value"},
        )
        data = event.to_dict()
        assert data["type"] == "tool_call"
        assert data["content"] == "Test"
        assert data["session_id"] == "session-123"
        assert data["tool_name"] == "test_tool"
        assert data["tool_args"] == {"arg": "value"}
        assert data["metadata"] == {"key": "value"}
        assert "timestamp" in data

    def test_to_json(self):
        """Test converting event to JSON string"""
        event = AgentEvent(
            type=EventType.THINK,
            content="Thinking",
            session_id="session-123",
        )
        json_str = event.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data["type"] == "think"
        assert data["content"] == "Thinking"

    def test_from_dict(self):
        """Test creating event from dictionary"""
        data = {
            "type": "tool_call",
            "content": "Test",
            "session_id": "session-123",
            "timestamp": 1234567890.0,
            "tool_name": "test_tool",
            "tool_args": {"arg": "value"},
            "metadata": {"key": "value"},
        }
        event = AgentEvent.from_dict(data)
        assert event.type == EventType.TOOL_CALL
        assert event.content == "Test"
        assert event.session_id == "session-123"
        assert event.timestamp == 1234567890.0
        assert event.tool_name == "test_tool"
        assert event.tool_args == {"arg": "value"}
        assert event.metadata == {"key": "value"}

    def test_from_dict_with_missing_fields(self):
        """Test from_dict handles missing optional fields"""
        data = {
            "type": "think",
            "content": "Test",
        }
        event = AgentEvent.from_dict(data)
        assert event.type == EventType.THINK
        assert event.content == "Test"
        assert event.session_id == ""
        assert event.tool_name is None
        assert event.tool_args is None
        assert event.metadata == {}

    def test_serialization_roundtrip(self):
        """Test event survives serialization roundtrip"""
        original = AgentEvent.tool_call(
            "test_tool",
            {"arg": "value"},
            "session-123",
            call_id="call-456"
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = AgentEvent.from_dict(data)

        # Verify all fields match
        assert restored.type == original.type
        assert restored.content == original.content
        assert restored.session_id == original.session_id
        assert restored.tool_name == original.tool_name
        assert restored.tool_args == original.tool_args
        assert restored.metadata == original.metadata


class TestAgentEventUtilities:
    """Test AgentEvent utility methods"""

    def test_repr_without_tool(self):
        """Test repr without tool name"""
        event = AgentEvent(type=EventType.THINK, content="This is a test message")
        repr_str = repr(event)
        assert "AgentEvent" in repr_str
        assert "think" in repr_str
        assert "This is a test message..." in repr_str

    def test_repr_with_tool(self):
        """Test repr with tool name"""
        event = AgentEvent(
            type=EventType.TOOL_CALL,
            content="Test",
            tool_name="test_tool"
        )
        repr_str = repr(event)
        assert "AgentEvent" in repr_str
        assert "tool_call" in repr_str
        assert "tool=test_tool" in repr_str

    def test_repr_long_content_truncated(self):
        """Test repr truncates long content"""
        long_content = "x" * 100
        event = AgentEvent(type=EventType.THINK, content=long_content)
        repr_str = repr(event)
        # Should only show first 50 chars
        assert "xxx..." in repr_str
        assert len(repr_str) < len(long_content)


class TestEventStreamType:
    """Test EventStream type alias"""

    def test_event_stream_is_async_iterator(self):
        """Test EventStream is AsyncIterator type alias"""
        from typing import get_origin, get_args
        # EventStream should be AsyncIterator[AgentEvent]
        # Check that EventStream is properly typed as AsyncIterator[AgentEvent]
        origin = get_origin(EventStream)
        args = get_args(EventStream)
        assert origin == AsyncIterator or EventStream == AsyncIterator[AgentEvent]


class TestEventIntegration:
    """Integration tests for event system"""

    def test_event_workflow_complete(self):
        """Test complete event workflow from creation to serialization"""
        # Create event using factory
        event = AgentEvent.tool_call(
            "read_file",
            {"path": "test.txt"},
            "session-123",
            call_id="call-456"
        )

        # Verify event structure
        assert event.type == EventType.TOOL_CALL
        assert event.tool_name == "read_file"
        assert event.tool_args == {"path": "test.txt"}

        # Serialize
        json_data = event.to_json()

        # Deserialize
        restored = AgentEvent.from_dict(json.loads(json_data))

        # Verify roundtrip
        assert restored.type == event.type
        assert restored.tool_name == event.tool_name
        assert restored.tool_args == event.tool_args
        assert restored.session_id == event.session_id

    def test_multiple_events_same_session(self):
        """Test multiple events can share same session_id"""
        session_id = "test-session"

        events = [
            AgentEvent.session_start("Query", session_id),
            AgentEvent.think("Thinking", session_id),
            AgentEvent.tool_call("tool", {}, session_id),
            AgentEvent.tool_result("tool", "result", session_id),
            AgentEvent.session_end(session_id, "Done"),
        ]

        # All should have same session_id
        for event in events:
            assert event.session_id == session_id

    def test_event_metadata_extensibility(self):
        """Test event metadata can hold arbitrary data"""
        event = AgentEvent(
            type=EventType.THINK,
            content="Test",
            metadata={
                "custom_field": "value",
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "number": 123,
            }
        )

        # Metadata should preserve all data
        assert event.metadata["custom_field"] == "value"
        assert event.metadata["nested"]["key"] == "value"
        assert event.metadata["list"] == [1, 2, 3]
        assert event.metadata["number"] == 123
