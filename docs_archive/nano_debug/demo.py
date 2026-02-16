#!/usr/bin/env python
"""
FastReAct Nano - Simple demo

This script demonstrates basic usage of FastReAct Nano.
"""

import asyncio
from pathlib import Path

# Add src to path for development
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import (
    LiteLLMProvider,
    ToolRegistry,
    ReActCore,
    ContextManager,
    FileContextStore,
    EchoTool,
    AddTool,
)


async def demo_basic():
    """Basic demo without channels"""
    print("=" * 60)
    print("FastReAct Nano - Basic Demo")
    print("=" * 60)

    # Setup LLM (requires ANTHROPIC_API_KEY or OPENAI_API_KEY)
    print("\n[INFO] Initializing LLM provider...")
    llm = LiteLLMProvider()

    # Setup tools
    print("[INFO] Setting up tools...")
    tools = ToolRegistry()
    tools.register(EchoTool())
    tools.register(AddTool())
    print(f"[INFO] Registered tools: {tools.list_all()}")

    # Create ReAct core
    print("[INFO] Creating ReAct core...")
    agent = ReActCore(llm=llm, tools=tools, max_iterations=10)

    # Setup context manager
    print("[INFO] Setting up context manager...")
    sessions_dir = Path.cwd() / "data" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    store = FileContextStore(sessions_dir)
    context_mgr = ContextManager(store=store)

    # Add event handler for visibility
    print("[INFO] Setting up event handler...")
    def on_event(event):
        phase = event.phase.value
        if phase == "think":
            print(f"[Think] Iteration {event.iteration}")
        elif phase == "action":
            print(f"[Action] Calling tool: {event.tool_call.name}")
        elif phase == "observe":
            print(f"[Observe] Result: {event.content[:50]}...")
        elif phase == "error":
            print(f"[ERROR] {event.error}")

    agent.on_event(on_event)

    # Test questions
    questions = [
        "Echo 'Hello FastReAct Nano!'",
        "What is 123 + 456?",
    ]

    for i, question in enumerate(questions, 1):
        print("\n" + "=" * 60)
        print(f"Question {i}: {question}")
        print("=" * 60)

        # Build messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ]

        # Run agent
        try:
            response = await agent.run(messages)
            print(f"\n[Response] {response}")
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


async def demo_with_events():
    """Demo with detailed event tracking"""
    print("\n" + "=" * 60)
    print("FastReAct Nano - Event Tracking Demo")
    print("=" * 60)

    # Setup
    llm = LiteLLMProvider()
    tools = ToolRegistry()
    tools.register(EchoTool())
    agent = ReActCore(llm=llm, tools=tools)

    # Track all events
    events = []

    def track_event(event):
        events.append({
            "phase": event.phase.value,
            "iteration": event.iteration,
            "content": event.content,
            "tool": event.tool_call.name if event.tool_call else None,
            "error": event.error,
        })

    agent.on_event(track_event)

    # Run
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Echo 'Event Tracking'"},
    ]

    print("\n[INFO] Running agent with event tracking...")
    response = await agent.run(messages)

    # Print event log
    print("\n[Event Log]")
    for i, event in enumerate(events, 1):
        print(f"{i}. Phase: {event['phase']:8} | Iteration: {event['iteration']}", end="")
        if event['tool']:
            print(f" | Tool: {event['tool']}", end="")
        if event['content']:
            content = event['content'][:40]
            print(f" | Content: {content}...", end="")
        if event['error']:
            print(f" | Error: {event['error']}", end="")
        print()

    print(f"\n[Final Response] {response}")
    print("\n[INFO] Total events: {len(events)}")


async def main():
    """Main demo entry point"""
    try:
        await demo_basic()
        await demo_with_events()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for API key
    import os
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("[ERROR] Missing API key!")
        print("\nPlease set either:")
        print("  - ANTHROPIC_API_KEY (for Claude)")
        print("  - OPENAI_API_KEY (for GPT-4)")
        print("\nExample:")
        print("  export ANTHROPIC_API_KEY=sk-xxx")
        print("  python demo.py")
        sys.exit(1)

    asyncio.run(main())
