"""
Task Scheduler Demo - Demonstrates Sprint 4 FollowUpPump capability

This demo shows how to use the TaskScheduler to create multi-step workflows
that execute automatically without user intervention.

Example workflow:
1. Write code
2. Run tests
3. Fix bugs (if tests fail)
4. Commit changes

Usage:
    python demo_task_chaining.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import FastReAct
from fastreact.core import ScheduledTask, SimpleTaskScheduler, SequentialTaskScheduler, create_workflow_from_list
from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model


async def demo_sequential_workflow():
    """
    Demo 1: Sequential workflow using create_workflow_from_list
    """
    print("=" * 70)
    print("DEMO 1: Sequential Workflow (Write -> Test -> Document)")
    print("=" * 70)
    print()

    # Load configuration
    config = load_config()
    config["reactive_loop"] = {"enabled": True}

    # Create agent
    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    # Get task scheduler
    scheduler = agent.get_task_scheduler()
    if not scheduler:
        print("[ERROR] Task scheduler not available. Enable reactive loop in config.")
        return False

    # Create a workflow from a list of instructions
    workflow = create_workflow_from_list([
        "Create a simple Python function that calculates fibonacci numbers",
        "Write unit tests for the fibonacci function",
        "Document the function with docstring and examples",
    ])

    # Add workflow tasks to scheduler
    for task_id in workflow._queue:
        scheduler.add_task(task_id)
        print(f"[SCHEDULER] Queued task: {task_id.task_id}")

    print()
    print("[INFO] Starting workflow execution...")
    print("[INFO] The agent will automatically proceed through each task.")
    print()

    # Execute workflow
    result = await agent.run_async("Start the workflow")

    print()
    print("[DONE] Workflow completed")
    print(f"[RESULT] {result['answer'][:200]}...")
    print()

    # Show scheduler status
    status = scheduler.get_status()
    print("[STATS] Scheduler status:")
    print(f"  Completed: {status['completed_count']}")
    print(f"  Pending: {status['pending_count']}")
    print()

    return True


async def demo_manual_scheduling():
    """
    Demo 2: Manual task scheduling with priorities
    """
    print("=" * 70)
    print("DEMO 2: Manual Task Scheduling with Priorities")
    print("=" * 70)
    print()

    # Load configuration
    config = load_config()
    config["reactive_loop"] = {"enabled": True}

    # Create agent
    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    # Get task scheduler
    scheduler = agent.get_task_scheduler()
    if not scheduler:
        print("[ERROR] Task scheduler not available")
        return False

    # Create tasks with different priorities
    tasks = [
        ScheduledTask(
            task_id="high_priority",
            instruction="List all Python files in the current directory",
            priority=100,  # High priority
            task_type="listing"
        ),
        ScheduledTask(
            task_id="low_priority",
            instruction="Count the total lines of code",
            priority=10,  # Low priority
            task_type="analysis",
            depends_on=["high_priority"]  # Depends on high_priority
        ),
    ]

    # Add tasks
    for task in tasks:
        scheduler.add_task(task)
        print(f"[SCHEDULER] Added task: {task.task_id} (priority={task.priority})")

    print()
    print("[INFO] Starting tasks...")
    print("[INFO] High priority task will execute first.")
    print()

    # Execute
    result = await agent.run_async("Begin task execution")

    print()
    print("[DONE] All tasks completed")
    print()

    # Show status
    status = scheduler.get_status()
    print("[STATS] Scheduler status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    print()

    return True


async def demo_conditional_scheduling():
    """
    Demo 3: Conditional task scheduling based on results

    Uses a custom conditional scheduler that generates tasks dynamically
    based on previous task results.
    """
    print("=" * 70)
    print("DEMO 3: Conditional Task Scheduling")
    print("=" * 70)
    print()

    from fastreact.core import ConditionalTaskScheduler, ScheduledTask

    # Define a task generator function
    def generate_next_task(context):
        """
        Generate next task based on context

        This function is called after each task completes to determine
        what to do next.
        """
        # Check if previous task mentioned "error" or "failed"
        if hasattr(context, 'messages') and context.messages:
            last_message = context.messages[-1]
            content = str(last_message.get('content', ''))

            if 'error' in content.lower() or 'failed' in content.lower():
                return ScheduledTask(
                    task_id="fix_error",
                    instruction="Fix the error that occurred",
                    task_type="fix",
                    priority=100
                )

        # Default: no follow-up task
        return None

    # Create conditional scheduler
    scheduler = ConditionalTaskScheduler(
        task_generator=generate_next_task,
        max_iterations=5
    )

    # Note: This would require integrating the custom scheduler into the agent
    # For now, just demonstrate the concept
    print("[INFO] Conditional scheduler created")
    print("[INFO] Tasks will be generated dynamically based on results")
    print("[INFO] If an error occurs, a fix task will be automatically scheduled")
    print()

    return True


async def main():
    """
    Run all demos
    """
    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 10 + "SPRINT 4: TASK CHAINING DEMONSTRATIONS" + " " * 18 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()

    # Demo 1: Sequential workflow
    # result1 = await demo_sequential_workflow()

    # Demo 2: Manual scheduling
    result2 = await demo_manual_scheduling()

    # Demo 3: Conditional scheduling
    # result3 = await demo_conditional_scheduling()

    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 25 + "DEMO SUMMARY" + " " * 31 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()
    print("[INFO] Task Scheduler enables:")
    print("  1. Multi-step workflows without manual intervention")
    print("  2. Priority-based task execution")
    print("  3. Conditional task generation based on results")
    print("  4. Dependency management between tasks")
    print()
    print("[NEXT] Integrate with FollowUpPump for automatic execution")
    print()


if __name__ == "__main__":
    asyncio.run(main())
