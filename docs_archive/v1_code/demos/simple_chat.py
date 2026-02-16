"""
FastReAct Simple Chat Demo

Simple terminal chat without any channel integration.
"""

import asyncio
import os
import sys
from fastreact import FastReAct


async def main():
    print("=" * 60)
    print("FastReAct Simple Chat Demo")
    print("=" * 60)

    # Read API config
    import json
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        # Try different config formats
        if "api_key" in config:
            api_key = config["api_key"]
            model = config.get("model", "deepseek-ai/DeepSeek-V3")
        elif "llm" in config and "providers" in config["llm"]:
            default_provider = config.get("default_provider", "siliconflow")
            provider_config = config["llm"]["providers"].get(default_provider, {})
            api_key = provider_config.get("api_key")
            model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")
        else:
            raise ValueError("Unknown config format")

    except Exception as e:
        # Fallback to env vars
        print(f"[*] Config load failed: {e}")
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3")

    if not api_key:
        print("\n[ERROR] API Key not found")
        print("\nPlease configure via:")
        print("1. Create config.json:")
        print('   {')
        print('     "api_key": "your-api-key",')
        print('     "model": "deepseek-ai/DeepSeek-V3"')
        print('   }')
        print("\n2. Or set environment variables:")
        print('   set LLM_API_KEY=your-api-key')
        print('   set LLM_MODEL=deepseek-ai/DeepSeek-V3')
        return

    # Create FastReAct Agent
    print(f"\n[*] Initializing Agent (model: {model})...")
    agent = FastReAct(
        api_key=api_key,
        model=model,
        max_iterations=5,
        verbose=False
    )

    print("[OK] Agent ready!\n")
    print("Commands:")
    print("  - Type your message to chat")
    print("  - Type 'quit' or 'exit' to exit")
    print("  - Type 'reset' to reset conversation")
    print("-" * 60)

    session_id = "simple_chat_session"

    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # Check exit command
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n[BYE] Goodbye!")
                break

            # Check reset command
            if user_input.lower() == 'reset':
                print("\n[RESET] Conversation reset")
                session_id = f"simple_chat_{asyncio.get_event_loop().time()}"
                continue

            # Run Agent
            print("\nAI: ", end="", flush=True)
            result = await agent.run_async(user_input)
            answer = result['answer'] if isinstance(result, dict) else result
            print(answer)

        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("Please try again or type 'quit' to exit")

    # Cleanup
    await agent.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")

