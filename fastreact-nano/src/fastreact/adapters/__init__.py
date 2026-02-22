"""
FastReAct Nano Adapters

Peripheral systems for interacting with the Nano kernel:

CLI Adapter:
    pip install fastreact-nano[cli]
    fastreact "help me analyze code"

HTTP Adapter (OpenAI-compatible):
    pip install fastreact-nano[http]
    python -m fastreact.adapters.http

Gateway Adapter:
    pip install fastreact-nano[gateway]
    python -m fastreact.adapters.gateway

Telegram Adapter:
    pip install fastreact-nano[telegram]
    export TELEGRAM_BOT_TOKEN="your_token_from_botfather"
    python -m fastreact.adapters.telegram

Feishu Adapter (SDK - Recommended):
    pip install fastreact-nano[feishu]
    python examples/feishu_sdk_bot.py

REPL Adapter (Development):
    pip install fastreact-nano[cli]
    python -m fastreact.adapters.repl
"""

from fastreact.adapters.base import BaseAdapter
from fastreact.adapters.telegram import TelegramAdapter

__all__ = [
    "BaseAdapter",
    "TelegramAdapter",
]
