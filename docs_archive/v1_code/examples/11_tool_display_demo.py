"""
Tool Display Demonstration

This example demonstrates the Tool Display feature, which provides
user-friendly formatting for tool calls and results.

Key features:
- Formatted display with icons and colors
- Clear error messages
- Execution information (time, status)
- Tool categorization
- Multiple display modes
"""

import sys
import io
import time

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fastreact.core.tool_display import (
    ToolDisplay,
    DisplayConfig,
    DisplayMode,
    ToolCategory,
    create_default_display,
)


def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_minimal_mode():
    """Demonstrate minimal display mode"""
    print_separator("Demo 1: Minimal Mode")

    config = DisplayConfig(mode=DisplayMode.MINIMAL)
    display = ToolDisplay(config)

    tools = ["bash", "search", "edit_file", "http_request", "analyze_data"]

    print("Minimal mode - just tool names with icons:\n")
    for tool in tools:
        print(display.format_tool_call(tool, {}))


def demo_normal_mode():
    """Demonstrate normal display mode"""
    print_separator("Demo 2: Normal Mode")

    config = DisplayConfig(mode=DisplayMode.NORMAL)
    display = ToolDisplay(config)

    print("Normal mode - tool name, parameters, and risk:\n")

    # Example 1: Shell command
    print("1. Shell command:")
    print(display.format_tool_call(
        "bash",
        {"command": "ls -la", "cwd": "/tmp"}
    ))
    print()

    # Example 2: Search
    print("2. Search:")
    print(display.format_tool_call(
        "grep_search",
        {"pattern": "TODO", "path": "./src", "recursive": True}
    ))
    print()

    # Example 3: Edit file
    print("3. Edit file:")
    print(display.format_tool_call(
        "edit_file",
        {"path": "test.py", "search_block": "old code", "replace_block": "new code"}
    ))


def demo_verbose_mode():
    """Demonstrate verbose display mode"""
    print_separator("Demo 3: Verbose Mode")

    config = DisplayConfig(mode=DisplayMode.VERBOSE)
    display = ToolDisplay(config)

    print("Verbose mode - all details including category:\n")

    print(display.format_tool_call(
        "bash_exec",
        {"command": "docker run -it ubuntu", "timeout": 60},
        risk_level="HIGH"
    ))


def demo_success_result():
    """Demonstrate success result formatting"""
    print_separator("Demo 4: Success Result")

    config = DisplayConfig(mode=DisplayMode.NORMAL)
    display = ToolDisplay(config)

    print("Successful tool execution:\n")

    # Short result
    print("1. Short result:")
    print(display.format_result(
        "bash",
        "Files: 5\nDirectories: 2\nTotal: 7",
        execution_time=0.5
    ))
    print()

    # Long result (truncated)
    print("2. Long result (truncated):")
    long_result = "\n".join([f"Line {i}: Some content here" for i in range(100)])
    print(display.format_result(
        "grep_search",
        long_result,
        execution_time=1.2
    ))


def demo_error_result():
    """Demonstrate error result formatting"""
    print_separator("Demo 5: Error Result")

    config = DisplayConfig(mode=DisplayMode.NORMAL)
    display = ToolDisplay(config)

    print("Failed tool execution:\n")

    errors = [
        ("bash", "Permission denied: Cannot access /root"),
        ("edit_file", "File not found: /path/to/file.py"),
        ("http_request", "Connection timeout after 30s"),
    ]

    for tool, error in errors:
        print(f"{tool}:")
        print(display.format_result(tool, None, error, execution_time=0.3))
        print()


def demo_tool_categories():
    """Demonstrate tool categorization"""
    print_separator("Demo 6: Tool Categories")

    display = ToolDisplay()

    tools_and_categories = [
        ("bash", ToolCategory.EXECUTION),
        ("grep_search", ToolCategory.SEARCH),
        ("edit_file", ToolCategory.EDIT),
        ("analyze_json", ToolCategory.DATA),
        ("http_get", ToolCategory.NETWORK),
        ("system_info", ToolCategory.SYSTEM),
        ("unknown_tool", ToolCategory.UNKNOWN),
    ]

    print("Tool categorization:\n")
    for tool, expected in tools_and_categories:
        category = display.get_tool_category(tool)
        match = "✓" if category == expected else "✗"
        print(f"  {match} {tool:20s} → {category.name}")


def demo_context_manager():
    """Demonstrate context manager for tracking calls"""
    print_separator("Demo 7: Context Manager Tracking")

    config = DisplayConfig(mode=DisplayMode.NORMAL)
    display = ToolDisplay(config)

    print("Using context manager to track tool calls:\n")

    # Simulated tool call 1
    with display.track_call("bash", {"command": "ls -la"}, risk_level="LOW") as info:
        time.sleep(0.1)  # Simulate work
        info.status = "success"
        info.result = "file1.txt\nfile2.txt\ndir1/"

    print()

    # Simulated tool call 2 (error)
    with display.track_call("bash", {"command": "rm -rf /"}, risk_level="CRITICAL") as info:
        time.sleep(0.05)
        info.status = "error"
        info.error = "Permission denied"

    print()
    print(f"Statistics: {display.get_statistics()}")


def demo_no_colors():
    """Demonstrate display without colors/emoji"""
    print_separator("Demo 8: Plain Text Mode")

    config = DisplayConfig(mode=DisplayMode.NORMAL, use_colors=False)
    display = ToolDisplay(config)

    print("Plain text mode (no colors/emoji):\n")

    print(display.format_tool_call("bash", {"command": "ls"}))
    print(display.format_result("bash", "file1\nfile2", execution_time=0.3))


def demo_config_from_dict():
    """Demonstrate loading configuration from dictionary"""
    print_separator("Demo 9: Configuration from Dictionary")

    config_dict = {
        "mode": "normal",
        "use_colors": True,
        "show_time": True,
        "show_risk": True,
        "max_result_lines": 30,
        "truncate_results": True,
    }

    config = DisplayConfig.from_dict(config_dict)

    print("Configuration loaded from dictionary:")
    print(f"  Mode: {config.mode.name}")
    print(f"  Colors: {config.use_colors}")
    print(f"  Show time: {config.show_time}")
    print(f"  Show risk: {config.show_risk}")
    print(f"  Max lines: {config.max_result_lines}")
    print(f"  Truncate: {config.truncate_results}")


def demo_real_world_example():
    """Demonstrate real-world usage example"""
    print_separator("Demo 10: Real-World Example")

    config = DisplayConfig(mode=DisplayMode.NORMAL)
    display = ToolDisplay(config)

    print("Simulated coding agent workflow:\n")

    # Step 1: Read file
    print("Step 1: Read repository structure")
    with display.track_call("list_files", {"path": "./src", "recursive": False}) as info:
        time.sleep(0.1)
        info.status = "success"
        info.result = "engine.py\ntool.py\ncache.py\n"

    print()

    # Step 2: Search for specific code
    print("Step 2: Search for TODO comments")
    with display.track_call("grep_search", {"pattern": "TODO", "path": "./src"}) as info:
        time.sleep(0.2)
        info.status = "success"
        info.result = "engine.py:42: # TODO: Implement caching\n"

    print()

    # Step 3: Edit file
    print("Step 3: Edit file to add caching")
    with display.track_call("edit_file", {
        "path": "engine.py",
        "search_block": "# TODO: Implement caching",
        "replace_block": "# Implemented: LRU cache"
    }) as info:
        time.sleep(0.15)
        info.status = "success"
        info.result = "Changed 1 line in engine.py"

    print()

    # Step 4: Run tests
    print("Step 4: Run tests")
    with display.track_call("bash", {"command": "pytest tests/"}) as info:
        time.sleep(0.3)
        info.status = "success"
        info.result = "15 passed, 0 failed in 2.5s"


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 60)
    print("  Tool Display Feature Demonstration")
    print("=" * 60)

    try:
        demo_minimal_mode()
        demo_normal_mode()
        demo_verbose_mode()
        demo_success_result()
        demo_error_result()
        demo_tool_categories()
        demo_context_manager()
        demo_no_colors()
        demo_config_from_dict()
        demo_real_world_example()

        print_separator("All Demos Complete")
        print("Tool Display successfully enhances output readability!")
        print("\nKey benefits:")
        print("  → Icons make tools easily recognizable")
        print("  → Structured output is easy to scan")
        print("  → Error messages are clear and actionable")
        print("  → Execution time helps track performance")
        print("  → Risk levels increase safety awareness")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
