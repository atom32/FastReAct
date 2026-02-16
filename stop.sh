#!/bin/bash
# FastReAct Nano - Stop Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping FastReAct Nano services...${NC}"

# Stop Gateway
GATEWAY_PIDS=$(ps aux | grep -E "fastreact.adapters.gateway" | grep -v grep | awk '{print $2}')
if [ -n "$GATEWAY_PIDS" ]; then
    echo "Stopping Gateway (PIDs: $GATEWAY_PIDS)..."
    echo $GATEWAY_PIDS | xargs kill 2>/dev/null || true
    echo -e "${GREEN}✓ Gateway stopped${NC}"
else
    echo "Gateway not running"
fi

# Stop Next.js (if running in background)
WEB_PIDS=$(ps aux | grep "next dev" | grep -v grep | awk '{print $2}')
if [ -n "$WEB_PIDS" ]; then
    echo "Stopping Web UI (PIDs: $WEB_PIDS)..."
    echo $WEB_PIDS | xargs kill 2>/dev/null || true
    echo -e "${GREEN}✓ Web UI stopped${NC}"
else
    echo "Web UI not running"
fi

echo ""
echo -e "${GREEN}All services stopped${NC}"
