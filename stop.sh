#!/usr/bin/env bash
# Stop local FastReAct daemon and service console processes.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

stop_pattern() {
  local label="$1"
  local pattern="$2"
  local pids
  pids="$(pgrep -f "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    echo "$label not running"
    return
  fi
  echo "Stopping $label (PIDs: $pids)..."
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  echo -e "${GREEN}✓ $label stopped${NC}"
}

echo -e "${YELLOW}Stopping FastReAct local services...${NC}"

stop_pattern "FastReAct daemon" "fastreact.adapters.http"
stop_pattern "FastReAct service console" "next dev.*fastreact-nano-web|next-server.*fastreact-nano-web"

echo ""
echo -e "${GREEN}Done${NC}"
