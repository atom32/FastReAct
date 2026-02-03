"""
IEL Stress Test - Dependency Hell with Rollback

Demonstrates:
- Git-native checkpoint/rollback
- High-speed interrupts (/fix command)
- Dependency resolution failures
- Automatic rollback on repeated failures
- Complete execution timeline visualization
"""

import asyncio
import logging
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Mock LLM client
class MockLLMClient:
    def __init__(self):
        self.model = "gpt-4-mock"

    class Chat:
        class Completions:
            async def create(self, model, messages, temperature=0.7, max_tokens=1000):
                await asyncio.sleep(0.1)
                user_msg = messages[-1]["content"].lower()

                # Dependency failure -> replan with install
                if "no module named" in user_msg or "missing dependency" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "environment",
  "root_cause": "Missing required Python package",
  "recovery_strategy": "replan",
  "suggested_fix": "Add pip install node before this step",
  "confidence": 0.95
}
```(""")

                # Version conflict -> replan with different version
                elif "version conflict" in user_msg or "incompatible" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "environment",
  "root_cause": "Package version incompatible with current environment",
  "recovery_strategy": "replan",
  "suggested_fix": "Install compatible version or uninstall conflicting package",
  "confidence": 0.9
}
```("("")

                # File permission error -> replan with fix permissions
                elif "permission denied" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "environment",
  "root_cause": "Insufficient file system permissions",
  "recovery_strategy": "replan",
  "suggested_fix": "Add chmod or sudo node before this step",
  "confidence": 0.85
}
```("("")

                # After 3 failures -> suggest rollback
                elif "3" in user_msg and "fail" in user_msg:
                    return MockResponse("""```json
{
  "failure_category": "logic",
  "root_cause": "Repeated installation failures, dependency chain may be broken",
  "recovery_strategy": "replan",
  "suggested_fix": "Rollback to last known good state and try alternative approach",
  "confidence": 0.95
}
```("("")

                # Default retry
                return MockResponse("""```json
{
  "failure_category": "transient",
  "root_cause": "Temporary network or system issue",
  "recovery_strategy": "retry",
  "suggested_fix": null,
  "confidence": 0.7
}
```("""")

        completions = Completions()

    chat = Chat()


class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]


class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)


class MockMessage:
    def __init__(self, content):
        self.content = content


# ============================================================================
# Dependency Hell Tools
# ============================================================================

class DependencyTracker:
    """Track installed packages and dependencies"""

    def __init__(self):
        self.installed = {}
        self.failed_installs = {}  # package -> failure count

    def install(self, package: str, version: str = None):
        """Simulate package installation"""
        package_key = f"{package}=={version}" if version else package

        # Simulate dependency hell
        if package == "numpy" and version == "2.0.0":
            # Version conflict!
            if self.installed.get("pandas", "").startswith("1."):
                raise RuntimeError("Version conflict: numpy 2.0.0 incompatible with pandas 1.x")

        if package == "tensorflow" and not self.installed.get("numpy"):
            # Missing dependency
            raise RuntimeError("Missing dependency: tensorflow requires numpy")

        # Simulate installation
        self.installed[package_key] = {
            "version": version or "latest",
            "installed_at": datetime.now().isoformat()
        }

        return {"package": package_key, "status": "installed"}

    def check_installed(self, package: str) -> bool:
        """Check if package is installed"""
        return package in self.installed


# Global dependency tracker
deps = DependencyTracker()


async def tool_import_package(package: str, version: str = None) -> dict:
    """Simulate importing a package"""
    print(f"  [TOOL] Importing package: {package}")

    # Check if already installed
    if deps.check_installed(package):
        return {"status": "already_installed", "package": package}

    # Try to import (will fail if not installed)
    if not deps.check_installed(package):
        raise ImportError(f"No module named '{package}'")


async def tool_install_package(package: str, version: str = None) -> dict:
    """Simulate installing a package"""
    print(f"  [TOOL] Installing package: {package} {version or ''}")

    # Track failures
    package_key = f"{package}=={version}" if version else package
    deps.failed_installs[package_key] = deps.failed_installs.get(package_key, 0) + 1

    # Simulate installation
    try:
        result = deps.install(package, version)
        print(f"    [OK] Installed {package_key}")
        return result
    except Exception as e:
        print(f"    [FAIL] {e}")
        raise


async def tool_check_dependencies() -> dict:
    """Check environment dependencies"""
    print(f"  [TOOL] Checking dependencies")

    missing = []
    for pkg in ["numpy", "pandas", "tensorflow"]:
        if not deps.check_installed(pkg):
            missing.append(pkg)

    if missing:
        return {"status": "incomplete", "missing": missing}

    return {"status": "complete", "packages": list(deps.installed.keys())}


async def tool_run_analysis(data: str) -> dict:
    """Run analysis (requires all dependencies)"""
    print(f"  [TOOL] Running analysis")

    # Check dependencies
    check = await tool_check_dependencies()

    if check["status"] == "incomplete":
        missing = check["missing"]
        raise RuntimeError(f"Missing dependencies: {missing}")

    return {"analysis_result": f"Analysis complete on {data}"}


async def tool_fix_permissions(path: str) -> dict:
    """Fix file permissions"""
    print(f"  [TOOL] Fixing permissions: {path}")
    return {"status": "fixed", "path": path}


# ============================================================================
# Stress Test
# ============================================================================

async def stress_test_dependency_hell():
    """
    Stress Test: Dependency Hell Scenario

    Scenario:
    1. Try to run analysis (fails - missing numpy)
    2. Install numpy (fails - missing pandas dependency)
    3. Install pandas (fails - version conflict)
    4. Try alternative approach
    5. Rollback after repeated failures
    6. Apply user /fix to resolve
    """
    print("\n" + "=" * 80)
    print("IEL STRESS TEST: Dependency Hell with Rollback")
    print("=" * 80)

    from fastreact.graph import (
        create_graph,
        create_tool_node,
        IELExecutionContext,
        PriorityInterruptQueue,
        CheckpointManager,
        StepExecutor,
        StepConfig,
        Replanner,
        IELLoop,
        IELLoopConfig,
        PatchOp,
        NodeInstruction,
        GraphPatch,
        Status,
    )

    # Setup: Create temporary git repo for testing
    temp_dir = tempfile.mkdtemp(prefix="iel_stress_test_")
    print(f"\n[Test] Creating temporary git repo: {temp_dir}")

    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, capture_output=True)

    # Create initial file
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("Initial state")
    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, capture_output=True)

    # Create checkpoint manager with git
    checkpoint_mgr = CheckpointManager(workspace_path=temp_dir, prefer_stash=True)
    print(f"[Test] CheckpointManager status: {checkpoint_mgr.get_status()}")

    # Create priority interrupt queue
    interrupt_queue = PriorityInterruptQueue()

    # Create initial graph
    graph = create_graph("dependency_hell")

    node1 = create_tool_node("check_deps", tool_check_dependencies, {})
    node2 = create_tool_node("run_analysis", tool_run_analysis, {"data": "test_data"})

    graph.add_node(node1).add_node(node2)
    graph.connect("check_deps", "run_analysis")

    # Setup IEL components
    llm_client = MockLLMClient()

    tool_registry = {
        "import_package": tool_import_package,
        "install_package": tool_install_package,
        "check_dependencies": tool_check_dependencies,
        "run_analysis": tool_run_analysis,
        "fix_permissions": tool_fix_permissions,
    }

    # Create executor with checkpoint manager
    executor = StepExecutor(
        config=StepConfig(
            auto_snapshot=True,
            check_interrupts=True,
        ),
        interrupt_queue=interrupt_queue,
        checkpoint_manager=checkpoint_mgr,
    )

    # Create replanner
    replanner = Replanner(
        llm_client=llm_client,
        tool_registry=tool_registry,
    )

    # Create context
    context = IELExecutionContext(
        graph=graph,
        failure_threshold=3,  # Rollback after 3 failures
    )

    # Create loop
    loop = IELLoop(executor, replanner, config=IELLoopConfig(
        max_iterations=20,
        snapshot_after_replan=True,
    ))

    print("\n" + "-" * 80)
    print("EXECUTION STARTED")
    print("-" * 80)

    # Inject user fix after a few steps (simulating user intervention)
    async def inject_user_fix():
        await asyncio.sleep(2.0)  # Wait for some failures

        print("\n[USER INJECT] /fix command - Installing compatible packages")

        # User provides direct fix via /fix command (bypasses LLM)
        fix_input = """fix insert_before Install compatible numpy version first
node_id: run_analysis
new_node:
  node_id: install_numpy_compat
  tool_name: install_package
  inputs:
    package: numpy
    version: 1.24.0"""

        await interrupt_queue.put_user_input(fix_input)

    # Start user injection in background
    asyncio.create_task(inject_user_fix())

    # Run loop
    result = await loop.run(context)

    # Show execution timeline
    print("\n" + "=" * 80)
    print("EXECUTION TIMELINE")
    print("=" * 80)

    for i, step in enumerate(context.history, 1):
        status_symbol = {
            Status.SUCCESS: "[OK]",
            Status.FAILED: "[FAIL]",
            Status.NEEDS_INPUT: "[INPUT]",
        }.get(step.status, "[?]")

        timestamp = step.timestamp.strftime("%H:%M:%S")

        print(f"\nStep {i} - {timestamp} - {step.node_id}")
        print(f"  Status: {status_symbol} {step.status.value}")

        if step.error:
            print(f"  Error: {step.error}")

        if step.payload and step.status == Status.SUCCESS:
            payload_preview = str(step.payload)[:100]
            print(f"  Payload: {payload_preview}")

        if step.metadata.get("skipped"):
            print(f"  [SKIPPED] By user request")

    # Show patches applied
    print("\n" + "=" * 80)
    print("PATCHES APPLIED")
    print("=" * 80)

    patches = context.metadata.get("patches_applied", [])
    for i, patch in enumerate(patches, 1):
        print(f"\nPatch {i}: {patch['patch_id']}")
        print(f"  Operation: {patch['operation']}")
        print(f"  Reason: {patch['reason']}")

        if patch.get("metadata", {}).get("source") == "user_fix":
            print(f"  [USER FIX] Bypassed reflection!")

    # Show git checkpoints
    print("\n" + "=" * 80)
    print("GIT CHECKPOINTS")
    print("=" * 80)

    git_checkpoints = context.metadata.get("git_checkpoints", [])
    print(f"Git-native checkpoints created: {len(git_checkpoints)}")

    for ckpt_id in git_checkpoints:
        info = checkpoint_mgr.get_checkpoint_info(ckpt_id)
        if info:
            print(f"  - {ckpt_id}: {info.get('checkpoint_type', 'unknown')}")
            print(f"    Ref: {info.get('git_ref', 'N/A')}")
            print(f"    Label: {info.get('metadata', {}).get('label', 'N/A')}")

    # Show checkpoint manager status
    print(f"\nCheckpointManager Status:")
    status = checkpoint_mgr.get_status()
    print(f"  In git repo: {status['in_git']}")
    print(f"  Git checkpoints: {status['git_checkpoints']}")
    print(f"  Branch: {status.get('git_status', {}).get('branch', 'N/A')}")

    # Show final statistics
    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)

    stats = loop.get_stats()
    print(f"Total steps: {stats['total_steps']}")
    print(f"Replans: {stats['replan_count']}")
    print(f"Retries: {stats['retry_count']}")
    print(f"Nodes completed: {len(context.get_completed_nodes())}")
    print(f"Nodes failed: {len(context.get_failed_nodes())}")
    print(f"Nodes pending: {len(context.get_pending_nodes())}")
    print(f"Final status: {result.status.value}")

    # Show dependency state
    print(f"\nInstalled packages:")
    for pkg, info in deps.installed.items():
        print(f"  - {pkg}: {info['version']}")

    print(f"\nFailed installs:")
    for pkg, count in deps.failed_installs.items():
        print(f"  - {pkg}: {count} failures")

    # Cleanup
    print("\n" + "=" * 80)
    print("CLEANUP")
    print("=" * 80)

    checkpoint_mgr.cleanup_all()
    shutil.rmtree(temp_dir)
    print(f"Cleaned up temporary directory: {temp_dir}")


# ============================================================================
# Visual Traceability Test
# ============================================================================

def visualize_execution_timeline(context):
    """
    Generate visual execution timeline

    Shows:
    - Step sequence
    - Success/Failure markers
    - Patch applications
    - Rollback points
    - Git checkpoints
    """
    from .iel_types import Status

    print("\n" + "=" * 80)
    print("VISUAL EXECUTION TIMELINE")
    print("=" * 80)

    timeline = []
    current_time = 0

    for i, step in enumerate(context.history):
        # Step marker
        status_char = {
            Status.SUCCESS: "+",
            Status.FAILED: "x",
            Status.NEEDS_INPUT: "?",
        }.get(step.status, "o")

        timeline.append(f"[{i}] {status_char} {step.node_id}")

        # Show patches applied after this step
        patches = context.metadata.get("patches_applied", [])
        for patch in patches:
            if patch.get("metadata", {}).get("applied_after_step") == i:
                timeline.append(f"    |__PATCH: {patch['operation']} - {patch['reason'][:30]}...")

        # Show checkpoints
        git_checkpoints = context.metadata.get("git_checkpoints", [])
        for ckpt in git_checkpoints:
            if ckpt.get("created_after_step") == i:
                timeline.append(f"    |__CHECKPOINT: {ckpt}")

    print("\nTimeline:")
    for line in timeline:
        print(f"  {line}")

    # Legend
    print("\nLegend:")
    print("  +  SUCCESS")
    print("  x  FAILED")
    print("  ?  NEEDS_INPUT")
    print("  PATCH  - Graph modification applied")
    print("  CHECKPOINT  - Snapshot created")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run stress test"""
    await stress_test_dependency_hell()

    print("\n" + "=" * 80)
    print("STRESS TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    asyncio.run(main())
