#!/usr/bin/env python3
"""
Unified test runner for FastReAct Nano

Provides multiple test execution strategies:
1. Unit tests only (fast, no API calls)
2. Integration tests only (may require API keys)
3. All tests (complete coverage)
4. Quick validation (subset of tests)
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
        choices=["unit", "integration", "all", "quick"],
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

    if args.suite == "unit":
        pytest_cmd.extend([
            str(project_root / "tests" / "unit"),
            "-v",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "Unit Tests")

    elif args.suite == "integration":
        pytest_cmd.extend([
            str(project_root / "tests" / "integration"),
            "-v",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "Integration Tests")

    elif args.suite == "quick":
        # Quick validation - run only fast tests
        pytest_cmd.extend([
            str(project_root / "tests"),
            "-v",
            "-m", "not slow",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "Quick Tests")

    else:  # "all"
        # Run all tests
        pytest_cmd.extend([
            str(project_root / "tests"),
            "-v",
            "--tb=short"
        ])
        return run_command(pytest_cmd, "All Tests")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
