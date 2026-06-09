#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$ROOT/fastreact-nano"
FRONTEND="$ROOT/fastreact-nano-web"
GATEWAY_PORT="${GATEWAY_PORT:-9000}"
WEB_PORT="${WEB_PORT:-3000}"

load_env_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$file"
    set +a
  fi
}

load_env_file "$BACKEND/.env"
load_env_file "$FRONTEND/.env.local"

export PYTHONPATH="$BACKEND/src:${PYTHONPATH:-}"
export NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL="${NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL:-http://localhost:${GATEWAY_PORT}}"
export NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL="${NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL:-ws://localhost:${GATEWAY_PORT}}"
export FASTREACT_CORS_ORIGINS="${FASTREACT_CORS_ORIGINS:-http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}}"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting FastReAct Gateway on http://localhost:${GATEWAY_PORT}"
(
  cd "$BACKEND"
  python3 -c "from fastreact.adapters.gateway import run_gateway; run_gateway(host='${GATEWAY_HOST:-127.0.0.1}', port=${GATEWAY_PORT}, log_level='${GATEWAY_LOG_LEVEL:-info}')"
) &

echo "Starting FastReAct Web on http://localhost:${WEB_PORT}"
(
  cd "$FRONTEND"
  npm run dev -- -p "$WEB_PORT"
) &

wait
