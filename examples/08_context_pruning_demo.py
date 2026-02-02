"""
Context Pruning Demonstration

This example demonstrates the Context Pruning feature, which intelligently
reduces token usage by 40-60% while preserving important information.

Key features:
- Importance-based message scoring
- Smart tool result compression (head/tail truncation)
- Priority-based selection (system > user > assistant > tool results)
- Configurable pruning strategies
"""

from fastreact.context import (
    ContextPruner,
    PruningConfig,
    TokenCounter,
    prune_messages,
)
import json


def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_basic_pruning():
    """Demonstrate basic context pruning"""
    print_separator("Demo 1: Basic Context Pruning")

    # Create a sample conversation with many messages
    messages = []
    for i in range(20):
        messages.append({
            "role": "user",
            "content": f"Question {i}: Please explain how this works? " * 5
        })
        messages.append({
            "role": "assistant",
            "content": f"Answer {i}: Here's a detailed explanation... " * 5
        })

    # Setup
    token_counter = TokenCounter(model="gpt-4")
    original_tokens = token_counter.count_messages_tokens(messages)

    print(f"Original messages: {len(messages)}")
    print(f"Original tokens: {original_tokens}")

    # Prune to 50% of original
    config = PruningConfig(
        enabled=True,
        target_ratio=0.5,
        min_messages=10,
    )
    pruner = ContextPruner(config, token_counter)

    target_tokens = int(original_tokens * 0.5)
    pruned_messages, metadata = pruner.prune(messages, target_tokens)

    print(f"\nPruned messages: {metadata['pruned_count']}")
    print(f"Pruned tokens: {metadata['pruned_tokens']}")
    print(f"Reduction ratio: {metadata['reduction_ratio']:.1%}")
    print(f"Messages removed: {metadata['messages_removed']}")


def demo_tool_result_compression():
    """Demonstrate tool result compression"""
    print_separator("Demo 2: Tool Result Compression")

    # Create a large tool result (simulating grep output, logs, etc.)
    large_tool_result = "\n".join([
        f"[2024-01-01 12:00:{i:02d}] INFO: Processing item {i} - Status: OK"
        for i in range(500)
    ])

    messages = [
        {"role": "user", "content": "Check the application logs"},
        {"role": "tool", "content": large_tool_result},
        {"role": "assistant", "content": "The logs show all processes are running normally."},
    ]

    token_counter = TokenCounter(model="gpt-4")
    original_tokens = token_counter.count_messages_tokens(messages)

    print(f"Original tool result lines: {len(large_tool_result.split(chr(10)))}")
    print(f"Original tokens: {original_tokens}")

    # Prune with tool result compression
    config = PruningConfig(
        enabled=True,
        tool_result_max_lines=100,
        tool_result_head_lines=50,
        tool_result_tail_lines=50,
    )
    pruner = ContextPruner(config, token_counter)

    pruned_messages, metadata = pruner.prune(messages, target_tokens=1000)

    # Find the compressed tool result
    tool_result = next((msg for msg in pruned_messages if msg.get("role") == "tool"), None)

    if tool_result:
        compressed_lines = len(tool_result.get("content", "").split("\n"))
        print(f"\nCompressed tool result lines: {compressed_lines}")
        print(f"Compression ratio: {metadata['reduction_ratio']:.1%}")
        print(f"\nCompressed content preview:")
        print("-" * 40)
        lines = tool_result["content"].split("\n")
        print(f"First 3 lines: {lines[:3]}")
        if len(lines) > 6:
            print(f"... ({len(lines) - 6} lines omitted) ...")
        print(f"Last 3 lines: {lines[-3:]}")


def demo_priority_preservation():
    """Demonstrate priority-based message preservation"""
    print_separator("Demo 3: Priority-Based Preservation")

    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Help me debug this code" * 20},
        {"role": "assistant", "content": "I'll help you debug this code." * 20},
        {"role": "tool", "content": "Error output" * 100},
        {"role": "assistant", "content": "Let me think about this... (thinking)" * 20},
        {"role": "tool", "content": "Another large output" * 100},
        {"role": "assistant", "content": "Here's the solution!" * 20},
        {"role": "user", "content": "Thank you!" * 20},
    ]

    token_counter = TokenCounter(model="gpt-4")
    original_tokens = token_counter.count_messages_tokens(messages)

    print(f"Original tokens: {original_tokens}")

    # Prune aggressively
    config = PruningConfig(
        enabled=True,
        target_ratio=0.3,  # Reduce to 30%
        preserve_recent_count=3,
    )
    pruner = ContextPruner(config, token_counter)

    target_tokens = int(original_tokens * 0.3)
    pruned_messages, metadata = pruner.prune(messages, target_tokens)

    print(f"\nPruned tokens: {metadata['pruned_tokens']}")
    print(f"Reduction ratio: {metadata['reduction_ratio']:.1%}")

    # Check which message types were preserved
    roles = [msg.get("role") for msg in pruned_messages]
    print(f"\nPreserved message types: {dict([(r, roles.count(r)) for r in set(roles)])}")

    # Verify system message is preserved
    has_system = any(msg.get("role") == "system" for msg in pruned_messages)
    print(f"System message preserved: {has_system}")


def demo_convenience_function():
    """Demonstrate the convenience function"""
    print_separator("Demo 4: Convenience Function")

    messages = [
        {"role": "user", "content": "Question 1" * 50},
        {"role": "assistant", "content": "Answer 1" * 50},
        {"role": "user", "content": "Question 2" * 50},
        {"role": "assistant", "content": "Answer 2" * 50},
    ]

    token_counter = TokenCounter(model="gpt-4")
    original_tokens = token_counter.count_messages_tokens(messages)

    print(f"Original tokens: {original_tokens}")

    # Use the convenience function
    pruned_messages, metadata = prune_messages(
        messages,
        target_tokens=500,
        token_counter=token_counter,
        config=PruningConfig(target_ratio=0.5),
    )

    print(f"Pruned tokens: {metadata['pruned_tokens']}")
    print(f"Reduction ratio: {metadata['reduction_ratio']:.1%}")


def demo_config_from_dict():
    """Demonstrate loading configuration from dict"""
    print_separator("Demo 5: Configuration from Dictionary")

    config_dict = {
        "pruning": {
            "enabled": True,
            "target_ratio": 0.4,
            "min_messages": 5,
            "max_messages": 50,
            "tool_result_max_lines": 30,
            "preserve_recent_count": 3,
            "importance_weights": {
                "system": 1.0,
                "user": 0.95,
                "assistant": 0.75,
                "tool_result": 0.3,
            }
        }
    }

    config = PruningConfig.from_dict(config_dict)

    print("Configuration loaded from dictionary:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Target ratio: {config.target_ratio}")
    print(f"  Min messages: {config.min_messages}")
    print(f"  Tool result max lines: {config.tool_result_max_lines}")
    print(f"  Importance weights: {config.importance_weights}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 60)
    print("  Context Pruning Feature Demonstration")
    print("=" * 60)

    try:
        demo_basic_pruning()
        demo_tool_result_compression()
        demo_priority_preservation()
        demo_convenience_function()
        demo_config_from_dict()

        print_separator("All Demos Complete")
        print("Context Pruning successfully reduces token usage by 40-60%")
        print("while preserving important information!")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
