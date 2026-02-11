"""
ReActCore v2.0 - Event-Driven ReAct Engine

Pure event generator. Yields AgentEvent stream.
No callbacks, no state, just events.
"""

import asyncio
from typing import AsyncIterator, Optional

from fastreact.core.messages import Message, MessageQueue
from fastreact.core.tools import ToolRegistry, ValidationError
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, ConfirmationCallback
from fastreact.providers.litellm import LiteLLMProvider


class ReActCore:
    """
    ReAct core v2.0 - Pure event generator

    This is a stateless ReAct engine that yields AgentEvent objects.
    All external communication happens through the event stream.

    Architecture:
    - No internal state (session-based)
    - No callbacks (event-driven)
    - No UI dependencies (pure logic)

    Usage:
        async for event in core.run_event_stream("task", "session-123"):
            if event.type == EventType.TOOL_CALL:
                print(f"Calling {event.tool_name}")
    """

    def __init__(
        self,
        llm: LiteLLMProvider,
        tools: ToolRegistry,
        context_monitor: Optional[ContextMonitor] = None,
        filesystem_memory: Optional[FilesystemMemory] = None,
        safety_policy: Optional[SafetyPolicy] = None,
        confirmation_callback: Optional[ConfirmationCallback] = None,
        max_iterations: int = 20,
    ):
        """
        Initialize ReAct core

        Args:
            llm: LLM provider
            tools: Tool registry
            context_monitor: Context monitor for token management
            filesystem_memory: Filesystem memory (Ghost Map)
            safety_policy: Safety policy for guardrails
            confirmation_callback: User confirmation callback
            max_iterations: Maximum loop iterations
        """
        self._llm = llm
        self._tools = tools
        self._context_monitor = context_monitor or ContextMonitor()
        self._filesystem_memory = filesystem_memory
        self._safety_policy = safety_policy
        self._confirmation_callback = confirmation_callback
        self._max_iterations = max_iterations

    async def run_event_stream(
        self,
        query: str,
        session_id: str,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Run ReAct loop with unified event stream

        This is the ONLY interface to the ReAct engine.
        It yields AgentEvent objects, providing complete visibility into execution.

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

                # === Inner loop: Process tools ===
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

                # No more tool calls and no pending messages, break
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
