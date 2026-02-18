"""
FastReAct Nano Adapters

Peripheral systems for interacting with the Nano kernel:

Web Adapter:
    pip install fastreact-nano[web]
    streamlit run src/fastreact/adapters/web.py

CLI Adapter:
    pip install fastreact-nano[cli]
    fastreact "help me analyze code"

HTTP Adapter:
    pip install fastreact-nano[http]
    python -m fastreact.adapters.http

Gateway Adapter:
    pip install fastreact-nano[gateway]
    python -m fastreact.adapters.gateway

Feishu Adapter (Webhook):
    pip install fastreact-nano[feishu]
    python examples/feishu_webhook_bot.py

Feishu Adapter (SDK - Recommended):
    pip install fastreact-nano[feishu]
    python examples/feishu_sdk_bot.py
"""

__all__ = []
