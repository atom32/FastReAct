"""
ReActCore v2.1 - Pure Intent Generator (Brain)

This is the BRAIN of the Brain-Body Split architecture.
Core responsibilities:
- Call LLM
- Emit reasoning events (THINK)
- Emit intent events (TOOL_CALL)
- Signal step completion (STEP_END)

Core does NOT:
- Execute tools
- Check safety
- Manage loop control
- Handle state
- Process context

All execution moved to Agent (Body).
"""

import asyncio
from typing import Any, AsyncIterator, Optional

from fastreact.core.messages import Message
from fastreact.core.tools import ToolRegistry
from fastreact.core.prompts import SYSTEM_PROMPT_CORE
from fastreact.providers.litellm import LiteLLMProvider


class ReActCore:
    """
    Pure Intent Generator (The Brain)

    This is a stateless reasoning engine that yields AgentEvent objects.
    All it does is think and emit intent. No execution, no side effects.

    Architecture:
    - Zero state (session-based)
    - Zero side effects (no I/O)
    - Zero control flow (single step)

    Usage:
        async for event in core.run_step_stream(messages, "session-123"):
            if event.type == EventType.TOOL_CALL:
                # This is just INTENT, not execution
                print(f"Intent: {event.tool_name}")

    The Agent (Body) layer handles:
    - Loop control
    - Tool execution
    - Safety checks
    - Context management
    """

    def __init__(
        self,
        llm: LiteLLMProvider,
        tools: ToolRegistry,
        max_iterations: int = 20,
    ):
        """
        Initialize pure reasoning core

        Args:
            llm: LLM provider
            tools: Tool registry (for schema only, no execution)
            max_iterations: Maximum reasoning steps (safety limit)
        """
        self._llm = llm
        self._tools = tools
        self._max_iterations = max_iterations

    async def run_step_stream(
        self,
        messages: list[dict],
        session_id: str,
        system_prompt: Optional[str] = None,
        llm_options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Single reasoning step: Ask LLM, Emit Intent

        This is the ONLY interface to the Core engine.
        It performs ONE reasoning step and yields:
        - THINK event (LLM reasoning)
        - TOOL_CALL events (intents to execute, NOT executed here)
        - STEP_END event (signals step completion)

        The Agent layer (Body) will:
        1. Receive TOOL_CALL events
        2. Execute tools (with safety checks)
        3. Build result messages
        4. Call run_step_stream again with updated messages

        Args:
            messages: Current message history (list of LLM message dicts)
            session_id: Session identifier for concurrency
            system_prompt: Optional custom system prompt (default: SYSTEM_PROMPT_CORE)

        Yields:
            AgentEvent objects (THINK, TOOL_CALL, STEP_END, ERROR)

        Example:
            # Agent layer usage
            messages = [{"role": "user", "content": "What is 2+2?"}]

            while True:
                tool_calls = []
                final_answer = None

                async for event in core.run_step_stream(messages, session_id):
                    if event.type == EventType.THINK:
                        # Stream thinking to user
                        print(event.content)

                    elif event.type == EventType.TOOL_CALL:
                        # Collect tool call intents
                        tool_calls.append(event)

                    elif event.type == EventType.STEP_END:
                        # Step complete
                        final_answer = event.content

                # Execute tools in Body layer
                if tool_calls:
                    for call in tool_calls:
                        result = await tools.execute(call.tool_name, call.tool_args)
                        messages.append(Message.tool(call.tool_name, result).to_llm_format())
                else:
                    # No more tool calls, we're done
                    break
        """
        from fastreact.core.events import AgentEvent, EventType

        try:
            # Build messages for LLM
            messages_for_llm = []

            # Inject system prompt
            messages_for_llm.append({
                "role": "system",
                "content": system_prompt or SYSTEM_PROMPT_CORE,
            })

            # Add message history
            messages_for_llm.extend(messages)

            # Call LLM
            try:
                response = await self._llm.chat(
                    messages_for_llm,
                    tools=self._tools.schemas(),
                    **(llm_options or {}),
                )
            except Exception as e:
                yield AgentEvent.error(f"LLM call failed: {e}", session_id)
                return

            # Emit thinking content
            # Note: When LLM decides to call tools, response.content may be empty
            # In that case, emit a brief thinking message
            think_content = response.content
            has_tool_calls = len(response.tool_calls) > 0

            if not think_content and has_tool_calls:
                # LLM is calling tools directly without text reasoning
                # Generate a brief description of what it's doing
                tool_names = [tc.name for tc in response.tool_calls]
                if len(tool_names) == 1:
                    think_content = f"Using {tool_names[0]} tool"
                else:
                    think_content = f"Using {', '.join(tool_names)} tools"

            # Emit thinking content
            if think_content:
                yield AgentEvent.think(think_content, session_id)

            # Emit tool call intents (NOT executing here)
            if has_tool_calls:
                for tool_call in response.tool_calls:
                    # Include call_id in metadata for proper OpenAI format
                    yield AgentEvent.tool_call(
                        tool_call.name,
                        tool_call.params,
                        session_id,
                        call_id=tool_call.id,
                    )

            # Signal step completion
            step_end = AgentEvent.step_end(
                session_id,
                final_answer=response.content or "",
                has_tool_calls=has_tool_calls,
            )
            step_end.metadata.update({
                "llm_usage": response.usage or {},
                "model": response.model,
            })
            yield step_end

        except Exception as e:
            yield AgentEvent.error(f"Core step failed: {e}", session_id)
