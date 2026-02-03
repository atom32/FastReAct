"""
Step Executor - Step-based execution for Interactive Execution Loop

Replaces ToolRuntime's execute-once pattern with step-by-step execution.
Each step is interruptible and returns structured StepResult.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Set, List
from datetime import datetime

from .iel_context import IELExecutionContext
from .iel_types import StepResult, Status, FailureType, from_node_result
from .graph import ToolGraph
from .node import NodeStatus
from .checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


# ============================================================================
# Execution Configuration
# ============================================================================

class StepConfig:
    """
    Configuration for step-based execution

    Attributes:
        timeout: Timeout per step (seconds)
        max_steps: Maximum steps before forcing stop
        continue_on_error: Continue execution on node failure
        auto_snapshot: Auto-create snapshot before high-side-effect nodes
        check_interrupts: Enable interrupt checking (default: True)
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_steps: int = 100,
        continue_on_error: bool = False,
        auto_snapshot: bool = True,
        check_interrupts: bool = True,
    ):
        self.timeout = timeout
        self.max_steps = max_steps
        self.continue_on_error = continue_on_error
        self.auto_snapshot = auto_snapshot
        self.check_interrupts = check_interrupts

        # Nodes that require snapshots before execution
        self.high_side_effect_nodes = {
            "write_file", "edit_file", "bash", "delete_file",
            "install_dependency", "run_tests",
        }


# ============================================================================
# Interrupt Queue
# ============================================================================

class InterruptQueue:
    """
    Async queue for external interrupts (user input, system events)

    Non-blocking: Executor polls queue at start of each step.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._enabled = True

    async def put(self, observation) -> None:
        """Add interrupt to queue"""
        if self._enabled:
            await self._queue.put(observation)

    def poll(self) -> List:
        """
        Poll for pending interrupts (non-blocking)

        Returns:
            List of all pending observations
        """
        observations = []
        while not self._queue.empty():
            try:
                obs = self._queue.get_nowait()
                observations.append(obs)
            except asyncio.QueueEmpty:
                break
        return observations

    def enable(self) -> None:
        """Enable interrupt processing"""
        self._enabled = True

    def disable(self) -> None:
        """Disable interrupt processing"""
        self._enabled = False

    def has_pending(self) -> bool:
        """Check if there are pending interrupts"""
        return not self._queue.empty()

    def clear(self) -> None:
        """Clear all pending interrupts"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# ============================================================================
# Step Executor
# ============================================================================

class StepExecutor:
    """
    Step-based executor for Interactive Execution Loop

    Replaces ToolRuntime's execute-once pattern with:
    - Step-by-step execution via step() method
    - Interrupt checking before each step
    - Automatic snapshot creation
    - Structured StepResult returns
    - Replanning triggers on failure/input

    Usage:
        executor = StepExecutor(config=StepConfig())
        context = IELExecutionContext(graph=graph)

        while not context.is_complete():
            result = await executor.step(context)
            if result.should_replan():
                # Trigger replanning
                ...
    """

    def __init__(
        self,
        config: Optional[StepConfig] = None,
        interrupt_queue: Optional[InterruptQueue] = None,
        checkpoint_manager: Optional['CheckpointManager'] = None,
    ):
        """
        Initialize StepExecutor

        Args:
            config: Execution configuration
            interrupt_queue: Optional interrupt queue (creates new if None)
            checkpoint_manager: Optional checkpoint manager for git-native snapshots
        """
        self.config = config or StepConfig()
        self.interrupt_queue = interrupt_queue or InterruptQueue()
        self.checkpoint_manager = checkpoint_manager

        # Step tracking
        self._step_count = 0
        self._start_time: Optional[datetime] = None

        # Callbacks
        self._pre_step_callback: Optional[Callable] = None
        self._post_step_callback: Optional[Callable] = None

        logger.debug("StepExecutor initialized")

    # ========================================================================
    # Core Execution
    # ========================================================================

    async def step(
        self,
        context: IELExecutionContext,
        node_id: Optional[str] = None,
    ) -> StepResult:
        """
        Execute a single step

        If node_id provided, execute that specific node.
        Otherwise, select next ready node from pending queue.

        Args:
            context: IEL execution context
            node_id: Optional specific node to execute

        Returns:
            StepResult with status and payload
        """
        if self._step_count == 0:
            self._start_time = datetime.now()

        self._step_count += 1

        # Pre-step callback
        if self._pre_step_callback:
            await self._call_callback(self._pre_step_callback, context)

        # Check for interrupts
        if self.config.check_interrupts:
            interrupt_result = await self._check_interrupts(context)
            if interrupt_result:
                return interrupt_result

        # Select node to execute
        if node_id:
            node = context.graph.nodes.get(node_id)
            if not node:
                return StepResult.failure(
                    error=f"Node not found: {node_id}",
                    failure_type=FailureType.LOGIC,
                    node_id=node_id
                )
        else:
            node = await self._select_next_node(context)
            if not node:
                # No ready nodes, execution complete
                return StepResult.success(
                    payload="Execution complete: no more ready nodes",
                    meta={"reason": "no_ready_nodes"}
                )

        # Check if node is ready
        if not await self._is_node_ready(node, context):
            return StepResult.failure(
                error=f"Node dependencies not satisfied: {node.id}",
                failure_type=FailureType.LOGIC,
                node_id=node.id
            )

        # Auto-snapshot before high-side-effect nodes
        if self.config.auto_snapshot:
            await self._auto_snapshot(node, context)

        # Execute node
        step_result = await self._execute_node(node, context)

        # Record to history
        context.record_step(step_result)

        # Check for rollback trigger
        if context.should_rollback():
            snapshot = context.get_latest_snapshot()
            if snapshot:
                logger.info(f"Rollback triggered, restoring snapshot: {snapshot.snapshot_id}")
                context.restore_snapshot(snapshot.snapshot_id)

        # Post-step callback
        if self._post_step_callback:
            await self._call_callback(self._post_step_callback, context, step_result)

        # Check max steps
        if self._step_count >= self.config.max_steps:
            logger.warning(f"Max steps reached: {self._step_count}")
            return StepResult.failure(
                error=f"Max steps exceeded: {self.config.max_steps}",
                failure_type=FailureType.LOGIC,
                meta={"step_count": self._step_count}
            )

        return step_result

    async def run_to_completion(
        self,
        context: IELExecutionContext,
    ) -> List[StepResult]:
        """
        Convenience method: Run all steps until completion

        Args:
            context: IEL execution context

        Returns:
            List of all step results
        """
        results = []

        while not context.is_complete() and self._step_count < self.config.max_steps:
            result = await self.step(context)
            results.append(result)

            if result.is_failed() and not self.config.continue_on_error:
                logger.warning(f"Execution stopped on failure: {result.node_id}")
                break

        return results

    # ========================================================================
    # Node Selection
    # ========================================================================

    async def _select_next_node(
        self,
        context: IELExecutionContext,
    ) -> Optional:
        """
        Select next node to execute

        Strategy: Get ready nodes (dependencies satisfied), pick first
        """
        completed = context.get_completed_nodes()
        ready_nodes = context.graph.get_ready_nodes(set(completed))

        if not ready_nodes:
            return None

        # Simple strategy: pick first ready node
        # Could be enhanced with priorities, heuristics, etc.
        return ready_nodes[0]

    async def _is_node_ready(
        self,
        node,
        context: IELExecutionContext,
    ) -> bool:
        """Check if node dependencies are satisfied"""
        dependencies = node.get_dependencies()
        completed = set(context.get_completed_nodes())
        return dependencies.issubset(completed)

    # ========================================================================
    # Node Execution
    # ========================================================================

    async def _execute_node(
        self,
        node,
        context: IELExecutionContext,
    ) -> StepResult:
        """
        Execute a single node

        Args:
            node: ToolNode to execute
            context: IEL execution context

        Returns:
            StepResult
        """
        logger.info(f"Executing node: {node.id}")

        # Resolve inputs from context
        inputs = await self._resolve_inputs(node, context)

        # Execute with timeout
        try:
            node_result = await asyncio.wait_for(
                node.execute(inputs, context.shared_memory),
                timeout=self.config.timeout
            )

            # Convert NodeResult to StepResult
            step_result = from_node_result(node_result)

            # Update shared memory with outputs
            if step_result.is_success():
                for key, value in node_result.outputs.items():
                    context.set_shared_memory(f"{node.id}.{key}", value)

            return step_result

        except asyncio.TimeoutError:
            return StepResult.failure(
                error=f"Node execution timeout: {node.id}",
                failure_type=FailureType.ACTION,
                node_id=node.id,
                meta={"timeout": self.config.timeout}
            )
        except Exception as e:
            logger.error(f"Node execution error: {node.id} - {e}")
            return StepResult.failure(
                error=str(e),
                failure_type=FailureType.ACTION,
                node_id=node.id
            )

    async def _resolve_inputs(
        self,
        node,
        context: IELExecutionContext,
    ) -> Dict[str, Any]:
        """
        Resolve node inputs from context

        Supports:
        - Direct values from node.inputs
        - References to shared memory (@shared.key)
        - References to other node outputs (@node_id.output)
        """
        from .state import ReferenceResolver

        resolved = {}

        for key, value in node.inputs.items():
            # Skip if already a simple value
            if not isinstance(value, str) or not value.startswith("@"):
                resolved[key] = value
                continue

            # Resolve reference
            # This is a simplified version - full implementation would
            # use ReferenceResolver from state.py
            if value.startswith("@shared."):
                mem_key = value[8:]  # Remove "@shared."
                resolved[key] = context.get_shared_memory(mem_key)
            elif value.startswith("@"):
                # Reference to another node
                ref_parts = value[1:].split(".")
                if len(ref_parts) == 1:
                    # Just node ID, get entire output
                    resolved[key] = context.get_node_output(ref_parts[0])
                else:
                    # node_id.output_key
                    node_id = ref_parts[0]
                    output_key = ".".join(ref_parts[1:])
                    output = context.get_node_output(node_id)
                    if isinstance(output, dict):
                        resolved[key] = output.get(output_key)
                    else:
                        resolved[key] = output
            else:
                resolved[key] = value

        return resolved

    # ========================================================================
    # Interrupt Handling
    # ========================================================================

    async def _check_interrupts(
        self,
        context: IELExecutionContext,
    ) -> Optional[StepResult]:
        """
        Check for pending interrupts

        Returns StepResult if interrupt should halt execution, None otherwise.
        """
        observations = self.interrupt_queue.poll()

        if not observations:
            return None

        # Add observations to context
        for obs in observations:
            context.add_observation(obs)

        # Return NEEDS_INPUT to trigger replanning
        return StepResult.needs_input(
            prompt=f"Received {len(observations)} external input(s)",
            meta={
                "interrupt_count": len(observations),
                "sources": [obs.source for obs in observations]
            }
        )

    # ========================================================================
    # Auto-Snapshot
    # ========================================================================

    async def _auto_snapshot(
        self,
        node,
        context: IELExecutionContext,
    ) -> None:
        """
        Auto-create snapshot before high-side-effect nodes

        Uses CheckpointManager if available (git-native snapshots).
        Falls back to context snapshots otherwise.

        High-side-effect nodes are those that modify files, run commands, etc.
        """
        # Check if node is high-side-effect
        is_high_risk = False

        # Check by node ID
        if node.id in self.config.high_side_effect_nodes:
            is_high_risk = True

        # Check by tool name
        elif hasattr(node, 'tool') and hasattr(node.tool, '__name__'):
            if node.tool.__name__ in self.config.high_side_effect_nodes:
                is_high_risk = True

        if is_high_risk:
            # Use CheckpointManager if available
            if self.checkpoint_manager:
                snapshot_id = self.checkpoint_manager.create_checkpoint(
                    label=f"Before high-side-effect node: {node.id}"
                )
                logger.debug(f"Auto-created git checkpoint: {snapshot_id}")

                # Track in context
                if "git_checkpoints" not in context.metadata:
                    context.metadata["git_checkpoints"] = []
                context.metadata["git_checkpoints"].append(snapshot_id)
            else:
                # Fallback to context snapshot
                snapshot_id = context.create_snapshot(
                    label=f"Before high-side-effect node: {node.id}"
                )
                logger.debug(f"Auto-created context snapshot: {snapshot_id}")

    # ========================================================================
    # Callbacks
    # ========================================================================

    def set_pre_step_callback(self, callback: Callable) -> None:
        """Set callback called before each step"""
        self._pre_step_callback = callback

    def set_post_step_callback(self, callback: Callable) -> None:
        """Set callback called after each step"""
        self._post_step_callback = callback

    async def _call_callback(
        self,
        callback: Callable,
        *args,
    ) -> None:
        """Call callback safely"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    # ========================================================================
    # Utility
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "step_count": self._step_count,
            "start_time": self._start_time.isoformat() if self._start_time else None,
        }

    def reset(self) -> None:
        """Reset executor state"""
        self._step_count = 0
        self._start_time = None
