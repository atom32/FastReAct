"""
FastReAct Nano v2.0 - End-to-End Test Suite

Comprehensive testing of all features:
- ReAct Loop (Think-Act-Observe)
- Token Guard (ContextMonitor)
- Ghost Map (FilesystemMemory)
- Interactive Guardrails (SafetyPolicy)
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import (
    Agent,
    Config,
    ContextMonitor,
    FilesystemMemory,
    SafetyPolicy,
    AlwaysAllowCallback,
)


class TestReporter:
    """Test result reporter"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def add_result(self, test_name: str, passed: bool, message: str = ""):
        """Add test result"""
        self.results.append({
            "name": test_name,
            "passed": passed,
            "message": message,
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print("  END-TO-END TEST SUMMARY")
        print("=" * 70)
        print(f"\nTotal Tests: {total}")
        print(f"  [PASS] {self.passed}")
        print(f"  [FAIL] {self.failed}")

        if self.failed > 0:
            print("\n[FAILED TESTS]")
            for result in self.results:
                if not result["passed"]:
                    print(f"  - {result['name']}")
                    if result["message"]:
                        print(f"    {result['message']}")
        else:
            print("\n[SUCCESS] All end-to-end tests passed!")

        print("=" * 70)


async def test_react_loop_basic(reporter: TestReporter):
    """Test 1: Basic ReAct loop functionality"""
    print("\n" + "=" * 70)
    print("  Test 1: ReAct Loop - Basic Functionality")
    print("=" * 70)

    try:
        # Create agent with minimal safety (auto-approve for testing)
        config = Config()
        config.react.enable_safety = False  # Disable safety for automated testing

        agent = Agent(config=config)

        # Test simple query (no tools needed)
        print("\n[Test 1.1] Simple query (no tools)")
        response = await agent.run("What is 2+2?")
        print(f"Response: {response[:100]}...")
        reporter.add_result("Simple query", True)

        # Test tool availability
        print("\n[Test 1.2] Tool availability")
        tools = agent.list_tools()
        expected_tools = {"read_file", "write_file", "exec", "edit_file"}
        has_all_tools = expected_tools.issubset(set(tools))
        print(f"Available tools: {tools}")
        print(f"Expected tools present: {has_all_tools}")
        reporter.add_result("Tool availability", has_all_tools)

        # Test skills availability
        print("\n[Test 1.3] Skills availability")
        skills = agent.list_skills()
        print(f"Available skills: {skills}")
        has_skills = len(skills) > 0
        reporter.add_result("Skills availability", has_skills)

    except Exception as e:
        reporter.add_result("ReAct loop basic", False, str(e))


async def test_token_guard(reporter: TestReporter):
    """Test 2: Token Guard functionality"""
    print("\n" + "=" * 70)
    print("  Test 2: Token Guard (ContextMonitor)")
    print("=" * 70)

    try:
        # Test context monitor
        monitor = ContextMonitor(
            max_tokens=1000,
            max_tool_output_chars=100,
        )

        # Test token estimation
        print("\n[Test 2.1] Token estimation")
        text = "Hello world, this is a test"
        tokens = monitor.estimate_tokens(text)
        print(f"Text: '{text}'")
        print(f"Estimated tokens: {tokens}")
        is_reasonable = 0 < tokens < 100
        reporter.add_result("Token estimation", is_reasonable)

        # Test truncation
        print("\n[Test 2.2] Output truncation")
        large_output = "Line " * 1000  # ~5000 chars
        truncated = monitor.truncate_tool_output(large_output, "test_tool")
        print(f"Original length: {len(large_output)}")
        print(f"Truncated length: {len(truncated)}")
        is_truncated = len(truncated) < len(large_output)
        has_notice = "[System: Tool output truncated]" in truncated
        reporter.add_result("Output truncation", is_truncated and has_notice)

        # Test context checking
        print("\n[Test 2.3] Context size checking")
        messages = [
            {"role": "user", "content": "A" * 100},
            {"role": "assistant", "content": "B" * 100},
        ]
        is_safe, ratio = monitor.check_context_size(messages)
        print(f"Messages: {len(messages)}")
        print(f"Usage ratio: {ratio:.2%}")
        print(f"Is safe: {is_safe}")
        reporter.add_result("Context checking", is_safe)

    except Exception as e:
        reporter.add_result("Token guard", False, str(e))


async def test_filesystem_memory(reporter: TestReporter):
    """Test 3: Ghost Map functionality"""
    print("\n" + "=" * 70)
    print("  Test 3: Ghost Map (FilesystemMemory)")
    print("=" * 70)

    try:
        memory = FilesystemMemory(
            max_tree_depth=2,
            max_files_per_dir=10,
        )

        # Test learning from ls
        print("\n[Test 3.1] Learn from ls output")
        ls_output = "README.md\nsrc/\ntests/\nsetup.py"
        memory.update_from_tool_call("exec", {"command": "ls"}, ls_output)
        stats = memory.get_stats()
        print(f"Total nodes: {stats['total_nodes']}")
        learned = stats['total_nodes'] > 0
        reporter.add_result("Learn from ls", learned)

        # Test tree rendering
        print("\n[Test 3.2] Tree rendering")
        tree = memory.get_prompt_injection()
        print(tree[:200] + "...")
        has_tree = "[FileSystem Memory]" in tree
        reporter.add_result("Tree rendering", has_tree)

        # Test file operations tracking
        print("\n[Test 3.3] File operations tracking")
        memory.update_from_tool_call("read_file", {"path": "test.py"}, "content")
        stats_after = memory.get_stats()
        tracked = stats_after['total_nodes'] > stats['total_nodes']
        print(f"Nodes before: {stats['total_nodes']}")
        print(f"Nodes after: {stats_after['total_nodes']}")
        reporter.add_result("File operations tracking", tracked)

    except Exception as e:
        reporter.add_result("Filesystem memory", False, str(e))


async def test_safety_policy(reporter: TestReporter):
    """Test 4: Safety Guardrails functionality"""
    print("\n" + "=" * 70)
    print("  Test 4: Safety Guardrails (SafetyPolicy)")
    print("=" * 70)

    try:
        policy = SafetyPolicy()

        # Test safe operations
        print("\n[Test 4.1] Safe operations (Green)")
        safe_ops = [
            ("exec", {"command": "ls"}),
            ("read_file", {"path": "config.json"}),
        ]
        all_safe = True
        for tool_name, args in safe_ops:
            decision = policy.check(tool_name, args)
            is_safe = decision.level.value == "safe"
            print(f"  {tool_name}: {decision.level.value}")
            all_safe = all_safe and is_safe
        reporter.add_result("Safe operations", all_safe)

        # Test dangerous operations
        print("\n[Test 4.2] Dangerous operations (Red)")
        dangerous_ops = [
            ("exec", {"command": "rm file.txt"}),
            ("exec", {"command": "mv a.txt b.txt"}),
        ]
        all_dangerous = True
        for tool_name, args in dangerous_ops:
            decision = policy.check(tool_name, args)
            requires_confirm = decision.should_ask
            print(f"  {tool_name}: {decision.level.value} (needs confirm: {requires_confirm})")
            all_dangerous = all_dangerous and requires_confirm
        reporter.add_result("Dangerous operations", all_dangerous)

        # Test forbidden operations
        print("\n[Test 4.3] Forbidden operations (Black)")
        forbidden_ops = [
            ("exec", {"command": "rm -rf /"}),
            ("exec", {"command": "format c:"}),
        ]
        all_forbidden = True
        for tool_name, args in forbidden_ops:
            decision = policy.check(tool_name, args)
            is_forbidden = decision.level.value == "forbidden"
            print(f"  {tool_name}: {decision.level.value}")
            all_forbidden = all_forbidden and is_forbidden
        reporter.add_result("Forbidden operations", all_forbidden)

        # Test audit logging
        print("\n[Test 4.4] Audit logging")
        policy.log("exec", {"command": "ls"}, policy.check("exec", {"command": "ls"}))
        audit_log = policy.get_audit_log()
        has_audit = len(audit_log) > 0
        print(f"Audit log entries: {len(audit_log)}")
        reporter.add_result("Audit logging", has_audit)

    except Exception as e:
        reporter.add_result("Safety policy", False, str(e))


async def test_integration(reporter: TestReporter):
    """Test 5: Integration of all components"""
    print("\n" + "=" * 70)
    print("  Test 5: Integration - All Components Working Together")
    print("=" * 70)

    try:
        # Create agent with all features enabled but auto-approve for testing
        config = Config()
        config.react.enable_safety = True
        config.react.enable_filesystem_memory = True

        # Use auto-approve callback for testing
        from fastreact import AlwaysAllowCallback
        agent = Agent(config=config)
        agent._confirmation_callback = AlwaysAllowCallback()

        # Test 1: Context monitor is active
        print("\n[Test 5.1] Context monitor integration")
        has_context_monitor = agent._context_monitor is not None
        print(f"Context monitor present: {has_context_monitor}")
        reporter.add_result("Context monitor integration", has_context_monitor)

        # Test 2: Filesystem memory is active
        print("\n[Test 5.2] Filesystem memory integration")
        has_fs_memory = agent._filesystem_memory is not None
        print(f"Filesystem memory present: {has_fs_memory}")
        reporter.add_result("Filesystem memory integration", has_fs_memory)

        # Test 3: Safety policy is active
        print("\n[Test 5.3] Safety policy integration")
        has_safety = agent._safety_policy is not None
        print(f"Safety policy present: {has_safety}")
        reporter.add_result("Safety policy integration", has_safety)

        # Test 4: Configuration accessibility
        print("\n[Test 5.4] Configuration accessibility")
        max_tokens = agent._config.react.max_context_tokens
        max_depth = agent._config.react.max_tree_depth
        strict_mode = agent._config.react.strict_mode
        print(f"Max context tokens: {max_tokens}")
        print(f"Max tree depth: {max_depth}")
        print(f"Strict mode: {strict_mode}")
        config_accessible = all([
            max_tokens == 128000,
            max_depth == 3,
            strict_mode == False,
        ])
        reporter.add_result("Configuration accessibility", config_accessible)

    except Exception as e:
        reporter.add_result("Integration test", False, str(e))


async def test_configuration(reporter: TestReporter):
    """Test 6: Configuration system"""
    print("\n" + "=" * 70)
    print("  Test 6: Configuration System")
    print("=" * 70)

    try:
        # Test default configuration
        print("\n[Test 6.1] Default configuration")
        config = Config.from_env()
        print(f"Model: {config.llm.model}")
        print(f"Max iterations: {config.react.max_iterations}")
        print(f"Enable steering: {config.react.enable_steering}")
        print(f"Enable followup: {config.react.enable_followup}")
        has_defaults = all([
            config.react.max_iterations == 20,
            config.react.enable_steering == True,
            config.react.enable_followup == True,
        ])
        reporter.add_result("Default configuration", has_defaults)

        # Test Cortex configuration
        print("\n[Test 6.2] Cortex configuration")
        print(f"Enable safety: {config.react.enable_safety}")
        print(f"Enable filesystem memory: {config.react.enable_filesystem_memory}")
        print(f"Max context tokens: {config.react.max_context_tokens}")
        print(f"Max tool output chars: {config.react.max_tool_output_chars}")
        has_cortex = all([
            config.react.enable_safety == True,
            config.react.enable_filesystem_memory == True,
            config.react.max_context_tokens > 0,
            config.react.max_tool_output_chars > 0,
        ])
        reporter.add_result("Cortex configuration", has_cortex)

    except Exception as e:
        reporter.add_result("Configuration system", False, str(e))


async def test_exports(reporter: TestReporter):
    """Test 7: Public API exports"""
    print("\n" + "=" * 70)
    print("  Test 7: Public API Exports")
    print("=" * 70)

    try:
        from fastreact import (
            Agent,
            ask_sync,
            Config,
            ContextMonitor,
            FilesystemMemory,
            SafetyPolicy,
            SafetyLevel,
        )

        print("\n[Test 7.1] Core exports")
        print(f"Agent: {Agent is not None}")
        print(f"ask_sync: {ask_sync is not None}")
        print(f"Config: {Config is not None}")
        reporter.add_result("Core exports", True)

        print("\n[Test 7.2] Cortex exports")
        print(f"ContextMonitor: {ContextMonitor is not None}")
        print(f"FilesystemMemory: {FilesystemMemory is not None}")
        print(f"SafetyPolicy: {SafetyPolicy is not None}")
        print(f"SafetyLevel: {SafetyLevel is not None}")
        reporter.add_result("Cortex exports", True)

    except ImportError as e:
        reporter.add_result("Public API exports", False, str(e))


async def main():
    """Run all end-to-end tests"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║        FastReAct Nano v2.0 - End-to-End Test Suite           ║
║                                                                ║
║  Comprehensive testing of all Cortex components               ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝
    """)

    reporter = TestReporter()

    try:
        # Run all tests
        await test_react_loop_basic(reporter)
        await test_token_guard(reporter)
        await test_filesystem_memory(reporter)
        await test_safety_policy(reporter)
        await test_integration(reporter)
        await test_configuration(reporter)
        await test_exports(reporter)

        # Print summary
        reporter.print_summary()

        # Return exit code
        return 0 if reporter.failed == 0 else 1

    except Exception as e:
        print(f"\n[FATAL ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
