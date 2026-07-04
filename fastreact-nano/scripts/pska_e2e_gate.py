#!/usr/bin/env python3
"""Run the live PSKA/FastReAct cross-repo MCP+LLM smoke gate."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path


DEFAULT_PSKA_ROOT = Path("/Users/xudawei/Documents/personal archive")


def default_pska_root() -> Path:
    root = os.getenv("PSKA_ROOT") or os.getenv("PSKA_REPO")
    if root:
        return Path(root)
    core = os.getenv("PSKA_CORE")
    if core:
        return Path(core).expanduser().parent
    return DEFAULT_PSKA_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PSKA's live FastReAct MCP+LLM E2E gate")
    parser.add_argument(
        "--pska-root",
        type=Path,
        default=default_pska_root(),
        help="Path to the PSKA repository root.",
    )
    parser.add_argument(
        "--pska-core",
        type=Path,
        default=None,
        help="Deprecated compatibility option. When set, its parent is used as --pska-root.",
    )
    parser.add_argument(
        "--python",
        dest="pska_python",
        type=Path,
        default=Path(os.getenv("PSKA_PYTHON")) if os.getenv("PSKA_PYTHON") else None,
        help="Deprecated compatibility option from the old fake-agent gate; ignored.",
    )
    parser.add_argument(
        "--smoke-script",
        type=Path,
        default=None,
        help="Override the live PSKA smoke script path.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Timeout passed to pska-fastreact-kb-scope-smoke.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Exit 0 when PSKA is not checked out on this machine.",
    )
    args = parser.parse_args()

    pska_root = resolve_pska_root(args.pska_root, args.pska_core)
    script = args.smoke_script.expanduser() if args.smoke_script else pska_root / "scripts" / "pska-fastreact-kb-scope-smoke"
    if not script.exists():
        message = f"[pska-e2e] missing PSKA live smoke script: {script}"
        if args.allow_missing:
            print(f"{message}; skipping because --allow-missing was set")
            return 0
        print(message, file=sys.stderr)
        return 2

    if args.pska_python:
        print(
            "[pska-e2e] --python is deprecated and ignored; live smoke uses the running PSKA service, "
            "running FastReAct daemon, real LLM, and HTTP MCP.",
            file=sys.stderr,
        )

    cmd = build_smoke_command(script, timeout_seconds=args.timeout_seconds)
    print(f"[pska-e2e] cwd: {pska_root}")
    print(f"[pska-e2e] command: {shlex.join(cmd)}")
    result = subprocess.run(cmd, cwd=pska_root)
    return result.returncode


def resolve_pska_root(pska_root: Path, pska_core: Path | None) -> Path:
    if pska_core is not None:
        return pska_core.expanduser().resolve().parent
    return pska_root.expanduser()


def build_smoke_command(script: Path, *, timeout_seconds: float | None = None) -> list[str]:
    cmd = [str(script)] if os.access(script, os.X_OK) else [sys.executable, str(script)]
    if timeout_seconds is not None:
        cmd.extend(["--timeout-seconds", str(timeout_seconds)])
    return cmd


if __name__ == "__main__":
    raise SystemExit(main())
