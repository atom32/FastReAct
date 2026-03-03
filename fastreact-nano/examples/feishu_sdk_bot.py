#!/usr/bin/env python3
"""
FastReAct Nano - Feishu SDK Bot Quickstart

This example shows how to run FastReAct Nano as a Feishu bot using the official
lark-oapi SDK with WebSocket long connection (the "ultimate form").

Features:
- No webhook server needed
- No public network exposure
- Automatic reconnection
- Multi-tenant user isolation
- Real-time streaming updates

Setup:
1. Install dependencies:
   pip install "fastreact-nano[all]"

2. Set environment variables:
   export FASTRACT_API_KEY="sk-xxx"
   export FASTRACT_MODEL="gpt-4o-mini"

   export FEISHU_APP_ID="cli_xxxxxxxxx"
   export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"

3. Run the bot:
   python examples/feishu_sdk_bot.py

Configuration:
- FEISHU_CONNECTION_MODE: "sdk" (use official SDK with WebSocket)
- FEISHU_MULTITENANT: "true" (enable multi-tenant user isolation)
- FEISHU_AUTO_RECONNECT: "true" (auto-reconnect on connection loss)
- FEISHU_LOG_LEVEL: "info" (log level: debug, info, warn, error)
"""

import os
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import Agent, Config, FeishuConfig
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter


def main():
    """Main entry point"""

    print("=" * 60)
    print("FastReAct Nano - Feishu SDK Bot")
    print("=" * 60)

    # Load configuration from file (includes MCP and Feishu config)
    # Falls back to environment variables if file not found
    config = Config.load()

    # Use Feishu config from loaded config (unified approach)
    feishu_config = config.feishu

    # Validate configuration
    if not feishu_config.app_id or not feishu_config.app_secret:
        print("[ERROR] FEISHU_APP_ID and FEISHU_APP_SECRET are required")
        print("")
        print("Please set these environment variables:")
        print("  export FEISHU_APP_ID='cli_xxxxxxxxx'")
        print("  export FEISHU_APP_SECRET='xxxxxxxxxxxxxxxxxxxx'")
        sys.exit(1)

    if not config.llm.api_key:
        print("[ERROR] FASTRACT_API_KEY is required")
        print("")
        print("Please set your API key:")
        print("  export FASTRACT_API_KEY='sk-xxx'")
        sys.exit(1)

    # Create agent
    print(f"[INFO] Creating agent with model: {config.llm.model}")
    agent = Agent(config=config, multitenant=True)

    # Create Feishu SDK adapter
    print("[INFO] Initializing Feishu SDK adapter")
    print(f"[INFO] Connection mode: {feishu_config.connection_mode}")
    print(f"[INFO] Multi-tenant: {feishu_config.enable_multitenant}")
    print(f"[INFO] Auto-reconnect: {feishu_config.auto_reconnect}")

    adapter = FeishuSDKAdapter(agent, feishu_config)

    # Start the bot (blocking)
    print("")
    print("[INFO] Bot is running. Press Ctrl+C to stop.")
    print("")

    try:
        adapter.start()
    except KeyboardInterrupt:
        print("")
        print("[INFO] Bot stopped by user")
    except Exception as e:
        print(f"[ERROR] Bot failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
