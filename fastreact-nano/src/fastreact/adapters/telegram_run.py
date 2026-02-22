#!/usr/bin/env python3
"""
Telegram Bot Runner for FastReAct Nano

This script starts the Telegram bot adapter.

Usage:
    # Set token
    export TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"

    # Run bot
    python3 -m fastreact.adapters.telegram
"""

import asyncio
import os
import sys

from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import Agent, Config
from fastreact.adapters.telegram import TelegramAdapter


async def main():
    """Main entry point"""
    # Get token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("[ERROR] TELEGRAM_BOT_TOKEN environment variable not set")
        print("\nHow to get a token:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot command")
        print("3. Follow the prompts to create your bot")
        print("4. Copy the token (looks like: 123456789:ABCdefGhIJKlnMoPQRsTUVwxyZ")
        print("\nThen set the environment variable:")
        print("export TELEGRAM_BOT_TOKEN='your_token_here'")
        sys.exit(1)

    # Create agent
    try:
        config = Config.load()
        agent = Agent(config=config)
    except Exception as e:
        print(f"[ERROR] Failed to initialize Agent: {e}")
        sys.exit(1)

    # Create and start adapter
    adapter = TelegramAdapter(token=token, agent=agent)

    print(f"[INFO] Starting FastReAct Nano Telegram bot...")
    print(f"[INFO] Press Ctrl+C to stop")

    try:
        await adapter.start()
    except KeyboardInterrupt:
        print("\n[INFO] Received shutdown signal")
    finally:
        await adapter.stop()
        print("[OK] Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
