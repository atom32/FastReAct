#!/usr/bin/env python
"""
FastReAct Nano v2.0 - Complete Agent Demo

Demonstrates the fully integrated autonomous agent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import Agent, ask_sync


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_quick_query():
    """Demonstrate quick synchronous query"""
    print_separator("Demo 1: Quick Query")

    # Simple synchronous query
    response = ask_sync("What is 2+2?")

    print(f"Query: What is 2+2?")
    print(f"Response: {response}")


async def demo_async_query():
    """Demonstrate async query"""
    print_separator("Demo 2: Async Query")

    agent = Agent()

    # List available capabilities
    print(f"[INFO] Available tools: {agent.list_tools()}")
    print(f"[INFO] Available skills: {agent.list_skills()}")

    # Run query
    response = await agent.run(
        "Explain what you can do"
    )

    print(f"\n[Agent Response]\n{response}")


async def demo_with_skills():
    """Demonstrate using specific skills"""
    print_separator("Demo 3: Query with Skills")

    agent = Agent()

    # Use git_workflow skill
    response = await agent.run(
        "How do I create a new branch?",
        skills=["git_workflow"]
    )

    print(f"\n[Agent Response]\n{response}")


def demo_configuration():
    """Demonstrate configuration"""
    print_separator("Demo 4: Configuration")

    from fastreact import Config

    # Load from environment
    config = Config.from_env()

    print(f"[INFO] LLM Model: {config.llm.model}")
    print(f"[INFO] Max Tokens: {config.llm.max_tokens}")
    print(f"[INFO] Max Iterations: {config.react.max_iterations}")
    print(f"[INFO] Enable Steering: {config.react.enable_steering}")
    print(f"[INFO] Enable Follow-up: {config.react.enable_followup}")


async def main():
    """Run all demos"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                            ║
║      FastReAct Nano v2.0 - Complete Agent Demo           ║
║                                                            ║
║  Fully autonomous agent with integrated:                  ║
║  - ReActCore (dual-layer loop)                            ║
║  - Skills (progressive disclosure)                        ║
║  - Tools (4 core tools)                                   ║
║  - Config (environment-based)                             ║
║                                                            ║
╚════════════════════════════════════════════════════════════════╝
    """)

    try:
        # Demo 1: Quick sync query
        demo_quick_query()

        # Demo 2: Async query
        await demo_async_query()

        # Demo 3: With skills
        await demo_with_skills()

        # Demo 4: Configuration
        demo_configuration()

        print("\n" + "=" * 60)
        print("  [SUCCESS] All agent demos completed!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
