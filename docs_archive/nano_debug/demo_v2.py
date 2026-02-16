#!/usr/bin/env python
"""
FastReAct Nano v2.0 Demo - Dual-layer loop demonstration

Demonstrates:
1. Dual-layer loop architecture
2. Steering messages (real-time intervention)
3. Follow-up messages (async task continuation)
"""

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import (
    LiteLLMProvider,
    ToolRegistry,
    EchoTool,
    AddTool,
)
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.callbacks import (
    FileSteeringCallback,
    QueueFollowUpCallback,
    CallbackManager,
)
from fastreact.core.react import ReActCore, Phase


def print_separator(title: str):
    """Print a section separator"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_message_types():
    """Demonstrate new message types"""
    print_separator("Demo 1: Message Types (v2.0)")

    # Standard messages
    user_msg = Message.user("What is 2+2?")
    print(f"[User] {user_msg.content}")

    assistant_msg = Message.assistant("2+2 equals 4")
    print(f"[Assistant] {assistant_msg.content}")

    tool_msg = Message.tool("add", "Result: 5", "call_123")
    print(f"[Tool] {tool_msg.content}")

    # v2.0 specific messages
    steering_msg = Message.steering("Stop processing, answer directly")
    print(f"[Steering] {steering_msg.content}")

    followup_msg = Message.followup("Background task completed")
    print(f"[Follow-up] {followup_msg.content}")

    print("\n[OK] All message types demonstrated")


def demo_message_queue():
    """Demonstrate message queue for pending messages"""
    print_separator("Demo 2: Message Queue")

    queue = MessageQueue()

    # Add pending messages
    queue.push(Message.steering("First intervention"))
    queue.push(Message.steering("Second intervention"))

    print(f"[INFO] Added 2 steering messages to queue")

    # Peek without draining
    peeked = queue.peek()
    print(f"[INFO] Peek: {len(peeked)} messages waiting")

    # Drain the queue
    drained = queue.drain()
    print(f"[INFO] Drained {len(drained)} messages")
    for msg in drained:
        print(f"  - {msg.role}: {msg.content}")

    print(f"[OK] Queue is now empty: {len(queue)} messages")


async def demo_steering_callback():
    """Demonstrate steering callback"""
    print_separator("Demo 3: Steering Callback")

    # Create temporary steering file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
        steering_file = Path(f.name)
        # Write steering messages
        f.write('{"content": "Stop and explain what you did"}\n')
        f.write('{"content": "Try a different approach"}\n')

    print(f"[INFO] Created steering file: {steering_file.name}")

    # Create callback
    callback = FileSteeringCallback(steering_file)

    # Get steering messages
    messages = await callback.get_steering_messages()

    if messages:
        print(f"[INFO] Retrieved {len(messages)} steering messages:")
        for msg in messages:
            print(f"  - {msg.content}")

        # File should be cleared after reading
        print(f"[INFO] Steering file should be cleared")
    else:
        print("[INFO] No steering messages found")

    # Cleanup
    try:
        steering_file.unlink()
    except Exception:
        pass

    print("[OK] Steering callback demonstrated")


async def demo_followup_callback():
    """Demonstrate follow-up callback"""
    print_separator("Demo 4: Follow-up Callback")

    callback = QueueFollowUpCallback()

    # Schedule delayed follow-ups
    await callback.schedule_followup(
        delay=0.5,
        message=Message.followup("Search completed"),
    )
    print("[INFO] Scheduled follow-up message in 0.5s")

    await callback.schedule_followup(
        delay=1.0,
        message=Message.followup("File analysis ready"),
    )
    print("[INFO] Scheduled second follow-up message in 1.0s")

    # Wait for messages
    print("[INFO] Waiting for follow-up messages...")
    await asyncio.sleep(1.5)

    # Check for messages
    messages = await callback.get_followup_messages()

    if messages:
        print(f"[INFO] Received {len(messages)} follow-up messages:")
        for msg in messages:
            print(f"  - {msg.content}")

    print("[OK] Follow-up callback demonstrated")


async def demo_dual_layer_loop():
    """Demonstrate dual-layer loop"""
    print_separator("Demo 5: Dual-Layer Loop Concept")

    print("""
Dual-layer loop architecture (Moltbot style):

    Outer loop (Process follow-up queue):
        while True:
            Inner loop (Process tools + steering):
                while has_more_tool_calls OR pending_messages:
                    1. Process pending messages
                    2. Call LLM
                    3. Execute tools
                    4. Check steering messages

            Check follow-up messages:
                If follow-ups arrive:
                    Add to pending
                    Continue outer loop
                Else:
                    Break outer loop

This enables:
    - Real-time intervention (steering)
    - Async task continuation (follow-up)
    - Complex agent workflows
    """)

    print("[OK] Dual-layer loop concept explained")


def demo_callback_manager():
    """Demonstrate callback manager"""
    print_separator("Demo 6: Callback Manager")

    # Create callback manager
    steering = FileSteeringCallback(Path.cwd() / ".steering.jsonl")
    followup = QueueFollowUpCallback()
    manager = CallbackManager(steering_callback=steering, followup_callback=followup)

    print(f"[INFO] CallbackManager created")
    print(f"[INFO] Has steering: {manager.has_steering}")
    print(f"[INFO] Has follow-up: {manager.has_followup}")

    print("[OK] Callback manager demonstrated")


async def main():
    """Run all demos"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                            ║
║        FastReAct Nano v2.0 - Dual-Layer Loop Demo        ║
║                                                            ║
╚════════════════════════════════════════════════════════════════╝

New v2.0 Features:
- Dual-layer loop (Moltbot style)
- Steering messages (real-time intervention)
- Follow-up messages (async task continuation)
- Message types extension
- Callback system
    """)

    try:
        demo_message_types()
        demo_message_queue()
        await demo_steering_callback()
        await demo_followup_callback()
        demo_dual_layer_loop()
        demo_callback_manager()

        print("\n" + "=" * 60)
        print("  [SUCCESS] All v2.0 demos completed!")
        print("=" * 60)

        return 0

    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
