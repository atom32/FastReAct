"""
ReActCore v2.0 - Dual-layer loop with steering and follow-up

Based on Moltbot's dual-layer loop pattern:
- Outer loop: Process follow-up messages queue
- Inner loop: Process tool calls and steering messages
"""

import asyncio
from enum import Enum
from typing import AsyncIterator, Optional, Callable, Any
from dataclasses import dataclass

from fastreact.core.messages import Message, MessageQueue
from fastreact.core.tools import ToolRegistry, ValidationError
from fastreact.core.callbacks import CallbackManager
from fastreact.providers.litellm import LiteLLMProvider, LLMResponse, ToolCall


class Phase(Enum):
    """Execution phases for callbacks"""
    THINK = "think"       # LLM reasoning
    ACTION = "action"     # Tool call
    OBSERVE = "observe"   # Tool result
    STEERING = "steering" # Real-time intervention
    FOLLOWUP = "followup" # Async task continuation
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
    ReAct core v2.0 - Dual-layer loop architecture

    Implements Moltbot-style dual-layer loop:
    - Outer loop: Process follow-up messages queue
    - Inner loop: Process tool calls and steering messages

    This enables:
    - Real-time intervention (steering messages)
    - Async task continuation (follow-up messages)
    - More complex agent workflows
    """

    def __init__(
        self,
        llm: LiteLLMProvider,
        tools: ToolRegistry,
        callbacks: Optional[CallbackManager] = None,
        max_iterations: int = 20,
    ):
        """
        Initialize ReAct core v2.0

        Args:
            llm: LLM provider
            tools: Tool registry
            callbacks: Callback manager for steering/follow-up
            max_iterations: Maximum loop iterations
        """
        self._llm = llm
        self._tools = tools
        self._callbacks = callbacks or CallbackManager()
        self._max_iterations = max_iterations

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
            except Exception:
                # Don't let handler errors break the loop
                pass

    async def run(
        self,
        messages: list[Message],
        stream_callback: Optional[Callable[[str], Any]] = None,
    ) -> str:
        """
        Run dual-layer ReAct loop

        Args:
            messages: Conversation history (Message objects)
            stream_callback: Optional callback for streaming chunks

        Returns:
            Final response text
        """
        pending_messages = MessageQueue()

        # === Outer loop: Process follow-up messages ===
        while True:
            has_more_tool_calls = True
            steering_after_tools = None

            # === Inner loop: Process tools and steering ===
            while has_more_tool_calls or pending_messages:
                # 1. Process pending messages (user input or steering)
                if pending_messages:
                    for msg in pending_messages.drain():
                        # Emit steering event if applicable
                        if msg.role == "steering":
                            await self._emit(Phase.STEERING, content=msg.content)

                        # Add to conversation
                        messages.append(msg.to_llm_format())

                # 2. Call LLM
                try:
                    response = await self._llm.chat(
                        messages,
                        tools=self._tools.schemas(),
                    )
                except Exception as e:
                    await self._emit(
                        Phase.ERROR,
                        error=str(e),
                    )
                    return f"[ERROR] LLM call failed: {str(e)}"

                # 3. Stream content if available
                if response.content:
                    if stream_callback:
                        await stream_callback(response.content)
                    await self._emit(
                        Phase.THINK,
                        content=response.content,
                    )

                # 4. Check for tool calls
                has_more_tool_calls = len(response.tool_calls) > 0

                # 5. Execute tools
                if has_more_tool_calls:
                    await self._emit(Phase.ACTION)

                    for tool_call in response.tool_calls:
                        await self._emit(
                            Phase.ACTION,
                            tool_call=tool_call,
                        )

                        # Execute tool
                        try:
                            result = await self._tools.execute(
                                tool_call.name,
                                tool_call.params,
                            )

                            # Add tool result message
                            tool_msg = Message.tool(
                                name=tool_call.name,
                                result=result,
                                call_id=tool_call.id,
                            )
                            messages.append(tool_msg.to_llm_format())

                            await self._emit(
                                Phase.OBSERVE,
                                content=result,
                                tool_call=tool_call,
                            )

                        except ValidationError as e:
                            error_msg = f"Validation error: {e}"
                            tool_msg = Message.tool(
                                name=tool_call.name,
                                result=error_msg,
                                call_id=tool_call.id,
                            )
                            messages.append(tool_msg.to_llm_format())

                            await self._emit(
                                Phase.ERROR,
                                error=error_msg,
                                tool_call=tool_call,
                            )

                        except Exception as e:
                            error_msg = f"Tool execution error: {str(e)}"
                            tool_msg = Message.tool(
                                name=tool_call.name,
                                result=error_msg,
                                call_id=tool_call.id,
                            )
                            messages.append(tool_msg.to_llm_format())

                            await self._emit(
                                Phase.ERROR,
                                error=error_msg,
                                tool_call=tool_call,
                            )

                # 6. Check for steering messages (real-time intervention)
                steering = await self._callbacks.get_steering_messages()
                if steering:
                    pending_messages.extend(steering)
                    # Optional: Reset tool calls flag to reprocess with steering
                    # has_more_tool_calls = True

            # === End inner loop ===

            # 7. Check for follow-up messages (async tasks)
            followup = await self._callbacks.get_followup_messages()
            if followup:
                # Add follow-up messages to pending
                pending_messages.extend(followup)
                await self._emit(Phase.FOLLOWUP, content=f"{len(followup)} follow-up messages")
                # Continue outer loop to process follow-ups
                continue

            # No more follow-ups, break outer loop
            break

        # 8. Return final response
        # Find last assistant message
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return msg.get("content", "")

        return ""

    async def run_stream(
        self,
        messages: list[Message],
    ) -> AsyncIterator[str]:
        """
        Run dual-layer loop with streaming

        Args:
            messages: Conversation history (Message objects)

        Yields:
            Content chunks
        """
        async def stream_callback(chunk: str):
            yield chunk

        result = await self.run(messages, stream_callback=stream_callback)
        yield result
