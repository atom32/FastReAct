"""
Message Pumps - The Triple Message Pump Architecture for Reactive Loop

Implements the three-pump system for cognitive steering:
1. SteeringPump (转向泵) - High priority, real-time intervention
2. ExecutionPump (执行泵) - Medium priority, standard ReACT loop
3. FollowUpPump (跟进泵) - Low priority, task chaining

Architecture approved in Sprint 4: The Reactive Loop

Key innovation: "Physical Stop vs Cognitive Steering"
- CRITICAL interrupts -> Physical stop (terminate execution)
- NORMAL/HIGH interrupts -> Cognitive steering (inject message, redirect agent)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from .message import AgentMessage, MessageRole, MessageSource, steering_message, policy_intervention_message
from ..graph.interrupt import (
    PriorityInterruptQueue,
    PriorityInterrupt,
    InterruptPriority,
    SpecialCommand
)

logger = logging.getLogger(__name__)


# ============================================================================
# Message Pump Base Class
# ============================================================================

class MessagePump(ABC):
    """
    Abstract base class for message pumps

    A pump "draws" messages from various sources and injects them
    into the agent's context at specific points in the execution loop.

    Pump Priority (high to low):
    1. SteeringPump - Check before LLM call, after tool execution
    2. ExecutionPump - Standard LLM responses
    3. FollowUpPump - Check after task completion

    Usage:
        pump = SteeringPump(interrupt_queue)
        messages = await pump.pump(context)
        if messages:
            context.add_messages(messages)
    """

    @abstractmethod
    async def pump(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Draw messages from the pump source

        Args:
            context: Current agent execution context

        Returns:
            List of AgentMessage objects to inject into context
        """
        pass

    def is_enabled(self) -> bool:
        """Check if pump is enabled"""
        return True


# ============================================================================
# Steering Pump (转向泵)
# ============================================================================

class SteeringPump(MessagePump):
    """
    High priority pump for real-time cognitive steering

    Sources:
    1. PriorityInterruptQueue - User interruptions (/fix, normal input)
    2. PolicyEngine - Policy interventions (security, compliance)
    3. Custom callbacks - External steering hooks

    Behavior:
    - CRITICAL interrupts (/stop) -> Mark context as terminated
    - HIGH interrupts (/fix, /skip) -> Convert to steering messages
    - NORMAL interrupts -> Convert to user messages
    - Policy violations -> Convert to system messages

    Example:
        pump = SteeringPump(
            interrupt_queue=user_queue,
            policy_engine=policy_engine
        )

        # Check for steering
        messages = await pump.pump(context)
        for msg in messages:
            if msg.metadata.get("critical"):
                context.terminate(reason=msg.content)
            else:
                context.add_message(msg)  # Redirect agent
    """

    def __init__(
        self,
        interrupt_queue: Optional[PriorityInterruptQueue] = None,
        policy_engine = None,
        custom_steering_hooks: Optional[List[Callable]] = None,
    ):
        """
        Initialize steering pump

        Args:
            interrupt_queue: Priority interrupt queue for user input
            policy_engine: Optional policy engine for runtime checks
            custom_steering_hooks: Optional list of async callbacks for custom steering
        """
        self.interrupt_queue = interrupt_queue
        self.policy_engine = policy_engine
        self.custom_steering_hooks = custom_steering_hooks or []
        self._enabled = True

        # Statistics
        self._stats = {
            "total_interrupts_handled": 0,
            "critical_stops": 0,
            "policy_interventions": 0,
            "custom_steering": 0,
        }

    async def pump(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Draw steering messages from all sources

        Priority order:
        1. Critical interrupts (terminate immediately)
        2. Policy engine checks
        3. User interrupts (HIGH/NORMAL priority)
        4. Custom steering hooks

        Args:
            context: Current agent execution context

        Returns:
            List of steering messages to inject into context

        Note:
            If CRITICAL interrupt is detected, context.mark_terminated() is called
            and the returned list may contain a termination message.
        """
        if not self._enabled:
            return []

        messages = []

        # ====================================================================
        # 1. Check Critical Interrupts (Physical Stop)
        # ====================================================================
        if self.interrupt_queue and self.interrupt_queue.has_critical():
            logger.warning("[STEERING] Critical interrupt detected")
            critical = self.interrupt_queue.poll()

            for interrupt in critical:
                if interrupt.is_critical():
                    self._handle_critical_interrupt(context, interrupt)
                    self._stats["critical_stops"] += 1

                    # Return termination message (will end loop)
                    return [AgentMessage(
                        role=MessageRole.SYSTEM,
                        content=f"[TERMINATED] {interrupt.raw_input}",
                        source=MessageSource.INTERRUPT_QUEUE,
                        metadata={"critical": True, "command": interrupt.command.value}
                    )]

        # ====================================================================
        # 2. Check Policy Engine (Cognitive Steering)
        # ====================================================================
        if self.policy_engine:
            policy_messages = await self._check_policy_engine(context)
            if policy_messages:
                messages.extend(policy_messages)
                self._stats["policy_interventions"] += len(policy_messages)
                logger.info(f"[STEERING] Policy intervention: {len(policy_messages)} messages")

        # ====================================================================
        # 3. Check User Interrupts (Cognitive Steering)
        # ====================================================================
        if self.interrupt_queue and self.interrupt_queue.has_pending():
            user_messages = await self._handle_user_interrupts(context)
            if user_messages:
                messages.extend(user_messages)
                self._stats["total_interrupts_handled"] += len(user_messages)
                logger.info(f"[STEERING] User interruption: {len(user_messages)} messages")

        # ====================================================================
        # 4. Check Custom Steering Hooks
        # ====================================================================
        for hook in self.custom_steering_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    custom_msgs = await hook(context)
                else:
                    custom_msgs = hook(context)

                if custom_msgs:
                    messages.extend(custom_msgs)
                    self._stats["custom_steering"] += len(custom_msgs)

            except Exception as e:
                logger.error(f"[STEERING] Custom hook failed: {e}")

        return messages

    def _handle_critical_interrupt(
        self,
        context: 'AgentContext',
        interrupt: PriorityInterrupt
    ) -> None:
        """
        Handle critical interrupt (physical stop)

        Sets termination flag on context, which will cause the
        reactive loop to break after current iteration.

        Args:
            context: Agent execution context
            interrupt: Critical interrupt object
        """
        if interrupt.command == SpecialCommand.STOP:
            logger.warning("[STEERING] /stop command received - terminating execution")

            # Set termination flag
            if hasattr(context, 'mark_terminated'):
                context.mark_terminated(reason="User requested stop (/stop)")
            elif hasattr(context, 'metadata'):
                context.metadata["halted"] = True
                context.metadata["halt_reason"] = "User requested stop (/stop)"

    async def _check_policy_engine(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Check policy engine for interventions

        Args:
            context: Agent execution context

        Returns:
            List of policy intervention messages
        """
        if not self.policy_engine:
            return []

        messages = []

        try:
            # Call policy engine check method
            if hasattr(self.policy_engine, 'check_and_intervene'):
                interventions = await self.policy_engine.check_and_intervene(
                    current_state=self._extract_current_state(context)
                )

                if interventions:
                    for intervention in interventions:
                        messages.append(policy_intervention_message(
                            content=intervention.get("message", "Policy intervention"),
                            policy_name=intervention.get("policy")
                        ))

        except Exception as e:
            logger.error(f"[STEERING] Policy engine check failed: {e}")

        return messages

    async def _handle_user_interrupts(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Handle user interrupts from PriorityInterruptQueue

        Converts PriorityInterrupt objects to AgentMessage objects.

        Priority handling:
        - HIGH (/fix, /skip) -> Mark as high priority in metadata
        - NORMAL -> Standard user message

        Args:
            context: Agent execution context

        Returns:
            List of user message objects
        """
        if not self.interrupt_queue:
            return []

        messages = []
        interrupts = self.interrupt_queue.poll()

        for interrupt in interrupts:
            # Skip critical interrupts (already handled above)
            if interrupt.is_critical():
                continue

            # Convert to steering message
            if interrupt.is_high_priority():
                # HIGH priority: /fix, /skip
                messages.append(AgentMessage(
                    role=MessageRole.USER,
                    content=f"[{interrupt.command.value.upper()}] {interrupt.raw_input}",
                    source=MessageSource.INTERRUPT_QUEUE,
                    metadata={
                        "interrupt_priority": "high",
                        "command": interrupt.command.value,
                        "timestamp": interrupt.timestamp.isoformat()
                    }
                ))

                logger.info(f"[STEERING] High priority interrupt: {interrupt.command.value}")

            else:
                # NORMAL priority: standard user input
                messages.append(steering_message(
                    content=interrupt.raw_input,
                    metadata={
                        "interrupt_priority": "normal",
                        "timestamp": interrupt.timestamp.isoformat()
                    }
                ))

                logger.info(f"[STEERING] User input: {interrupt.raw_input[:50]}...")

        return messages

    def _extract_current_state(self, context: 'AgentContext') -> Dict[str, Any]:
        """
        Extract current state for policy engine inspection

        Args:
            context: Agent execution context

        Returns:
            Dictionary of current state
        """
        state = {}

        # Extract messages
        if hasattr(context, 'messages'):
            state["message_count"] = len(context.messages)
            state["last_role"] = context.messages[-1].role.value if context.messages else None

        # Extract iteration info
        if hasattr(context, 'iteration'):
            state["iteration"] = context.iteration

        # Extract any flags
        if hasattr(context, 'metadata'):
            state["metadata"] = dict(context.metadata)

        return state

    def enable(self) -> None:
        """Enable steering pump"""
        self._enabled = True
        logger.debug("[STEERING] Pump enabled")

    def disable(self) -> None:
        """Disable steering pump"""
        self._enabled = False
        logger.debug("[STEERING] Pump disabled")

    def get_stats(self) -> Dict[str, Any]:
        """Get pump statistics"""
        return dict(self._stats)


# ============================================================================
# Execution Pump (执行泵)
# ============================================================================

class ExecutionPump(MessagePump):
    """
    Standard ReACT execution pump

    Wraps the LLM client and produces assistant messages with tool calls.

    This is the "normal" operation of the agent - not really a "pump"
    in the intervention sense, but follows the same interface for
    consistency in the triple-pump architecture.

    Usage:
        pump = ExecutionPump(llm_client=llm)
        messages = await pump.pump(context)
        # Returns: [AgentMessage(role=ASSISTANT, content="...", tool_calls=[...])]
    """

    def __init__(self, llm_client):
        """
        Initialize execution pump

        Args:
            llm_client: LLM client (must have async chat method)
        """
        self.llm_client = llm_client
        self._enabled = True

        # Statistics
        self._stats = {
            "total_llm_calls": 0,
            "total_tool_calls_generated": 0,
        }

    async def pump(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Execute LLM call and generate assistant message

        Args:
            context: Agent execution context with messages

        Returns:
            List containing single assistant message (possibly with tool calls)
        """
        if not self._enabled:
            return []

        try:
            # Convert AgentMessage to OpenAI format
            openai_messages = self._convert_to_openai_format(context.messages)

            # Call LLM
            response = await self.llm_client.chat(
                messages=openai_messages,
                tools=getattr(context, 'tools', None),
            )

            self._stats["total_llm_calls"] += 1

            # Parse tool calls
            tool_calls = response.get("tool_calls", [])
            if tool_calls:
                self._stats["total_tool_calls_generated"] += len(tool_calls)

            # Create assistant message
            message = AgentMessage(
                role=MessageRole.ASSISTANT,
                content=response.get("content", ""),
                tool_calls=tool_calls,
                source=MessageSource.LLM,
                metadata={
                    "model": response.get("model", "unknown"),
                    "finish_reason": response.get("finish_reason"),
                }
            )

            return [message]

        except Exception as e:
            logger.error(f"[EXECUTION] LLM call failed: {e}")
            return []

    def _convert_to_openai_format(self, messages: List[AgentMessage]) -> List[Dict[str, Any]]:
        """Convert AgentMessage list to OpenAI format"""
        return [msg.to_dict() for msg in messages]

    def get_stats(self) -> Dict[str, Any]:
        """Get pump statistics"""
        return dict(self._stats)


# ============================================================================
# Follow-Up Pump (跟进泵)
# ============================================================================

class FollowUpPump(MessagePump):
    """
    Low priority pump for task chaining and follow-up tasks

    Sources:
    1. TaskScheduler - Pending tasks in a workflow
    2. AutoReflector - Suggestions for improving results
    3. Custom callbacks - External follow-up hooks

    Behavior:
    - Only checked when current task is complete (no more tool calls)
    - If messages available, inject and continue loop
    - If no messages, terminate loop

    Example scenario:
        Task 1: "Write code"
        [Task completes]
        FollowUpPump: "Run tests" (from TaskScheduler)
        [Task completes]
        FollowUpPump: "Commit changes" (from TaskScheduler)
        [No more follow-ups]
        Loop terminates
    """

    def __init__(
        self,
        task_scheduler = None,
        auto_reflector = None,
        custom_followup_hooks: Optional[List[Callable]] = None,
        enable_auto_evaluation: bool = True,
    ):
        """
        Initialize follow-up pump

        Args:
            task_scheduler: Optional task scheduler for chaining
            auto_reflector: Optional auto-reflector for improvement suggestions
            custom_followup_hooks: Optional list of async callbacks for custom follow-ups
            enable_auto_evaluation: Enable auto-evaluation (Sprint 5)
        """
        self.task_scheduler = task_scheduler
        self.auto_reflector = auto_reflector
        self.custom_followup_hooks = custom_followup_hooks or []
        self.enable_auto_evaluation = enable_auto_evaluation
        self._enabled = True

        # Sprint 5: Auto-Reflector
        self._evaluator = None
        if self.enable_auto_evaluation:
            try:
                from .evaluator import TaskEvaluator
                self._evaluator = TaskEvaluator()
                logger.info("[SPRINT-5] TaskEvaluator initialized in FollowUpPump")
            except Exception as e:
                logger.warning(f"[SPRINT-5] Failed to initialize TaskEvaluator: {e}")

        # Statistics
        self._stats = {
            "total_followups": 0,
            "from_scheduler": 0,
            "from_reflector": 0,
            "from_custom": 0,
            "from_evaluator": 0,  # Sprint 5
        }

    async def pump(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Draw follow-up messages from all sources

        Only called when current task is marked as complete.

        Priority (Sprint 5):
        1. Auto-Evaluation (Self-Correction) - Highest priority
        2. Task Scheduler (Task Chaining)
        3. Auto-Reflector (Improvement Suggestions)
        4. Custom Hooks

        Args:
            context: Agent execution context

        Returns:
            List of follow-up messages, or empty list if no follow-ups
        """
        if not self._enabled:
            return []

        messages = []

        # ====================================================================
        # Sprint 5: Phase 1 - Auto-Evaluation (Self-Correction)
        # ====================================================================
        # Priority: Check for failures before scheduling new tasks
        if self._evaluator and self.enable_auto_evaluation:
            eval_result = await self._check_and_evaluate(context)

            if eval_result:
                # If task failed, inject fix task immediately
                # This takes priority over all other follow-ups
                return eval_result

        # ====================================================================
        # 2. Check Task Scheduler
        # ====================================================================
        if self.task_scheduler:
            scheduler_messages = await self._check_task_scheduler(context)
            if scheduler_messages:
                messages.extend(scheduler_messages)
                self._stats["from_scheduler"] += len(scheduler_messages)
                logger.info(f"[FOLLOW-UP] Task scheduler: {len(scheduler_messages)} tasks")

        # ====================================================================
        # 2. Check Auto-Reflector
        # ====================================================================
        if self.auto_reflector:
            reflector_messages = await self._check_auto_reflector(context)
            if reflector_messages:
                messages.extend(reflector_messages)
                self._stats["from_reflector"] += len(reflector_messages)
                logger.info(f"[FOLLOW-UP] Auto-reflector: {len(reflector_messages)} suggestions")

        # ====================================================================
        # 3. Check Custom Follow-Up Hooks
        # ====================================================================
        for hook in self.custom_followup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    custom_msgs = await hook(context)
                else:
                    custom_msgs = hook(context)

                if custom_msgs:
                    messages.extend(custom_msgs)
                    self._stats["from_custom"] += len(custom_msgs)

            except Exception as e:
                logger.error(f"[FOLLOW-UP] Custom hook failed: {e}")

        self._stats["total_followups"] += len(messages)

        return messages

    async def _check_task_scheduler(self, context: 'AgentContext') -> List[AgentMessage]:
        """Check task scheduler for pending tasks"""
        if not self.task_scheduler:
            return []

        messages = []

        try:
            # Call task scheduler - get next single task
            if hasattr(self.task_scheduler, 'get_next_task'):
                task = await self.task_scheduler.get_next_task(context)

                if task:
                    # Get scheduler status for metadata
                    status = self.task_scheduler.get_status()
                    total_tasks = status.get("pending_count", 0) + status.get("completed_count", 0)
                    current_number = status.get("completed_count", 0) + 1

                    messages.append(AgentMessage(
                        role=MessageRole.USER,
                        content=task.instruction,
                        source=MessageSource.FOLLOWUP_SCHEDULER,
                        metadata={
                            "task_id": task.task_id,
                            "task_type": task.task_type,
                            "priority": task.priority,
                            "task_number": current_number,
                            "total_tasks": total_tasks,
                        }
                    ))

        except Exception as e:
            logger.error(f"[FOLLOW-UP] Task scheduler check failed: {e}")

        return messages

    async def _check_and_evaluate(self, context: 'AgentContext') -> List[AgentMessage]:
        """
        Sprint 5: Auto-Evaluation - Self-correction before task chaining

        Checks the last tool result and determines if a fix is needed.
        This takes priority over all other follow-up actions.

        Args:
            context: Agent execution context

        Returns:
            List of fix messages if evaluation failed, empty list otherwise
        """
        if not self._evaluator:
            return []

        messages = []

        try:
            # Extract last tool result from context
            last_result = self._get_last_tool_result(context)

            if last_result:
                logger.info(f"[SPRINT-5] Evaluating last tool result...")

                # Evaluate the result
                evaluation = await self._evaluator.evaluate(
                    tool_result=last_result,
                    context=context
                )

                # Update statistics
                self._stats["from_evaluator"] += 1

                # Check if fix is needed
                if not evaluation.success:
                    logger.warning(f"[SPRINT-5] Evaluation failed: {evaluation.failure_reason}")

                    # Generate fix message
                    fix_message = AgentMessage(
                        role=MessageRole.USER,
                        content=self._generate_fix_message(evaluation),
                        source=MessageSource.AUTO_REFLECTOR,
                        metadata={
                            "evaluation_outcome": evaluation.outcome.value,
                            "failure_reason": evaluation.failure_reason,
                            "suggested_fix": evaluation.suggested_fix,
                        }
                    )

                    messages.append(fix_message)

                    logger.info(f"[SPRINT-5] Auto-fix task injected")
                    return messages

        except Exception as e:
            logger.error(f"[SPRINT-5] Evaluation failed: {e}")

        return messages

    def _get_last_tool_result(self, context: 'AgentContext') -> Optional['ToolResult']:
        """
        Extract the last tool result from execution context

        Args:
            context: Agent execution context

        Returns:
            Last ToolResult, or None if not found
        """
        # Try to get from context metadata
        if hasattr(context, 'last_tool_result'):
            return context.last_tool_result

        # Try to extract from messages
        if hasattr(context, 'messages'):
            # Search backwards through messages
            for msg in reversed(context.messages):
                # Check if message contains tool result
                if isinstance(msg, dict):
                    if msg.get("role") == "tool":
                        # This is a tool result message
                        # Create a pseudo ToolResult
                        from ..tool import ToolResult

                        # Extract tool call ID and content
                        tool_call_id = msg.get("tool_call_id")
                        content = msg.get("content", "")

                        # Check for error markers
                        is_error = "[ERROR]" in content or "[FAIL]" in content

                        return ToolResult(
                            tool_name="unknown",  # We don't have the tool name here
                            result=content,
                            error="Error detected in output" if is_error else None
                        )

        return None

    def _generate_fix_message(self, evaluation) -> str:
        """
        Generate a fix message based on evaluation

        Args:
            evaluation: Evaluation result

        Returns:
            Fix message content
        """
        parts = [
            "[AUTO-REFLECTOR] Quality Check Failed",
            "",
            f"Failure Reason: {evaluation.failure_reason}",
            f"Suggested Fix: {evaluation.suggested_fix}",
            "",
            "Please fix this issue and continue.",
        ]

        return "\n".join(parts)

    async def _check_auto_reflector(self, context: 'AgentContext') -> List[AgentMessage]:
        """Check auto-reflector for improvement suggestions"""
        if not self.auto_reflector:
            return []

        messages = []

        try:
            # Call auto-reflector
            if hasattr(self.auto_reflector, 'evaluate'):
                suggestions = await self.auto_reflector.evaluate(
                    result=context.get("final_answer", ""),
                    messages=context.messages
                )

                if suggestions:
                    messages.append(AgentMessage(
                        role=MessageRole.USER,
                        content=f"The previous result could be improved: {suggestions}",
                        source=MessageSource.AUTO_REFLECTOR,
                        metadata={"suggestion_type": "improvement"}
                    ))

        except Exception as e:
            logger.error(f"[FOLLOW-UP] Auto-reflector check failed: {e}")

        return messages

    def enable(self) -> None:
        """Enable follow-up pump"""
        self._enabled = True
        logger.debug("[FOLLOW-UP] Pump enabled")

    def disable(self) -> None:
        """Disable follow-up pump"""
        self._enabled = False
        logger.debug("[FOLLOW-UP] Pump disabled")

    def get_stats(self) -> Dict[str, Any]:
        """Get pump statistics"""
        return dict(self._stats)


# ============================================================================
# Convenience Functions
# ============================================================================

def create_steering_pump(
    interrupt_queue: Optional[PriorityInterruptQueue] = None,
    policy_engine = None,
) -> SteeringPump:
    """Create steering pump with common configuration"""
    return SteeringPump(
        interrupt_queue=interrupt_queue,
        policy_engine=policy_engine,
    )


def create_followup_pump(
    task_scheduler = None,
    auto_reflector = None,
) -> FollowUpPump:
    """Create follow-up pump with common configuration"""
    return FollowUpPump(
        task_scheduler=task_scheduler,
        auto_reflector=auto_reflector,
    )
