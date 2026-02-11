"""
Test the new unified event stream API

This demonstrates:
1. AgentEvent protocol
2. run_event_stream API
3. Event consumption patterns
"""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import Agent, EventType, Config


def _load_config():
    """
    Load config from standard locations

    Tries multiple standard config locations in order:
    1. ~/.fastreact/config.json (user home)
    2. ./.fastreact/config.json (current directory)
    3. config.json (current directory)
    4. Environment variables (fallback)
    """
    from pathlib import Path as LibPath

    # Standard config locations
    config_locations = [
        LibPath.home() / ".fastreact" / "config.json",
        LibPath.cwd() / ".fastreact" / "config.json",
        LibPath.cwd() / "config.json",
    ]

    # Try each location
    for config_path in config_locations:
        if config_path.exists():
            return Config.load(config_path)

    # Fallback to environment
    return Config.from_env()


async def test_event_stream():
    """Test the new event stream API"""

    print("=" * 60)
    print("  FastReAct Nano v2.0 - Event Stream Test")
    print("=" * 60)

    # Load config from standard locations
    config = _load_config()

    # Create agent
    print("\n[INIT] Creating Agent...")
    agent = Agent(config=config)

    # Test query
    query = "What is 2+2?"

    print(f"\n[QUERY] {query}")
    print("\n[RUN] Starting event stream...\n")

    # Track events
    event_counts = {}
    final_answer = None

    try:
        async for event in agent.run_event_stream(query):
            # Count event types
            event_counts[event.type] = event_counts.get(event.type, 0) + 1

            # Display events
            if event.type == EventType.SESSION_START:
                print(f"[{event.type.value.upper()}] Session: {event.session_id}")
                print(f"         Query: {event.content}")

            elif event.type == EventType.THINK:
                # Show thinking (truncate if long)
                content = event.content[:100] + "..." if len(event.content) > 100 else event.content
                print(f"[{event.type.value.upper()}] {content}")

            elif event.type == EventType.TOOL_CALL:
                args = event.tool_args or {}
                print(f"[{event.type.value.upper()}] {event.tool_name}({args})")

            elif event.type == EventType.TOOL_RESULT:
                result = event.content[:100] + "..." if len(event.content) > 100 else event.content
                print(f"[{event.type.value.upper()}] {event.tool_name} -> {result}")

            elif event.type == EventType.ERROR:
                print(f"[{event.type.value.upper()}] {event.content}")

            elif event.type == EventType.SESSION_END:
                final_answer = event.content
                print(f"\n[{event.type.value.upper()}] Session complete")
                print(f"\n[ANSWER] {final_answer}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print("\n" + "=" * 60)
    print("  Event Summary")
    print("=" * 60)

    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type.value}: {count}")

    print(f"\n  Total events: {sum(event_counts.values())}")

    print("\n" + "=" * 60)
    print("  [SUCCESS] Event stream test passed!")
    print("=" * 60)


async def test_with_tools():
    """Test event stream with actual tool usage"""

    print("\n\n" + "=" * 60)
    print("  Test 2: Tool Usage")
    print("=" * 60)

    config = _load_config()
    agent = Agent(config=config)
    query = "List files in the current directory"

    print(f"\n[QUERY] {query}")
    print("\n[RUN] Starting event stream...\n")

    async for event in agent.run_event_stream(query):
        if event.type == EventType.THINK:
            print(f"[THINK] {event.content[:80]}...")

        elif event.type == EventType.TOOL_CALL:
            print(f"\n[TOOL_CALL] {event.tool_name}")
            print(f"           Args: {event.tool_args}")

        elif event.type == EventType.TOOL_RESULT:
            # Show first few lines
            lines = event.content.split("\n")[:5]
            preview = "\n".join(lines)
            print(f"[TOOL_RESULT] {preview}...")

        elif event.type == EventType.SESSION_END:
            print(f"\n[DONE] {event.content[:100]}...")

    print("\n[SUCCESS] Tool usage test passed!")


async def main():
    """Run all tests"""
    await test_event_stream()
    await test_with_tools()


if __name__ == "__main__":
    asyncio.run(main())
