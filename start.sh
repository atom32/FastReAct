#!/usr/bin/env bash
# Start the FastReAct daemon and OpenClaw-like service console.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/fastreact-nano"
FRONTEND="$ROOT/fastreact-nano-web"
SERVICE_HOST="${FASTREACT_SERVICE_HOST:-127.0.0.1}"
SERVICE_PORT="${FASTREACT_SERVICE_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
HTTP_LOG="${FASTREACT_HTTP_LOG:-/tmp/fastreact-http.log}"
WEB_LOG="${FASTREACT_WEB_LOG:-/tmp/fastreact-web.log}"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

load_env_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$file"
    set +a
  fi
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-30}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

cleanup() {
  echo ""
  echo -e "${YELLOW}Stopping FastReAct services...${NC}"
  [[ -n "${SERVICE_PID:-}" ]] && kill "$SERVICE_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}

trap cleanup INT TERM

if [[ ! -d "$BACKEND" || ! -d "$FRONTEND" ]]; then
  echo -e "${RED}Run this script from the FastReAct repository root.${NC}"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}python3 is required.${NC}"
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo -e "${RED}Node.js and npm are required for the service console.${NC}"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo -e "${RED}curl is required for local readiness checks.${NC}"
  exit 1
fi

load_env_file "$BACKEND/.env"
load_env_file "$FRONTEND/.env.local"

export PYTHONPATH="$BACKEND/src:${PYTHONPATH:-}"
export NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL="${NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL:-http://${SERVICE_HOST}:${SERVICE_PORT}}"
export FASTREACT_CORS_ORIGINS="${FASTREACT_CORS_ORIGINS:-http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}}"

echo -e "${BLUE}Starting FastReAct daemon...${NC}"
(
  cd "$BACKEND"
  python3 -m fastreact.adapters.http \
    --host "$SERVICE_HOST" \
    --port "$SERVICE_PORT" \
    --log-level "${FASTREACT_LOG_LEVEL:-info}"
) >"$HTTP_LOG" 2>&1 &
SERVICE_PID=$!

if ! wait_for_http "http://${SERVICE_HOST}:${SERVICE_PORT}/health" 40; then
  echo -e "${RED}FastReAct daemon did not become healthy.${NC}"
  echo "Log: $HTTP_LOG"
  tail -n 40 "$HTTP_LOG" || true
  cleanup
  exit 1
fi

echo -e "${GREEN}Daemon ready:${NC} http://${SERVICE_HOST}:${SERVICE_PORT}"
echo "Daemon log: $HTTP_LOG"

if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo -e "${YELLOW}Installing web console dependencies...${NC}"
  (cd "$FRONTEND" && npm install)
fi

echo -e "${BLUE}Starting FastReAct service console...${NC}"
(
  cd "$FRONTEND"
  npm run dev -- -p "$WEB_PORT"
) >"$WEB_LOG" 2>&1 &
WEB_PID=$!

if ! wait_for_http "http://127.0.0.1:${WEB_PORT}/service" 60; then
  echo -e "${RED}Service console did not become ready.${NC}"
  echo "Log: $WEB_LOG"
  tail -n 60 "$WEB_LOG" || true
  cleanup
  exit 1
fi

echo ""
echo -e "${GREEN}FastReAct is ready.${NC}"
echo "Service console: http://127.0.0.1:${WEB_PORT}/service"
echo "Daemon health:   http://${SERVICE_HOST}:${SERVICE_PORT}/health"
echo "Daemon ready:    http://${SERVICE_HOST}:${SERVICE_PORT}/ready"
echo ""
echo "Logs:"
echo "  daemon: $HTTP_LOG"
echo "  web:    $WEB_LOG"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both services.${NC}"

wait "$WEB_PID"
