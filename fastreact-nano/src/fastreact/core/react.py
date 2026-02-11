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
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, ConfirmationCallback, CLIConfirmationCallback
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
        context_monitor: Optional[ContextMonitor] = None,
        filesystem_memory: Optional[FilesystemMemory] = None,
        safety_policy: Optional[SafetyPolicy] = None,
        confirmation_callback: Optional[ConfirmationCallback] = None,
        max_iterations: int = 20,
    ):
        """
        Initialize ReAct core v2.0

        Args:
            llm: LLM provider
            tools: Tool registry
            callbacks: Callback manager for steering/follow-up
            context_monitor: Context monitor for token management
            filesystem_memory: Filesystem memory (Ghost Map)
            safety_policy: Safety policy for guardrails
            confirmation_callback: User confirmation callback
            max_iterations: Maximum loop iterations
        """
        self._llm = llm
        self._tools = tools
        self._callbacks = callbacks or CallbackManager()
        self._context_monitor = context_monitor or ContextMonitor()
        self._filesystem_memory = filesystem_memory
        self._safety_policy = safety_policy
        self._confirmation_callback = confirmation_callback
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

        # Convert initial messages to LLM format
        llm_messages = [msg.to_llm_format() if isinstance(msg, Message) else msg for msg in messages]

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
                        llm_messages.append(msg.to_llm_format())

                # 2. Build messages for LLM call (inject system messages at beginning)
                messages_for_llm = []

                # 2a. Inject filesystem memory if enabled (Ghost Map) - add first as system message
                if self._filesystem_memory:
                    memory_injection = self._filesystem_memory.get_prompt_injection()
                    if memory_injection:
                        # Prepend system message at the beginning
                        messages_for_llm.append({
                            "role": "system",
                            "content": memory_injection,
                        })

                # 2b. Add all conversation messages
                messages_for_llm.extend(llm_messages)

                # 3. Call LLM
                try:
                    response = await self._llm.chat(
                        messages_for_llm,
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
                    # IMPORTANT: Add assistant message with tool_calls to history
                    # This is required for OpenAI API format
                    assistant_msg = {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": str(tc.params),
                                },
                            }
                            for tc in response.tool_calls
                        ],
                    }
                    llm_messages.append(assistant_msg)

                    await self._emit(Phase.ACTION)

                    for tool_call in response.tool_calls:
                        await self._emit(
                            Phase.ACTION,
                            tool_call=tool_call,
                        )

                        # Execute tool
                        try:
                            # Safety check (guardrails)
                            if self._safety_policy:
                                decision = self._safety_policy.check(
                                    tool_call.name,
                                    tool_call.params,
                                )

                                # Log the decision
                                self._safety_policy.log(
                                    tool_call.name,
                                    tool_call.params,
                                    decision,
                                )

                                # Check if forbidden
                                if not decision.should_allow:
                                    error_result = (
                                        f"[FORBIDDEN] Operation blocked by safety policy.\n"
                                        f"Reason: {decision.reason}\n"
                                        f"Pattern: {decision.pattern_matched}"
                                    )
                                    tool_msg = Message.tool(
                                        name=tool_call.name,
                                        result=error_result,
                                        call_id=tool_call.id,
                                    )
                                    llm_messages.append(tool_msg.to_llm_format())

                                    await self._emit(
                                        Phase.ERROR,
                                        error=error_result,
                                        tool_call=tool_call,
                                    )
                                    continue  # Skip execution

                                # Check if requires confirmation
                                if decision.should_ask and self._confirmation_callback:
                                    user_approved = await self._confirmation_callback.request_confirmation(
                                        tool_call.name,
                                        tool_call.params,
                                        decision.reason,
                                    )

                                    # Update audit log with user decision
                                    self._safety_policy.log(
                                        tool_call.name,
                                        tool_call.params,
                                        decision,
                                        user_approved=user_approved,
                                    )

                                    if not user_approved:
                                        deny_result = (
                                            f"[DENIED] Operation blocked by user.\n"
                                            f"Reason: {decision.reason}"
                                        )
                                        tool_msg = Message.tool(
                                            name=tool_call.name,
                                            result=deny_result,
                                            call_id=tool_call.id,
                                        )
                                        llm_messages.append(tool_msg.to_llm_format())

                                        await self._emit(
                                            Phase.ERROR,
                                            error=deny_result,
                                            tool_call=tool_call,
                                        )
                                        continue  # Skip execution

                            result = await self._tools.execute(
                                tool_call.name,
                                tool_call.params,
                            )

                            # Update filesystem memory (Ghost Map)
                            if self._filesystem_memory:
                                self._filesystem_memory.update_from_tool_call(
                                    tool_call.name,
                                    tool_call.params,
                                    result,
                                )

                            # Apply context truncation
                            safe_result = self._context_monitor.truncate_tool_output(
                                result,
                                tool_name=tool_call.name,
                            )

                            # Add tool result message
                            tool_msg = Message.tool(
                                name=tool_call.name,
                                result=safe_result,
                                call_id=tool_call.id,
                            )
                            llm_messages.append(tool_msg.to_llm_format())

                            await self._emit(
                                Phase.OBSERVE,
                                content=safe_result,
                                tool_call=tool_call,
                            )

                        except ValidationError as e:
                            error_msg = f"Validation error: {e}"
                            # Apply context truncation to errors too
                            safe_error = self._context_monitor.truncate_tool_output(
                                error_msg,
                                tool_name=tool_call.name,
                            )
                            tool_msg = Message.tool(
                                name=tool_call.name,
                                result=safe_error,
                                call_id=tool_call.id,
                            )
                            llm_messages.append(tool_msg.to_llm_format())

                            await self._emit(
                                Phase.ERROR,
                                error=safe_error,
                                tool_call=tool_call,
                            )

                        except Exception as e:
                            error_msg = f"Tool execution error: {str(e)}"
                            # Apply context truncation to errors too
                            safe_error = self._context_monitor.truncate_tool_output(
                                error_msg,
                                tool_name=tool_call.name,
                            )
                            tool_msg = Message.tool(
                                name=tool_call.name,
                                result=safe_error,
                                call_id=tool_call.id,
                            )
                            llm_messages.append(tool_msg.to_llm_format())

                            await self._emit(
                                Phase.ERROR,
                                error=error_msg,
                                tool_call=tool_call,
                            )

                else:
                    # No tool calls - add assistant's response to history
                    # This is important for multi-turn conversations
                    assistant_msg = {
                        "role": "assistant",
                        "content": response.content or "",
                    }
                    llm_messages.append(assistant_msg)

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
        for msg in reversed(llm_messages):
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

    async def run_event_stream(
        self,
        query: str,
        session_id: str,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Run ReAct loop with unified event stream

        This is the NEW preferred API that replaces run() and run_stream().
        It yields AgentEvent objects, providing complete visibility into
        the agent's execution.

        Args:
            query: User query
            session_id: Session identifier for concurrency

        Yields:
            AgentEvent objects (SESSION_START, THINK, TOOL_CALL, TOOL_RESULT, ERROR, SESSION_END)

        Example:
            async for event in core.run_event_stream("What is 2+2?", "session-123"):
                if event.type == EventType.THINK:
                    print(f"Thinking: {event.content}")
                elif event.type == EventType.TOOL_CALL:
                    print(f"Calling: {event.tool_name}")
        """
        from fastreact.core.events import AgentEvent, EventType

        # 1. SESSION_START
        yield AgentEvent.session_start(query, session_id)

        # Initialize messages (use dict format consistently)
        messages = [Message.user(query).to_llm_format()]
        pending_messages = MessageQueue()

        try:
            # === Outer loop: Process follow-up messages ===
            while True:
                has_more_tool_calls = True
                steering_after_tools = None

                # === Inner loop: Process tools and steering ===
                while has_more_tool_calls or pending_messages:
                    # 1. Process pending messages
                    if pending_messages:
                        for msg in pending_messages.drain():
                            messages.append(msg.to_llm_format())

                    # 2. Build messages for LLM
                    messages_for_llm = []

                    # Inject Ghost Map if enabled
                    if self._filesystem_memory:
                        memory_injection = self._filesystem_memory.get_prompt_injection()
                        if memory_injection:
                            messages_for_llm.append({
                                "role": "system",
                                "content": memory_injection,
                            })

                    messages_for_llm.extend(messages)

                    # 3. Call LLM
                    try:
                        response = await self._llm.chat(
                            messages_for_llm,
                            tools=self._tools.schemas(),
                        )
                    except Exception as e:
                        yield AgentEvent.error(str(e), session_id)
                        return

                    # 4. Stream thinking content
                    if response.content:
                        yield AgentEvent.think(response.content, session_id)

                    # 5. Check for tool calls
                    has_more_tool_calls = len(response.tool_calls) > 0

                    # 6. Execute tools
                    if has_more_tool_calls:
                        # Add assistant message with tool_calls
                        assistant_msg = {
                            "role": "assistant",
                            "content": response.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.name,
                                        "arguments": str(tc.params),
                                    },
                                }
                                for tc in response.tool_calls
                            ],
                        }
                        messages.append(assistant_msg)

                        for tool_call in response.tool_calls:
                            # Emit TOOL_CALL event
                            yield AgentEvent.tool_call(
                                tool_call.name,
                                tool_call.params,
                                session_id,
                            )

                            # Execute tool
                            try:
                                # Safety check
                                if self._safety_policy:
                                    decision = self._safety_policy.check(
                                        tool_call.name,
                                        tool_call.params,
                                    )

                                    # Log decision
                                    self._safety_policy.log(
                                        tool_call.name,
                                        tool_call.params,
                                        decision,
                                    )

                                    # Check if forbidden
                                    if not decision.should_allow:
                                        error_result = (
                                            f"[FORBIDDEN] {decision.reason}\n"
                                            f"Pattern: {decision.pattern_matched}"
                                        )
                                        tool_msg = Message.tool(
                                            name=tool_call.name,
                                            result=error_result,
                                            call_id=tool_call.id,
                                        )
                                        messages.append(tool_msg.to_llm_format())

                                        yield AgentEvent.tool_result(
                                            tool_call.name,
                                            error_result,
                                            session_id,
                                        )
                                        continue

                                    # Check if needs confirmation
                                    if decision.should_ask and self._confirmation_callback:
                                        yield AgentEvent.ask_user(
                                            decision.reason,
                                            tool_call.name,
                                            tool_call.params,
                                            session_id,
                                        )

                                        user_approved = await self._confirmation_callback.request_confirmation(
                                            tool_call.name,
                                            tool_call.params,
                                            decision.reason,
                                        )

                                        self._safety_policy.log(
                                            tool_call.name,
                                            tool_call.params,
                                            decision,
                                            user_approved=user_approved,
                                        )

                                        if not user_approved:
                                            deny_result = f"[DENIED] {decision.reason}"
                                            tool_msg = Message.tool(
                                                name=tool_call.name,
                                                result=deny_result,
                                                call_id=tool_call.id,
                                            )
                                            messages.append(tool_msg.to_llm_format())

                                            yield AgentEvent.tool_result(
                                                tool_call.name,
                                                deny_result,
                                                session_id,
                                            )
                                            continue

                                result = await self._tools.execute(
                                    tool_call.name,
                                    tool_call.params,
                                )

                                # Update Ghost Map
                                if self._filesystem_memory:
                                    self._filesystem_memory.update_from_tool_call(
                                        tool_call.name,
                                        tool_call.params,
                                        result,
                                    )

                                # Apply context truncation
                                safe_result = self._context_monitor.truncate_tool_output(
                                    result,
                                    tool_name=tool_call.name,
                                )

                                # Add tool result message
                                tool_msg = Message.tool(
                                    name=tool_call.name,
                                    result=safe_result,
                                    call_id=tool_call.id,
                                )
                                messages.append(tool_msg.to_llm_format())

                                # Emit TOOL_RESULT event
                                yield AgentEvent.tool_result(
                                    tool_call.name,
                                    safe_result,
                                    session_id,
                                )

                            except ValidationError as e:
                                error_msg = f"Validation error: {e}"
                                safe_error = self._context_monitor.truncate_tool_output(
                                    error_msg,
                                    tool_name=tool_call.name,
                                )
                                tool_msg = Message.tool(
                                    name=tool_call.name,
                                    result=safe_error,
                                    call_id=tool_call.id,
                                )
                                messages.append(tool_msg.to_llm_format())

                                yield AgentEvent.tool_result(
                                    tool_call.name,
                                    safe_error,
                                    session_id,
                                )

                            except Exception as e:
                                error_msg = f"Tool execution error: {str(e)}"
                                safe_error = self._context_monitor.truncate_tool_output(
                                    error_msg,
                                    tool_name=tool_call.name,
                                )
                                tool_msg = Message.tool(
                                    name=tool_call.name,
                                    result=safe_error,
                                    call_id=tool_call.id,
                                )
                                messages.append(tool_msg.to_llm_format())

                                yield AgentEvent.tool_result(
                                    tool_call.name,
                                    safe_error,
                                    session_id,
                                )

                    else:
                        # No tool calls - add assistant response to history
                        assistant_msg = {
                            "role": "assistant",
                            "content": response.content or "",
                        }
                        messages.append(assistant_msg)

                # Check for follow-up messages
                followup = await self._callbacks.get_followup_messages()
                if followup:
                    pending_messages.extend(followup)
                    continue

                # No more follow-ups, break
                break

            # Extract final answer
            final_answer = ""
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    final_answer = msg.get("content", "")
                    break

            # Emit SESSION_END
            yield AgentEvent.session_end(session_id, final_answer)

        except Exception as e:
            yield AgentEvent.error(str(e), session_id)
