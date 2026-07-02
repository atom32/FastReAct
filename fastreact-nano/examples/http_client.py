"""
HTTP API Client Example for FastReAct Nano

Demonstrates how to interact with the HTTP adapter.
"""

import requests
import json


def test_run():
    """Test running a query"""
    url = "http://localhost:18741/run"

    payload = {
        "query": "What is FastReAct Nano?",
        "model": "gpt-4o-mini",
        "stream": False
    }

    print("[INFO] Sending request to HTTP API...")
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"\n[Response]\n{data['response']}")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")


def test_with_skills():
    """Test using skills"""
    url = "http://localhost:18741/run"

    payload = {
        "query": "如何创建一个新的git分支？",
        "skills": ["git_workflow"]
    }

    print("[INFO] Testing with git_workflow skill...")
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"\n[Response]\n{data['response']}")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")


def test_list_skills():
    """Test listing skills"""
    url = "http://localhost:18741/skills"

    print("[INFO] Fetching skills list...")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print(f"\n[Available Skills: {len(data['skills'])}]\n")

        for skill in data['skills']:
            print(f"  • {skill['name']}: {skill['description']}")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")


def test_list_tools():
    """Test listing tools"""
    url = "http://localhost:18741/tools"

    print("[INFO] Fetching tools list...")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print(f"\n[Available Tools: {len(data['tools'])}]\n")

        for tool in data['tools']:
            print(f"  • {tool}")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")


def test_health():
    """Test health check"""
    url = "http://localhost:18741/health"

    print("[INFO] Checking server health...")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print(f"\n[Status: {data['status']}]")
        print(f"[Agent: {'Running' if data['agent'] else 'Stopped'}]")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")


if __name__ == "__main__":
    import sys

    # Check if server is running
    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to HTTP server")
        print("\nStart the server first:")
        print("  pip install fastreact-nano[http]")
        print("  python -m fastreact.adapters.http")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  FastReAct Nano - HTTP API Client Demo")
    print("=" * 60 + "\n")

    # Run tests
    test_list_tools()
    print()
    test_list_skills()
    print()
    test_run()
    print()
    test_with_skills()

    print("\n[SUCCESS] All tests completed!")
