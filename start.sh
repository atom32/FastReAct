#!/bin/bash
# FastReAct Nano - Startup Script
# This script starts both the HTTP daemon (backend) and Web UI (frontend)

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FastReAct Nano - Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "fastreact-nano" ] || [ ! -d "fastreact-nano-web" ]; then
    echo -e "${RED}Error: Please run this script from the FastReAct root directory${NC}"
    echo "Expected directories: fastreact-nano/, fastreact-nano-web/"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js not found${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"

    # Kill HTTP daemon
    if [ -n "$SERVICE_PID" ]; then
        echo "Stopping HTTP daemon (PID: $SERVICE_PID)..."
        kill $SERVICE_PID 2>/dev/null || true
    fi

    # Kill Web UI (if run in foreground)
    if [ -n "$WEB_PID" ]; then
        echo "Stopping Web UI (PID: $WEB_PID)..."
        kill $WEB_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}All services stopped${NC}"
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# ============================
# Start HTTP Daemon (Backend)
# ============================
echo -e "${BLUE}[1/2] Starting HTTP daemon (backend)...${NC}"

cd fastreact-nano

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found, creating from .env.example${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env and add your API keys${NC}"
    fi
fi

# Start HTTP daemon in background
python3 -m fastreact.adapters.http --host 127.0.0.1 --port 8000 > /tmp/fastreact-http.log 2>&1 &
SERVICE_PID=$!

echo -e "${GREEN}✓ HTTP daemon started (PID: $SERVICE_PID)${NC}"
echo "  Logs: /tmp/fastreact-http.log"
echo "  URL: http://localhost:8000"

# Wait for HTTP daemon to be ready
echo "Waiting for HTTP daemon to initialize..."
sleep 3

# Check if HTTP daemon is still running
if ! ps -p $SERVICE_PID > /dev/null; then
    echo -e "${RED}Error: HTTP daemon failed to start${NC}"
    echo "Check logs: tail /tmp/fastreact-http.log"
    exit 1
fi

cd ..

# ============================
# Start Web UI (Frontend)
# ============================
echo ""
echo -e "${BLUE}[2/2] Starting Web UI (frontend)...${NC}"

cd fastreact-nano-web

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}Creating .env.local...${NC}"
    cat > .env.local << EOF
# Next.js
NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL=http://localhost:8000
EOF
fi

echo -e "${GREEN}✓ Starting Web UI...${NC}"
echo "  URL: http://localhost:3000"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Start Web UI in foreground
npm run dev &
WEB_PID=$!

# Wait for Web UI to start
sleep 5

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "HTTP API: ${BLUE}http://localhost:8000${NC} (PID: $SERVICE_PID)"
echo -e "Web UI:   ${BLUE}http://localhost:3000/service${NC} (PID: $WEB_PID)"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo -e "  HTTP API: tail -f /tmp/fastreact-http.log"
echo -e "  Web UI:  Check browser console"
echo ""

# Keep script running
wait $WEB_PID
