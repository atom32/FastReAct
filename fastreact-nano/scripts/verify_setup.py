#!/usr/bin/env python3
"""
FastReAct Nano - Setup Verification Script

Run this script to verify your installation and configuration.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_python_version():
    """Check Python version"""
    print("\n--- Python Version Check ---")
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")

    if version >= (3, 11):
        print("[OK] Python version is 3.11+")
        return True
    else:
        print(f"[WARNING] Python {version.major}.{version.minor} detected")
        print("[INFO] Python 3.11+ recommended for best compatibility")
        return False

def check_env_file():
    """Check API key configuration (env vars, credentials.json, or config.json)"""
    print("\n--- API Key Configuration Check ---")

    # Priority 1: Environment variables
    print("[INFO] Checking environment variables...")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if api_key and not api_key.startswith("sk-your"):
        provider = "OpenAI" if os.getenv("OPENAI_API_KEY") else "Anthropic"
        print(f"[OK] API key found in environment variables ({provider})")
        print(f"[OK] API key: {api_key[:10]}...")
        return True

    # Priority 2: credentials.json
    print("[INFO] Checking credentials.json...")
    from fastreact.core.credentials import Credentials

    credentials = Credentials.load()
    if credentials.llm_api_keys:
        # Check for any configured key
        for provider, key in credentials.llm_api_keys.items():
            if key and not key.startswith("sk-your"):
                print(f"[OK] API key found in credentials.json ({provider})")
                print(f"[OK] API key: {key[:10]}...")
                return True

    # Priority 3: config.json
    print("[INFO] Checking config.json...")
    config_paths = [
        Path.home() / ".fastreact" / "config.json",
        Path.cwd() / ".fastreact" / "config.json",
        Path.cwd() / "config.json",
    ]

    config_file = None
    for path in config_paths:
        if path.exists():
            config_file = path
            break

    if config_file:
        try:
            from fastreact.core.config import Config
            config = Config.load(config_file)
            api_key = config.llm.api_key

            if api_key and not api_key.startswith("sk-your") and api_key != "your-api-key-here":
                print(f"[OK] API key found in config.json")
                print(f"[OK] API key: {api_key[:10]}...")
                print(f"[OK] Model: {config.llm.model}")
                return True
        except Exception as e:
            print(f"[WARNING] Failed to load config: {e}")

    # No API key found
    print("[WARNING] No API key configured")
    print("\n[INFO] Choose one of these methods:")
    print("\n  Method 1: Environment variable (recommended)")
    print("    export OPENAI_API_KEY='sk-your-key-here'")
    print("\n  Method 2: credentials.json (local development)")
    print("    cp credentials.json.example ~/.fastreact/credentials.json")
    print("    nano ~/.fastreact/credentials.json")
    print("\n  Method 3: config.json (simple, not recommended)")
    print("    cp config.example.json ~/.fastreact/config.json")
    print("    nano ~/.fastreact/config.json")

    return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n--- Dependencies Check ---")

    required_modules = [
        ("fastreact", "FastReAct core"),
        ("anthropic", "Anthropic SDK"),
        ("openai", "OpenAI SDK"),
    ]

    all_ok = True
    for module_name, description in required_modules:
        try:
            __import__(module_name)
            print(f"[OK] {description} ({module_name})")
        except ImportError:
            print(f"[WARNING] {description} ({module_name}) not found")
            all_ok = False

    if not all_ok:
        print("\n[INFO] Install missing dependencies:")
        print("       pip install -e .[all]")

    return all_ok

def check_core_components():
    """Check if core components can be imported"""
    print("\n--- Core Components Check ---")

    components = [
        ("fastreact.core.config", "Config"),
        ("fastreact.core.messages", "Messages"),
        ("fastreact.core.multitenant", "MultiTenant"),
        ("fastreact.mcp.manager", "MCP Manager"),
        ("fastreact.agent", "Agent"),
    ]

    all_ok = True
    for module_path, name in components:
        try:
            __import__(module_path)
            print(f"[OK] {name}")
        except ImportError as e:
            print(f"[ERROR] {name}: {e}")
            all_ok = False

    return all_ok

def run_quick_test(with_api=False):
    """Run a quick functionality test"""
    print("\n--- Quick Functionality Test ---")

    try:
        from fastreact import Agent

        print("[INFO] Creating Agent...")
        agent = Agent()
        print("[OK] Agent created successfully")

        if with_api:
            print("[INFO] Testing with API (this will use credits)...")
            print("[INFO] Query: 'What is 2+2?'")

            response_text = ""
            for event in agent.run_event_stream("What is 2+2?"):
                if event.type == "STEP_END":
                    response_text = event.content

            if response_text:
                print(f"[OK] Agent response: {response_text[:100]}...")
                return True
            else:
                print("[WARNING] Agent returned empty response")
                return False
        else:
            print("[INFO] Skipping API test (no API key configured)")
            print("[INFO] To test with API, configure your key in .env and run:")
            print("       python3 scripts/verify_setup.py --with-api")
            return True

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main verification flow"""
    print("=" * 70)
    print("FastReAct Nano - Setup Verification")
    print("=" * 70)

    # Parse arguments
    with_api = "--with-api" in sys.argv

    # Run checks
    checks = [
        ("Python Version", check_python_version),
        ("Environment Configuration", check_env_file),
        ("Dependencies", check_dependencies),
        ("Core Components", check_core_components),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"[ERROR] {name} check failed: {e}")
            results[name] = False

    # Run functionality test if other checks passed
    if all(results.values()):
        print("\n--- Functionality Test ---")
        results["Functionality Test"] = run_quick_test(with_api=with_api)

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    for name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")

    all_passed = all(results.values())

    print("=" * 70)

    if all_passed:
        print("\n[SUCCESS] All checks passed! FastReAct is ready to use.")
        print("\nNext steps:")
        print("  - Run unit tests: python3 run_tests.py unit")
        print("  - Test with query: python3 -m fastreact 'Hello'")
        print("  - Start Gateway: python3 -m fastreact.adapters.gateway")
        return 0
    else:
        print("\n[WARNING] Some checks failed. Please fix the issues above.")
        failed = [name for name, passed in results.items() if not passed]
        print(f"\nFailed checks: {', '.join(failed)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
