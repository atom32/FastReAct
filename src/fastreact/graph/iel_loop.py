"""
IEL Execution Loop - Main execution loop for Interactive Execution Loop

Implements the core Plan -> Execute -> Reflect -> (Replan | Continue) cycle
"""

import asyncio
import logging
from typing import Optional, Callable

from .iel_context import IELExecutionContext
from .iel_types import StepResult, Status, ExternalObservation
from .step_executor import StepExecutor, StepConfig, InterruptQueue
from .replanner import Replanner
from .interrupt import PriorityInterruptQueue, PriorityInterrupt, InterruptPriority, SpecialCommand, parse_fix_command

logger = logging.getLogger(__name__)


# ============================================================================
# IEL Execution Loop
# ============================================================================

class IELLoop:
    """
    Interactive Execution Loop

    Main execution loop implementing:
    1. Check interrupts
    2. Execute single step
    3. Reflect on failures
    4. Apply patches (replan or retry)

    Usage:
        loop = IELLoop(
            executor=executor,
            replanner=replanner,
        )

        result = await loop.run(context)
    """

    def __init__(
        self,
        executor: StepExecutor,
        replanner: Replanner,
        config: Optional['IELLoopConfig'] = None,
    ):
        """
        Initialize IEL Loop

        Args:
            executor: StepExecutor for step-by-step execution
            replanner: Replanner for reflection and patching
            config: Optional loop configuration
        """
        self.executor = executor
        self.replanner = replanner
        self.config = config or IELLoopConfig()

        # Statistics
        self._total_steps = 0
        self._replan_count = 0
        self._retry_count = 0

    async def run(
        self,
        context: IELExecutionContext,
    ) -> StepResult:
        """
        Run IEL loop until completion or max iterations

        Args:
            context: IEL execution context

        Returns:
            Final step result
        """
        logger.info("Starting IEL execution loop")
        self._total_steps = 0

        while not context.is_complete() and self._total_steps < self.config.max_iterations:
            self._total_steps += 1

            # ====================================================================
            # 1. Check Interrupts
            # ====================================================================
            if self.executor.interrupt_queue.has_pending():
                logger.info("[INTERRUPT] Processing user input")
                await self._handle_interrupt(context)

            # ====================================================================
            # 2. Execute Single Step
            # ====================================================================
            logger.info(f"\n[STEP {self._total_steps}] Executing next node")
            result = await self.executor.step(context)

            # Log result
            if result.is_success():
                logger.info(f"  [OK] {result.node_id}: {str(result.payload)[:50]}...")
            elif result.is_failed():
                logger.error(f"  [FAIL] {result.node_id}: {result.error}")
            elif result.needs_input():
                logger.info(f"  [INPUT] {result.node_id}: {result.payload}")

            # ====================================================================
            # 3. Reflect on Failures
            # ====================================================================
            if result.status == Status.FAILED:
                logger.info(f"[REFLECT] Analyzing failure: {result.node_id}")

                patch = await self.replanner.reflect_and_patch(context, result)

                if patch:
                    # ====================================================================
                    # 4. Apply Patch (Replan or Retry)
                    # ====================================================================
                    if patch.is_retry():
                        self._retry_count += 1
                        logger.info(f"[RETRY] Retrying node: {patch.instructions.get('node_id')}")

                        # Reset node to pending for retry
                        node_id = patch.instructions.get("node_id")
                        if node_id:
                            context._failed.discard(node_id)
                            context._pending.add(node_id)

                    else:
                        self._replan_count += 1
                        logger.info(f"[REPLAN] Applying patch: {patch.patch_id}")
                        logger.info(f"  Reason: {patch.reason}")

                        # Apply patch to context
                        context.apply_patch(patch)

                        # Create snapshot after replanning
                        if self.config.snapshot_after_replan:
                            context.create_snapshot(
                                label=f"After replan #{self._replan_count}"
                            )

            # Check for early termination conditions
            if self._should_terminate(context, result):
                break

            # Check for critical interrupts (e.g., /stop)
            if context.metadata.get("halted", False):
                logger.warning("[HALTED] Execution halted by critical interrupt")
                break

        # Loop completed
        logger.info(f"\nIEL loop completed after {self._total_steps} steps")
        logger.info(f"  Replans: {self._replan_count}")
        logger.info(f"  Retries: {self._retry_count}")
        logger.info(f"  Status: {'COMPLETE' if context.is_complete() else 'MAX_ITERATIONS'}")

        return result

    async def _handle_interrupt(self, context: IELExecutionContext) -> None:
        """
        Handle user interrupts with priority support

        Priority handling:
        1. CRITICAL (/stop) - Halt execution immediately
        2. HIGH (/fix, /skip) - Apply directly without reflection
        3. NORMAL - Go through reflection/replanning
        """
        # Get priority interrupts (if using PriorityInterruptQueue)
        if hasattr(self.executor.interrupt_queue, 'poll'):
            interrupts = self.executor.interrupt_queue.poll()

            for interrupt in interrupts:
                # Handle based on priority
                if interrupt.is_critical():
                    self._handle_critical_interrupt(context, interrupt)

                elif interrupt.is_high_priority():
                    await self._handle_high_priority_interrupt(context, interrupt)

                else:
                    await self._handle_normal_interrupt(context, interrupt)

        else:
            # Fallback to legacy interrupt handling
            observations = self.executor.interrupt_queue.poll()

            for obs in observations:
                context.add_observation(obs)
                logger.info(f"  [OBSERVATION] {obs.source}: {obs.content[:50]}...")

                # Trigger replanning from user input
                if obs.source == "user":
                    patch = await self.replanner.replan_from_user(
                        context,
                        obs.content
                    )

                    if patch:
                        logger.info(f"[REPLAN] Applying user-requested patch")
                        context.apply_patch(patch)
                        self._replan_count += 1

    def _handle_critical_interrupt(
        self,
        context: IELExecutionContext,
        interrupt: PriorityInterrupt,
    ) -> None:
        """Handle critical interrupt (e.g., /stop)"""
        logger.info(f"[CRITICAL] {interrupt.command.value}: {interrupt.raw_input}")

        if interrupt.command == SpecialCommand.STOP:
            logger.warning("[STOP] Execution halted by user")
            # Set flag to terminate loop
            context.metadata["halted"] = True

    async def _handle_high_priority_interrupt(
        self,
        context: IELExecutionContext,
        interrupt: PriorityInterrupt,
    ) -> None:
        """
        Handle high priority interrupt (bypasses reflection)

        Commands:
        - /fix - Direct patch application
        - /skip - Skip current node
        """
        logger.info(f"[HIGH PRIORITY] {interrupt.command.value}: {interrupt.raw_input}")

        if interrupt.command == SpecialCommand.FIX:
            # Parse /fix command and apply directly
            self._apply_fix_command(context, interrupt.raw_input)

        elif interrupt.command == SpecialCommand.SKIP:
            # Skip current node
            self._skip_current_node(context, interrupt.raw_input)

    async def _handle_normal_interrupt(
        self,
        context: IELExecutionContext,
        interrupt: PriorityInterrupt,
    ) -> None:
        """Handle normal interrupt (goes through reflection/replanning)"""
        context.add_observation(interrupt.observation)
        logger.info(f"  [INPUT] {interrupt.observation.source}: {interrupt.raw_input[:50]}...")

        # Trigger replanning from user input
        if interrupt.observation.source == "user":
            patch = await self.replanner.replan_from_user(
                context,
                interrupt.raw_input
            )

            if patch:
                logger.info(f"[REPLAN] Applying user-requested patch")
                context.apply_patch(patch)
                self._replan_count += 1

    def _apply_fix_command(self, context: IELExecutionContext, user_input: str) -> None:
        """Apply /fix command directly (bypasses LLM reflection)"""
        from .replanner import GraphPatch, PatchOp

        # Parse the /fix command
        patch_data = parse_fix_command(user_input)

        logger.info(f"[FIX] Direct patch application (bypassing reflection)")
        logger.info(f"  Operation: {patch_data['operation']}")
        logger.info(f"  Reason: {patch_data['reason']}")

        # Create GraphPatch directly
        try:
            operation = PatchOp(patch_data['operation'])

            patch = GraphPatch(
                patch_id=f"fix_{datetime.now().strftime('%H%M%S')}",
                operation=operation,
                reason=patch_data['reason'],
                instructions=patch_data['instructions'],
                metadata={"source": "user_fix", "bypass_reflection": True}
            )

            # Apply patch
            context.apply_patch(patch)
            self._replan_count += 1

            logger.info(f"  [OK] Fix applied successfully")

        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")

    def _skip_current_node(self, context: IELExecutionContext, user_input: str) -> None:
        """Skip current pending node"""
        pending = context.get_pending_nodes()

        if pending:
            node_to_skip = pending[0]

            # Move from pending to completed (without execution)
            context._pending.discard(node_to_skip)
            context._completed.add(node_to_skip)

            logger.info(f"[SKIP] Skipped node: {node_to_skip}")

            from .iel_types import StepResult
            # Record skip as success
            result = StepResult.success(
                payload="Skipped by user",
                node_id=node_to_skip,
                skipped=True
            )
            context.record_step(result)

        else:
            logger.warning("[SKIP] No pending nodes to skip")

    def _should_terminate(
        self,
        context: IELExecutionContext,
        result: StepResult,
    ) -> bool:
        """Check if loop should terminate early"""
        # Terminate on NEEDS_INPUT (unless auto-handle is enabled)
        if result.needs_input() and not self.config.auto_handle_input:
            logger.info("[TERMINATE] Awaiting user input")
            return True

        # Terminate on catastrophic failure
        if result.is_failed() and result.failure_type and "catastrophic" in str(result.metadata.get("severity", "")):
            logger.error("[TERMINATE] Catastrophic failure")
            return True

        return False

    def get_stats(self) -> dict:
        """Get loop statistics"""
        return {
            "total_steps": self._total_steps,
            "replan_count": self._replan_count,
            "retry_count": self._retry_count,
            "executor_stats": self.executor.get_stats(),
            "replanner_stats": self.replanner.get_stats(),
        }


# ============================================================================
# IEL Loop Configuration
# ============================================================================

class IELLoopConfig:
    """
    Configuration for IEL Loop

    Attributes:
        max_iterations: Maximum loop iterations (default: 100)
        snapshot_after_replan: Create snapshot after each replan (default: True)
        auto_handle_input: Automatically handle NEEDS_INPUT (default: False)
        verbose_logging: Enable detailed logging (default: False)
    """

    def __init__(
        self,
        max_iterations: int = 100,
        snapshot_after_replan: bool = True,
        auto_handle_input: bool = False,
        verbose_logging: bool = False,
    ):
        self.max_iterations = max_iterations
        self.snapshot_after_replan = snapshot_after_replan
        self.auto_handle_input = auto_handle_input
        self.verbose_logging = verbose_logging


# ============================================================================
# Convenience Function
# ============================================================================

async def run_iel_loop(
    context: IELExecutionContext,
    llm_client,
    tool_registry: dict,
    model: str = "gpt-4",
    interrupt_queue: Optional[InterruptQueue] = None,
    config: Optional[IELLoopConfig] = None,
) -> StepResult:
    """
    Convenience function to run IEL loop

    Args:
        context: IEL execution context
        llm_client: LLM client for replanner
        tool_registry: Available tools
        model: Model name
        interrupt_queue: Optional interrupt queue
        config: Optional loop configuration

    Returns:
        Final step result
    """
    # Create executor
    executor = StepExecutor(
        config=StepConfig(
            auto_snapshot=True,
            check_interrupts=True,
        ),
        interrupt_queue=interrupt_queue or InterruptQueue(),
    )

    # Create replanner
    replanner = Replanner(
        llm_client=llm_client,
        tool_registry=tool_registry,
        model=model,
    )

    # Create and run loop
    loop = IELLoop(executor, replanner, config)
    return await loop.run(context)
