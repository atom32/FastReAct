"""
Test helper utilities for FastReAct test suite

This module provides helper functions for creating test configurations
and other test utilities that keep test code clean and maintainable.
"""

import asyncio
from typing import List
from fastreact import EventType
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
from fastreact.core.events import AgentEvent
from typing import Union, Optional


async def collect_events(event_stream) -> List[AgentEvent]:
    """
    Collect all events from an async event stream

    Args:
        event_stream: Async generator of AgentEvent objects

    Returns:
        List of collected events
    """
    events = []
    async for event in event_stream:
        events.append(event)
    return events


def extract_final_answer(events: List[AgentEvent]) -> str:
    """
    Extract the final answer from a list of events

    Args:
        events: List of AgentEvent objects

    Returns:
        Final answer string or None if not found
    """
    for event in events:
        if event.type == EventType.SESSION_END:
            return event.content
    return None


def assert_session_completed(events: List[AgentEvent]) -> None:
    """
    Assert that a session completed successfully

    Args:
        events: List of AgentEvent objects

    Raises:
        AssertionError: If session did not complete
    """
    # Check that we have events
    assert len(events) > 0, "No events collected"

    # Check that session ended
    has_session_end = any(e.type == EventType.SESSION_END for e in events)
    assert has_session_end, "Session did not complete (no SESSION_END event)"


def create_test_config(
    llm: Union[dict, LLMConfig, None] = None,
    tools: Union[dict, ToolConfig, None] = None,
    react: Union[dict, ReactConfig, None] = None,
) -> Config:
    """
    Create test configuration from dicts or dataclasses

    Smartly converts dicts to appropriate config objects. This helper
    solves the issue where Python dataclasses don't auto-convert dicts
    to typed fields.

    Args:
        llm: LLM config (dict or LLMConfig or None for defaults)
        tools: Tool config (dict or ToolConfig or None for defaults)
        react: React config (dict or ReactConfig or None for defaults)

    Returns:
        Config instance with properly typed sub-configs

    Examples:
        >>> # Using dicts (most common in tests)
        >>> config = create_test_config(llm={"model": "gpt-4o-mini"})

        >>> # Using dataclasses
        >>> from fastreact.core.config import LLMConfig
        >>> config = create_test_config(llm=LLMConfig(model="gpt-4o-mini"))

        >>> # Mixed usage
        >>> config = create_test_config(
        ...     llm={"model": "gpt-4o-mini"},
        ...     react=ReactConfig(max_iterations=5)
        ... )

        >>> # Multiple config values
        >>> config = create_test_config(
        ...     llm={"model": "gpt-4o-mini", "temperature": 0.5},
        ...     tools={"max_file_size": 2048},
        ...     react={"max_iterations": 10, "enable_safety": True}
        ... )

    Rationale:
        Python dataclasses don't auto-convert dicts to typed fields.
        When you do Config(llm={"model": "gpt-4"}), the llm field
        becomes a dict, not an LLMConfig object. This causes AttributeErrors
        when Agent tries to access config.llm.model (dict has no 'model' attr).

        This helper properly converts dicts to dataclass instances before
        passing to Config constructor.
    """
    return Config(
        llm=LLMConfig(**llm) if isinstance(llm, dict) else (llm or LLMConfig()),
        tools=ToolConfig(**tools) if isinstance(tools, dict) else (tools or ToolConfig()),
        react=ReactConfig(**react) if isinstance(react, dict) else (react or ReactConfig()),
    )
