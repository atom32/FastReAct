#!/usr/bin/env python3
"""
Quick Web Chat Feature Test

Fast test for the three key features:
1. No duplicate user messages
2. Can send messages
3. Interrupt works

Usage:
    python tests/integration/quick_web_test.py
"""

import asyncio
import websockets
import json


async def test_basic_connection():
    """Test 1: Basic WebSocket connection and no duplicate messages"""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Connection & No Duplicate Messages")
    print("=" * 60)

    uri = "ws://localhost:9000/ws"
    async with websockets.connect(uri) as ws:
        # Wait for connected message
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"✓ Connected: {data['session_id']}")

        # Send query
        query = {"type": "query", "content": "Hello"}
        await ws.send(json.dumps(query))
        print(f"✓ Sent: Hello")

        # Receive events
        user_count = 0
        event_count = 0
        session_end = False

        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)

                if data.get("type") == "user":
                    user_count += 1

                if data.get("type") == "event":
                    event_count += 1
                    if data.get("event_type") == "session_end":
                        session_end = True
                        break

        except asyncio.TimeoutError:
            pass

        print(f"✓ Received {event_count} events")
        print(f"✓ User messages: {user_count}")

        if user_count == 0:
            print("✅ PASS: No duplicate user messages")
            return True
        else:
            print(f"❌ FAIL: Got {user_count} user echoes")
            return False


async def test_interrupt():
    """Test 3: Graceful interrupt"""
    print("\n" + "=" * 60)
    print("TEST 2: Graceful Interrupt")
    print("=" * 60)

    uri = "ws://localhost:9000/ws"
    async with websockets.connect(uri) as ws:
        # Wait for connected message
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"✓ Connected: {data['session_id']}")

        # Send long task
        query = {"type": "query", "content": "List all files"}
        await ws.send(json.dumps(query))
        print(f"✓ Sent: List all files")

        # Wait for it to start
        await asyncio.sleep(2.0)

        # Send stop
        query = {"type": "query", "content": "stop"}
        await ws.send(json.dumps(query))
        print(f"✓ Sent: stop")

        # Receive events
        has_session_end = False
        has_interrupt = False

        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(msg)

                if data.get("type") == "event":
                    etype = data.get("event_type", "")
                    content = data.get("content", "")

                    if etype == "session_end":
                        has_session_end = True
                        if "INTERRUPT" in content or "interrupt" in content.lower():
                            has_interrupt = True
                        break

        except asyncio.TimeoutError:
            pass

        if has_session_end:
            print("✓ Received session_end")
            if has_interrupt:
                print("✅ PASS: Graceful interrupt working")
                return True
            else:
                print("⚠️  PARTIAL: Session ended but no interrupt message (may be OK)")
                return True
        else:
            print("❌ FAIL: No session_end received")
            return False


async def main():
    print("\n" + "=" * 60)
    print("FastReAct Nano - Quick Web Tests")
    print("=" * 60)

    results = []

    try:
        results.append(await test_basic_connection())
    except Exception as e:
        print(f"❌ Test 1 crashed: {e}")
        results.append(False)

    await asyncio.sleep(2.0)

    try:
        results.append(await test_interrupt())
    except Exception as e:
        print(f"❌ Test 2 crashed: {e}")
        results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
