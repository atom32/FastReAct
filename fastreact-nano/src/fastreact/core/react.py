"""
ReActCore - Reasoning + Acting loop

Based on the ReAct pattern: Thought -> Action -> Observation
Combines Nanobot's simplicity with FastReAct's enterprise features.
"""

import asyncio
from enum import Enum
from typing import AsyncIterator, Optional, Callable, Any
from dataclasses import dataclass

from fastreact.core.bus import InboundMessage
from fastreact.core.tools import ToolRegistry, ValidationError
from fastreact.providers.litellm import LiteLLMProvider, LLMResponse, ToolCall


class Phase(Enum):
    """Execution phases for callbacks"""
    THINK = "think"       # LLM reasoning
    ACTION = "action"     # Tool call
    OBSERVE = "observe"   # Tool result
    ERROR = "error"       # Error occurred


@dataclass
class StepEvent:
    """Event emitted during execution"""
    phase: Phase
    content: str = ""
    tool_call: Optional[ToolCall] = None
    error: Optional[str] = None
    iteration: int = 0
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ReActCore:
    """
    ReAct core loop - the brain of the agent

    Implements the Think-Act-Observe loop:
    1. Think: Call LLM with context
    2. Act: Execute tool calls (if any)
    3. Observe: Add tool results to context
    4. Repeat until done or max iterations
    """

    def __init__(
        self,
        llm: LiteLLMProvider,
        tools: ToolRegistry,
        max_iterations: int = 20,
        streaming: bool = False,
    ):
        """
        Initialize ReAct core

        Args:
            llm: LLM provider
            tools: Tool registry
            max_iterations: Maximum loop iterations
            streaming: Enable streaming output
        """
        self._llm = llm
        self._tools = tools
        self._max_iterations = max_iterations
        self._streaming = streaming

        # Event handlers
        self._handlers: list[Callable[[StepEvent], Any]] = []

    def on_event(self, handler: Callable[[StepEvent], Any]):
        """Register event handler"""
        self._handlers.append(handler)

    async def _emit(self, phase: Phase, **kwargs):
        """Emit event to all handlers"""
        event = StepEvent(phase=phase, **kwargs)
        for handler in self._handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                # Don't let handler errors break the loop
                pass

    async def run(
        self,
        messages: list[dict[str, str]],
        stream_callback: Optional[Callable[[str], Any]] = None,
    ) -> str:
        """
        Run ReAct loop

        Args:
            messages: Conversation history
            stream_callback: Optional callback for streaming chunks

        Returns:
            Final response text
        """
        # Event: start thinking
        await self._emit(Phase.THINK, iteration=0)

        # Loop iterations
        for i in range(self._max_iterations):
            # Call LLM
            try:
                response = await self._llm.chat(
                    messages=messages,
                    tools=self._tools.schemas(),
                )
            except Exception as e:
                await self._emit(
                    Phase.ERROR,
                    error=str(e),
                    iteration=i,
                )
                return f"[ERROR] LLM call failed: {str(e)}"

            # Stream content if available
            if response.content:
                if stream_callback:
                    await stream_callback(response.content)
                await self._emit(
                    Phase.THINK,
                    content=response.content,
                    iteration=i,
                )

            # Check for tool calls
            if not response.tool_calls:
                # No tool calls, we're done
                break

            # Execute tool calls
            await self._emit(Phase.ACTION, iteration=i)

            for tool_call in response.tool_calls:
                await self._emit(
                    Phase.ACTION,
                    tool_call=tool_call,
                    iteration=i,
                )

                # Execute tool
                try:
                    result = await self._tools.execute(
                        tool_call.name,
                        tool_call.params,
                    )

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": result,
                    })

                    # Event: observation
                    await self._emit(
                        Phase.OBSERVE,
                        content=result,
                        tool_call=tool_call,
                        iteration=i,
                    )

                except ValidationError as e:
                    error_msg = f"Validation error: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": error_msg,
                    })

                    await self._emit(
                        Phase.ERROR,
                        error=error_msg,
                        tool_call=tool_call,
                        iteration=i,
                    )

                except Exception as e:
                    error_msg = f"Tool execution error: {str(e)}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": error_msg,
                    })

                    await self._emit(
                        Phase.ERROR,
                        error=error_msg,
                        tool_call=tool_call,
                        iteration=i,
                    )

        # Return final assistant message
        if messages and messages[-1]["role"] == "assistant":
            return messages[-1].get("content", "")

        return ""

    async def run_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """
        Run ReAct loop with streaming

        Args:
            messages: Conversation history

        Yields:
            Content chunks
        """
        async def stream_callback(chunk: str):
            yield chunk

        # For now, use non-streaming mode
        # TODO: Implement full streaming with LLM provider
        result = await self.run(messages)
        yield result
