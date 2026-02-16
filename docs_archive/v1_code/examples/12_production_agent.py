"""
Production-Ready FastReAct Agent

This is a complete, production-ready example that demonstrates:
- Auto configuration loading
- Environment variable support
- All advanced features enabled
- Proper error handling
- Logging
- Tool Display integration

Usage:
    # Set environment variables first
    export FASTREACT_API_KEY=your-key
    export FASTREACT_BASE_URL=https://api.siliconflow.cn/v1

    # Run
    python examples/12_production_agent.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import FastReAct
from fastreact.bootstrap.config_loader import (
    load_config,
    get_api_key,
    get_base_url,
    get_model,
)
from fastreact.context import ContextConfig, PruningConfig
from fastreact.core import (
    ToolPolicy,
    ToolPolicyConfig,
    PolicyMode,
    ApprovalManager,
    ApprovalConfig,
    ApprovalMode,
    ToolDisplay,
    DisplayConfig,
    DisplayMode,
)
from fastreact.tools import (
    create_bash_tool,
    create_edit_file_tool,
    create_repo_map_tool,
    create_sandbox_exec_tool,
)


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_production_agent():
    """Create a production-ready FastReAct agent with all features"""

    # Load configuration
    config = load_config()

    # Get credentials from config or environment
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    print(f"[START] Initializing FastReAct Agent")
    print(f"   Model: {model}")
    print(f"   Base URL: {base_url}")
    print()

    # Setup logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    # Create Context Configuration with Pruning
    context_config = ContextConfig(
        max_history_tokens=48000,
        smart_truncate=True,
        pruning=PruningConfig(
            enabled=config.get("context", {}).get("pruning", {}).get("enabled", True),
            target_ratio=0.5,
            min_messages=10,
            tool_result_max_lines=50,
            preserve_recent_count=5
        )
    )

    # Create Tool Policy
    tool_policy_config = ToolPolicyConfig.from_dict(
        config.get("tool_policy", {})
    )
    tool_policy = ToolPolicy(tool_policy_config)

    # Create Approval Manager
    approval_config = ApprovalConfig.from_dict(
        config.get("approval", {})
    )

    # Create approval callback
    def get_user_approval(request):
        """Get user approval for tool execution"""
        from fastreact.core import ApprovalResponse

        print(f"\n{'='*60}")
        print(f"[WARNING]  Tool Execution Request")
        print(f"{'='*60}")
        print(f"Tool: {request.tool_name}")
        print(f"Risk Level: {request.risk_level.name}")
        print(f"Parameters: {request.parameters}")
        print(f"Reason: {request.reason}")
        print(f"{'='*60}")

        while True:
            response = input("Allow execution? (y/n/v=details/q=quit): ").lower().strip()

            if response in ['y', 'yes']:
                return ApprovalResponse.ALLOW
            elif response in ['n', 'no']:
                return ApprovalResponse.DENY
            elif response == 'v':
                print(f"\nDetails:")
                print(f"  Request ID: {request.request_id}")
                print(f"  Created: {request.created_at}")
                print(f"  Timeout: {request.timeout}s")
                print(f"  Context: {request.context}")
            elif response in ['q', 'quit']:
                return ApprovalResponse.CANCEL
            else:
                print("Please enter y/n/v/q")

    approval = ApprovalManager(approval_config)
    approval.set_user_input_callback(get_user_approval)

    # Create Tool Display
    display_config = DisplayConfig(
        mode=DisplayMode.NORMAL,
        use_colors=config.get("display", {}).get("use_colors", True),
        show_time=True,
        show_risk=True
    )
    display = ToolDisplay(display_config)

    # Create Agent with all features
    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
        context_config=context_config,
        policy=tool_policy,
        approval=approval,
        display=display,
        enable_cache=config.get("react", {}).get("enable_cache", True),
        enable_event_stream=True
    )

    return agent, display


def main():
    """Main entry point"""

    try:
        # Create production agent
        agent, display = create_production_agent()

        print("=" * 60)
        print("FastReAct Production Agent Ready!")
        print("=" * 60)
        print()
        print("Features enabled:")
        print("  [OK] Context Pruning (50% token reduction)")
        print("  [OK] Tool Policy (security control)")
        print("  [OK] Approval Workflow (user confirmation)")
        print("  [OK] Tool Display (formatted output)")
        print("  [OK] LRU Cache (performance)")
        print()
        print("Enter your queries (or 'quit' to exit):")
        print("-" * 60)

        # Interactive loop
        while True:
            try:
                query = input("\nYou: ").strip()

                if not query:
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                # Process query
                print(f"\n[BOT] Processing: {query}")
                print("-" * 60)

                result = agent.run(query)

                print("\n[OK] Answer:")
                print(result["answer"])

                if "stats" in result:
                    stats = result["stats"]
                    print(f"\n[STATS] Stats:")
                    print(f"   Iterations: {stats.get('iterations', 0)}")
                    print(f"   Tool Calls: {stats.get('tool_calls', 0)}")
                    print(f"   Tokens Used: {stats.get('tokens_used', 0)}")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n[ERROR] Error: {e}")
                import traceback
                traceback.print_exc()

    except ValueError as e:
        print(f"\n[ERROR] Configuration Error: {e}")
        print("\nPlease check:")
        print("  1. .env file exists")
        print("  2. FASTREACT_API_KEY is set")
        print("  3. API key is valid")
        print("\nRun: cp .env.example .env")
        print("Then: vim .env  # Add your API key")
        sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
