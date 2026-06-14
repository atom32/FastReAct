#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$ROOT/fastreact-nano"
FRONTEND="$ROOT/fastreact-nano-web"
SERVICE_PORT="${FASTREACT_SERVICE_PORT:-8000}"
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
export NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL="${NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL:-http://localhost:${SERVICE_PORT}}"
export FASTREACT_CORS_ORIGINS="${FASTREACT_CORS_ORIGINS:-http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}}"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ ! -d "$FRONTEND/.next" ]]; then
  echo "Building FastReAct Web"
  (cd "$FRONTEND" && npm run build)
fi

echo "Starting FastReAct HTTP daemon on http://localhost:${SERVICE_PORT}"
(
  cd "$BACKEND"
  python3 -m fastreact.adapters.http --host "${FASTREACT_SERVICE_HOST:-127.0.0.1}" --port "$SERVICE_PORT" --log-level "${FASTREACT_LOG_LEVEL:-info}"
) &

echo "Starting FastReAct Web on http://localhost:${WEB_PORT}/service"
(
  cd "$FRONTEND"
  npm run start -- -p "$WEB_PORT"
) &

wait
