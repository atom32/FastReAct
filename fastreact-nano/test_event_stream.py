#!/usr/bin/env python3
"""Test actual event streaming with a simple query"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact.adapters.web import WebSession, event_stream_generator

def test_simple_query():
    """Test a simple query to see event flow"""
    print("[TEST] Testing simple query: 'What files are in current directory?'")
    print("=" * 60)

    # Check if API key is set
    if not os.getenv("FASTRACT_API_KEY"):
        print("[SKIP] No FASTRACT_API_KEY set, skipping actual query test")
        print("[INFO] To test: export FASTRACT_API_KEY=sk-your-key")
        return

    # Create session
    session = WebSession()
    session.initialize()

    # Test query
    query = "What files are in current directory?"
    print(f"[INFO] Query: {query}")
    print("[INFO] Streaming events:")
    print("-" * 60)

    event_count = 0
    try:
        for event_text in event_stream_generator(session, query):
            event_count += 1
            print(f"[Event {event_count}] ", end="")
            print(event_text[:100] + "..." if len(event_text) > 100 else event_text)

        print("-" * 60)
        print(f"[OK] Total events received: {event_count}")
        print(f"[OK] Events in buffer: {len(session.event_buffer)}")

        # Check final answer
        if session.event_buffer:
            from fastreact.core.events import EventType
            final_events = [e for e in session.event_buffer if e["type"] == EventType.SESSION_END]
            if final_events:
                final_answer = final_events[-1].get("content", "")
                print(f"[OK] Final answer length: {len(final_answer)} chars")
                print(f"[Preview] {final_answer[:100]}...")

    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_query()
