"""
Demo script for session resume feature

Creates a test session and demonstrates the resume prompt.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime


def create_demo_session():
    """Create a demo session file in current directory"""
    # Create .fastreact directory
    fastreact_dir = Path.cwd() / ".fastreact"
    fastreact_dir.mkdir(parents=True, exist_ok=True)

    # Create session file
    session_file = fastreact_dir / f"autosave_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    session_data = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "title": "Demo Session - Testing Resume Feature",
        "messages": [
            {"role": "user", "content": "What is FastReAct?"},
            {"role": "assistant", "content": "FastReAct is a lightweight AI agent framework."},
            {"role": "user", "content": "Show me an example"},
            {"role": "assistant", "content": "Here's how to use it..."},
            {"role": "user", "content": "Thanks!"},
            {"role": "assistant", "content": "You're welcome!"},
        ],
        "variables": {
            "project": "FastReAct",
            "version": "1.1.0",
            "feature": "Session Resume"
        },
    }

    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print("Demo session created!")
    print("="*70)
    print(f"\nLocation: {session_file}")
    print(f"\nSession info:")
    print(f"  Title: {session_data['title']}")
    print(f"  Messages: {len(session_data['messages'])}")
    print(f"  Variables: {len(session_data['variables'])}")
    print(f"  Time: {session_data['timestamp']}")

    print("\n" + "="*70)
    print("Next steps:")
    print("="*70)
    print("\n1. Run the REPL to see the resume prompt:")
    print("   $ python -m fastreact.cli.main shell")
    print("\n2. You should see:")
    print("   'Previous session detected:'")
    print("   'Continue? [Y/n]'")
    print("\n3. Type 'Y' to resume or 'N' to start fresh")
    print("\n4. To clean up demo session:")
    print("   $ rm .fastreact/autosave_demo_*.json")
    print("\n" + "="*70)


if __name__ == "__main__":
    create_demo_session()
