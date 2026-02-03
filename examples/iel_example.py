"""
IEL (Interactive Execution Loop) Example

Demonstrates the new step-based execution system with:
- Step-by-step execution
- Interrupt handling
- Structured results
- Snapshot/rollback
"""

import asyncio
import logging

from fastreact.graph import (
    ToolGraph,
    IELExecutionContext,
    StepExecutor,
    StepConfig,
    StepResult,
    Status,
    ExternalObservation,
    InterruptQueue,
    create_graph,
    create_tool_node,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example Tools
# ============================================================================

async def tool_search(query: str) -> dict:
    """Example search tool"""
    logger.info(f"Searching: {query}")
    await asyncio.sleep(0.5)
    return {"results": f"Search results for: {query}"}


async def tool_process(data: str) -> dict:
    """Example processing tool"""
    logger.info(f"Processing: {data}")
    await asyncio.sleep(0.3)
    return {"processed": f"Processed: {data}"}


async def tool_save(content: str) -> dict:
    """Example save tool (high-side-effect)"""
    logger.info(f"Saving: {content}")
    await asyncio.sleep(0.2)
    return {"saved": True, "path": "/tmp/output.txt"}


async def tool_validate(data: dict) -> dict:
    """Example validation tool"""
    logger.info(f"Validating: {data}")
    await asyncio.sleep(0.1)
    return {"valid": True}


# ============================================================================
# Example 1: Basic Step-by-Step Execution
# ============================================================================

async def example_basic_execution():
    """Demonstrate basic step-by-step execution"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Step-by-Step Execution")
    print("=" * 60)

    # Create graph
    graph = create_graph("example_pipeline")

    # Add nodes
    search_node = create_tool_node("search", tool_search, {"query": "AI trends"})
    process_node = create_tool_node("process", tool_process, {"data": "@search.results"})
    save_node = create_tool_node("save", tool_save, {"content": "@process.processed"})

    graph.add_node(search_node)
    graph.add_node(process_node)
    graph.add_node(save_node)

    # Connect nodes
    graph.connect("search", "process")
    graph.connect("process", "save")

    # Create context
    context = IELExecutionContext(graph=graph)

    # Create executor
    executor = StepExecutor(config=StepConfig(
        timeout=10.0,
        auto_snapshot=True,
    ))

    # Execute step by step
    print("\nExecuting step by step...")
    for i in range(4):
        result = await executor.step(context)

        print(f"\nStep {i + 1}:")
        print(f"  Node: {result.node_id}")
        print(f"  Status: {result.status.value}")
        print(f"  Payload: {result.payload}")

        if result.is_success():
            print(f"  [OK] Step succeeded")
        elif result.is_failed():
            print(f"  [ERROR] Step failed: {result.error}")
            break
        elif result.needs_input():
            print(f"  [INPUT] Step needs input: {result.payload}")
            break

        if context.is_complete():
            print(f"\n[COMPLETE] Execution finished successfully")
            break

    # Show final stats
    print(f"\nExecutor stats: {executor.get_stats()}")
    print(f"Context state: {context.to_dict()}")


# ============================================================================
# Example 2: Interrupt Handling
# ============================================================================

async def example_interrupts():
    """Demonstrate interrupt handling"""
    print("\n" + "=" * 60)
    print("Example 2: Interrupt Handling")
    print("=" * 60)

    # Create simple graph
    graph = create_graph("interrupt_example")
    node1 = create_tool_node("node1", tool_search, {"query": "test"})
    node2 = create_tool_node("node2", tool_process, {"data": "@node1.results"})

    graph.add_node(node1).add_node(node2)
    graph.connect("node1", "node2")

    # Create executor with interrupt queue
    interrupt_queue = InterruptQueue()
    executor = StepExecutor(
        config=StepConfig(check_interrupts=True),
        interrupt_queue=interrupt_queue
    )

    context = IELExecutionContext(graph=graph)

    # Simulate user interrupt during execution
    async def inject_interrupt():
        await asyncio.sleep(0.1)
        observation = ExternalObservation(
            source="user",
            content="Wait, I need to change the query",
        )
        await executor.interrupt_queue.put(observation)
        print("\n[INTERRUPT] User input injected")

    # Start interrupt injection in background
    asyncio.create_task(inject_interrupt())

    # Execute first step
    print("\nExecuting step 1 (will be interrupted)...")
    result = await executor.step(context)

    print(f"\nStep Result:")
    print(f"  Status: {result.status.value}")
    print(f"  Payload: {result.payload}")

    if result.needs_input():
        print(f"  [INTERRUPT] Execution halted for replanning")


# ============================================================================
# Example 3: Failure and Rollback
# ============================================================================

async def example_failure_rollback():
    """Demonstrate failure tracking and rollback"""
    print("\n" + "=" * 60)
    print("Example 3: Failure Tracking and Rollback")
    print("=" * 60)

    # Create graph with a failing node
    graph = create_graph("failure_example")

    async def failing_tool(msg: str) -> dict:
        """Tool that fails"""
        await asyncio.sleep(0.1)
        raise ValueError("Intentional failure for demo")

    node1 = create_tool_node("node1", tool_search, {"query": "test"})
    node2 = create_tool_node("node2", failing_tool, {"msg": "fail me"})

    graph.add_node(node1).add_node(node2)
    graph.connect("node1", "node2")

    executor = StepExecutor(
        config=StepConfig(
            continue_on_error=True,  # Continue to see failure counting
        )
    )

    context = IELExecutionContext(
        graph=graph,
        failure_threshold=3,  # Rollback after 3 failures
    )

    # Create snapshot before execution
    snapshot_id = context.create_snapshot(label="Initial state")
    print(f"\n[SNAPSHOT] Created: {snapshot_id}")

    # Execute and fail multiple times
    for i in range(3):
        result = await executor.step(context)

        if result.is_failed():
            print(f"\nStep {i + 1}: FAILED - {result.error}")
            print(f"  Failure count: {context.failure_counter.failures.get(result.node_id, 0)}")

            # Check if rollback triggered
            if context.should_rollback():
                print(f"\n[ROLLBACK] Threshold exceeded!")
                context.restore_snapshot(snapshot_id)
                print(f"  Restored snapshot: {snapshot_id}")
                break
        else:
            print(f"\nStep {i + 1}: SUCCESS")
            break


# ============================================================================
# Example 4: Auto-Snapshot
# ============================================================================

async def example_auto_snapshot():
    """Demonstrate automatic snapshot creation"""
    print("\n" + "=" * 60)
    print("Example 4: Auto-Snapshot Before High-Side-Effect Nodes")
    print("=" * 60)

    # Create graph with high-side-effect node
    graph = create_graph("auto_snapshot_example")

    node1 = create_tool_node("search", tool_search, {"query": "test"})
    node2 = create_tool_node("process", tool_process, {"data": "@search.results"})
    node3 = create_tool_node("save", tool_save, {"content": "@process.processed"})  # High-side-effect

    graph.add_node(node1).add_node(node2).add_node(node3)
    graph.connect("search", "process")
    graph.connect("process", "save")

    # Executor with auto-snapshot enabled
    executor = StepExecutor(config=StepConfig(auto_snapshot=True))
    context = IELExecutionContext(graph=graph)

    # Execute all steps
    results = await executor.run_to_completion(context)

    print(f"\nExecuted {len(results)} steps")

    # Check snapshots
    snapshot_count = len(context._snapshots)
    print(f"Auto-created snapshots: {snapshot_count}")

    if snapshot_count > 0:
        snapshot = context.get_latest_snapshot()
        print(f"Latest snapshot: {snapshot.snapshot_id}")
        print(f"  Label: {snapshot.metadata.get('label')}")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""
    await example_basic_execution()
    await example_interrupts()
    await example_failure_rollback()
    await example_auto_snapshot()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
