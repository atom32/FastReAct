"""
Priority Interrupt Queue - High-speed user input handling

Supports priority interrupts with special commands:
- /fix - Skip LLM reflection, directly apply user's patch
- /stop - Halt execution immediately
- /skip - Skip current node
- Normal input - Goes through reflection/replanning
"""

import asyncio
import logging
from typing import List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .iel_types import ExternalObservation

logger = logging.getLogger(__name__)


# ============================================================================
# Priority Levels
# ============================================================================

class InterruptPriority(str, Enum):
    """Interrupt priority levels"""
    CRITICAL = "critical"  # /stop - Halt immediately
    HIGH = "high"         # /fix - Skip reflection, apply directly
    NORMAL = "normal"     # Regular user input - goes through reflection


# ============================================================================
# Special Commands
# ============================================================================

class SpecialCommand(str, Enum):
    """Special command prefixes"""
    STOP = "/stop"    # Halt execution
    FIX = "/fix"      # Direct patch (skip reflection)
    SKIP = "/skip"    # Skip current node
    INFO = "/info"    # Show execution info
    HELP = "/help"    # Show help


# ============================================================================
# Priority Interrupt
# ============================================================================

@dataclass
class PriorityInterrupt:
    """
    Priority-based interrupt with special command support

    Attributes:
        observation: Base ExternalObservation
        priority: Interrupt priority level
        command: Special command (if any)
        raw_input: Original user input
        timestamp: When interrupt was created
    """
    observation: ExternalObservation
    priority: InterruptPriority
    command: Optional[SpecialCommand]
    raw_input: str
    timestamp: datetime = None

    if timestamp is None:
        timestamp = datetime.now()

    def is_critical(self) -> bool:
        """Check if this is a critical interrupt (halts execution)"""
        return self.priority == InterruptPriority.CRITICAL

    def is_high_priority(self) -> bool:
        """Check if this is high priority (bypasses reflection)"""
        return self.priority == InterruptPriority.HIGH

    def has_command(self) -> bool:
        """Check if this has a special command"""
        return self.command is not None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "observation": self.observation.to_dict() if hasattr(self.observation, 'to_dict') else str(self.observation),
            "priority": self.priority.value,
            "command": self.command.value if self.command else None,
            "raw_input": self.raw_input,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# Priority Interrupt Queue
# ============================================================================

class PriorityInterruptQueue:
    """
    Priority-based interrupt queue for high-speed user interaction

    Features:
    - Priority levels (CRITICAL > HIGH > NORMAL)
    - Special commands (/stop, /fix, /skip, etc.)
    - Non-blocking polling
    - Command parsing

    Usage:
        queue = PriorityInterruptQueue()

        # User input
        await queue.put_user_input("/fix Add node X before node Y")

        # Poll in executor
        interrupts = queue.poll()
        for interrupt in interrupts:
            if interrupt.is_critical():
                # Halt execution
                break
            elif interrupt.is_high_priority():
                # Apply directly without reflection
                apply_direct_patch(interrupt.raw_input)
            else:
                # Normal reflection/replanning
                await replanner.replan_from_user(context, interrupt.raw_input)
    """

    def __init__(self):
        """Initialize priority interrupt queue"""
        self._queues = {
            InterruptPriority.CRITICAL: asyncio.Queue(),
            InterruptPriority.HIGH: asyncio.Queue(),
            InterruptPriority.NORMAL: asyncio.Queue(),
        }
        self._enabled = True

    # ========================================================================
    # Input Methods
    # ========================================================================

    async def put_user_input(self, user_input: str, source: str = "user") -> None:
        """
        Add user input to queue with automatic priority detection

        Parses special commands and assigns appropriate priority.

        Args:
            user_input: Raw user input string
            source: Input source (default: "user")

        Special Commands:
            /stop    - CRITICAL priority, halt execution
            /fix     - HIGH priority, skip reflection
            /skip    - HIGH priority, skip current node
            /info    - NORMAL priority, show info
            /help    - NORMAL priority, show help
        """
        if not self._enabled:
            logger.warning("Interrupt queue disabled, ignoring input")
            return

        # Parse command and priority
        priority, command = self._parse_input(user_input)

        # Create observation
        observation = ExternalObservation(
            source=source,
            content=user_input,
            metadata={"command": command.value if command else None}
        )

        # Create priority interrupt
        interrupt = PriorityInterrupt(
            observation=observation,
            priority=priority,
            command=command,
            raw_input=user_input,
            timestamp=datetime.now(),
        )

        # Add to appropriate queue
        await self._queues[priority].put(interrupt)

        logger.info(f"Enqueued interrupt: {priority.value} - {user_input[:50]}...")

    async def put(self, interrupt: PriorityInterrupt) -> None:
        """
        Add pre-parsed interrupt to queue

        Args:
            interrupt: PriorityInterrupt object
        """
        if not self._enabled:
            return

        await self._queues[interrupt.priority].put(interrupt)

    async def put_observation(
        self,
        observation: ExternalObservation,
        priority: InterruptPriority = InterruptPriority.NORMAL,
    ) -> None:
        """
        Add ExternalObservation to queue

        Args:
            observation: ExternalObservation object
            priority: Interrupt priority (default: NORMAL)
        """
        if not self._enabled:
            return

        interrupt = PriorityInterrupt(
            observation=observation,
            priority=priority,
            command=None,
            raw_input=observation.content,
            timestamp=datetime.now(),
        )

        await self._queues[interrupt.priority].put(interrupt)

    # ========================================================================
    # Polling
    # ========================================================================

    def poll(self) -> List[PriorityInterrupt]:
        """
        Poll for pending interrupts (non-blocking)

        Returns all pending interrupts in priority order:
        CRITICAL first, then HIGH, then NORMAL

        Returns:
            List of PriorityInterrupt objects
        """
        interrupts = []

        # Poll in priority order
        for priority in [InterruptPriority.CRITICAL, InterruptPriority.HIGH, InterruptPriority.NORMAL]:
            queue = self._queues[priority]

            while not queue.empty():
                try:
                    interrupt = queue.get_nowait()
                    interrupts.append(interrupt)
                except asyncio.QueueEmpty:
                    break

        return interrupts

    def has_pending(self) -> bool:
        """Check if any interrupts are pending"""
        return any(
            not queue.empty()
            for queue in self._queues.values()
        )

    def has_critical(self) -> bool:
        """Check if critical interrupts are pending"""
        return not self._queues[InterruptPriority.CRITICAL].empty()

    def has_high_priority(self) -> bool:
        """Check if high priority interrupts are pending"""
        return not self._queues[InterruptPriority.HIGH].empty()

    # ========================================================================
    # Command Parsing
    # ========================================================================

    def _parse_input(self, user_input: str) -> tuple:
        """
        Parse user input to detect special commands and priority

        Args:
            user_input: Raw user input string

        Returns:
            (InterruptPriority, SpecialCommand or None)
        """
        import re

        # Strip whitespace
        input_stripped = user_input.strip()

        # Check for special commands
        if input_stripped.startswith("/stop"):
            return InterruptPriority.CRITICAL, SpecialCommand.STOP

        elif input_stripped.startswith("/fix"):
            return InterruptPriority.HIGH, SpecialCommand.FIX

        elif input_stripped.startswith("/skip"):
            return InterruptPriority.HIGH, SpecialCommand.SKIP

        elif input_stripped.startswith("/info"):
            return InterruptPriority.NORMAL, SpecialCommand.INFO

        elif input_stripped.startswith("/help"):
            return InterruptPriority.NORMAL, SpecialCommand.HELP

        # No special command - normal priority
        return InterruptPriority.NORMAL, None

    # ========================================================================
    # Control
    # ========================================================================

    def enable(self) -> None:
        """Enable interrupt processing"""
        self._enabled = True
        logger.debug("Interrupt queue enabled")

    def disable(self) -> None:
        """Disable interrupt processing"""
        self._enabled = False
        logger.debug("Interrupt queue disabled")

    def clear(self) -> None:
        """Clear all pending interrupts"""
        for queue in self._queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        logger.debug("Cleared all pending interrupts")

    # ========================================================================
    # Utility
    # ========================================================================

    def get_status(self) -> dict:
        """Get queue status"""
        return {
            "enabled": self._enabled,
            "critical_pending": not self._queues[InterruptPriority.CRITICAL].empty(),
            "high_priority_pending": not self._queues[InterruptPriority.HIGH].empty(),
            "normal_pending": not self._queues[InterruptPriority.NORMAL].empty(),
            "total_pending": sum(
                not queue.empty()
                for queue in self._queues.values()
            )
        }


# ============================================================================
# Direct Patch Parser (for /fix command)
# ============================================================================

def parse_fix_command(user_input: str) -> dict:
    """
    Parse /fix command to extract patch instructions

    /fix format:
    /fix <operation> <reason>
         <instructions>

    Example:
    /fix insert_before Add file creation node
         node_id: read_file
         new_node:
           node_id: create_file
           tool_name: write_file
           inputs:
             path: /tmp/file.txt
             content: "Hello"

    Args:
        user_input: User input string starting with /fix

    Returns:
        Dict with operation, reason, instructions
    """
    import re
    import yaml

    # Remove /fix prefix
    content = user_input[4:].strip()

    # Try to parse as YAML (most flexible)
    try:
        # Split into first line (operation+reason) and rest (instructions)
        lines = content.split("\n", 1)

        first_line = lines[0].strip()
        instructions_str = lines[1] if len(lines) > 1 else ""

        # Parse operation and reason from first line
        parts = first_line.split(None, 1)
        operation = parts[0] if parts else ""
        reason = parts[1] if len(parts) > 1 else ""

        # Parse instructions as YAML
        instructions = {}
        if instructions_str.strip():
            try:
                instructions = yaml.safe_load(instructions_str)
            except yaml.YAMLError:
                # Fallback: simple key:value parsing
                instructions = _parse_simple_instructions(instructions_str)

        return {
            "operation": operation,
            "reason": reason,
            "instructions": instructions,
        }

    except Exception as e:
        logger.error(f"Failed to parse /fix command: {e}")
        return {
            "operation": "retry",
            "reason": f"Parse error: {e}",
            "instructions": {},
        }


def _parse_simple_instructions(text: str) -> dict:
    """Simple key:value parser for /fix instructions"""
    instructions = {}

    for line in text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            instructions[key.strip()] = value.strip()

    return instructions


# ============================================================================
# Backward Compatibility
# ============================================================================

# Keep old InterruptQueue as alias for PriorityInterruptQueue
# with normal-only priority for backward compatibility
class InterruptQueue(PriorityInterruptQueue):
    """
    Backward-compatible interrupt queue

    Uses NORMAL priority for all inputs (no special commands).
    """

    async def put(self, observation) -> None:
        """Legacy put method (always normal priority)"""
        if not self._enabled:
            return

        # Create normal priority interrupt
        interrupt = PriorityInterrupt(
            observation=observation,
            priority=InterruptPriority.NORMAL,
            command=None,
            raw_input=str(observation.content),
            timestamp=datetime.now(),
        )

        await self._queues[InterruptPriority.NORMAL].put(interrupt)
