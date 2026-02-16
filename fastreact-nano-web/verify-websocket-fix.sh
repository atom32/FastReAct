#!/bin/bash

# WebSocket Fix Verification Script
# This script helps verify that the WebSocket connection fix is working correctly

echo "========================================="
echo "WebSocket Fix Verification Script"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Gateway is running
echo -n "[1/5] Checking if Gateway is running... "
if pgrep -f "python.*gateway" > /dev/null; then
    echo -e "${GREEN}YES${NC}"
    GATEWAY_PID=$(pgrep -f "python.*gateway")
    echo "      Gateway PID: $GATEWAY_PID"
else
    echo -e "${RED}NO${NC}"
    echo ""
    echo "ERROR: Gateway is not running!"
    echo "Please start the Gateway first:"
    echo "  cd fastreact-nano"
    echo "  ./start.sh"
    exit 1
fi

echo ""

# Check if Next.js dev server is running
echo -n "[2/5] Checking if Next.js dev server is running... "
if pgrep -f "next dev" > /dev/null; then
    echo -e "${GREEN}YES${NC}"
    NEXTJS_PID=$(pgrep -f "next dev")
    echo "      Next.js PID: $NEXTJS_PID"
else
    echo -e "${YELLOW}NO${NC}"
    echo ""
    echo "WARNING: Next.js dev server is not running!"
    echo "Please start it:"
    echo "  cd fastreact-nano-web"
    echo "  npm run dev"
    echo ""
    read -p "Press Enter to continue anyway (or Ctrl+C to exit)..."
fi

echo ""

# Check browser console instructions
echo "[3/5] Browser Console Setup"
echo "     Please open your browser and navigate to:"
echo "     ${YELLOW}http://localhost:3000${NC}"
echo ""
echo "     Then open the browser console:"
echo "     - Mac: Cmd+Option+I"
echo "     - Windows: F12"
echo "     - Go to the 'Console' tab"
echo ""
read -p "     Press Enter when you have the console open..."

echo ""

# Clear browser cache instruction
echo "[4/5] Clear Browser Cache"
echo "     Please hard refresh the page to clear cache:"
echo "     - Mac: Cmd+Shift+R"
echo "     - Windows: Ctrl+Shift+R"
echo ""
read -p "     Press Enter after refreshing..."

echo ""

# Check expected logs
echo "[5/5] Expected Console Log Sequence"
echo ""
echo "     You should see these logs (in order):"
echo ""
echo -e "       ${GREEN}[ChatInterface]${NC} Render count: 1"
echo -e "       ${GREEN}[ChatInterface]${NC} Component mounted"
echo -e "       ${GREEN}[WebSocket]${NC} Setting up connection"
echo -e "       ${GREEN}[WebSocket]${NC} connectInternal called"
echo -e "       ${GREEN}[WebSocket]${NC} Connecting to ws://localhost:9000/ws"
echo -e "       ${GREEN}[WebSocket]${NC} onopen fired - connection established"
echo -e "       ${GREEN}[WebSocket]${NC} Received: {type: \"connected\", ...}"
echo ""
echo "     You should NOT see:"
echo -e "       ${RED}[ERROR] Failed to connect to Gateway${NC}"
echo -e "       ${RED}[WebSocket] Cleanup called${NC} (immediately after connection)"
echo -e "       ${RED}Multiple [WebSocket] Connecting to${NC} messages"
echo ""

# Ask user to verify
echo "========================================="
echo "Verification Checklist"
echo "========================================="
echo ""
echo "Please confirm the following:"
echo ""
read -p "[ ] Do you see only ONE '[ChatInterface] Component mounted' message? (y/n) " MOUNT_OK
read -p "[ ] Do you see only ONE '[WebSocket] Connecting to' message? (y/n) " CONNECT_OK
read -p "[ ] Do you see '[WebSocket] Received: {type: \"connected\"}'? (y/n) " CONNECTED_OK
read -p "[ ] Is the connection status showing 'Connected' in green? (y/n) " STATUS_OK
read -p "[ ] Are there NO '[ERROR] Failed to connect to Gateway' messages? (y/n) " NO_ERROR_OK

echo ""

# Evaluate results
if [[ "$MOUNT_OK" == "y" && "$CONNECT_OK" == "y" && "$CONNECTED_OK" == "y" && "$STATUS_OK" == "y" && "$NO_ERROR_OK" == "y" ]]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}SUCCESS! All checks passed!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "The WebSocket fix is working correctly."
    echo "Your connection should now be stable."
    exit 0
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}ISSUES DETECTED${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    echo "Some checks failed. Please check:"
    echo "1. Browser console for error messages"
    echo "2. Gateway terminal for any errors"
    echo "3. Network tab in browser dev tools for WebSocket status"
    echo ""
    echo "For debugging tips, see: WEBSOCKET_FIX_SUMMARY.md"
    exit 1
fi
