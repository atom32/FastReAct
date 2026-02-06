"""
Auto-Reflection Demo - Sprint 5 Integration Test

This demo shows FastReAct's self-awareness in action:
1. Agent executes a task that will fail
2. TaskEvaluator detects the failure
3. FollowUpPump auto-injects a fix task
4. Agent attempts to fix the error

Usage:
    python demo_auto_reflection.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import FastReAct
from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model


async def demo_syntax_error():
    """
    Demo 1: Agent writes Python code with syntax error
    Expected: Evaluator detects SyntaxError and suggests fix
    """
    print("=" * 70)
    print("DEMO 1: Syntax Error Detection")
    print("=" * 70)
    print()

    config = load_config()
    config["reactive_loop"] = {"enabled": True}

    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    print("[TASK] Write a Python file with intentional syntax error")
    print()

    task = """
Write a Python file named 'test_syntax.py' with this content:

def hello(    # Missing colon
    print("Hello, world")
"""

    print(f"[TASK CONTENT]")
    print(task)
    print()

    result = await agent.run_async(task)

    print()
    print("[RESULT]")
    print(f"Answer: {str(result.get('answer', 'No answer'))[:200]}...")
    print()

    # Check if fix task was auto-generated
    scheduler = agent.get_task_scheduler()
    if scheduler:
        status = scheduler.get_status()
        print(f"[SCHEDULER] Pending tasks: {status['total_tasks']}")
        if status['pending_tasks']:
            print("[SCHEDULER] Pending tasks:")
            for task_id in status['pending_tasks']:
                task = scheduler._tasks[task_id]
                print(f"  - {task_id}: {task.instruction[:50]}...")
        print()

    return result


async def demo_bash_error():
    """
    Demo 2: Agent tries to access non-existent file
    Expected: Evaluator detects "no such file" and suggests fix
    """
    print()
    print("=" * 70)
    print("DEMO 2: Bash Error Detection")
    print("=" * 70)
    print()

    config = load_config()
    config["reactive_loop"] = {"enabled": True}

    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    print("[TASK] Try to read a non-existent file")
    print()

    task = "Read the content of /nonexistent_file_12345.txt"

    print(f"[TASK CONTENT] {task}")
    print()

    result = await agent.run_async(task)

    print()
    print("[RESULT]")
    print(f"Answer: {str(result.get('answer', 'No answer'))[:200]}...")
    print()

    # Check if fix task was auto-generated
    scheduler = agent.get_task_scheduler()
    if scheduler:
        status = scheduler.get_status()
        print(f"[SCHEDULER] Pending tasks: {status['total_tasks']}")
        if status['pending_tasks']:
            print("[SCHEDULER] Pending tasks:")
            for task_id in status['pending_tasks']:
                task = scheduler._tasks[task_id]
                print(f"  - {task_id}: {task.instruction[:50]}...")
        print()

    return result


async def demo_success_case():
    """
    Demo 3: Agent executes successful task
    Expected: Evaluator classifies as SUCCESS, no fix needed
    """
    print()
    print("=" * 70)
    print("DEMO 3: Success Case (No Fix Needed)")
    print("=" * 70)
    print()

    config = load_config()
    config["reactive_loop"] = {"enabled": True}

    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    print("[TASK] Execute a simple successful command")
    print()

    task = 'echo "Hello, FastReAct!"'

    print(f"[TASK CONTENT] {task}")
    print()

    result = await agent.run_async(task)

    print()
    print("[RESULT]")
    print(f"Answer: {str(result.get('answer', 'No answer'))[:200]}...")
    print()

    # Check if any fix tasks were generated (should be none)
    scheduler = agent.get_task_scheduler()
    if scheduler:
        status = scheduler.get_status()
        print(f"[SCHEDULER] Pending tasks: {status['total_tasks']}")
        if status['total_tasks'] == 0:
            print("[SCHEDULER] No fix tasks generated (as expected)")
        print()

    return result


async def demo_manual_evaluation():
    """
    Demo 4: Manual evaluation of tool results
    Shows direct usage of TaskEvaluator API
    """
    print()
    print("=" * 70)
    print("DEMO 4: Manual TaskEvaluator Usage")
    print("=" * 70)
    print()

    from fastreact.core import create_evaluator, ToolResult

    evaluator = create_evaluator()

    print("[TEST 1] Successful execution")
    result1 = ToolResult(
        tool_name="echo",
        result="Hello, World!"
    )
    eval1 = await evaluator.evaluate(result1)
    print(f"  Outcome: {eval1.outcome.value}")
    print(f"  Success: {eval1.success}")
    print(f"  Needs Fix: {eval1.needs_fix}")
    print()

    print("[TEST 2] Python traceback")
    result2 = ToolResult(
        tool_name="python",
        result="""Traceback (most recent call last):
  File "test.py", line 5, in <module>
    print("Hello"
NameError: name 'print' is not defined"""
    )
    eval2 = await evaluator.evaluate(result2)
    print(f"  Outcome: {eval2.outcome.value}")
    print(f"  Success: {eval2.success}")
    print(f"  Needs Fix: {eval2.needs_fix}")
    print(f"  Failure Reason: {eval2.failure_reason}")
    print(f"  Suggested Fix: {eval2.suggested_fix}")
    print()

    print("[TEST 3] Bash error")
    result3 = ToolResult(
        tool_name="bash",
        result="ls: cannot access '/nonexistent': No such file or directory"
    )
    eval3 = await evaluator.evaluate(result3)
    print(f"  Outcome: {eval3.outcome.value}")
    print(f"  Success: {eval3.success}")
    print(f"  Needs Fix: {eval3.needs_fix}")
    print(f"  Failure Reason: {eval3.failure_reason}")
    print(f"  Suggested Fix: {eval3.suggested_fix}")
    print()

    # Show statistics
    stats = evaluator.get_stats()
    print("[STATISTICS]")
    print(f"  Total evaluations: {stats['total_evaluations']}")
    print(f"  Success: {stats['success_count']}")
    print(f"  Retry: {stats['retry_count']}")
    print(f"  Fix: {stats['fix_count']}")
    print(f"  Fatal: {stats['fatal_count']}")


async def main():
    """
    Run all demos
    """
    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 15 + "SPRINT 5: AUTO-REFLECTION DEMO" + " " * 21 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()
    print("[CAPABILITIES] This demo shows:")
    print("  1. Syntax error detection and fix suggestion")
    print("  2. Bash error detection and fix suggestion")
    print("  3. Success case (no fix needed)")
    print("  4. Manual TaskEvaluator API usage")
    print()
    print("[NOTE] Demos 1-3 use actual LLM calls (may take time)")
    print("[NOTE] Demo 4 uses mock data (fast)")
    print()
    print("=" * 70)
    print()

    # Run demo 4 first (fast, no LLM calls)
    await demo_manual_evaluation()

    # Uncomment to run full demos (requires LLM)
    # print()
    # print("[PROMPT] Run full demos? (This will make LLM calls)")
    # response = input("Continue? (y/N): ")
    # if response.lower() == 'y':
    #     await demo_syntax_error()
    #     await demo_bash_error()
    #     await demo_success_case()
    # else:
    #     print("[SKIP] Full demos skipped")

    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 25 + "DEMO COMPLETE" + " " * 31 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()
    print("[NEXT STEPS]")
    print("  1. Try Demo 1-3 (uncomment in main()) to test with real LLM")
    print("  2. Use CLI: 'python -m fastreact.cli.unified_repl'")
    print("  3. In REPL: run a failing task and watch for auto-fix")
    print()


if __name__ == "__main__":
    asyncio.run(main())
