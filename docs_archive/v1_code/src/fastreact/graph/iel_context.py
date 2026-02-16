"""
IEL ExecutionContext - Enhanced execution context for Interactive Execution Loop

Extends the base ExecutionContext with IEL-specific features:
- Mutable graph reference
- Structured history tracking
- Pending nodes queue
- Snapshot/rollback support
"""

import copy
import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .graph import ToolGraph
from .iel_types import StepResult, Status, ExternalObservation

logger = logging.getLogger(__name__)


# ============================================================================
# Snapshot
# ============================================================================

@dataclass
class GraphSnapshot:
    """
    Immutable snapshot of graph state for rollback

    Captures:
    - Graph structure
    - Current execution state
    - Shared memory
    - Metadata
    """
    snapshot_id: str
    timestamp: datetime
    graph_dict: Dict[str, Any]
    node_outputs: Dict[str, Any]
    shared_memory: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "graph_dict": self.graph_dict,
            "node_outputs": self.node_outputs,
            "shared_memory": self.shared_memory,
            "metadata": self.metadata,
        }


# ============================================================================
# Failure Counter
# ============================================================================

@dataclass
class FailureCounter:
    """
    Track consecutive failures for rollback triggering

    Threshold: 3 consecutive failures on same goal/node
    """
    failures: Dict[str, int] = field(default_factory=dict)
    threshold: int = 3

    def record_failure(self, target: str) -> int:
        """Record a failure, return count"""
        self.failures[target] = self.failures.get(target, 0) + 1
        return self.failures[target]

    def record_success(self, target: str) -> None:
        """Reset counter on success"""
        if target in self.failures:
            del self.failures[target]

    def should_rollback(self, target: str) -> bool:
        """Check if threshold exceeded"""
        return self.failures.get(target, 0) >= self.threshold

    def reset(self) -> None:
        """Reset all counters"""
        self.failures.clear()


# ============================================================================
# IEL ExecutionContext
# ============================================================================

class IELExecutionContext:
    """
    Enhanced ExecutionContext for Interactive Execution Loop

    Single source of truth for agent lifecycle:
    - Mutable graph (can be patched during execution)
    - Structured history (StepResult list)
    - Shared memory (for cross-node communication)
    - Pending nodes (queue of nodes to execute)
    - Snapshots (for rollback)
    - Failure tracking (for rollback triggering)

    Backward compatible with base ExecutionContext from state.py
    """

    def __init__(
        self,
        graph: ToolGraph,
        initial_inputs: Optional[Dict[str, Any]] = None,
        failure_threshold: int = 3,
    ):
        """
        Initialize IEL ExecutionContext

        Args:
            graph: Initial ToolGraph (mutable during execution)
            initial_inputs: Initial input data
            failure_threshold: Failures before rollback (default: 3)
        """
        # Core graph reference (MUTABLE)
        self.graph = graph

        # Structured history
        self.history: List[StepResult] = []

        # Shared memory (for passing data between nodes)
        self.shared_memory: Dict[str, Any] = initial_inputs or {}

        # Pending nodes (execution queue)
        self._pending: Set[str] = set(graph.nodes.keys())
        self._completed: Set[str] = set()
        self._failed: Set[str] = set()

        # Snapshot/rollback system
        self._snapshots: Dict[str, GraphSnapshot] = {}
        self._snapshot_counter = 0

        # Failure tracking
        self.failure_counter = FailureCounter(threshold=failure_threshold)

        # External observations (user input, interrupts)
        self.observations: List[ExternalObservation] = []

        # Metadata
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "total_steps": 0,
            "replan_count": 0,
        }

        logger.debug(f"Created IELExecutionContext with {len(self._pending)} pending nodes")

    # ========================================================================
    # Graph Access
    # ========================================================================

    def get_graph(self) -> ToolGraph:
        """Get current graph (may have been patched)"""
        return self.graph

    def update_graph(self, new_graph: ToolGraph) -> None:
        """
        Replace graph with new version (after replanning)

        Args:
            new_graph: New ToolGraph to use
        """
        old_node_count = len(self.graph.nodes)
        self.graph = new_graph

        # Update pending/completed/failed based on new graph
        new_nodes = set(new_graph.nodes.keys())
        self._pending = new_nodes - self._completed - self._failed

        logger.info(f"Graph updated: {old_node_count} -> {len(new_graph.nodes)} nodes")

    def patch_graph(self, operation: str, **kwargs) -> None:
        """
        Apply patch operation to current graph

        Args:
            operation: Patch type (add_node, remove_node, replace_node, reconnect)
            **kwargs: Operation-specific arguments
        """
        if operation == "add_node":
            self._patch_add_node(**kwargs)
        elif operation == "remove_node":
            self._patch_remove_node(**kwargs)
        elif operation == "replace_node":
            self._patch_replace_node(**kwargs)
        elif operation == "reconnect":
            self._patch_reconnect(**kwargs)
        else:
            raise ValueError(f"Unknown patch operation: {operation}")

        logger.debug(f"Applied patch: {operation}")

    def _patch_add_node(self, node, dependencies: List[str] = None) -> None:
        """Add node to graph"""
        from .node import ToolEdge

        self.graph.add_node(node)
        self._pending.add(node.id)

        if dependencies:
            for dep_id in dependencies:
                if dep_id in self.graph.nodes:
                    self.graph.connect(dep_id, node.id)

    def _patch_remove_node(self, node_id: str) -> None:
        """Remove node from graph"""
        if node_id in self.graph.nodes:
            del self.graph.nodes[node_id]
            self._pending.discard(node_id)
            self._completed.discard(node_id)
            self._failed.discard(node_id)

            # Remove edges
            self.graph.edges = [e for e in self.graph.edges if e.source.id != node_id and e.target.id != node_id]

    def _patch_replace_node(self, node_id: str, new_node) -> None:
        """Replace node implementation"""
        if node_id in self.graph.nodes:
            self.graph.add_node(new_node)

            # Preserve dependencies
            old_node = self.graph.nodes.get(node_id)
            if old_node:
                new_node._dependencies = old_node._dependencies.copy()
                new_node._dependents = old_node._dependents.copy()

    def _patch_reconnect(self, source_id: str, target_id: str, condition: str = None) -> None:
        """Add or modify connection"""
        if source_id in self.graph.nodes and target_id in self.graph.nodes:
            self.graph.connect(source_id, target_id, condition)

    def apply_patch(self, patch) -> None:
        """
        Apply GraphPatch from Replanner

        This is the main entry point for applying patches generated by Replanner.
        It validates the patch and executes the operation.

        Args:
            patch: GraphPatch object from Replanner.reflect_and_patch()

        Raises:
            ValueError: If patch operation is invalid
        """
        from .replanner import PatchOp

        logger.info(f"Applying patch: {patch.patch_id} - {patch.operation.value}")
        logger.info(f"  Reason: {patch.reason}")

        # Record patch to metadata for traceability
        if "patches_applied" not in self.metadata:
            self.metadata["patches_applied"] = []

        self.metadata["patches_applied"].append(patch.to_dict())

        # Handle RETRY operation (special case - no graph modification)
        if patch.operation == PatchOp.RETRY:
            logger.info(f"  [RETRY] Will retry node: {patch.instructions.get('node_id')}")
            # No graph modification needed, just log
            return

        # Execute patch operation
        operation = patch.operation.value

        if operation == "add_node":
            self._apply_add_node(patch)

        elif operation == "remove_node":
            self._apply_remove_node(patch)

        elif operation == "replace_node":
            self._apply_replace_node(patch)

        elif operation == "reconnect":
            self._apply_reconnect(patch)

        elif operation == "insert_before":
            self._apply_insert_before(patch)

        elif operation == "insert_after":
            self._apply_insert_after(patch)

        else:
            raise ValueError(f"Unknown patch operation: {operation}")

        logger.info(f"  [OK] Patch applied successfully")

    def _apply_add_node(self, patch) -> None:
        """Apply add_node patch"""
        from .node import create_tool_node

        instr = patch.instructions
        tool_func = self._get_tool_from_registry(instr["tool_name"])

        node = create_tool_node(
            id=instr["node_id"],
            tool=tool_func,
            inputs=instr.get("inputs", {}),
        )

        deps = instr.get("dependencies", [])
        self._patch_add_node(node, dependencies=deps)

    def _apply_remove_node(self, patch) -> None:
        """Apply remove_node patch"""
        node_id = patch.instructions.get("node_id")
        if node_id:
            self._patch_remove_node(node_id)

    def _apply_replace_node(self, patch) -> None:
        """Apply replace_node patch"""
        from .node import create_tool_node

        instr = patch.instructions
        node_id = instr.get("node_id")

        if not node_id:
            logger.warning("Replace node patch missing node_id")
            return

        # Get new tool
        tool_func = self._get_tool_from_registry(instr.get("tool_name"))

        new_node = create_tool_node(
            id=node_id,
            tool=tool_func,
            inputs=instr.get("inputs", {}),
        )

        self._patch_replace_node(node_id, new_node)

    def _apply_reconnect(self, patch) -> None:
        """Apply reconnect patch"""
        instr = patch.instructions
        source_id = instr.get("source_id")
        target_id = instr.get("target_id")
        condition = instr.get("condition")

        if source_id and target_id:
            self._patch_reconnect(source_id, target_id, condition)

    def _apply_insert_before(self, patch) -> None:
        """Apply insert_before patch"""
        from .node import create_tool_node

        instr = patch.instructions
        target_node = instr.get("target_node")
        new_node_instr = instr.get("new_node")

        if not target_node or not new_node_instr:
            logger.warning("Insert_before patch missing required fields")
            return

        # Create new node
        tool_func = self._get_tool_from_registry(new_node_instr["tool_name"])

        new_node = create_tool_node(
            id=new_node_instr["node_id"],
            tool=tool_func,
            inputs=new_node_instr.get("inputs", {}),
        )

        # Add node to graph
        self.graph.add_node(new_node)
        self._pending.add(new_node.id)

        # Get target node's dependencies
        target = self.graph.nodes.get(target_node)
        if target:
            # New node inherits target's dependencies
            for dep_id in target.get_dependencies():
                if dep_id in self.graph.nodes:
                    self.graph.connect(dep_id, new_node.id)

            # Connect new node to target
            self.graph.connect(new_node.id, target_node)

            # Update target's dependencies
            target._dependencies.add(new_node.id)

    def _apply_insert_after(self, patch) -> None:
        """Apply insert_after patch"""
        from .node import create_tool_node

        instr = patch.instructions
        target_node = instr.get("target_node")
        new_node_instr = instr.get("new_node")

        if not target_node or not new_node_instr:
            logger.warning("Insert_after patch missing required fields")
            return

        # Create new node
        tool_func = self._get_tool_from_registry(new_node_instr["tool_name"])

        new_node = create_tool_node(
            id=new_node_instr["node_id"],
            tool=tool_func,
            inputs=new_node_instr.get("inputs", {}),
        )

        # Add node to graph
        self.graph.add_node(new_node)
        self._pending.add(new_node.id)

        # Connect target to new node
        self.graph.connect(target_node, new_node.id)

        # Reconnect target's dependents to new node
        target = self.graph.nodes.get(target_node)
        if target:
            for dependent_id in target.get_dependents():
                if dependent_id in self.graph.nodes:
                    dependent = self.graph.nodes[dependent_id]
                    # Remove old connection
                    dependent._dependencies.discard(target_node)
                    # Connect to new node
                    self.graph.connect(new_node.id, dependent_id)

    def _get_tool_from_registry(self, tool_name: str):
        """
        Get tool function from registry

        This is a placeholder - in production, this would access
        the actual tool registry passed from the Agent.
        """
        # For now, return a dummy function
        # The actual implementation would get tools from self.tool_registry
        async def dummy_tool(**kwargs):
            return f"Tool {tool_name} called with {kwargs}"

        return dummy_tool

    # ========================================================================
    # History Management
    # ========================================================================

    def record_step(self, result: StepResult) -> None:
        """
        Record a step result to history

        Args:
            result: StepResult to record
        """
        self.history.append(result)
        self.metadata["total_steps"] += 1

        # Update node tracking
        if result.node_id:
            if result.is_success():
                self._completed.add(result.node_id)
                self._pending.discard(result.node_id)
                self._failed.discard(result.node_id)
                self.failure_counter.record_success(result.node_id)
            elif result.is_failed():
                self._failed.add(result.node_id)
                self._pending.discard(result.node_id)
                count = self.failure_counter.record_failure(result.node_id)
                logger.warning(f"Node {result.node_id} failed {count} time(s)")

    def get_history(self) -> List[StepResult]:
        """Get execution history"""
        return self.history.copy()

    def get_last_result(self, node_id: str = None) -> Optional[StepResult]:
        """
        Get most recent step result

        Args:
            node_id: Optional node ID to filter by

        Returns:
            Most recent StepResult matching criteria
        """
        if node_id:
            for result in reversed(self.history):
                if result.node_id == node_id:
                    return result
        else:
            return self.history[-1] if self.history else None
        return None

    def get_failed_nodes(self) -> List[str]:
        """Get list of failed node IDs"""
        return list(self._failed)

    def get_completed_nodes(self) -> List[str]:
        """Get list of completed node IDs"""
        return list(self._completed)

    def get_pending_nodes(self) -> List[str]:
        """Get list of pending node IDs"""
        return list(self._pending)

    # ========================================================================
    # Snapshot & Rollback
    # ========================================================================

    def create_snapshot(self, label: str = None) -> str:
        """
        Create snapshot of current state

        Args:
            label: Optional label for snapshot

        Returns:
            Snapshot ID
        """
        self._snapshot_counter += 1
        snapshot_id = f"snapshot_{self._snapshot_counter}"

        snapshot = GraphSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(),
            graph_dict=self.graph.to_dict(),
            node_outputs={node_id: self.get_node_output(node_id) for node_id in self._completed},
            shared_memory=copy.deepcopy(self.shared_memory),
            metadata={
                "label": label,
                "history_length": len(self.history),
            }
        )

        self._snapshots[snapshot_id] = snapshot
        logger.debug(f"Created snapshot: {snapshot_id} ({label})")
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore state from snapshot

        Args:
            snapshot_id: Snapshot to restore

        Returns:
            True if successful
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False

        # Restore graph structure
        # Note: This requires reconstructing graph from dict
        # For now, we restore the data state
        self.shared_memory = copy.deepcopy(snapshot.shared_memory)

        # Clear history after snapshot
        # (In production, we'd truncate history properly)
        logger.info(f"Restored snapshot: {snapshot_id}")
        return True

    def get_latest_snapshot(self) -> Optional[GraphSnapshot]:
        """Get most recent snapshot"""
        if not self._snapshots:
            return None
        return list(self._snapshots.values())[-1]

    def should_rollback(self) -> bool:
        """Check if any node has exceeded failure threshold"""
        for target, count in self.failure_counter.failures.items():
            if count >= self.failure_counter.threshold:
                logger.warning(f"Rollback threshold exceeded for {target}: {count} failures")
                return True
        return False

    # ========================================================================
    # Node Output Access
    # ========================================================================

    def get_node_output(self, node_id: str) -> Any:
        """Get output from completed node"""
        result = self.get_last_result(node_id)
        if result and result.is_success():
            return result.payload
        return None

    def set_shared_memory(self, key: str, value: Any) -> None:
        """Set value in shared memory"""
        self.shared_memory[key] = value

    def get_shared_memory(self, key: str, default: Any = None) -> Any:
        """Get value from shared memory"""
        return self.shared_memory.get(key, default)

    # ========================================================================
    # Observation Management
    # ========================================================================

    def add_observation(self, observation: ExternalObservation) -> None:
        """Add external observation (e.g., user input)"""
        self.observations.append(observation)
        logger.debug(f"Added observation from {observation.source}")

    def has_pending_observations(self) -> bool:
        """Check if there are unprocessed observations"""
        return len(self.observations) > 0

    def get_next_observation(self) -> Optional[ExternalObservation]:
        """Get and remove next observation"""
        if self.observations:
            return self.observations.pop(0)
        return None

    # ========================================================================
    # Utility
    # ========================================================================

    def is_complete(self) -> bool:
        """Check if execution is complete (no pending nodes)"""
        return len(self._pending) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for inspection"""
        return {
            "graph": {
                "name": self.graph.name,
                "nodes": len(self.graph.nodes),
                "edges": len(self.graph.edges),
            },
            "history_length": len(self.history),
            "pending": len(self._pending),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "snapshots": len(self._snapshots),
            "failure_counts": self.failure_counter.failures,
            "metadata": self.metadata,
        }
