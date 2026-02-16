"""
Demo: ContextMonitor in Action

Shows how the Token Guard prevents token explosion in real scenarios.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import Agent, ContextMonitor


def demo_explosive_command():
    """Demo 1: Explosive command output"""
    print("=" * 70)
    print("  Demo 1: What happens with 'find /' without Token Guard")
    print("=" * 70)

    print("\n[SCENARIO]")
    print("  User: 'Find all Python files in /usr'")
    print("  Agent: exec('find /usr -name \"*.py\"')")
    print("  Result: 50,000 lines of file paths (~5MB text)")

    print("\n[WITHOUT Token Guard]")
    print("  - LLM receives: 50,000 lines (~1.25M tokens)")
    print("  - Context window: [EXPLODED]")
    print("  - Cost: $$$$$ (huge token bill)")
    print("  - Latency: High (processing 1.25M tokens)")

    print("\n[WITH Token Guard]")
    monitor = ContextMonitor(max_tool_output_chars=5000)

    # Simulate explosive output
    explosive_output = "\n".join([f"/path/to/file{i}.py" for i in range(50000)])

    # Apply truncation
    safe_output = monitor.truncate_tool_output(explosive_output, "exec")

    print(f"  - Original output: {len(explosive_output):,} chars")
    print(f"  - Truncated output: {len(safe_output):,} chars")
    print(f"  - Tokens saved: ~{(len(explosive_output) - len(safe_output)) // 4:,} tokens")
    print(f"  - LLM receives: Truncated result with context notice")
    print(f"  - Cost: $$ (reasonable)")
    print(f"  - Latency: Low")

    print("\n[Truncation Preview]")
    lines = safe_output.split("\n")
    print(f"  First 3 lines:")
    for line in lines[:3]:
        print(f"    {line}")

    if "[System: Tool output truncated]" in safe_output:
        idx = safe_output.index("[System:")
        print(f"\n  Truncation message:")
        for line in safe_output[idx:].split("\n")[:5]:
            print(f"    {line}")


def demo_config_options():
    """Demo 2: Configuration options"""
    print("\n\n" + "=" * 70)
    print("  Demo 2: Configuration Options")
    print("=" * 70)

    print("\n[Default Configuration]")
    print("  max_tool_output_chars: 5000")
    print("  max_context_tokens: 128000")
    print("  context_warning_threshold: 0.8 (80%)")

    print("\n[Environment Variables]")
    print("  export FASTRACT_MAX_TOOL_OUTPUT_CHARS=10000  # Larger outputs")
    print("  export FASTRACT_MAX_CONTEXT_TOKENS=8000       # Smaller models")
    print("  export FASTRACT_CONTEXT_WARNING_THRESHOLD=0.9  # Later warning")

    print("\n[Programmatic Configuration]")
    print("""
    from fastreact import Agent, Config

    # For models with smaller context windows
    config = Config()
    config.react.max_context_tokens = 16000  # GPT-3.5
    config.react.max_tool_output_chars = 3000

    agent = Agent(config=config)
    """)


def demo_statistics():
    """Demo 3: Usage statistics"""
    print("\n\n" + "=" * 70)
    print("  Demo 3: Monitoring and Statistics")
    print("=" * 70)

    monitor = ContextMonitor(max_tool_output_chars=5000, max_tokens=10000)

    print("\n[Simulating Agent Activity]")

    # Simulate some tool outputs
    outputs = [
        ("Small file", "A" * 100),
        ("Medium file", "B" * 3000),
        ("Huge log", "C" * 50000),  # Will be truncated
        ("Normal output", "D" * 2000),
        ("Another huge", "E" * 60000),  # Will be truncated
    ]

    for name, output in outputs:
        monitor.truncate_tool_output(output, "exec")

    stats = monitor.get_stats()

    print(f"\n[Statistics]")
    print(f"  Total tool outputs processed: 5")
    print(f"  Truncated outputs: {stats['truncated_count']}")
    print(f"  Last truncated tool: {stats['last_truncated']}")
    print(f"  Token usage ratio: {stats['usage_ratio']:.2%}")

    print(f"\n[Progress Bar]")
    print(f"  {monitor.get_progress_bar()}")


def demo_real_world_scenario():
    """Demo 4: Real-world scenario"""
    print("\n\n" + "=" * 70)
    print("  Demo 4: Real-World Scenario")
    print("=" * 70)

    print("""
[SCENARIO: Analyzing Web Server Logs]

User: "Analyze access.log to find 404 errors"

Agent execution:
  1. exec('cat access.log')           # 100,000 lines
     -> WITHOUT guard: 25M chars (6.25M tokens) - EXPLOSION
     -> WITH guard: 5,000 chars (1.25K tokens) - SAFE

  2. LLM sees: [System: Tool output truncated]
     "Use filtering commands (head, tail, grep) to view specific parts"

  3. Agent intelligently retries:
     exec('grep \" 404 \" access.log | head -20')
     -> Returns 20 lines - PERFECT

[Result]
  - WITHOUT guard: $$$$ + slow + possible crash
  - WITH guard: $$ + fast + intelligent retry
    """)


def main():
    """Run all demos"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║        FastReAct Nano - Token Guard Demo                      ║
║                                                                ║
║  See how ContextMonitor prevents token explosion              ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝
    """)

    demo_explosive_command()
    demo_config_options()
    demo_statistics()
    demo_real_world_scenario()

    print("\n" + "=" * 70)
    print("  [SUMMARY] Token Guard Benefits")
    print("=" * 70)

    print("""
  1. [Cost Savings]
     - Prevents massive token bills from large outputs
     - Typical savings: 90-99% token reduction on large outputs

  2. [Performance]
     - Keeps context window manageable
     - Faster LLM processing (less tokens to process)
     - Prevents context window overflow errors

  3. [Intelligence]
     - Teaches LLM to use filtering tools (grep, head, tail)
     - Encourages more efficient command usage

  4. [Safety]
     - Prevents crashes from memory exhaustion
     - Graceful degradation with clear truncation notices

[Ready for Production]
  The Token Guard is now active in FastReAct Nano v2.0!
  All tool outputs are automatically protected.
    """)

    return 0


if __name__ == "__main__":
    sys.exit(main())
