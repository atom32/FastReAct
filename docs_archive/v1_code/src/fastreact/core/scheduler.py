"""
Task Scheduler - Task chaining and orchestration for Reactive Loop

Implements task scheduling for the FollowUpPump in Sprint 4.

Core concept:
- Task A completes -> FollowUpPump checks scheduler
- Scheduler provides Task B -> Injected as UserMessage
- Loop continues with Task B

This enables multi-step workflows without user intervention.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# Task Definition
# ============================================================================

@dataclass
class ScheduledTask:
    """
    A task scheduled for execution after current task completes

    Attributes:
        task_id: Unique task identifier
        instruction: Natural language instruction for the agent
        task_type: Type of task (e.g., "test", "deploy", "document")
        priority: Task priority (higher = earlier execution)
        metadata: Additional task information
        depends_on: List of task IDs this task depends on
        created_at: When task was created
    """

    task_id: str
    instruction: str
    task_type: str = "general"
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "type": self.task_type,
            "priority": self.priority,
            "metadata": self.metadata,
            "depends_on": self.depends_on,
            "created_at": self.created_at.isoformat(),
        }

    def is_ready(self, completed_tasks: List[str]) -> bool:
        """
        Check if task is ready to execute

        Args:
            completed_tasks: List of completed task IDs

        Returns:
            True if all dependencies are satisfied
        """
        for dep in self.depends_on:
            if dep not in completed_tasks:
                return False
        return True


# ============================================================================
# Task Scheduler Interface
# ============================================================================

class TaskScheduler(ABC):
    """
    Abstract base class for task schedulers

    A task scheduler manages a queue of tasks to be executed
    sequentially or in dependency order.

    Usage:
        scheduler = SimpleTaskScheduler()
        scheduler.add_task(ScheduledTask(
            task_id="test_1",
            instruction="Run the test suite"
        ))

        # Later, in FollowUpPump:
        next_task = await scheduler.get_next_task(context)
        if next_task:
            # Inject task instruction as UserMessage
            ...
    """

    @abstractmethod
    async def get_next_task(self, context: 'AgentContext') -> Optional[ScheduledTask]:
        """
        Get the next task to execute

        Args:
            context: Current agent execution context

        Returns:
            Next ScheduledTask, or None if no more tasks
        """
        pass

    @abstractmethod
    def add_task(self, task: ScheduledTask) -> None:
        """
        Add a task to the scheduler

        Args:
            task: Task to schedule
        """
        pass

    @abstractmethod
    def mark_completed(self, task_id: str) -> None:
        """
        Mark a task as completed

        Args:
            task_id: ID of completed task
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all pending tasks"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        pass


# ============================================================================
# Simple Task Scheduler (List-based)
# ============================================================================

class SimpleTaskScheduler(TaskScheduler):
    """
    Simple list-based task scheduler

    Tasks are executed in priority order (higher priority first).
    Tasks with unmet dependencies are skipped until dependencies complete.

    Example:
        scheduler = SimpleTaskScheduler()

        # Add independent tasks
        scheduler.add_task(ScheduledTask(
            task_id="task_1",
            instruction="Write code",
            priority=10
        ))

        scheduler.add_task(ScheduledTask(
            task_id="task_2",
            instruction="Test code",
            priority=5,  # Lower priority, runs after task_1
            depends_on=["task_1"]
        ))

        # Get next task
        task = await scheduler.get_next_task(context)
        # Returns: task_1 (write code)

        # After task_1 completes
        scheduler.mark_completed("task_1")
        task = await scheduler.get_next_task(context)
        # Returns: task_2 (test code)
    """

    def __init__(self):
        """Initialize simple task scheduler"""
        self._tasks: List[ScheduledTask] = []
        self._completed: List[str] = []
        self._current_index = 0

    async def get_next_task(self, context: 'AgentContext') -> Optional[ScheduledTask]:
        """
        Get the next ready task

        Returns the highest priority ready task (all dependencies satisfied).

        Args:
            context: Agent execution context (unused in simple version)

        Returns:
            Next ScheduledTask, or None if no ready tasks
        """
        # Sort by priority (descending)
        sorted_tasks = sorted(
            self._tasks,
            key=lambda t: t.priority,
            reverse=True
        )

        # Find first ready task
        for task in sorted_tasks:
            if task.task_id not in self._completed and task.is_ready(self._completed):
                logger.info(f"[SCHEDULER] Next task: {task.task_id} - {task.instruction[:50]}...")
                return task

        logger.debug("[SCHEDULER] No more ready tasks")
        return None

    def add_task(self, task: ScheduledTask) -> None:
        """
        Add a task to the scheduler

        Args:
            task: Task to schedule
        """
        self._tasks.append(task)
        logger.info(f"[SCHEDULER] Task added: {task.task_id} (priority={task.priority})")

    def mark_completed(self, task_id: str) -> None:
        """
        Mark a task as completed

        Args:
            task_id: ID of completed task
        """
        if task_id not in self._completed:
            self._completed.append(task_id)
            logger.info(f"[SCHEDULER] Task completed: {task_id}")

    def clear(self) -> None:
        """Clear all pending tasks"""
        self._tasks.clear()
        self._completed.clear()
        self._current_index = 0
        logger.debug("[SCHEDULER] Cleared all tasks")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "type": "simple",
            "pending_count": len([t for t in self._tasks if t.task_id not in self._completed]),
            "completed_count": len(self._completed),
            "total_tasks": len(self._tasks),
            "pending_tasks": [
                t.task_id for t in self._tasks
                if t.task_id not in self._completed
            ],
            "completed_tasks": list(self._completed),
        }


# ============================================================================
# Sequential Task Scheduler (Ordered execution)
# ============================================================================

class SequentialTaskScheduler(TaskScheduler):
    """
    Sequential task scheduler

    Tasks are executed in the order they were added,
    regardless of priority.

    Useful for fixed workflows like:
    1. Write code
    2. Run tests
    3. Fix bugs
    4. Commit
    """

    def __init__(self):
        """Initialize sequential task scheduler"""
        self._queue: List[ScheduledTask] = []
        self._completed: List[str] = []

    async def get_next_task(self, context: 'AgentContext') -> Optional[ScheduledTask]:
        """
        Get the next task in sequence

        Args:
            context: Agent execution context

        Returns:
            Next ScheduledTask, or None if queue empty
        """
        while self._queue:
            task = self._queue[0]

            # Skip if already completed
            if task.task_id in self._completed:
                self._queue.pop(0)
                continue

            # Check dependencies
            if task.is_ready(self._completed):
                logger.info(f"[SCHEDULER] Next task: {task.task_id} - {task.instruction[:50]}...")
                return task
            else:
                logger.warning(f"[SCHEDULER] Task {task.task_id} has unmet dependencies")
                break

        return None

    def add_task(self, task: ScheduledTask) -> None:
        """Add a task to the end of the queue"""
        self._queue.append(task)
        logger.info(f"[SCHEDULER] Task queued: {task.task_id}")

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed"""
        if task_id not in self._completed:
            self._completed.append(task_id)
            # Remove from queue if present
            self._queue = [t for t in self._queue if t.task_id != task_id]
            logger.info(f"[SCHEDULER] Task completed: {task_id}")

    def clear(self) -> None:
        """Clear all tasks"""
        self._queue.clear()
        self._completed.clear()
        logger.debug("[SCHEDULER] Cleared all tasks")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "type": "sequential",
            "pending_count": len(self._queue),
            "completed_count": len(self._completed),
            "queue": [t.task_id for t in self._queue],
            "completed": list(self._completed),
        }


# ============================================================================
# Conditional Task Scheduler (Dynamic workflow)
# ============================================================================

class ConditionalTaskScheduler(TaskScheduler):
    """
    Conditional task scheduler with dynamic task generation

    Tasks can be generated dynamically based on:
    - Previous task results
    - Context state
    - External conditions

    Example:
        def decide_next_task(context):
            if "test_failed" in context.metadata:
                return ScheduledTask(
                    task_id="fix_tests",
                    instruction="Fix the failing tests"
                )
            return None

        scheduler = ConditionalTaskScheduler(decide_next_task)
    """

    def __init__(
        self,
        task_generator: Callable[['AgentContext'], Optional[ScheduledTask]],
        max_iterations: int = 10
    ):
        """
        Initialize conditional task scheduler

        Args:
            task_generator: Function that generates next task based on context
            max_iterations: Maximum number of tasks to generate
        """
        self._task_generator = task_generator
        self._max_iterations = max_iterations
        self._generated_count = 0
        self._completed: List[str] = []

    async def get_next_task(self, context: 'AgentContext') -> Optional[ScheduledTask]:
        """
        Generate the next task dynamically

        Args:
            context: Agent execution context

        Returns:
            Generated task, or None if no more tasks
        """
        if self._generated_count >= self._max_iterations:
            logger.info("[SCHEDULER] Max iterations reached")
            return None

        task = self._task_generator(context)

        if task:
            # Skip if already completed
            if task.task_id in self._completed:
                logger.debug(f"[SCHEDULER] Task {task.task_id} already completed")
                return None

            self._generated_count += 1
            logger.info(f"[SCHEDULER] Generated task: {task.task_id}")
            return task

        return None

    def add_task(self, task: ScheduledTask) -> None:
        """
        Add a task manually (not recommended for conditional scheduler)

        This method is provided for API compatibility but does nothing
        in conditional scheduler since tasks are generated dynamically.
        """
        logger.warning("[SCHEDULER] add_task() called on conditional scheduler (no-op)")

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed"""
        if task_id not in self._completed:
            self._completed.append(task_id)
            logger.info(f"[SCHEDULER] Task completed: {task_id}")

    def clear(self) -> None:
        """Clear scheduler state"""
        self._completed.clear()
        self._generated_count = 0
        logger.debug("[SCHEDULER] Cleared state")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "type": "conditional",
            "generated_count": self._generated_count,
            "max_iterations": self._max_iterations,
            "completed_tasks": list(self._completed),
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_simple_scheduler() -> SimpleTaskScheduler:
    """Create a simple priority-based task scheduler"""
    return SimpleTaskScheduler()


def create_sequential_scheduler() -> SequentialTaskScheduler:
    """Create a sequential task scheduler"""
    return SequentialTaskScheduler()


def create_conditional_scheduler(
    task_generator: Callable[['AgentContext'], Optional[ScheduledTask]],
    max_iterations: int = 10
) -> ConditionalTaskScheduler:
    """
    Create a conditional task scheduler

    Args:
        task_generator: Function that generates tasks based on context
        max_iterations: Maximum number of tasks to generate

    Returns:
        ConditionalTaskScheduler instance
    """
    return ConditionalTaskScheduler(task_generator, max_iterations)


def create_workflow_from_list(instructions: List[str]) -> SequentialTaskScheduler:
    """
    Create a sequential workflow from a list of instructions

    Args:
        instructions: List of task instructions

    Returns:
        SequentialTaskScheduler with tasks

    Example:
        scheduler = create_workflow_from_list([
            "Write the function",
            "Test the function",
            "Document the function"
        ])
    """
    scheduler = SequentialTaskScheduler()

    for idx, instruction in enumerate(instructions):
        task = ScheduledTask(
            task_id=f"task_{idx}",
            instruction=instruction,
            priority=0,
            task_type="workflow_step"
        )
        scheduler.add_task(task)

    return scheduler
