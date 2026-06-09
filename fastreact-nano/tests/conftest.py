"""
pytest configuration for FastReAct Nano

This conftest.py provides:
1. Automatic src/ path configuration
2. Shared fixtures for all tests
3. Mock LLM for fast, reliable testing
4. Test markers (slow, api, e2e)
"""

import sys
import os
from pathlib import Path
from typing import AsyncIterator
import pytest

# Add src/ to path for all tests
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Add tests/helpers to path for test utilities
tests_root = Path(__file__).parent
helpers_path = tests_root / "helpers"

if str(helpers_path) not in sys.path:
    sys.path.insert(0, str(helpers_path))

# Clean sys.path from other potential FastReAct installations
sys.path = [p for p in sys.path if not ('FastReAct/src' in p and 'fastreact-nano' not in p)]


def pytest_configure(config):
    """Pytest configuration hook"""
    # Register custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "api: marks tests that require real API key")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "unit: marks unit tests")
    config.addinivalue_line("markers", "release_llm: marks release-only real LLM efficiency tests")


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture
def project_root():
    """Get project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture
def src_path(project_root):
    """Get src directory"""
    return project_root / "src"


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file"""
    import json

    config = {
        "llm": {
            "model": "gpt-4o-mini",
            "api_base": "http://localhost:8000",
            "api_key": "test-key",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "tools": {
            "max_file_size": 10485760,
            "exec_timeout": 30,
            "working_dir": str(tmp_path),
            "protected_paths": [],
        },
        "react": {
            "max_iterations": 10,
            "max_context_tokens": 128000,
            "context_warning_threshold": 0.8,
            "max_tool_output_chars": 10000,
            "enable_safety": False,
            "strict_mode": False,
            "enable_filesystem_memory": False,
            "max_tree_depth": 3,
            "max_files_per_dir": 50,
        },
    }

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


# ============================================================================
# Mock LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_response(monkeypatch):
    """
    Mock LLM chat method for fast testing

    Returns LLMResponse with optional tool calls based on query content.
    """
    from fastreact.providers.litellm import LLMResponse, ToolCall

    async def mock_chat(self, messages, **kwargs):
        """Return mock LLM response"""
        # Analyze query to determine if tools are needed
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", "").lower()

        tool_calls = []

        # Add tool calls based on content
        if "read" in content or "file" in content:
            tool_calls.append(ToolCall(
                id="call-read-001",
                name="read_file",
                params={"path": "test.py"}
            ))
        elif "write" in content:
            tool_calls.append(ToolCall(
                id="call-write-001",
                name="write_file",
                params={"path": "test.py", "content": "print('hello')"}
            ))
        elif "add" in content or "calculator" in content:
            tool_calls.append(ToolCall(
                id="call-add-001",
                name="add",
                params={"a": 20, "b": 22}
            ))

        return LLMResponse(
            content="Mock response: 42",
            tool_calls=tool_calls,
            model=self.model,
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )

    # Apply mock
    import fastreact.providers.litellm
    monkeypatch.setattr(
        fastreact.providers.litellm.LiteLLMProvider,
        "chat",
        mock_chat
    )


@pytest.fixture
def mock_llm_with_tools(monkeypatch):
    """Mock LLM that always returns tool calls"""
    from fastreact.providers.litellm import LLMResponse, ToolCall

    async def mock_chat(self, messages, **kwargs):
        """Return mock response with tool call"""
        return LLMResponse(
            content="I'll read the file",
            tool_calls=[
                ToolCall(
                    id="call-read-001",
                    name="read_file",
                    params={"path": "test.txt"}
                )
            ],
            model=self.model,
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )

    import fastreact.providers.litellm
    monkeypatch.setattr(
        fastreact.providers.litellm.LiteLLMProvider,
        "chat",
        mock_chat
    )


@pytest.fixture
def mock_llm_no_tools(monkeypatch):
    """Mock LLM that never returns tool calls"""
    from fastreact.providers.litellm import LLMResponse

    async def mock_chat(self, messages, **kwargs):
        """Return mock response without tools"""
        return LLMResponse(
            content="The answer is 42",
            tool_calls=[],
            model=self.model,
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )

    import fastreact.providers.litellm
    monkeypatch.setattr(
        fastreact.providers.litellm.LiteLLMProvider,
        "chat",
        mock_chat
    )


@pytest.fixture
def mock_llm_error(monkeypatch):
    """Mock LLM that raises errors"""
    async def mock_chat(self, messages, **kwargs):
        """Always raise error"""
        raise Exception("Mock LLM error")

    import fastreact.providers.litellm
    monkeypatch.setattr(
        fastreact.providers.litellm.LiteLLMProvider,
        "chat",
        mock_chat
    )


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_messages():
    """Sample message history for testing"""
    return [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "2+2 equals 4."},
    ]


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary"""
    return {
        "llm": {
            "model": "gpt-4o-mini",
            "api_base": "https://api.openai.com/v1",
            "api_key": "sk-test",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "tools": {
            "max_file_size": 10485760,
            "exec_timeout": 30,
            "working_dir": "/tmp",
            "protected_paths": ["/etc", "/usr"],
        },
        "react": {
            "max_iterations": 10,
            "max_context_tokens": 128000,
            "context_warning_threshold": 0.8,
            "max_tool_output_chars": 10000,
            "enable_safety": False,
            "strict_mode": False,
            "enable_filesystem_memory": False,
            "max_tree_depth": 3,
            "max_files_per_dir": 50,
        },
    }


# ============================================================================
# Mock Feishu Client Fixtures
# ============================================================================

@pytest.fixture
def mock_feishu_client():
    """
    Mock Feishu client for testing

    Provides a mock implementation that simulates Feishu events
    without requiring real credentials or WebSocket connections.
    """
    from tests.helpers.mock_feishu_client import MockFeishuClient
    return MockFeishuClient()


@pytest.fixture
def test_feishu_users():
    """
    Test Feishu user data

    Returns dict of test users with user_id, chat_id, and name.
    """
    from tests.helpers.mock_feishu_client import TEST_FEISHU_USERS
    return TEST_FEISHU_USERS


@pytest.fixture
def config_with_real_llm():
    """
    Config with real LLM API for integration testing

    Uses environment variable FASTRACT_API_KEY for API key.
    Mark tests using this with @pytest.mark.api
    """
    import os
    from fastreact.core.config import Config

    api_key = os.getenv("FASTRACT_API_KEY")

    if not api_key:
        pytest.skip("FASTRACT_API_KEY not set - skipping real API test")

    config = Config()
    config.llm.api_key = api_key
    config.llm.model = os.getenv("FASTRACT_MODEL", "gpt-4o-mini")

    return config


@pytest.fixture
def config_with_graphrag():
    """
    Config with GraphRAG MCP server

    Pre-configured with GraphRAG server for testing.
    """
    import sys
    from fastreact.core.config import Config

    config = Config()

    # Add GraphRAG MCP server
    config.mcp.servers = [
        {
            "name": "graphrag",
            "command": sys.executable,
            "args": ["mcp_servers/builtin/graph_rag_server.py"],
            "description": "GraphRAG knowledge graph tools",
            "associated_skill": "graphrag_workflow",
        }
    ]

    return config


# ============================================================================
# Helper Functions
# ============================================================================

def assert_valid_event(event):
    """Assert that an event is valid"""
    from fastreact.core.events import AgentEvent, EventType

    assert isinstance(event, AgentEvent)
    assert event.type in EventType
    assert event.session_id
    assert hasattr(event, 'timestamp')


def assert_tool_call_valid(event, tool_name=None):
    """Assert that a tool call event is valid"""
    from fastreact.core.events import EventType

    assert event.type == EventType.TOOL_CALL
    assert event.tool_name
    assert event.tool_args is not None
    assert event.metadata.get("call_id")

    if tool_name:
        assert event.tool_name == tool_name


def assert_session_end_valid(event):
    """Assert that a session end event is valid"""
    from fastreact.core.events import EventType

    assert event.type == EventType.SESSION_END
    assert event.session_id
    assert event.content or event.metadata.get("error")
