#!/usr/bin/env python3
"""Test LLM connection and debug LiteLLM issues"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_llm_connection():
    """Test if LLM can be called successfully"""

    # Load config
    from fastreact.core.config import Config
    config = Config.load()

    print("=" * 60)
    print("LLM Configuration Test")
    print("=" * 60)
    print(f"Model: {config.llm.model}")
    print(f"API Base: {config.llm.api_base}")
    api_key = config.llm.api_key or ""
    print(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
    print(f"Temperature: {config.llm.temperature}")
    print(f"Max Tokens: {config.llm.max_tokens}")
    print()

    # Turn on LiteLLM debugging
    try:
        import litellm
        litellm._turn_on_debug()
        print("[OK] LiteLLM debug mode enabled")
    except Exception as e:
        print(f"[WARNING] Could not enable LiteLLM debug: {e}")
    print()

    # Test LLM call
    print("[INFO] Testing LLM call...")
    print("-" * 60)

    try:
        from fastreact.providers.litellm import LiteLLMProvider
        import asyncio

        provider = LiteLLMProvider(config.llm)

        # Simple test prompt
        messages = [
            {"role": "user", "content": "你好"}
        ]

        print(f"[INFO] Sending messages: {messages}")
        print()

        # Call LLM (async method)
        response = asyncio.run(provider.chat(messages))

        print()
        print("-" * 60)
        print("[OK] LLM call successful!")
        print(f"Response: {response}")
        print()
        print("[SUCCESS] LLM is working correctly")
        return True

    except Exception as e:
        print()
        print("-" * 60)
        print("[ERROR] LLM call failed!")
        print(f"Exception type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print()

        # Print full traceback
        import traceback
        print("Full traceback:")
        traceback.print_exc()

        return False

if __name__ == "__main__":
    success = test_llm_connection()
    sys.exit(0 if success else 1)
