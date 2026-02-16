"""
Test helper utilities for FastReAct test suite

This module provides helper functions for creating test configurations
and other test utilities that keep test code clean and maintainable.
"""

from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
from typing import Union, Optional


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
