"""
WebSocket Gateway Client Example for FastReAct Nano

Demonstrates how to interact with the Gateway adapter.
"""

import asyncio
import json
import sys

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("[ERROR] websockets not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def test_basic_query():
    """Test basic query through WebSocket"""
    uri = "ws://localhost:9000/ws"

    print("[INFO] Connecting to Gateway...")

    try:
        async with websockets.connect(uri) as ws:
            print("[OK] Connected\n")

            # Send query
            query = "What is FastReAct Nano?"
            message = {
                "type": "query",
                "content": query
            }

            print(f"[Query] {query}\n")
            await ws.send(json.dumps(message))

            # Receive responses
            while True:
                try:
                    response = await asyncio.wait_for(
                        ws.recv(),
                        timeout=10.0
                    )
                    data = json.loads(response)

                    msg_type = data.get("type")
                    content = data.get("content", "")

                    if msg_type == "user":
                        print(f"[You] {content}")
                    elif msg_type == "agent":
                        print(f"[Agent]\n{content}\n")
                        break  # Agent response complete
                    elif msg_type == "error":
                        print(f"[Error] {content}\n")
                        break

                except asyncio.TimeoutError:
                    print("[Timeout] No more responses")
                    break

    except Exception as e:
        print(f"[ERROR] {e}")


async def test_with_skill():
    """Test using a skill"""
    uri = "ws://localhost:9000/ws"

    print("[INFO] Testing with git_workflow skill...")

    try:
        async with websockets.connect(uri) as ws:
            print("[OK] Connected\n")

            # Send query with skill
            message = {
                "type": "query",
                "content": "如何创建新分支？",
                "skills": ["git_workflow"]
            }

            print(f"[Query] {message['content']}")
            print(f"[Skill] {message['skills'][0]}\n")

            await ws.send(json.dumps(message))

            # Receive responses
            while True:
                try:
                    response = await asyncio.wait_for(
                        ws.recv(),
                        timeout=10.0
                    )
                    data = json.loads(response)

                    msg_type = data.get("type")
                    content = data.get("content", "")

                    if msg_type == "user":
                        print(f"[You] {content}")
                    elif msg_type == "agent":
                        print(f"[Agent]\n{content}\n")
                        break
                    elif msg_type == "error":
                        print(f"[Error] {content}\n")
                        break

                except asyncio.TimeoutError:
                    print("[Timeout] No more responses")
                    break

    except Exception as e:
        print(f"[ERROR] {e}")


async def test_list_skills():
    """Test listing available skills"""
    uri = "ws://localhost:9000/ws"

    print("[INFO] Listing skills...")

    try:
        async with websockets.connect(uri) as ws:
            # Request skills list
            message = {"type": "list_skills"}
            await ws.send(json.dumps(message))

            # Receive response
            response = await ws.recv()
            data = json.loads(response)

            if data.get("type") == "skills":
                skills = data.get("skills", [])
                print(f"\n[Available Skills: {len(skills)}]\n")

                for skill in skills:
                    print(f"  • {skill}")
            else:
                print(f"[ERROR] Unexpected response: {data}")

    except Exception as e:
        print(f"[ERROR] {e}")


async def interactive_mode():
    """Interactive mode through WebSocket"""
    uri = "ws://localhost:9000/ws"

    print("[INFO] Starting interactive mode...")
    print("[Type 'quit' to exit]\n")

    try:
        async with websockets.connect(uri) as ws:
            print("[OK] Connected to Gateway\n")

            while True:
                # Get user input
                try:
                    query = input(">>> ")

                    if not query.strip():
                        continue

                    if query.lower() in ["quit", "exit", "q"]:
                        print("[INFO] Disconnecting...")
                        break

                    # Send query
                    message = {
                        "type": "query",
                        "content": query
                    }

                    await ws.send(json.dumps(message))

                    # Receive responses
                    while True:
                        response = await ws.recv()
                        data = json.loads(response)

                        msg_type = data.get("type")
                        content = data.get("content", "")

                        if msg_type == "user":
                            print(f"[You] {content}")
                        elif msg_type == "agent":
                            print(f"\n[Agent]\n{content}\n")
                            break  # Move to next query
                        elif msg_type == "error":
                            print(f"[Error] {content}\n")
                            break
                        elif msg_type == "pong":
                            continue  # Keepalive

                except KeyboardInterrupt:
                    print("\n[INFO] Interrupted")
                    break

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    import sys

    # Check if server is running
    async def check_server():
        try:
            async with websockets.connect("ws://localhost:9000/ws"):
                return True
        except:
            return False

    if not asyncio.run(check_server()):
        print("[ERROR] Cannot connect to Gateway server")
        print("\nStart the server first:")
        print("  pip install fastreact-nano[gateway]")
        print("  python -m fastreact.adapters.gateway")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  FastReAct Nano - WebSocket Gateway Client Demo")
    print("=" * 60 + "\n")

    # Run tests
    asyncio.run(test_list_skills())
    print()
    asyncio.run(test_basic_query())
    print()

    # Ask if user wants interactive mode
    try:
        answer = input("\nStart interactive mode? (y/N): ")
        if answer.lower() == "y":
            asyncio.run(interactive_mode())
    except KeyboardInterrupt:
        pass

    print("\n[SUCCESS] Demo completed!")
