"""
Simple Task Scheduler Demo - Working demonstration

This demo shows how to use TaskScheduler API directly.
Note: Full automatic task chaining requires completing the outer loop integration in run_async().
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import FastReAct
from fastreact.core import ScheduledTask, SimpleTaskScheduler
from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model


async def demo_basic_scheduling():
    """
    Demo: Basic task scheduling API usage
    """
    print("=" * 70)
    print("DEMO: Basic Task Scheduler API")
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
        print("[INFO] Enable reactive loop with config['reactive_loop']['enabled'] = True")
        return False

    print("[OK] Task scheduler initialized")
    print()

    # Method 1: Using schedule_task() convenience method
    print("[Method 1] Using agent.schedule_task()")
    task_id = await agent.schedule_task(
        "List all Python files in current directory",
        task_type="listing",
        priority=10
    )
    print(f"  Created task: {task_id}")
    print()

    # Method 2: Using scheduler.add_task() directly
    print("[Method 2] Using scheduler.add_task()")
    task2 = ScheduledTask(
        task_id="count_lines",
        instruction="Count total lines of Python code",
        task_type="analysis",
        priority=5
    )
    scheduler.add_task(task2)
    print(f"  Created task: {task2.task_id}")
    print()

    # Check status
    status = scheduler.get_status()
    print("[STATUS] Scheduler state:")
    print(f"  Total tasks: {status['total_tasks']}")
    print(f"  Pending: {status['pending_count']}")
    print(f"  Pending tasks: {', '.join(status['pending_tasks'])}")
    print()

    # Note: Tasks are NOT automatically executed yet
    # This requires completing the outer loop integration in run_async()
    print("[INFO] Note: Full automatic execution requires outer loop integration")
    print("[INFO] For now, tasks are queued but not automatically executed")
    print()

    # Demo: Manually execute next task
    print("[DEMO] Getting next task from scheduler...")
    temp_context = type('obj', (object,), {
        'messages': [],
        'metadata': {},
    })()

    next_task = await scheduler.get_next_task(temp_context)
    if next_task:
        print(f"  Next task: {next_task.task_id}")
        print(f"  Instruction: {next_task.instruction}")
        print()

        # Execute this task
        print("[EXECUTE] Running task with agent...")
        result = await agent.run_async(next_task.instruction)
        print(f"[RESULT] {result['answer'][:200]}...")
        print()

        # Mark as completed
        scheduler.mark_completed(next_task.task_id)
        print(f"[OK] Task {next_task.task_id} marked as completed")
        print()

    # Check updated status
    status = scheduler.get_status()
    print("[STATUS] Updated scheduler state:")
    print(f"  Completed: {status['completed_count']}")
    print(f"  Completed tasks: {', '.join(status['completed_tasks'])}")
    print()

    return True


async def demo_workflow_queue():
    """
    Demo: Creating a workflow queue
    """
    print("=" * 70)
    print("DEMO: Creating a Workflow Queue")
    print("=" * 70)
    print()

    from fastreact.core import SequentialTaskScheduler, create_workflow_from_list

    # Create a workflow from list
    print("[INFO] Creating workflow from instruction list...")
    workflow = create_workflow_from_list([
        "Say hello",
        "Count to 3",
        "Say goodbye"
    ])

    print(f"[OK] Created workflow with {len(workflow._queue)} tasks")
    for task in workflow._queue:
        print(f"  - {task.task_id}: {task.instruction}")
    print()

    # Replace agent's scheduler with this workflow
    config = load_config()
    config["reactive_loop"] = {"enabled": True}

    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    # Get the internal scheduler and add workflow tasks
    scheduler = agent.get_task_scheduler()
    for task in workflow._queue:
        scheduler.add_task(task)

    print("[INFO] Workflow tasks added to agent's scheduler")
    print()

    # Execute workflow manually (one by one)
    print("[EXECUTE] Executing workflow tasks sequentially...")
    for i in range(3):
        temp_context = type('obj', (object,), {'messages': [], 'metadata': {}})()
        task = await scheduler.get_next_task(temp_context)

        if not task:
            print(f"  [Iteration {i+1}] No more tasks")
            break

        print(f"  [Iteration {i+1}] Task: {task.instruction}")
        result = await agent.run_async(task.instruction)
        print(f"  [Iteration {i+1}] Result: {result['answer'][:100]}...")

        scheduler.mark_completed(task.task_id)
        print()

    print("[DONE] Workflow completed")
    print()

    return True


async def main():
    """
    Run all demos
    """
    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 15 + "TASK SCHEDULER API DEMONSTRATIONS" + " " * 19 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()

    # Demo 1: Basic scheduling
    await demo_basic_scheduling()

    # Demo 2: Workflow queue
    await demo_workflow_queue()

    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 25 + "DEMO SUMMARY" + " " * 31 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()
    print("[FEATURES] Task Scheduler API provides:")
    print("  1. schedule_task() - Convenience method for adding tasks")
    print("  2. add_task() - Direct task scheduling")
    print("  3. get_next_task() - Retrieve next pending task")
    print(" 4. mark_completed() - Mark task as done")
    print("  5. get_status() - Check scheduler state")
    print()
    print("[STATUS] Current implementation:")
    print("  - Task scheduling API: WORKING")
    print("  - Automatic task chaining: PENDING (requires outer loop integration)")
    print()
    print("[NEXT] Complete outer loop in run_async() for automatic execution")
    print()


if __name__ == "__main__":
    asyncio.run(main())
