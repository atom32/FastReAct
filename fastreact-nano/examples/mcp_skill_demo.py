#!/usr/bin/env python3
"""
MCP-SKILL Integration Demo

Demonstrates the new MCP-SKILL integration features in FastReAct Nano v2.1.

Features demonstrated:
1. Skills declaring MCP dependencies
2. Automatic MCP server loading based on skills
3. Tool discovery and matching
4. Progressive tool disclosure
5. Backward compatibility

Usage:
    python mcp_skill_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import Agent
from fastreact.core.config import Config


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}\n")


async def demo_1_basic_usage():
    """Demo 1: Basic usage with MCP-SKILL integration"""
    print_section("Demo 1: Basic MCP-SKILL Integration")

    print("[INFO] Creating agent with MCP-SKILL integration...")

    # Create agent (will load MCP servers lazily when skills are used)
    agent = Agent()

    print("[INFO] Agent created (MCP servers not loaded yet)")

    # Query that triggers github_integration skill
    query = "How do I create a pull request on GitHub?"

    print(f"\n[QUERY] {query}")
    print("[INFO] Running agent with auto-selected skills...")

    try:
        result = await agent.run(query)

        print(f"\n[RESULT] {result}")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        # Cleanup
        await agent.close_mcp_servers()


async def demo_2_explicit_skills():
    """Demo 2: Explicit skill selection with MCP tool loading"""
    print_section("Demo 2: Explicit Skill Selection")

    print("[INFO] Creating agent...")

    agent = Agent()

    # Explicitly specify skills
    skills = ["github_integration"]

    print(f"[INFO] Using skills: {skills}")
    print("[INFO] This will trigger loading of github_mcp server")

    query = "Create a new file in my GitHub repository"

    print(f"\n[QUERY] {query}")

    try:
        result = await agent.run(query, skills=skills)

        print(f"\n[RESULT] {result}")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        await agent.close_mcp_servers()


async def demo_3_tool_discovery():
    """Demo 3: Tool discovery service"""
    print_section("Demo 3: MCP Tool Discovery Service")

    print("[INFO] Creating agent...")

    agent = Agent()

    # Load MCP servers for a specific skill
    skill_name = "github_integration"

    print(f"[INFO] Loading MCP servers for skill: {skill_name}")

    try:
        await agent._load_mcp_servers(required_skills=[skill_name])

        # Check loaded servers
        servers = agent._mcp_manager.list_servers()
        print(f"\n[OK] Loaded MCP servers: {servers}")

        # Check tool discovery
        tools = agent._mcp_discovery.get_tools_for_skill(skill_name)
        print(f"\n[OK] Tools for '{skill_name}' skill:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        # Generate tools section for prompt
        tools_section = agent._mcp_discovery.generate_skill_tools_section(skill_name)
        print(f"\n[OK] Generated tools section for prompt:\n{tools_section}")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        await agent.close_mcp_servers()


async def demo_4_backward_compatibility():
    """Demo 4: Backward compatibility (no skill association)"""
    print_section("Demo 4: Backward Compatibility")

    print("[INFO] Creating agent with old-style config...")
    print("[INFO] MCP servers without skill association load normally")

    agent = Agent()

    # All MCP servers load (backward compatible)
    try:
        await agent._load_mcp_servers()

        servers = agent._mcp_manager.list_servers()
        print(f"\n[OK] All MCP servers loaded: {servers}")

        tools = agent._mcp_manager.list_mcp_tools()
        print(f"[OK] Total MCP tools available: {len(tools)}")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        await agent.close_mcp_servers()


async def demo_5_multiple_skills():
    """Demo 5: Multiple skills with different MCP requirements"""
    print_section("Demo 5: Multiple Skills with Different MCP Requirements")

    print("[INFO] Creating agent...")

    agent = Agent()

    # Use multiple skills that require different MCP servers
    skills = ["git_workflow", "github_integration"]

    print(f"[INFO] Using skills: {skills}")
    print("[INFO] This will load both git_mcp and github_mcp servers")

    query = "Create a feature branch and push it to GitHub"

    print(f"\n[QUERY] {query}")

    try:
        result = await agent.run(query, skills=skills)

        print(f"\n[RESULT] {result}")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        await agent.close_mcp_servers()


async def demo_6_skill_metadata():
    """Demo 6: Skill metadata and MCP dependencies"""
    print_section("Demo 6: Skill Metadata and MCP Dependencies")

    print("[INFO] Loading skills...")

    agent = Agent()

    # Check skill metadata
    skill_name = "github_integration"
    skill = agent._skills.get(skill_name)

    if skill:
        print(f"\n[OK] Skill: {skill.name}")
        print(f"[OK] Description: {skill.description}")
        print(f"[OK] Tags: {skill.metadata.tags}")
        print(f"[OK] MCP Servers: {skill.metadata.mcp_servers}")
        print(f"[OK] Recommended Tools: {skill.metadata.recommended_tools}")

        # Generate system prompt with skills
        prompt = agent._build_system_prompt_with_skills([skill_name])

        print(f"\n[OK] System prompt includes MCP tool information")
        print(f"[INFO] Prompt length: {len(prompt)} characters")

    else:
        print(f"[ERROR] Skill '{skill_name}' not found")


async def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print(" FastReAct Nano v2.1 - MCP-SKILL Integration Demo")
    print("=" * 70)

    demos = [
        ("Basic Usage", demo_1_basic_usage),
        ("Explicit Skills", demo_2_explicit_skills),
        ("Tool Discovery", demo_3_tool_discovery),
        ("Backward Compatibility", demo_4_backward_compatibility),
        ("Multiple Skills", demo_5_multiple_skills),
        ("Skill Metadata", demo_6_skill_metadata),
    ]

    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")

    print("\nRunning all demos...\n")

    for name, demo_func in demos:
        try:
            await demo_func()
        except KeyboardInterrupt:
            print("\n[INFO] Demo interrupted by user")
            break
        except Exception as e:
            print(f"\n[ERROR] Demo '{name}' failed: {e}")
            import traceback
            traceback.print_exc()

        # Wait between demos
        await asyncio.sleep(0.5)

    print("\n" + "=" * 70)
    print(" Demo Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Demo interrupted")
