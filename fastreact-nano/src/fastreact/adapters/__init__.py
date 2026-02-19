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

Feishu Adapter (SDK - Recommended):
    pip install fastreact-nano[feishu]
    python examples/feishu_sdk_bot.py

REPL Adapter (Development):
    pip install fastreact-nano[cli]
    python -m fastreact.adapters.repl
"""

__all__ = []
