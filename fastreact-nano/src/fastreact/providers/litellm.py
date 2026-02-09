"""
LLM Provider using LiteLLM for multi-provider support

Supports: OpenAI, Anthropic, DeepSeek, Azure, etc.
Uses environment variables for API keys and configuration.
"""

import os
from typing import AsyncIterator, Optional, Any
from dataclasses import dataclass
import asyncio


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    tool_calls: list["ToolCall"] = None
    model: str = ""
    usage: dict[str, int] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.usage is None:
            self.usage = {}


@dataclass
class ToolCall:
    """Tool call from LLM"""
    id: str
    name: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "params": self.params,
        }


class LiteLLMProvider:
    """
    LLM provider using LiteLLM for multi-provider support

    Supports automatic provider detection from environment variables.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize LLM provider

        Args:
            model: Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
            api_base: API base URL
            api_key: API key (defaults to environment variable)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self._model = model or self._detect_model()
        self._api_base = api_base
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens

        # Lazy import of litellm
        try:
            import litellm
            self._litellm = litellm
        except ImportError:
            raise ImportError(
                "litellm is required. Install with: pip install litellm"
            )

        # Configure litellm
        self._configure_litellm()

    def _detect_model(self) -> str:
        """Detect model from environment variables"""
        # Check common model variables
        for var in ["MODEL", "LLM_MODEL", "FASTREACT_MODEL"]:
            model = os.getenv(var)
            if model:
                return model

        # Detect from API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            return "claude-3-5-sonnet-20241022"
        if os.getenv("OPENAI_API_KEY"):
            return "gpt-4o"
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek-chat"

        # Default
        return "gpt-4o"

    def _configure_litellm(self):
        """Configure litellm with settings"""
        # Set cache if available
        self._litellm.cache = None  # Use our own cache

        # Set timeout
        self._litellm.timeout = 120.0

        # Drop params (clean up litellm params)
        self._litellm.drop_params = True

    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Chat completion

        Args:
            messages: List of message dicts with role and content
            tools: List of tool schemas (OpenAI format)
            model: Override model
            **kwargs: Additional parameters for litellm

        Returns:
            LLMResponse with content and tool calls
        """
        model = model or self._model

        # Build parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            **kwargs,
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Add API key if provided
        if self._api_key:
            params["api_key"] = self._api_key
        if self._api_base:
            params["api_base"] = self._api_base

        # Call litellm asynchronously
        response = await asyncio.to_thread(
            self._litellm.completion,
            **params,
        )

        # Parse response
        return self._parse_response(response, model)

    def _parse_response(self, response: Any, model: str) -> LLMResponse:
        """Parse litellm response"""
        # Get first choice
        choices = response.get("choices", [])
        if not choices:
            return LLMResponse(content="", model=model)

        choice = choices[0]
        message = choice.get("message", {})

        # Get content
        content = message.get("content", "") or ""

        # Get tool calls
        tool_calls = []
        raw_tool_calls = message.get("tool_calls", [])
        for tc in raw_tool_calls:
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    params=self._parse_function_args(
                        tc.get("function", {}).get("arguments", "{}")
                    ),
                )
            )

        # Get usage
        usage = response.get("usage", {})

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )

    def _parse_function_args(self, arguments: str) -> dict[str, Any]:
        """Parse JSON function arguments"""
        import json

        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return {}

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Chat completion with streaming

        Args:
            messages: List of message dicts
            tools: List of tool schemas
            model: Override model
            **kwargs: Additional parameters

        Yields:
            Content chunks
        """
        model = model or self._model

        # Build parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": True,
            **kwargs,
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        if self._api_key:
            params["api_key"] = self._api_key
        if self._api_base:
            params["api_base"] = self._api_base

        # Stream response
        response = await asyncio.to_thread(
            self._litellm.completion,
            **params,
        )

        for chunk in response:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
