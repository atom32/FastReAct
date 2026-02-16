"""
IEL Loop Example - Complete Interactive Execution Loop demonstration

Shows:
- Full IEL loop with reflection and replanning
- Failure analysis (retry vs replan)
- User interrupt handling
- Dynamic graph patching
"""

import asyncio
import logging
from datetime import datetime

# Mock LLM client for demonstration
class MockLLMClient:
    """Mock LLM client for testing without API calls"""

    def __init__(self):
        self.model = "gpt-4-mock"

    class Chat:
        class Completions:
            async def create(self, model, messages, temperature=0.7, max_tokens=1000):
                # Simulate LLM response delay
                await asyncio.sleep(0.1)

                # Analyze user message to determine response
                user_msg = messages[-1]["content"].lower()

                # Failure analysis responses
                if "analyze this execution failure" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "transient",
  "root_cause": "Network timeout - temporary connectivity issue",
  "recovery_strategy": "retry",
  "suggested_fix": null,
  "confidence": 0.9
}
```""")

                elif "file not found" in user_msg or "no such file" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "environment",
  "root_cause": "Required file does not exist",
  "recovery_strategy": "replan",
  "suggested_fix": "Add node to create file before reading it",
  "confidence": 0.95
}
```(""")

                elif "permission denied" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "environment",
  "root_cause": "Insufficient permissions to access resource",
  "recovery_strategy": "replan",
  "suggested_fix": "Add node to fix permissions before access",
  "confidence": 0.85
}
```(""")

                # User feedback responses
                elif "user has provided feedback" in user_msg:
                    if "change" in user_msg or "modify" in user_msg:
                        return MockResponse("""```json
{
  "operation": "replace_node",
  "reason": "User requested modification",
  "instructions": {
    "node_id": "process",
    "tool_name": "alternative_tool",
    "inputs": {"param": "new_value"}
  }
}
```(""")
                    else:
                        return MockResponse("""```json
{
  "operation": "add_node",
  "reason": "User requested additional step",
  "instructions": {
    "node_id": "validate_output",
    "tool_name": "validator",
    "inputs": {"data": "@process.result"},
    "dependencies": ["process"]
  }
}
```(""")

                # Default response
                return MockResponse("""```json
{
  "operation": "retry",
  "reason": "Continue execution",
  "instructions": {}
}
```(""")

        completions = Completions()

    chat = Chat()


class MockResponse:
    """Mock LLM response"""

    def __init__(self, content):
        self.choices = [MockChoice(content)]


class MockChoice:
    """Mock LLM choice"""

    def __init__(self, content):
        self.message = MockMessage(content)


class MockMessage:
    """Mock LLM message"""

    def __init__(self, content):
        self.content = content


# ============================================================================
# Example Tools
# ============================================================================

async def search_tool(query: str) -> dict:
    """Mock search tool"""
    print(f"  [TOOL] Searching: {query}")
    await asyncio.sleep(0.2)
    return {"results": f"Search results for: {query}"}


async def process_tool(data: str) -> dict:
    """Mock processing tool"""
    print(f"  [TOOL] Processing: {data}")
    await asyncio.sleep(0.2)
    return {"processed": f"Processed: {data}"}


async def save_tool(content: str, path: str = "/tmp/output.txt") -> dict:
    """Mock save tool"""
    print(f"  [TOOL] Saving to {path}")
    await asyncio.sleep(0.2)
    return {"saved": True, "path": path}


async def unreliable_tool(attempt: str = "1") -> dict:
    """Tool that fails first time, succeeds second (transient error)"""
    print(f"  [TOOL] Unstable operation (attempt {attempt})")
    await asyncio.sleep(0.1)

    # Fail on first attempt
    if attempt == "1":
        raise Exception("Network timeout - temporary connectivity issue")

    return {"result": "Success after retry"}


async def file_reader(path: str) -> dict:
    """Tool that fails if file doesn't exist"""
    print(f"  [TOOL] Reading file: {path}")
    await asyncio.sleep(0.1)

    if "nonexistent" in path.lower():
        raise FileNotFoundError(f"File not found: {path}")

    return {"content": f"Contents of {path}"}


# ============================================================================
# Examples
# ============================================================================

async def example_1_transient_error_retry():
    """
    Example 1: Transient error -> Automatic retry

    Demonstrates:
    - Failure detection
    - Reflection analysis (transient vs logic error)
    - Automatic retry without graph modification
    """
    print("\n" + "=" * 70)
    print("Example 1: Transient Error with Automatic Retry")
    print("=" * 70)

    from fastreact.graph import (
        create_graph,
        create_tool_node,
        IELExecutionContext,
        StepConfig,
        InterruptQueue,
        Replanner,
        IELLoop,
        IELLoopConfig,
        run_iel_loop,
    )

    # Create graph with unreliable node
    graph = create_graph("retry_example")
    node1 = create_tool_node("unstable", unreliable_tool, {"attempt": "1"})

    graph.add_node(node1)

    # Setup IEL components
    llm_client = MockLLMClient()
    tool_registry = {"search": search_tool, "process": process_tool, "unstable": unreliable_tool}

    context = IELExecutionContext(graph=graph)

    # Run IEL loop
    result = await run_iel_loop(
        context=context,
        llm_client=llm_client,
        tool_registry=tool_registry,
    )

    print(f"\nFinal result: {result.status.value}")
    print(f"Total steps in history: {len(context.history)}")

    # Show reflection happened
    for i, step in enumerate(context.history, 1):
        print(f"  Step {i}: {step.node_id} -> {step.status.value}")


async def example_2_file_not_found_replan():
    """
    Example 2: File not found -> Dynamic replan

    Demonstrates:
    - Environment error detection
    - Replanning with graph modification
    - Insert fix node before failed node
    """
    print("\n" + "=" * 70)
    print("Example 2: File Not Found - Dynamic Replan")
    print("=" * 70)

    from fastreact.graph import (
        create_graph,
        create_tool_node,
        IELExecutionContext,
        run_iel_loop,
    )

    # Create graph that tries to read non-existent file
    graph = create_graph("file_example")
    node1 = create_tool_node("read_file", file_reader, {"path": "/tmp/nonexistent.txt"})

    graph.add_node(node1)

    # Setup
    llm_client = MockLLMClient()
    tool_registry = {"read_file": file_reader}

    context = IELExecutionContext(graph=graph)

    # Run loop (will trigger replan)
    result = await run_iel_loop(
        context=context,
        llm_client=llm_client,
        tool_registry=tool_registry,
    )

    print(f"\nFinal result: {result.status.value}")
    print(f"Patches applied: {len(context.metadata.get('patches_applied', []))}")


async def example_3_user_interrupt():
    """
    Example 3: User interrupt -> Replan from feedback

    Demonstrates:
    - User interrupt during execution
    - Dynamic replanning based on user input
    - Graph modification
    """
    print("\n" + "=" * 70)
    print("Example 3: User Interrupt and Replan")
    print("=" * 70)

    from fastreact.graph import (
        create_graph,
        create_tool_node,
        IELExecutionContext,
        InterruptQueue,
        ExternalObservation,
        StepExecutor,
        StepConfig,
        Replanner,
        IELLoop,
    )

    # Create multi-step graph
    graph = create_graph("user_interrupt_example")
    node1 = create_tool_node("search", search_tool, {"query": "AI trends"})
    node2 = create_tool_node("process", process_tool, {"data": "@search.results"})
    node3 = create_tool_node("save", save_tool, {"content": "@process.processed"})

    graph.add_node(node1).add_node(node2).add_node(node3)
    graph.connect("search", "process")
    graph.connect("process", "save")

    # Setup
    interrupt_queue = InterruptQueue()

    executor = StepExecutor(
        config=StepConfig(check_interrupts=True),
        interrupt_queue=interrupt_queue,
    )

    llm_client = MockLLMClient()
    tool_registry = {
        "search": search_tool,
        "process": process_tool,
        "save": save_tool,
    }

    replanner = Replanner(
        llm_client=llm_client,
        tool_registry=tool_registry,
    )

    context = IELExecutionContext(graph=graph)
    loop = IELLoop(executor, replanner)

    # Inject user interrupt after first step
    async def inject_user_feedback():
        await asyncio.sleep(0.3)  # Wait for first step
        print("\n  [USER] Injecting interrupt: 'Change the search query'")
        observation = ExternalObservation(
            source="user",
            content="Change the search query to 'machine learning trends'",
        )
        await interrupt_queue.put(observation)

    # Start interrupt injection in background
    asyncio.create_task(inject_user_feedback())

    # Run loop
    result = await loop.run(context)

    print(f"\nFinal result: {result.status.value}")
    print(f"User observations processed: {len(context.observations)}")
    print(f"Replans triggered: {loop._replan_count}")


async def example_4_complete_pipeline():
    """
    Example 4: Complete pipeline with mixed scenarios

    Demonstrates:
    - Multiple steps
    - Mixed success/failure/retry scenarios
    - Full IEL loop capabilities
    """
    print("\n" + "=" * 70)
    print("Example 4: Complete Pipeline with Mixed Scenarios")
    print("=" * 70)

    from fastreact.graph import (
        create_graph,
        create_tool_node,
        IELExecutionContext,
        run_iel_loop,
    )

    # Create realistic pipeline
    graph = create_graph("complete_pipeline")

    node1 = create_tool_node("search", search_tool, {"query": "AI research"})
    node2 = create_tool_node("process", process_tool, {"data": "@search.results"})
    node3 = create_tool_node("validate", unreliable_tool, {"attempt": "1"})  # Will fail then retry
    node4 = create_tool_node("save", save_tool, {"content": "@process.processed"})

    graph.add_node(node1).add_node(node2).add_node(node3).add_node(node4)
    graph.connect("search", "process")
    graph.connect("process", "validate")
    graph.connect("validate", "save")

    # Setup
    llm_client = MockLLMClient()
    tool_registry = {
        "search": search_tool,
        "process": process_tool,
        "validate": unreliable_tool,
        "save": save_tool,
    }

    context = IELExecutionContext(
        graph=graph,
        failure_threshold=3,
    )

    # Run complete loop
    result = await run_iel_loop(
        context=context,
        llm_client=llm_client,
        tool_registry=tool_registry,
    )

    print(f"\n{'=' * 70}")
    print("EXECUTION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Final status: {result.status.value}")
    print(f"Total steps: {len(context.history)}")
    print(f"Nodes completed: {len(context.get_completed_nodes())}")
    print(f"Nodes failed: {len(context.get_failed_nodes())}")
    print(f"Nodes pending: {len(context.get_pending_nodes())}")
    print(f"Snapshots created: {len(context._snapshots)}")
    print(f"Patches applied: {len(context.metadata.get('patches_applied', []))}")

    print(f"\nExecution History:")
    for i, step in enumerate(context.history, 1):
        status_symbol = "[OK]" if step.is_success() else "[FAIL]" if step.is_failed() else "[INPUT]"
        print(f"  {i}. {status_symbol} {step.node_id}: {step.status.value}")
        if step.error:
            print(f"     Error: {step.error}")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""
    await example_1_transient_error_retry()
    await example_2_file_not_found_replan()
    await example_3_user_interrupt()
    await example_4_complete_pipeline()

    print("\n" + "=" * 70)
    print("All IEL loop examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'  # Simpler format for examples
    )

    asyncio.run(main())
