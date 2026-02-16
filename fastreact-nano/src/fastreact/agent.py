"""
FastReAct Nano v2.1 - Brain-Body Architecture

Agent = The Body (Executor)
Core = The Brain (Intent Generator)

The Agent layer handles:
- Loop control
- Tool execution
- Safety checks
- Context management
- Filesystem memory
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional, AsyncIterator

from fastreact.core.config import Config
from fastreact.core.tools import ToolRegistry, ValidationError
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, SafetyLevel, CLIConfirmationCallback
from fastreact.core.react import ReActCore
from fastreact.core.events import EventType
from fastreact.skills import SkillRegistry
from fastreact.providers.litellm import LiteLLMProvider

from fastreact.tools import ReadFileTool, WriteFileTool, ExecTool, EditFileTool


class Agent:
    """
    The Body - Executor & Loop Controller

    Wraps ReActCore (Brain) and handles all execution logic:
    - Loop control (dual-layer loops for steering/followup)
    - Tool execution
    - Safety checks
    - Context monitoring
    - Filesystem memory

    Architecture:
        User Query → Agent.run_event_stream()
                        ↓
        ┌──────────────────────────────────┐
        │ Loop Control (while True)       │
        │                                  │
        │  1. Brain: run_step_stream()    │
        │     → THINK events              │
        │     → TOOL_CALL events          │
        │     → STEP_END event            │
        │                                  │
        │  2. Body: Execute Tools         │
        │     → Safety check              │
        │     → Tool execution            │
        │     → Context truncate          │
        │     → TOOL_RESULT events        │
        │                                  │
        │  3. Check Steering/Follow-up    │
        └──────────────────────────────────┘
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        skills_dir: Optional[Path] = None,
    ):
        """
        Initialize Agent (The Body)

        Args:
            config: Agent configuration (default: from config file or environment)
            skills_dir: Directory containing skills (default: ./skills/)
        """
        # Load configuration
        self._config = config or Config.load()

        # Initialize LLM provider
        self._llm = LiteLLMProvider(
            model=self._config.llm.model,
            api_base=self._config.llm.api_base,
            api_key=self._config.llm.api_key,
            temperature=self._config.llm.temperature,
            max_tokens=self._config.llm.max_tokens,
        )

        # Initialize tools
        self._tools = ToolRegistry()
        self._setup_tools()

        # Initialize skills
        self._skills = SkillRegistry()
        # Always try to load skills from default location
        try:
            from fastreact.skills import SkillLoader
            # Try default skills directory
            default_skills_dir = Path.cwd() / "skills"
            if default_skills_dir.exists():
                loader = SkillLoader(skills_dir=default_skills_dir)
                self._skills = SkillRegistry(loader=loader)
            elif skills_dir:
                # Use custom skills directory
                loader = SkillLoader(skills_dir=skills_dir)
                self._skills = SkillRegistry(loader=loader)
        except Exception as e:
            # Skills not available
            pass

        # Skills selection configuration
        self._auto_select_skills = True  # Auto-select skills when not specified
        self._max_auto_skills = 3  # Max skills to auto-select

        # Initialize context monitor (Body layer)
        self._context_monitor = ContextMonitor(
            max_tokens=self._config.react.max_context_tokens,
            warning_threshold=self._config.react.context_warning_threshold,
            max_tool_output_chars=self._config.react.max_tool_output_chars,
        )

        # Initialize filesystem memory (Body layer)
        self._filesystem_memory = None
        if self._config.react.enable_filesystem_memory:
            self._filesystem_memory = FilesystemMemory(
                max_tree_depth=self._config.react.max_tree_depth,
                max_files_per_dir=self._config.react.max_files_per_dir,
            )

        # Initialize safety policy (Body layer)
        self._safety_policy = None
        self._confirmation_callback = None
        if self._config.react.enable_safety:
            self._safety_policy = SafetyPolicy(
                strict_mode=self._config.react.strict_mode,
            )
            self._confirmation_callback = CLIConfirmationCallback()

        # Initialize Core (Brain) - minimal dependencies
        self._core = ReActCore(
            llm=self._llm,
            tools=self._tools,
            max_iterations=self._config.react.max_iterations,
        )

        # Session queues for steering/followup support
        self._session_queues: dict[str, MessageQueue] = {}

    def _select_skills_auto(self, query: str, max_skills: int = 3) -> list[str]:
        """
        Automatically select relevant skills based on query

        Args:
            query: User's query
            max_skills: Maximum number of skills to select

        Returns:
            List of selected skill names
        """
        import re
        from fastreact.skills import Skill

        # Get all available skills
        all_skills = []
        try:
            for skill_name in self._skills.list_available():
                skill = self._skills.get(skill_name)
                if skill:
                    all_skills.append(skill)
        except Exception:
            # If skills not available, return empty
            return []

        if not all_skills:
            return []

        # Extract keywords from query (simple tokenization)
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))

        # Score each skill
        skill_scores = []

        for skill in all_skills:
            score = 0

            # Match in name (high weight)
            if skill.name.lower() in query_lower:
                score += 10

            # Match in description
            desc_lower = skill.description.lower()
            desc_words = set(re.findall(r'\w+', desc_lower))

            # Keyword overlap
            overlap = query_words & desc_words
            score += len(overlap) * 2

            # Tag matching
            for tag in skill.metadata.tags:
                if tag.lower() in query_lower:
                    score += 5

            skill_scores.append((skill.name, score))

        # Sort by score and return top-k
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        selected = [name for name, score in skill_scores[:max_skills] if score > 0]

        return selected

    def _build_system_prompt_with_skills(self, skills: Optional[list[str]]) -> str:
        """
        Build system prompt with skills injected

        Args:
            skills: List of skill names to inject

        Returns:
            System prompt string with skills
        """
        from fastreact.core.prompts import get_system_prompt

        # Get base system prompt
        base_prompt = get_system_prompt("core")

        # If no skills specified, return base prompt
        if not skills:
            return base_prompt

        # Load skill descriptions
        skill_descriptions = []
        for skill_name in skills:
            skill = self._skills.get(skill_name)
            if skill:
                # Format skill info
                skill_info = f"## {skill.name}\n{skill.description}"
                if skill.metadata.tags:
                    skill_info += f"\nTags: {', '.join(skill.metadata.tags)}"
                skill_descriptions.append(skill_info)

        # If no skills loaded, return base prompt
        if not skill_descriptions:
            return base_prompt

        # Inject skills into system prompt
        skills_section = "\n\n# Available Skills\nThese skills are available for this task:\n\n"
        skills_section += "\n\n".join(skill_descriptions)
        skills_section += "\n\nUse these skills when appropriate to complete the user's request."

        return base_prompt + skills_section

    def enable_auto_skill_selection(self, max_skills: int = 3):
        """
        Enable automatic skill selection

        Args:
            max_skills: Maximum number of skills to auto-select
        """
        self._auto_select_skills = True
        self._max_auto_skills = max_skills

    def disable_auto_skill_selection(self):
        """Disable automatic skill selection"""
        self._auto_select_skills = False

    def _validate_history(self, history: Optional[list[dict]]) -> list[dict]:
        """
        Validate and clean conversation history

        Args:
            history: Raw history from user

        Returns:
            Validated and cleaned history
        """
        if not history:
            return []

        # Validate each message
        clean_history = []
        for msg in history:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content", "")

            # Skip invalid messages
            if role not in ("user", "assistant"):
                continue

            # Ensure content exists and is string
            if not content or not isinstance(content, str):
                continue

            # Clean content
            content = content.strip()

            # Skip empty messages
            if not content:
                continue

            clean_history.append({"role": role, "content": content})

        return clean_history

    def _setup_tools(self):
        """Setup core tools with config"""
        tool_config = self._config.tools

        self._tools.register(ReadFileTool(max_size=tool_config.max_file_size))
        self._tools.register(WriteFileTool(
            max_size=tool_config.max_file_size,
            protected_paths=tool_config.protected_paths,
        ))
        self._tools.register(ExecTool(
            timeout=tool_config.exec_timeout,
            working_dir=tool_config.working_dir,
        ))
        self._tools.register(EditFileTool(max_size=tool_config.max_file_size))

    def inject_message(self, session_id: str, message: Message):
        """
        Inject message into active session

        Args:
            session_id: Target session
            message: Message to inject (steering/followup)

        Raises:
            ValueError: If session not active
        """
        if session_id not in self._session_queues:
            raise ValueError(f"Session not active: {session_id}")

        self._session_queues[session_id].push(message)

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Run agent with event stream (Brain-Body Loop)

        This is PREFERRED API. It yields AgentEvent objects,
        providing complete visibility into execution.

        Args:
            query: User query
            skills: List of skill names to inject into system prompt
                   Skills provide specialized knowledge and capabilities
                   Example: ["git_workflow", "code_review"]
                   Set to None for no specific skills
            session_id: Session identifier (auto-generated if None)
                       Use same session_id across multiple calls for multi-turn conversation
            history: Optional conversation history in OpenAI format
                    [
                        {"role": "user", "content": "..."},
                        {"role": "assistant", "content": "..."},
                    ]
                    Note: Tool messages are managed internally, don't include them

        Yields:
            AgentEvent objects (DOES NOT consume LLM context)

            Events are yielded in real-time for UI visualization only.
            They do NOT affect the LLM's context window.

            Event types:
                - SESSION_START: Conversation started
                - THINK: LLM reasoning (may be empty if only tool call)
                - TOOL_CALL: Tool being called (intent, not execution yet)
                - TOOL_RESULT: Tool execution result
                - SESSION_END: Conversation ended with final answer
                - ERROR: Error occurred

        Example:
            # Simple query
            agent = Agent()
            async for event in agent.run_event_stream("What is 2+2?"):
                if event.type == EventType.THINK:
                    print(f"Thinking: {event.content}")
                elif event.type == EventType.SESSION_END:
                    print(f"Answer: {event.content}")

            # With skills
            async for event in agent.run_event_stream(
                "Review this code",
                skills=["code_review", "python_best_practices"]
            ):
                ...

            # Multi-turn conversation with history
            history = [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
            ]
            async for event in agent.run_event_stream(
                "What about 3+3?",
                session_id="same-session",  # Maintain context
                history=history
            ):
                ...
        """
        from fastreact.core.events import AgentEvent, EventType

        # Generate session_id if not provided
        session_id = session_id or str(uuid.uuid4())

        # Create session queue for steering/followup
        self._session_queues[session_id] = MessageQueue()

        try:
            # Emit SESSION_START
            yield AgentEvent.session_start(query, session_id)

            # Validate and clean history
            messages = self._validate_history(history)

            # Add current user message
            messages.append(Message.user(query).to_llm_format())

            # Build system prompt with skills
            # Auto-select skills if not specified and enabled
            if skills is None and self._auto_select_skills:
                skills = self._select_skills_auto(query, self._max_auto_skills)

            system_prompt = self._build_system_prompt_with_skills(skills)

            # Interrupt flag
            interrupted = False

            # === Outer loop: Process follow-up messages ===
            while True:
                has_more_tool_calls = True
                executed_tools_this_iteration = False  # Track tools in this iteration only

                # === Inner loop: Process tools ===
                while has_more_tool_calls:
                    # 1. Brain: Ask LLM for reasoning
                    pending_messages = self._session_queues.get(session_id, MessageQueue())

                    # Process pending messages (steering/interrupt/followup)
                    if pending_messages:
                        for msg in pending_messages.drain():
                            # Check for interrupt signal
                            if msg.content.startswith("[INTERRUPT]"):
                                # Add to message history so LLM sees it
                                messages.append(msg.to_llm_format())

                                # Notify user about interrupt
                                yield AgentEvent.think(
                                    f"[USER INTERRUPT: {msg.content.replace('[INTERRUPT] ', '')}]",
                                    session_id,
                                    metadata={"source": "user"}
                                )

                                # Set flag to stop after current iteration
                                interrupted = True
                                has_more_tool_calls = False  # Stop tool loop
                                break  # Exit message processing loop

                            # Regular steering/followup messages
                            messages.append(msg.to_llm_format())
                            # Emit steering event for visibility
                            if msg.role in ("steering", "followup"):
                                yield AgentEvent.think(
                                    f"[{msg.role.upper()}] {msg.content}",
                                    session_id,
                                    metadata={"source": msg.metadata.get("source", "unknown")},
                                )

                    # Call Brain (Core) for reasoning step
                    step_end = None
                    tool_calls = []  # Collect tool calls from Core

                    async for event in self._core.run_step_stream(
                        messages=messages,
                        session_id=session_id,
                        system_prompt=system_prompt,  # Pass skills-enhanced prompt
                    ):
                        # Forward THINK events
                        if event.type == EventType.THINK:
                            yield event

                        # Collect TOOL_CALL events
                        elif event.type == EventType.TOOL_CALL:
                            yield event
                            # Collect tool call for execution
                            tool_calls.append({
                                "id": event.metadata.get("call_id", ""),
                                "name": event.tool_name,
                                "arguments": event.tool_args,
                            })

                        # Capture STEP_END to handle tool execution
                        elif event.type == EventType.STEP_END:
                            step_end = event
                            # CRITICAL: Add LLM response to message history
                            # Must include tool_calls if present (OpenAI format requirement)
                            if step_end.content and step_end.content.strip() or tool_calls:
                                assistant_msg = {
                                    "role": "assistant",
                                }
                                # Add content if present
                                if step_end.content and step_end.content.strip():
                                    assistant_msg["content"] = step_end.content
                                else:
                                    assistant_msg["content"] = ""  # Required by OpenAI

                                # Add tool_calls if present (CRITICAL for function calling)
                                if tool_calls:
                                    assistant_msg["tool_calls"] = [
                                        {
                                            "id": tc.get("id", ""),
                                            "type": "function",
                                            "function": {
                                                "name": tc.get("name", ""),
                                                "arguments": json.dumps(tc.get("arguments", {})),
                                            },
                                        }
                                        for tc in tool_calls
                                    ]

                                messages.append(assistant_msg)
                            break

                    # 2. Body: Execute tools (if any)
                    if step_end and step_end.metadata.get("has_tool_calls") and tool_calls:
                        for tool_call in tool_calls:
                            tool_name = tool_call.get("name", "")
                            tool_params = tool_call.get("arguments", {})
                            call_id = tool_call.get("id", "")

                            # TOOL_CALL already emitted by Core, no need to re-emit

                            # Safety check
                            if self._safety_policy:
                                decision = self._safety_policy.check(
                                    tool_name=tool_name,
                                    args=tool_params,
                                )
                                # Block forbidden operations
                                if decision.level == SafetyLevel.FORBIDDEN:
                                    result = f"[SAFETY_BLOCKED] {decision.reason}"
                                    yield AgentEvent.tool_result(tool_name, result, session_id)
                                    messages.append(Message.tool(
                                        name=tool_name,
                                        result=result,
                                        call_id=call_id,
                                    ).to_llm_format())
                                    continue

                            # Execute tool
                            try:
                                result = await self._tools.execute(tool_name, tool_params)

                                # Context truncate if needed
                                if self._context_monitor:
                                    result = self._context_monitor.truncate_tool_output(result)

                            except Exception as e:
                                result = f"[ERROR] {str(e)}"

                            # Emit TOOL_RESULT event
                            yield AgentEvent.tool_result(tool_name, result, session_id)

                            # Add tool result to history
                            import sys
                            print(f"[DEBUG] Tool result: tool_name={tool_name}, call_id='{call_id}'", file=sys.stderr)
                            messages.append(Message.tool(
                                name=tool_name,
                                result=result,
                                call_id=call_id,
                            ).to_llm_format())
                        # Tools executed, prepare for next LLM call
                        executed_tools_this_iteration = True
                        has_more_tool_calls = False
                        import sys
                        print(f"[DEBUG] Tools executed, will continue", file=sys.stderr)
                    else:
                        # No tool calls - exit inner loop
                        has_more_tool_calls = False

                # After inner loop, check if we should continue
                # Continue if:
                # 1. We just executed tools in this iteration (need LLM to process results)
                # 2. There are follow-up messages

                # Check for follow-up messages
                has_followup = bool(self._session_queues.get(session_id, MessageQueue()))

                # If we executed tools in this iteration, continue to next iteration
                if executed_tools_this_iteration and not has_followup:
                    # Continue to process tool results
                    continue

                # If there are follow-up messages, continue to process them
                if has_followup:
                    continue

                # Otherwise, we're done
                break

            # Check if we were interrupted
            if interrupted:
                # Extract last assistant message if available
                last_response = ""
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        if content and not content.startswith("["):
                            last_response = content
                            break

                # Emit interrupted session end
                interrupt_msg = "[INTERRUPTED] User stopped the execution"
                if last_response:
                    interrupt_msg = f"{last_response}\n\n[INTERRUPTED] User stopped the execution"

                yield AgentEvent.session_end(session_id, interrupt_msg)
                return

            # Extract final answer from last assistant message
            final_answer = ""
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if content and not content.startswith("["):
                        final_answer = content
                        break

            # Emit SESSION_END
            yield AgentEvent.session_end(session_id, final_answer)

        except Exception as e:
            yield AgentEvent.error(str(e), session_id)

    async def run(
        self,
        query: str,
        skills: Optional[list[str]] = None,
    ) -> str:
        """
        Run agent (simplified API)

        This is convenience method that aggregates all THINK events
        and returns final answer.

        Args:
            query: User query
            skills: List of skills to use (None = auto-select)

        Returns:
            Agent's final response
        """
        final_content = []

        async for event in self.run_event_stream(query, skills=skills):
            if event.type == EventType.THINK:
                final_content.append(event.content)
            elif event.type == EventType.SESSION_END:
                return event.content or "".join(final_content)

        return "".join(final_content)

    async def chat(
        self,
        message: str,
        history: Optional[list[Message]] = None,
    ) -> str:
        """
        Simple chat interface (legacy compatibility)

        Args:
            message: User message
            history: Conversation history (optional)

        Returns:
            Agent response
        """
        return await self.run(message)

    def list_skills(self) -> list[str]:
        """Return list of available skill names"""
        return self._skills.list_skills()

    @property
    def llm(self):
        """Expose LLM provider for REPL compatibility"""
        return self._llm


# Convenience functions
async def ask(
    query: str,
    skills: Optional[list[str]] = None,
    config: Optional[Config] = None,
) -> str:
    """
    Quick async query

    Args:
        query: User query
        skills: Skills to use (None = auto-select)
        config: Optional config

    Returns:
        Agent response
    """
    agent = Agent(config=config)
    return await agent.run(query, skills=skills)


def ask_sync(
    query: str,
    **kwargs,
) -> str:
    """
    Quick synchronous query

    Args:
        query: User query
        **kwargs: Additional arguments passed to Agent

    Returns:
        Agent response
    """
    return asyncio.run(ask(query, **kwargs))


__all__ = [
    "Agent",
    "ask",
    "ask_sync",
]
