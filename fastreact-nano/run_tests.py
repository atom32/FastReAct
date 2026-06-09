#!/usr/bin/env python3
"""
Unified test runner for FastReAct Nano

Provides multiple test execution strategies:
1. Unit tests only (fast, no API calls)
2. Integration tests only (mocked/local integration)
3. All default tests (excludes release LLM gate)
4. Quick validation (contracts + core runtime)
5. Release LLM efficiency gate (manual, real API)
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run command and report result"""
    print(f"\n{'='*60}")
    print(f"[Running] {description}")
    print(f"[Command] {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"[OK] {description}")
    else:
        print(f"[FAILED] {description}")

    return result.returncode == 0


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="FastReAct Nano Test Runner")
    parser.add_argument(
        "suite",
        nargs="?",
        choices=["unit", "integration", "all", "quick", "contracts", "release-llm", "release-full"],
        default="all",
        help="Test suite to run (default: all)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-k",
        help="Filter tests by keyword (passed to pytest)"
    )

    args = parser.parse_args()

    # Build pytest command
    pytest_cmd = ["python3", "-m", "pytest"]

    if args.verbose:
        pytest_cmd.append("-v")

    if args.k:
        pytest_cmd.extend(["-k", args.k])

    # Determine which tests to run
    project_root = Path(__file__).parent
    repo_root = project_root.parent
    frontend_root = repo_root / "fastreact-nano-web"

    if args.suite == "release-full":
        checks = [
            (
                [
                    "python3",
                    "-m",
                    "compileall",
                    "-q",
                    str(project_root / "src" / "fastreact"),
                    str(project_root / "scripts"),
                    str(project_root / "run_tests.py"),
                ],
                "Python Compile Check",
            ),
            (["python3", str(project_root / "run_tests.py"), "quick"], "Quick Suite"),
            (["python3", str(project_root / "run_tests.py"), "integration"], "Integration Suite"),
            (["python3", str(project_root / "run_tests.py"), "all"], "All Default Tests"),
            (["npm", "run", "build"], "Frontend Build"),
            (["npm", "audit", "--omit=dev"], "Frontend Production Audit"),
            (["python3", str(project_root / "scripts" / "frontend_e2e.py")], "Frontend E2E"),
            (["python3", str(project_root / "run_tests.py"), "release-llm"], "Release LLM Efficiency Gate"),
        ]
        for cmd, description in checks:
            cwd = frontend_root if cmd[0] == "npm" else repo_root
            print(f"\n{'='*60}")
            print(f"[Running] {description}")
            print(f"[Command] {' '.join(cmd)}")
            print('='*60)
            result = subprocess.run(cmd, cwd=cwd)
            if result.returncode == 0:
                print(f"[OK] {description}")
            else:
                print(f"[FAILED] {description}")
                return False
        return True

    if args.suite == "release-llm":
        return run_command(
            ["python3", str(project_root / "scripts" / "release_llm_gate.py")],
            "Release LLM Efficiency Gate",
        )

    if args.suite == "contracts":
        pytest_cmd.extend([
            str(project_root / "tests" / "contracts"),
            "-v",
            "--tb=short",
        ])
        return run_command(pytest_cmd, "Contract Tests")

    if args.suite == "unit":
        pytest_cmd.extend([
            str(project_root / "tests" / "unit"),
            "-v",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "Unit Tests")

    elif args.suite == "integration":
        pytest_cmd.extend([
            str(project_root / "tests" / "integration" / "gateway"),
            str(project_root / "tests" / "integration" / "mcp"),
            str(project_root / "tests" / "integration" / "multitenant"),
            "-v",
            "-k", "not graphrag_user_isolation",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "Integration Tests")

    elif args.suite == "quick":
        # Quick validation - run only fast tests
        quick_targets = []
        contracts_dir = project_root / "tests" / "contracts"
        runtime_dir = project_root / "tests" / "integration" / "agent_runtime"
        if contracts_dir.exists():
            quick_targets.append(str(contracts_dir))
        if runtime_dir.exists():
            quick_targets.append(str(runtime_dir))
        quick_targets.extend([
            str(project_root / "tests" / "unit" / "test_events.py"),
            str(project_root / "tests" / "unit" / "test_tools.py"),
            str(project_root / "tests" / "unit" / "test_agent_sessions.py"),
        ])
        pytest_cmd.extend(quick_targets + ["-v", "-m", "not slow and not release_llm", "--tb=short"])
        return run_command(pytest_cmd, "Quick Tests")

    else:  # "all"
        # Run default release-safe tests. Real LLM and legacy diagnostic tests
        # stay outside the default gate.
        pytest_cmd.extend([
            str(project_root / "tests" / "contracts"),
            str(project_root / "tests" / "unit"),
            str(project_root / "tests" / "integration" / "agent_runtime"),
            str(project_root / "tests" / "integration" / "gateway"),
            str(project_root / "tests" / "integration" / "mcp"),
            str(project_root / "tests" / "integration" / "multitenant"),
            "-v",
            "-m", "not release_llm",
            "-k", "not graphrag_user_isolation",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "All Tests")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
