#!/usr/bin/env bash
# Start the FastReAct daemon and local service console from a JSON config.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/fastreact-nano"
FRONTEND="$ROOT/fastreact-nano-web"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

resolve_config() {
  local requested="${1:-}"
  if [[ -n "$requested" ]]; then
    if [[ ! -f "$requested" ]]; then
      echo -e "${RED}Config file not found:${NC} $requested" >&2
      exit 1
    fi
    python3 - "$requested" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
    return
  fi

  local candidates=(
    "$ROOT/.fastreact/config.json"
    "$HOME/.fastreact/config.json"
    "$BACKEND/.fastreact/config.json"
    "$BACKEND/config.json"
  )
  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      python3 - "$candidate" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
      return
    fi
  done

  echo -e "${RED}Missing FastReAct config.${NC}" >&2
  echo "Create one at $ROOT/.fastreact/config.json, or pass a path: ./start.sh /path/to/config.json" >&2
  exit 1
}

read_start_config() {
  local config="$1"
  python3 - "$config" "$ROOT" <<'PY'
from pathlib import Path
import json
import shlex
import sys

config_path = Path(sys.argv[1]).expanduser().resolve()
root = Path(sys.argv[2]).resolve()
data = json.loads(config_path.read_text(encoding="utf-8"))

def get(path, default=None):
    value = data
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value

def as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

def as_path(value, default=None):
    if value in (None, ""):
        value = default
    if value in (None, ""):
        return ""
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = root / path
    return str(path)

def emit(key, value):
    print(f"{key}={shlex.quote(str(value))}")

emit("WEB_ENABLED", "true" if as_bool(get(["web", "enabled"], True), True) else "false")
emit("WEB_HOST", get(["web", "host"], "127.0.0.1"))
emit("WEB_PORT", int(get(["web", "port"], 3000)))
emit("HTTP_LOG", as_path(get(["logs", "http"]), "/tmp/fastreact-http.log"))
emit("WEB_LOG", as_path(get(["logs", "web"]), "/tmp/fastreact-web.log"))
emit("PSKA_ENABLED", "true" if as_bool(get(["pska", "enabled"], False), False) else "false")
emit("PSKA_REFRESH_CONFIG", "true" if as_bool(get(["pska", "refresh_config"], False), False) else "false")
emit("PSKA_ARCHIVE", as_path(get(["pska", "archive"]), ""))
emit("PSKA_CONFIG_FILE", as_path(get(["pska", "config_file"]), ""))
emit("PSKA_MCP_TRANSPORT", get(["pska", "mcp_transport"], "http"))
PY
}

read_service_config() {
  local config="$1"
  python3 - "$config" <<'PY'
from pathlib import Path
import json
import shlex
import sys

data = json.loads(Path(sys.argv[1]).expanduser().read_text(encoding="utf-8"))
service = data.get("service", {}) if isinstance(data, dict) else {}

def emit(key, value):
    print(f"{key}={shlex.quote(str(value))}")

host = service.get("host", "127.0.0.1")
port = int(service.get("port", 8000))
log_level = service.get("log_level", "info")
check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host

emit("SERVICE_HOST", host)
emit("SERVICE_PORT", port)
emit("SERVICE_LOG_LEVEL", log_level)
emit("SERVICE_CHECK_HOST", check_host)
PY
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

if ! command -v curl >/dev/null 2>&1; then
  echo -e "${RED}curl is required for local readiness checks.${NC}"
  exit 1
fi

CONFIG_PATH="$(resolve_config "${1:-}")"
eval "$(read_start_config "$CONFIG_PATH")"

BACKEND_CONFIG="$CONFIG_PATH"
if [[ "$PSKA_ENABLED" == "true" && "$PSKA_REFRESH_CONFIG" == "true" ]]; then
  if [[ -z "$PSKA_ARCHIVE" || -z "$PSKA_CONFIG_FILE" ]]; then
    echo -e "${RED}pska.refresh_config requires pska.archive and pska.config_file in config.${NC}"
    exit 1
  fi
  if [[ ! -x "$PSKA_ARCHIVE/scripts/fastreact-pska-service-config" ]]; then
    echo -e "${RED}Missing PSKA FastReAct config generator:${NC} $PSKA_ARCHIVE/scripts/fastreact-pska-service-config"
    exit 1
  fi
  echo -e "${YELLOW}Refreshing PSKA FastReAct config...${NC}"
  "$PSKA_ARCHIVE/scripts/fastreact-pska-service-config" \
    --mcp-transport "$PSKA_MCP_TRANSPORT" \
    --output "$PSKA_CONFIG_FILE" >/dev/null
  BACKEND_CONFIG="$PSKA_CONFIG_FILE"
elif [[ "$PSKA_ENABLED" == "true" && -n "$PSKA_CONFIG_FILE" ]]; then
  if [[ ! -f "$PSKA_CONFIG_FILE" ]]; then
    echo -e "${RED}Configured pska.config_file does not exist:${NC} $PSKA_CONFIG_FILE"
    exit 1
  fi
  BACKEND_CONFIG="$PSKA_CONFIG_FILE"
fi

if grep -q "pska_pska_agentic_search" "$BACKEND_CONFIG"; then
  echo -e "${RED}FastReAct config still references removed tool pska_pska_agentic_search.${NC}"
  exit 1
fi

eval "$(read_service_config "$BACKEND_CONFIG")"

export PYTHONPATH="$BACKEND/src:${PYTHONPATH:-}"
export NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL="http://${SERVICE_CHECK_HOST}:${SERVICE_PORT}"

echo -e "${BLUE}Starting FastReAct daemon...${NC}"
(
  cd "$BACKEND"
  python3 -m fastreact.adapters.http --config "$BACKEND_CONFIG"
) >"$HTTP_LOG" 2>&1 &
SERVICE_PID=$!

if ! wait_for_http "http://${SERVICE_CHECK_HOST}:${SERVICE_PORT}/health" 40; then
  echo -e "${RED}FastReAct daemon did not become healthy.${NC}"
  echo "Log: $HTTP_LOG"
  tail -n 40 "$HTTP_LOG" || true
  cleanup
  exit 1
fi

echo -e "${GREEN}Daemon ready:${NC} http://${SERVICE_CHECK_HOST}:${SERVICE_PORT}"
echo "Daemon config: $BACKEND_CONFIG"
echo "Daemon log:    $HTTP_LOG"

if [[ "$WEB_ENABLED" == "true" ]]; then
  if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo -e "${RED}Node.js and npm are required for the service console.${NC}"
    cleanup
    exit 1
  fi

  if [[ ! -d "$FRONTEND/node_modules" ]]; then
    echo -e "${YELLOW}Installing web console dependencies...${NC}"
    (cd "$FRONTEND" && npm install)
  fi

  echo -e "${BLUE}Starting FastReAct service console...${NC}"
  (
    cd "$FRONTEND"
    npm run dev -- -H "$WEB_HOST" -p "$WEB_PORT"
  ) >"$WEB_LOG" 2>&1 &
  WEB_PID=$!

  if ! wait_for_http "http://${WEB_HOST}:${WEB_PORT}/service" 60; then
    echo -e "${RED}Service console did not become ready.${NC}"
    echo "Log: $WEB_LOG"
    tail -n 60 "$WEB_LOG" || true
    cleanup
    exit 1
  fi
fi

echo ""
echo -e "${GREEN}FastReAct is ready.${NC}"
if [[ "$WEB_ENABLED" == "true" ]]; then
  echo "Service console: http://${WEB_HOST}:${WEB_PORT}/service"
fi
echo "Daemon health:   http://${SERVICE_CHECK_HOST}:${SERVICE_PORT}/health"
echo "Daemon ready:    http://${SERVICE_CHECK_HOST}:${SERVICE_PORT}/ready"
echo ""
echo "Logs:"
echo "  daemon: $HTTP_LOG"
if [[ "$WEB_ENABLED" == "true" ]]; then
  echo "  web:    $WEB_LOG"
fi
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop FastReAct services.${NC}"

if [[ "$WEB_ENABLED" == "true" ]]; then
  wait "$WEB_PID"
else
  wait "$SERVICE_PID"
fi
