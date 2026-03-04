"""
FastReAct Nano - Main entry point

Run adapters directly:
    python -m fastreact.adapters.http
    python -m fastreact.adapters.gateway
    python -m fastreact.adapters.feishu_sdk
"""

import sys


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m fastreact.adapters.<adapter>")
        print("")
        print("Available adapters:")
        print("  python -m fastreact.adapters.http        # HTTP server")
        print("  python -m fastreact.adapters.gateway     # WebSocket gateway")
        print("  python -m fastreact.adapters.feishu_sdk  # Feishu bot (SDK mode)")
        return 1

    adapter = sys.argv[1]

    if adapter == "http":
        from fastreact.adapters.http import run_server
        run_server()
    elif adapter == "gateway":
        from fastreact.adapters.gateway import run_gateway
        run_gateway()
    elif adapter == "feishu_sdk":
        from fastreact.adapters.feishu_sdk import run_feishu_sdk
        run_feishu_sdk()
    else:
        print(f"Unknown adapter: {adapter}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
