"""
LLM Provider using LiteLLM for multi-provider support

Supports: OpenAI, Anthropic, DeepSeek, Azure, etc.
Uses environment variables for API keys and configuration.
"""

import os
from typing import AsyncIterator, Optional, Any
from dataclasses import dataclass
import asyncio

from fastreact.core.config import DEFAULT_LLM_MAX_TOKENS


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
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
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

        # Detect if using custom OpenAI-compatible endpoint (like SiliconFlow)
        self._use_openai_client = api_base is not None

        if self._use_openai_client:
            # Use OpenAI client directly for custom endpoints (like v1)
            try:
                from openai import AsyncOpenAI
                import httpx

                # Create HTTP client
                self._http_client = httpx.AsyncClient(
                    timeout=120.0,
                    limits=httpx.Limits(max_connections=100),
                )

                # Create OpenAI client with custom base_url
                self._openai_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=api_base,
                    http_client=self._http_client,
                )
            except ImportError:
                raise ImportError(
                    "openai>=1.0.0 and httpx>=0.25.0 required for custom endpoints. "
                    "Install with: pip install openai httpx"
                )
        else:
            # Use LiteLLM for standard providers
            try:
                import litellm
                self._litellm = litellm
            except ImportError:
                raise ImportError(
                    "litellm is required. Install with: pip install litellm"
                )

            # Configure litellm
            self._configure_litellm()

    @property
    def model(self) -> str:
        """Public model name for diagnostics, tests, and lightweight adapters."""
        return self._model

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

        # Use OpenAI client for custom endpoints (like SiliconFlow)
        if self._use_openai_client:
            return await self._chat_openai(messages, tools, model, **kwargs)

        # Use LiteLLM for standard providers
        return await self._chat_litellm(messages, tools, model, **kwargs)

    async def _chat_openai(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]],
        model: str,
        **kwargs,
    ) -> LLMResponse:
        """Chat using OpenAI client directly (for custom endpoints like SiliconFlow)"""
        # Build parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Add extra kwargs
        params.update(kwargs)

        # Call OpenAI client
        response = await self._openai_client.chat.completions.create(**params)

        # Parse OpenAI response
        return self._parse_openai_response(response, model)

    async def _chat_litellm(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]],
        model: str,
        **kwargs,
    ) -> LLMResponse:
        """Chat using LiteLLM (for standard providers)"""
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

    def _parse_openai_response(self, response: Any, model: str) -> LLMResponse:
        """Parse OpenAI client response"""
        # Get first choice
        choice = response.choices[0]
        message = choice.message

        # Get content
        content = message.content or ""

        # Get tool calls
        tool_calls = []
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        params=self._parse_function_args(
                            tc.function.arguments
                        ),
                    )
                )

        # Get usage
        usage = {}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=model,
            usage=usage,
        )

    def _parse_function_args(self, arguments: str) -> dict[str, Any]:
        """
        Parse JSON function arguments with robust error recovery

        Attempts to fix common JSON formatting errors before falling back.
        This handles LLM "hallucinations" where JSON is slightly malformed.

        Args:
            arguments: JSON string to parse

        Returns:
            Parsed dictionary, or empty dict if all parsing attempts fail
        """
        import json
        import re
        import sys

        # Attempt 1: Normal parsing
        try:
            return json.loads(arguments)
        except json.JSONDecodeError as e:
            print(f"[WARNING] JSON parsing failed, attempting repair...", file=sys.stderr)
            print(f"[DEBUG] JSON error: {e}", file=sys.stderr)
            print(f"[DEBUG] Raw input (first 200 chars): {arguments[:200]}", file=sys.stderr)

        # Attempt 2: Fix missing quotes around keys (common LLM error)
        try:
            # Fix: {key: "value"} → {"key": "value"}
            fixed = re.sub(r'(\w+):', r'"\1":', arguments)
            result = json.loads(fixed)
            print(f"[OK] JSON repaired: added quotes to keys", file=sys.stderr)
            return result
        except json.JSONDecodeError:
            pass

        # Attempt 3: Fix trailing commas (another common error)
        try:
            # Fix: {"key": "value",} → {"key": "value"}
            fixed = re.sub(r',\s*}', '}', arguments)
            fixed = re.sub(r',\s*]', ']', fixed)
            result = json.loads(fixed)
            print(f"[OK] JSON repaired: removed trailing commas", file=sys.stderr)
            return result
        except json.JSONDecodeError:
            pass

        # Attempt 4: Fix single quotes instead of double quotes
        try:
            # Fix: {'key': 'value'} → {"key": "value"}
            fixed = arguments.replace("'", '"')
            result = json.loads(fixed)
            print(f"[OK] JSON repaired: single quotes to double quotes", file=sys.stderr)
            return result
        except json.JSONDecodeError:
            pass

        # Attempt 5: Combination of fixes (try them all together)
        try:
            fixed = arguments.replace("'", '"')  # Single to double quotes
            fixed = re.sub(r'(\w+):', r'"\1":', fixed)  # Add quotes to keys
            fixed = re.sub(r',\s*}', '}', fixed)  # Remove trailing commas
            fixed = re.sub(r',\s*]', ']', fixed)
            result = json.loads(fixed)
            print(f"[OK] JSON repaired: combination of fixes", file=sys.stderr)
            return result
        except json.JSONDecodeError as e:
            print(f"[ERROR] All JSON repair attempts failed", file=sys.stderr)
            print(f"[ERROR] Final error: {e}", file=sys.stderr)

        # Final fallback: Return empty dict to prevent tool execution crash
        print(f"[WARNING] Returning empty dict for malformed JSON", file=sys.stderr)
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

        # Use OpenAI client for custom endpoints
        if self._use_openai_client:
            async for chunk in self._stream_openai(messages, tools, model, **kwargs):
                yield chunk
        else:
            async for chunk in self._stream_litellm(messages, tools, model, **kwargs):
                yield chunk

    async def _stream_openai(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]],
        model: str,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream using OpenAI client"""
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

        stream = await self._openai_client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _stream_litellm(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]],
        model: str,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream using LiteLLM"""
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
