"""Agent runtime facade for the ReAct execution loop."""

import json
import logging
import uuid
from typing import AsyncIterator, Optional, TYPE_CHECKING

from fastreact.runtime.timing import TimingSpan
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.multitenant import UserContext
from fastreact.runtime.tool_policy import apply_tool_policy_scope, filter_tool_registry, normalize_tool_policy, tool_policy_denial

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastreact.agent import Agent
    from fastreact.core.events import AgentEvent


class DigestToolBudgetGuard:
    """Per-run MCP tool budget guard for constrained PSKA digest worker runs."""

    DEFAULT_BUDGET = {
        "pska_pska_write_candidates": 1,
        "pska_pska_job_context": 1,
    }

    def __init__(self, metadata: Optional[dict] = None):
        metadata = metadata or {}
        self.enabled = metadata.get("caller") == "pska_digest_worker" or metadata.get("purpose") == "digest"
        configured_budget = metadata.get("tool_budget") if isinstance(metadata.get("tool_budget"), dict) else {}
        self.budget = {
            name: int(configured_budget.get(name, default) or default)
            for name, default in self.DEFAULT_BUDGET.items()
        }
        self.counts = {name: 0 for name in self.budget}

    def allow(self, tool_name: str) -> bool:
        if not self.enabled or tool_name not in self.budget:
            return True
        if self.counts.get(tool_name, 0) >= self.budget[tool_name]:
            return False
        self.counts[tool_name] = self.counts.get(tool_name, 0) + 1
        return True

    def validate(self, tool_name: str, tool_args: Optional[dict] = None) -> str | None:
        if not self.enabled or tool_name != "pska_pska_write_candidates":
            return None
        args = tool_args if isinstance(tool_args, dict) else {}
        counts = _pska_candidate_counts(args)
        if sum(counts.values()) == 0:
            return (
                "pska_pska_write_candidates requires at least one candidate. "
                "For digest jobs, first write knowledge_claims with evidence_text and source_refs."
            )
        if (counts["digest_notes"] or counts["hyperedges"]) and not counts["knowledge_claims"]:
            return (
                "Digest notes, hyperedges, and relationship suggestions require at least one "
                "knowledge_claim in the same pska_pska_write_candidates payload."
            )
        return None


def _pska_candidate_counts(args: dict) -> dict[str, int]:
    return {
        "knowledge_claims": _list_count(args.get("knowledge_claims")),
        "digest_notes": _list_count(args.get("digest_notes")),
        "entities": _list_count(args.get("entities")),
        "hyperedges": _list_count(args.get("hyperedges")),
        "review_items": _list_count(args.get("review_items")),
        "memory_candidates": _list_count(args.get("memory_candidates") or args.get("memory")),
    }


def _list_count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


class AgentRuntime:
    """
    Runtime boundary for Agent execution.

    AgentRuntime owns the ReAct loop, runtime timing, persistence events,
    tool execution handoff, and queue-based user intervention handling.
    Agent remains the public facade for configuration and compatibility.
    """

    def __init__(self, agent: "Agent"):
        self._agent = agent

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        user_key: Optional[str] = None,
        run_metadata: Optional[dict] = None,
        llm_options: Optional[dict] = None,
    ) -> AsyncIterator["AgentEvent"]:
        span = TimingSpan("agent.run_event_stream")
        first_event_seen = False
        event_count = 0
        time_to_first_event_ms = None
        final_answer_length = 0
        usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async for event in self._run_event_stream_impl(
            query=query,
            skills=skills,
            session_id=session_id,
            history=history,
            user_key=user_key,
            run_metadata=run_metadata,
            llm_options=llm_options,
        ):
            event_count += 1
            if not first_event_seen:
                first_event_seen = True
                event.metadata.setdefault("timing", {})
                time_to_first_event_ms = round(span.elapsed_ms, 2)
                event.metadata["timing"]["time_to_first_event_ms"] = time_to_first_event_ms

            llm_usage = event.metadata.get("llm_usage")
            if isinstance(llm_usage, dict):
                if "total_tokens" not in llm_usage:
                    prompt_tokens = llm_usage.get("prompt_tokens", 0)
                    completion_tokens = llm_usage.get("completion_tokens", 0)
                    if isinstance(prompt_tokens, (int, float)) and isinstance(completion_tokens, (int, float)):
                        llm_usage["total_tokens"] = int(prompt_tokens) + int(completion_tokens)
                for key in usage_totals:
                    value = llm_usage.get(key)
                    if isinstance(value, (int, float)):
                        usage_totals[key] += int(value)

            if event.type.value in ("session_end", "error"):
                span.finish(event_type=event.type.value)
                event.metadata.setdefault("timing", {})
                event.metadata["timing"]["time_to_final_ms"] = round(span.elapsed_ms, 2)
                event.metadata["llm_usage_total"] = {
                    key: value for key, value in usage_totals.items() if value
                }
                final_answer_length = len(event.content or "")
                if hasattr(self._agent, "store"):
                    self._agent.store.append("traces", {
                        "session_id": event.session_id,
                        "query": query,
                        "skills": skills or event.metadata.get("skills", []),
                        "event_type": event.type.value,
                        "time_to_first_event_ms": time_to_first_event_ms,
                        "time_to_final_ms": round(span.elapsed_ms, 2),
                        "event_count": event_count,
                        "final_answer_length": final_answer_length,
                        "llm_usage_total": event.metadata["llm_usage_total"],
                    })

            self._record_event(event, query=query, user_key=user_key, skills=skills, final_answer_length=final_answer_length)
            yield event

    def _record_event(self, event: "AgentEvent", query: str, user_key: Optional[str], skills: Optional[list[str]], final_answer_length: int) -> None:
        if not hasattr(self._agent, "store"):
            return
        self._agent.store.append("events", event.to_dict())
        if event.type.value == "session_start":
            self._agent.store.upsert_snapshot("sessions", "session_id", {
                "session_id": event.session_id,
                "user_key": user_key,
                "status": "running",
                "query": query,
                "skills": event.metadata.get("skills", []),
                "last_event_type": event.type.value,
            })
        elif event.type.value in ("session_end", "error"):
            self._agent.store.upsert_snapshot("sessions", "session_id", {
                "session_id": event.session_id,
                "user_key": user_key,
                "status": "idle" if event.type.value == "session_end" else "error",
                "query": query,
                "skills": skills or [],
                "last_event_type": event.type.value,
                "final_answer_length": final_answer_length,
            })

    def _record_span(self, session_id: str, name: str, span: TimingSpan, **metadata) -> None:
        span.finish(**metadata)
        if hasattr(self._agent, "store"):
            self._agent.store.append("runtime_spans", {
                "session_id": session_id,
                "name": name,
                "duration_ms": round(span.elapsed_ms, 2),
                **metadata,
            })

    async def _run_event_stream_impl(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        user_key: Optional[str] = None,
        run_metadata: Optional[dict] = None,
        llm_options: Optional[dict] = None,
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
            user_key: User identifier for multi-tenant mode (format: "channel:user_id")
                     Example: "feishu:ou_1234567890"
                     If None and multi-tenant enabled, will extract from session_id

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
                    logger.debug(f"Thinking: {event.content}")
                elif event.type == EventType.SESSION_END:
                    logger.debug(f"Answer: {event.content}")

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

            # Multi-tenant mode
            agent = Agent(multitenant=True)
            async for event in agent.run_event_stream(
                "Create file test.txt",
                user_key="feishu:ou_xxx"  # User-specific workspace
            ):
                ...
        """
        from fastreact.core.events import AgentEvent, EventType

        agent = self._agent
        budget_guard = DigestToolBudgetGuard(run_metadata)
        llm_options = {key: value for key, value in (llm_options or {}).items() if value is not None}
        tenant_key = (run_metadata or {}).get("tenant_key")
        run_tool_policy = normalize_tool_policy((run_metadata or {}).get("tool_policy"))

        # Extract user_key from session_id if not provided
        if user_key is None and agent._multitenant_enabled and session_id:
            # Try to extract from session_id (e.g., "feishu:ou_xxx:session-uuid")
            if ":" in session_id:
                parts = session_id.split(":")
                if len(parts) >= 2:
                    user_key = f"{parts[0]}:{parts[1]}"

        # Get user context if multi-tenant (must be before skill selection)
        user_context: Optional[UserContext] = None
        if agent._multitenant_enabled and user_key:
            user_context = agent._multitenant.get_user_context(user_key, tenant_key=tenant_key)
            tenant_key = user_context.tenant_key

        # Auto-select skills if not specified and enabled
        if skills is None and agent._auto_select_skills:
            skills = agent.skill_resolver.auto_select(
                query,
                user_context=user_context,
            )

        # Load MCP servers on first run (lazy initialization)
        # Pass selected skills to load only required MCP servers
        mcp_span = TimingSpan("mcp.bootstrap")
        if run_tool_policy.mode != "none":
            await agent.mcp_bootstrapper.ensure_loaded(
                required_skills=skills,
                user_key=user_key,
                tenant_key=tenant_key,
            )

        # Generate session_id if not provided
        session_id = session_id or str(uuid.uuid4())

        # Prepend user_key to session_id for multi-tenant
        if user_context and ":" not in session_id:
            session_id = f"{user_key}:{session_id}"
        run_tools = filter_tool_registry(agent._tools, run_tool_policy)
        self._record_span(
            session_id,
            "mcp.bootstrap",
            mcp_span,
            skills=skills or [],
            tool_policy=run_tool_policy.to_metadata(),
            visible_tools=run_tools.list_all(),
        )

        # Get or create session and set user_key
        session = agent.get_session(session_id)
        if not session:
            session = agent.create_session(session_id, user_key=user_key, tenant_key=tenant_key)
        else:
            session.user_key = user_key
            session.tenant_key = tenant_key

        # Set running status
        session.set_status("running")

        # Create session queue for steering/followup (only if not exists)
        # This prevents overwriting queue that may have injected messages
        if session_id not in agent._session_queues:
            agent._session_queues[session_id] = MessageQueue()

        try:
            # Emit SESSION_START with skills information
            session_start = AgentEvent.session_start(query, session_id, skills=skills)
            session_start.metadata["tool_policy"] = run_tool_policy.to_metadata()
            session_start.metadata["visible_tools"] = run_tools.list_all()
            yield session_start

            # Validate and clean history
            messages = agent._validate_history(history)

            # Add current user message
            messages.append(Message.user(query).to_llm_format())

            # Build system prompt with skills (skills already selected above)
            # Returns (base_prompt, skills_content) for cache-friendly injection
            context_span = TimingSpan("context.assembly")
            base_prompt, skills_content = agent.skill_resolver.build_prompt(
                skills,
                user_context=user_context,
            )

            # Inject skills content as a separate system message at the START of messages
            # This keeps base_prompt constant (cacheable) while providing skills context
            messages.insert(0, {"role": "system", "content": skills_content})
            self._record_span(
                session_id,
                "context.assembly",
                context_span,
                skills=skills or [],
                tool_policy=run_tool_policy.to_metadata(),
                visible_tools=run_tools.list_all(),
            )

            # Use base_prompt for Core (constant, cacheable)
            system_prompt = base_prompt

            # Interrupt flag
            interrupted = False

            # Iteration counter with hard limit to prevent infinite loops
            iteration_count = 0
            max_iterations = agent._config.react.max_iterations if agent._config else 25

            # === Outer loop: Process follow-up messages ===
            while True:
                # HARD LIMIT: Prevent infinite loops
                iteration_count += 1
                if iteration_count > max_iterations:
                    # Circuit breaker: immediately terminate with clear error message
                    yield AgentEvent.session_end(
                        session_id,
                        f"[STOPPED] Task stopped due to maximum iteration limit ({max_iterations}). "
                        f"This usually means the agent is stuck in a loop or the task is too complex. "
                        f"Please try breaking down the task into smaller steps."
                    )
                    return
                has_more_tool_calls = True
                executed_tools_this_iteration = False  # Track tools in this iteration only

                # === Inner loop: Process tools ===
                while has_more_tool_calls:
                    # 1. Brain: Ask LLM for reasoning
                    pending_messages = agent._session_queues.get(session_id, MessageQueue())

                    # Log queue status at debug level only.
                    msg_count = len(pending_messages._messages) if pending_messages else 0
                    logger.debug(
                        "Inner loop start: queue has %s messages",
                        msg_count,
                    )

                    # Process pending messages (steering/interrupt/followup)
                    if pending_messages:
                        for msg in pending_messages.drain():
                            logger.debug(
                                "Processing message: role=%s, content=%s",
                                msg.role,
                                msg.content[:30],
                            )

                            # Check for steering messages (user intervention from any adapter)
                            # Use role="steering" instead of hardcoded adapter types
                            if msg.role == "steering":
                                msg_source = msg.metadata.get("source", "unknown")
                                # User intervention: append as new user message
                                # This preserves all previous tool results so LLM can understand "what you just did"
                                messages.append({
                                    "role": "user",
                                    "content": f"[USER INTERVENTION]: {msg.content}"
                                })

                                # Send notification
                                yield AgentEvent.think(
                                    f"[USER INTERVENTION] {msg.content}",
                                    session_id,
                                    source=msg_source,
                                    user_intervention=True
                                )
                                # Continue execution, don't set interrupted flag
                                break

                            # Legacy interrupt signal handling (for backward compatibility)
                            if msg.content.startswith("[INTERRUPT]"):
                                # Extract new query from metadata
                                new_query = msg.metadata.get("new_query", "")
                                if new_query:
                                    # Replace the original user query with the new one
                                    # Find and replace the first user message
                                    for i, m in enumerate(messages):
                                        if m.get("role") == "user":
                                            messages[i] = {
                                                "role": "user",
                                                "content": new_query
                                            }
                                            break

                                    # Notify user about the query switch
                                    yield AgentEvent.think(
                                        f"[查询切换] {new_query}",
                                        session_id,
                                        metadata={"source": "user", "query_switch": True}
                                    )

                                    # Continue processing with new query (don't set interrupted flag)
                                    # This preserves context from previous tool calls
                                    break

                            # Regular steering/followup messages
                            messages.append(msg.to_llm_format())
                            # Emit steering event for visibility
                            if msg.role in ("steering", "followup"):
                                yield AgentEvent.think(
                                    f"[{msg.role.upper()}] {msg.content}",
                                    session_id,
                                    metadata={"source": msg.metadata.get("source", "unknown")},
                                )

                    # Compress context before LLM call (each iteration)
                    compress_span = TimingSpan("context.compress")
                    metadata_context_tokens = _positive_int((run_metadata or {}).get("max_context_tokens"))
                    configured_context_tokens = int(getattr(agent._config.react, "max_context_tokens", 12000) or 12000)
                    max_context_tokens = metadata_context_tokens or configured_context_tokens
                    completion_buffer = _positive_int(llm_options.get("max_tokens")) or int(
                        getattr(agent._config.llm, "max_tokens", 0) or 0
                    )
                    compression_budget = max(1, max_context_tokens - completion_buffer)
                    compressed_messages = agent._compress_context(
                        messages,
                        max_tokens=compression_budget,
                        preserve_system=True,
                        preserve_initial_query=True,
                        # recent_count defaults to config value
                    )
                    compression_metadata = getattr(agent, "_last_compression_metadata", {})
                    self._record_span(
                        session_id,
                        "context.compress",
                        compress_span,
                        message_count=len(messages),
                        max_context_tokens=max_context_tokens,
                        completion_buffer_tokens=completion_buffer,
                        compression_budget_tokens=compression_budget,
                        **{key: value for key, value in compression_metadata.items() if key != "preserved_message_indices"},
                    )
                    if compression_metadata.get("compressed"):
                        yield AgentEvent.think(
                            "[CONTEXT_COMPRESSION] Sliding-window context compression applied",
                            session_id,
                            compression=compression_metadata,
                            compression_event=True,
                        )

                    # Call Brain (Core) for reasoning step
                    step_end = None
                    tool_calls = []  # Collect tool calls from Core

                    llm_span = TimingSpan("llm.step")
                    async for event in agent._core.run_step_stream(
                        messages=compressed_messages,  # Use compressed messages
                        session_id=session_id,
                        system_prompt=system_prompt,  # Pass skills-enhanced prompt
                        llm_options=llm_options,
                        tools=run_tools,
                    ):
                        # Collect TOOL_CALL events for execution
                        if event.type == EventType.TOOL_CALL:
                            scoped_args, scope_injected = apply_tool_policy_scope(event.tool_name or "", event.tool_args or {}, run_tool_policy)
                            if scope_injected:
                                event.tool_args = scoped_args
                                event.metadata["tool_policy_scope_applied"] = True
                                event.metadata["tool_policy"] = run_tool_policy.to_metadata()
                            denial = tool_policy_denial(event.tool_name or "", run_tool_policy)
                            if denial:
                                event.metadata["tool_policy_denied"] = True
                                event.metadata["tool_policy"] = run_tool_policy.to_metadata()
                                event.metadata["denial_reason"] = denial
                                yield event
                                tool_calls.append({
                                    "id": event.metadata.get("call_id", ""),
                                    "name": event.tool_name,
                                    "arguments": scoped_args,
                                    "tool_policy_denied": denial,
                                })
                                continue
                            validation_error = budget_guard.validate(event.tool_name or "", scoped_args)
                            if validation_error:
                                yield event
                                tool_calls.append({
                                    "id": event.metadata.get("call_id", ""),
                                    "name": event.tool_name,
                                    "arguments": scoped_args,
                                    "validation_error": validation_error,
                                })
                                continue
                            if not budget_guard.allow(event.tool_name or ""):
                                yield AgentEvent.think(
                                    f"[TOOL_BUDGET_DENIED] {event.tool_name} exceeded per-run budget",
                                    session_id,
                                    tool_name=event.tool_name,
                                    budget=budget_guard.budget.get(event.tool_name or ""),
                                    tool_budget_denied=True,
                                )
                                continue
                            # Forward allowed tool call intents only after budget filtering.
                            yield event
                            tool_calls.append({
                                "id": event.metadata.get("call_id", ""),
                                "name": event.tool_name,
                                "arguments": scoped_args,
                                "validation_error": validation_error,
                            })
                            continue

                        # Capture STEP_END to handle tool execution
                        if event.type == EventType.STEP_END:
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
                            yield event
                            break

                        # Forward all non-tool-call events directly.
                        yield event
                    self._record_span(session_id, "llm.step", llm_span, tool_calls=len(tool_calls))

                    # 2. Body: Execute tools (if any)
                    if step_end and step_end.metadata.get("has_tool_calls") and tool_calls:
                        for tool_call in tool_calls:
                            tool_name = tool_call.get("name", "")
                            tool_params = tool_call.get("arguments", {})
                            call_id = tool_call.get("id", "")
                            validation_error = tool_call.get("validation_error")
                            tool_policy_denied = tool_call.get("tool_policy_denied")

                            if tool_policy_denied:
                                result = f"[TOOL_POLICY_DENIED] {tool_policy_denied}"
                                result_event = AgentEvent.tool_result(tool_name, result, session_id)
                                result_event.metadata.update({
                                    "request_id": call_id,
                                    "tool_policy_denied": True,
                                    "tool_policy": run_tool_policy.to_metadata(),
                                    "denial_reason": tool_policy_denied,
                                })
                                yield result_event
                                messages.append(Message.tool(
                                    name=tool_name,
                                    result=result,
                                    call_id=call_id,
                                ).to_llm_format())
                                continue

                            if validation_error:
                                result = f"[PSKA_DIGEST_VALIDATION_ERROR] {validation_error}"
                                result_event = AgentEvent.tool_result(tool_name, result, session_id)
                                result_event.metadata.update({
                                    "request_id": call_id,
                                    "digest_validation_error": True,
                                })
                                yield result_event
                                messages.append(Message.tool(
                                    name=tool_name,
                                    result=result,
                                    call_id=call_id,
                                ).to_llm_format())
                                continue

                            # User input checkpoint: check for pending messages before tool execution
                            pending = agent._session_queues.get(session_id, MessageQueue())
                            if pending:
                                logger.debug(
                                    "Tool execution checkpoint: found %s messages",
                                    len(pending._messages),
                                )
                                for msg in pending.drain():
                                    logger.debug(
                                        "Tool checkpoint processing: role=%s, content=%s",
                                        msg.role,
                                        msg.content[:30],
                                    )

                                    # Check for steering messages (user intervention from any adapter)
                                    # Use role="steering" instead of hardcoded adapter types
                                    if msg.role == "steering":
                                        msg_source = msg.metadata.get("source", "unknown")
                                        # User intervention during tool execution
                                        # Pass metadata as keyword arguments, not nested dict
                                        yield AgentEvent.think(
                                            f"[USER INTERVENTION] {msg.content}",
                                            session_id,
                                            source=msg_source,
                                            user_intervention=True,
                                            tool_interrupted=True
                                        )

                                        # Add as steering message
                                        messages.append({
                                            "role": "user",
                                            "content": f"[USER INTERVENTION]: {msg.content}"
                                        })

                                        # Exit tool execution loop
                                        has_more_tool_calls = False
                                        break

                                # If user interrupted, skip remaining tools
                                if not has_more_tool_calls:
                                    break

                            # Execute tool through the runtime boundary
                            decision, approval_event = agent.tool_executor.assess(
                                tool_name=tool_name,
                                tool_params=tool_params,
                                session_id=session_id,
                                user_key=user_key,
                                tenant_key=tenant_key,
                            )
                            approved = None
                            request_id = None
                            if approval_event:
                                request_id = approval_event.metadata.get("request_id")
                                yield approval_event
                                approval_span = TimingSpan("tool.approval_wait")
                                approved = await agent.tool_executor.wait_for_approval(request_id)
                                self._record_span(session_id, "tool.approval_wait", approval_span, tool_name=tool_name, approved=approved)

                            tool_span = TimingSpan("tool.execution")
                            execution, result_event = await agent.tool_executor.execute(
                                tool_name=tool_name,
                                tool_params=tool_params,
                                session_id=session_id,
                                user_context=user_context,
                                decision=decision,
                                approved=approved,
                                request_id=request_id,
                            )
                            self._record_span(session_id, "tool.execution", tool_span, tool_name=tool_name, result_length=len(execution.result or ""))
                            result = execution.result
                            yield result_event

                            # Add tool result to history
                            logger.debug(
                                "Tool result: tool_name=%s, call_id=%r, result_length=%s",
                                tool_name,
                                call_id,
                                len(result),
                            )
                            messages.append(Message.tool(
                                name=tool_name,
                                result=result,
                                call_id=call_id,
                            ).to_llm_format())

                            # ✅ CRITICAL: Check queue immediately after each tool execution
                            # This allows faster response to user intervention
                            pending = agent._session_queues.get(session_id, MessageQueue())
                            if pending and pending._messages:
                                logger.debug(
                                    "Post-tool checkpoint: %s messages queued after %s",
                                    len(pending._messages),
                                    tool_name,
                                )
                                # Don't drain here - let next inner loop handle it
                                # Just break out of tool execution loop to speed up response
                                has_more_tool_calls = False
                                break

                        # Tools executed, prepare for next LLM call
                        executed_tools_this_iteration = True
                        has_more_tool_calls = False
                        logger.debug("Tools executed in this iteration, will continue to next iteration")
                    else:
                        # No tool calls - exit inner loop
                        has_more_tool_calls = False

                # After inner loop, check if we should continue
                # Continue if:
                # 1. We just executed tools in this iteration (need LLM to process results)
                # 2. There are follow-up messages
                # 3. LLM hasn't generated a final answer yet

                # Check for follow-up messages (user intervention, etc.)
                followup_queue = agent._session_queues.get(session_id, MessageQueue())
                has_followup = bool(followup_queue)

                queue_in_dict = agent._session_queues.get(session_id)
                logger.debug(
                    "After inner loop: queue_in_dict=%s, has_followup=%s, len=%s, executed_tools=%s",
                    queue_in_dict is not None,
                    has_followup,
                    len(followup_queue._messages) if followup_queue else "N/A",
                    executed_tools_this_iteration,
                )
                if has_followup:
                    logger.debug(
                        "Found %s follow-up messages, continuing loop",
                        len(followup_queue._messages),
                    )

                # If we executed tools in this iteration, continue to next iteration
                # (LLM needs to process tool results and generate next action)
                if executed_tools_this_iteration and not has_followup:
                    continue

                # If there are follow-up messages, continue to process them
                if has_followup:
                    continue

                # CRITICAL FIX: Check if LLM has generated a final answer
                # If the last assistant message is a text response (not tool calls),
                # we can consider the task complete
                has_final_answer = False
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        # Check if this is a meaningful text response (not just thinking)
                        if content and not content.startswith("[") and len(content.strip()) > 0:
                            has_final_answer = True
                            break

                # Only break if we have a final answer OR we've hit max iterations
                if has_final_answer:
                    logger.debug(
                        "Agent loop completed: has_final_answer=True, executed_tools=%s, has_followup=%s",
                        executed_tools_this_iteration,
                        has_followup,
                    )
                    break
                elif not executed_tools_this_iteration and not has_followup:
                    # LLM didn't call tools AND didn't generate text response
                    # This might be an error or empty response - log warning
                    logger.debug(
                        "Agent loop ended without final answer or tool calls (executed_tools=%s, has_followup=%s)",
                        executed_tools_this_iteration,
                        has_followup,
                    )
                    break
                # Otherwise, continue the loop
                logger.debug(
                    "Agent loop continuing (executed_tools=%s, has_followup=%s, has_final_answer=%s)",
                    executed_tools_this_iteration,
                    has_followup,
                    has_final_answer,
                )

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

        finally:
            # Update session state to idle and update activity
            session = agent.get_session(session_id)
            if session:
                session.set_status("idle")
                session.update_activity()
