"""
Test Configuration Priority Manager

验证四层配置加载的优先级：
1. DEFAULT (最低)
2. PROJECT (./config.json)
3. USER (~/.fastreact/config.json)
4. ENV (最高)
"""

import os
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact.core.config_manager import ConfigManager


def test_config_priority():
    """Test configuration loading priority"""

    print("\n" + "="*70)
    print("FastReAct Configuration Priority Test")
    print("="*70)

    # Get current project root
    project_root = Path.cwd()

    # Test 1: Default configuration
    print("\n[Test 1] Default Configuration (No overrides)")
    print("-"*70)
    manager = ConfigManager(project_root)

    api_key_default = manager.get("llm.providers.siliconflow.api_key")
    provider_default = manager.get("llm.default_provider")
    mcp_enabled = manager.get("mcp.enabled")

    print(f"API Key: {api_key_default or 'None (default)'}")
    print(f"Provider: {provider_default}")
    print(f"MCP Enabled: {mcp_enabled}")

    # Test 2: Project configuration override
    print("\n[Test 2] Project Configuration Override")
    print("-"*70)

    project_config = project_root / "config.json"
    if project_config.exists():
        with open(project_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

        project_provider = config.get("llm", {}).get("default_provider")
        project_api_key = config.get("llm", {}).get("providers", {}).get("siliconflow", {}).get("api_key", "")

        print(f"Project Provider: {project_provider}")
        print(f"Project API Key: {project_api_key[:20]}...{project_api_key[-4:] if project_api_key else 'None'}")
        print(f"[OK] Project configuration loaded")
    else:
        print("[SKIP] No project configuration found")

    # Test 3: User configuration override
    print("\n[Test 3] User Configuration Override")
    print("-"*70)

    user_config_dir = Path.home() / ".fastreact"
    user_config_path = user_config_dir / "config.json"

    if user_config_path.exists():
        with open(user_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        user_api_key = config.get("llm", {}).get("providers", {}).get("siliconflow", {}).get("api_key", "")
        github_token = config.get("mcp", {}).get("servers", {}).get("github", {}).get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN", "")

        print(f"User API Key: {user_api_key[:20]}...{user_api_key[-4:] if user_api_key else 'None'}")
        print(f"GitHub Token: {github_token[:20]}...{github_token[-4:] if github_token else 'None'}")
        print(f"[OK] User configuration loaded")
    else:
        print("[SKIP] No user configuration found")
        print(f"       Expected: {user_config_path}")

    # Test 4: Environment variable override
    print("\n[Test 4] Environment Variable Override (Highest Priority)")
    print("-"*70)

    env_api_key = os.getenv("FASTREACT_API_KEY")
    env_model = os.getenv("FASTREACT_MODEL")
    env_base_url = os.getenv("FASTREACT_BASE_URL")

    print(f"DEBUG - os.getenv('FASTREACT_API_KEY'): {env_api_key}")
    print(f"DEBUG - os.getenv('FASTREACT_MODEL'): {env_model}")

    if env_api_key:
        print(f"ENV API Key: {env_api_key[:20]}...{env_api_key[-4:]}")
        print(f"[OK] Environment variable loaded")
    else:
        print("[SKIP] No FASTREACT_API_KEY environment variable")

    if env_model:
        print(f"ENV Model: {env_model}")
        print(f"[OK] Model override loaded")
    else:
        print("[SKIP] No FASTREACT_MODEL environment variable")

    if env_base_url:
        print(f"ENV Base URL: {env_base_url}")
        print(f"[OK] Base URL override loaded")
    else:
        print("[SKIP] No FASTREACT_BASE_URL environment variable")

    # Summary
    print("\n" + "="*70)
    print("Configuration Priority Summary")
    print("="*70)
    print("\nPriority (Highest to Lowest):")
    print("  1. Environment Variables (ENV)")
    print("  2. User Configuration (~/.fastreact/config.json)")
    print("  3. Project Configuration (./config.json)")
    print("  4. Default Values (code)")
    print("\nRecommendation:")
    print("  - Personal Use: Set up ~/.fastreact/config.json")
    print("  - Team Use: Use ./config.json (without API keys)")
    print("  - CI/CD: Use environment variables")
    print("  - Multi-tenant: Use environment variables per tenant")

    # Setup instructions
    print("\n" + "="*70)
    print("Setup User Configuration")
    print("="*70)

    if not user_config_path.exists():
        print(f"\nCreate user configuration:")
        print(f"  mkdir -p ~/.fastreact")
        print(f"  cat > ~/.fastreact/config.json << EOF")
        print(f'  {{')
        print(f'    "llm": {{')
        print(f'      "providers": {{')
        print(f'        "siliconflow": {{')
        print(f'          "api_key": "sk-your-key-here"')
        print(f'        }}')
        print(f'      }}')
        print(f'    }}')
        print(f'  }}')
        print(f"  EOF")
    else:
        print(f"\n[OK] User configuration already exists")
        print(f"     Location: {user_config_path}")

    print("\n" + "="*70)


def create_example_user_config():
    """Create example user configuration"""
    user_config_dir = Path.home() / ".fastreact"
    user_config_path = user_config_dir / "config.json"

    if user_config_path.exists():
        print(f"\n[SKIP] User config already exists: {user_config_path}")
        return

    # Create example config
    example_config = {
        "_comment": "FastReAct User Configuration",
        "_purpose": "Personal API keys and preferences (DO NOT COMMIT TO GIT)",
        "llm": {
            "providers": {
                "siliconflow": {
                    "api_key": "YOUR_SILICONFLOW_KEY_HERE",
                    "base_url": "https://api.siliconflow.cn/v1",
                    "model": "deepseek-ai/DeepSeek-V3"
                },
                "openai": {
                    "api_key": "YOUR_OPENAI_KEY_HERE",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4"
                }
            }
        },
        "mcp": {
            "servers": {
                "github": {
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_TOKEN_HERE"
                    }
                }
            }
        }
    }

    # Create directory
    user_config_dir.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(user_config_path, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Created example user config: {user_config_path}")
    print(f"     Please edit it and add your actual API keys")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--create-user-config":
        create_example_user_config()
    else:
        test_config_priority()
