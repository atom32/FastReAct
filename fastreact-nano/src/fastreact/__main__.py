"""
FastReAct Nano - Main entry point

Run adapters directly:
    python -m fastreact.adapters.http
    python -m fastreact http
"""

import sys


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m fastreact.adapters.<adapter>")
        print("")
        print("Available adapters:")
        print("  python -m fastreact http        # HTTP daemon (Daemon 1.0 default)")
        return 1

    adapter = sys.argv[1]

    if adapter == "http":
        from fastreact.adapters.http import run_server
        run_server()
    else:
        print(f"Unknown adapter: {adapter}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
