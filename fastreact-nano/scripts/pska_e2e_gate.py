#!/usr/bin/env python3
"""Run the PSKA/FastReAct cross-repo HTTP/SSE smoke gate."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_PSKA_CORE = Path("/Users/xudawei/Documents/personal archive/core")
DEFAULT_PSKA_PYTHON = Path("/Users/xudawei/Documents/personal archive/.pska/venvs/pska-py312/bin/python")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PSKA's FastReAct HTTP/SSE E2E gate")
    parser.add_argument(
        "--pska-core",
        type=Path,
        default=Path(os.getenv("PSKA_CORE", DEFAULT_PSKA_CORE)),
        help="Path to the PSKA core directory.",
    )
    parser.add_argument(
        "--python",
        dest="pska_python",
        type=Path,
        default=Path(os.getenv("PSKA_PYTHON", DEFAULT_PSKA_PYTHON)),
        help="Python executable used by PSKA's MCP server.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Exit 0 when PSKA is not checked out on this machine.",
    )
    args = parser.parse_args()

    script = args.pska_core / "scripts" / "fastreact_http_sse_e2e.py"
    if not script.exists():
        message = f"[pska-e2e] missing PSKA E2E script: {script}"
        if args.allow_missing:
            print(f"{message}; skipping because --allow-missing was set")
            return 0
        print(message, file=sys.stderr)
        return 2

    cmd = [sys.executable, str(script)]
    if args.pska_python.exists():
        cmd.extend(["--python", str(args.pska_python)])
    else:
        print(f"[pska-e2e] PSKA python not found at {args.pska_python}; using script default")

    print(f"[pska-e2e] cwd: {args.pska_core}")
    print(f"[pska-e2e] command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=args.pska_core)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
