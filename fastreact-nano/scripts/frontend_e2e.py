#!/usr/bin/env python3
"""Run frontend E2E against a local Gateway and Next dev server."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "fastreact-nano"
FRONTEND = ROOT / "fastreact-nano-web"
ARTIFACT_DIR = BACKEND / ".fastreact" / "e2e"
GATEWAY_PORT = int(os.getenv("FASTREACT_E2E_GATEWAY_PORT", "19000"))
WEB_PORT = int(os.getenv("FASTREACT_E2E_WEB_PORT", "13000"))


def wait_http(url: str, timeout: float = 45.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001 - surfaced below with context
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_process(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def stop_process(proc: subprocess.Popen | None) -> None:
    if not proc or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=8)
    except Exception:
        os.killpg(proc.pid, signal.SIGKILL)


def tail_output(proc: subprocess.Popen | None, label: str) -> str:
    if not proc or not proc.stdout:
        return ""
    try:
        output = proc.stdout.read() or ""
    except Exception:
        output = ""
    return f"\n[{label}]\n{output[-4000:]}" if output else ""


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    if port_open(GATEWAY_PORT):
        raise RuntimeError(f"Port {GATEWAY_PORT} is already in use")
    if port_open(WEB_PORT):
        raise RuntimeError(f"Port {WEB_PORT} is already in use")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND / "src")
    env["NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL"] = f"http://127.0.0.1:{GATEWAY_PORT}"
    env["NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL"] = f"ws://127.0.0.1:{GATEWAY_PORT}"
    env["FASTREACT_CORS_ORIGINS"] = f"http://127.0.0.1:{WEB_PORT},http://localhost:{WEB_PORT}"

    gateway_cmd = [
        "python3",
        "-c",
        (
            "from pathlib import Path; "
            "from fastreact.adapters.gateway import run_gateway; "
            f"run_gateway(host='127.0.0.1', port={GATEWAY_PORT}, log_level='warning', "
            f"base_workspace=Path(r'{ARTIFACT_DIR / 'workspace'}'))"
        ),
    ]
    web_cmd = ["npm", "run", "start", "--", "-p", str(WEB_PORT)]
    e2e_cmd = ["node", str(FRONTEND / "scripts" / "frontend-e2e.mjs")]

    gateway = web = None
    try:
        gateway = start_process(gateway_cmd, BACKEND, env)
        wait_http(f"http://127.0.0.1:{GATEWAY_PORT}/api/status")

        build = subprocess.run(["npm", "run", "build"], cwd=FRONTEND, env=env, text=True)
        if build.returncode != 0:
            return build.returncode

        web = start_process(web_cmd, FRONTEND, env)
        wait_http(f"http://127.0.0.1:{WEB_PORT}")

        e2e_env = env | {
            "E2E_WEB_URL": f"http://127.0.0.1:{WEB_PORT}",
            "E2E_GATEWAY_HTTP_URL": f"http://127.0.0.1:{GATEWAY_PORT}",
            "E2E_GATEWAY_WS_URL": f"ws://127.0.0.1:{GATEWAY_PORT}/ws",
            "E2E_ARTIFACT_DIR": str(ARTIFACT_DIR),
        }
        result = subprocess.run(e2e_cmd, cwd=FRONTEND, env=e2e_env, text=True)
        return result.returncode
    finally:
        stop_process(web)
        stop_process(gateway)
        if gateway and gateway.returncode not in (0, None):
            sys.stderr.write(tail_output(gateway, "gateway"))
        if web and web.returncode not in (0, None):
            sys.stderr.write(tail_output(web, "web"))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CLI entrypoint
        print(f"[frontend-e2e] failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
