#!/bin/bash
set -e

# =====================================================
# FastReAct Nano One-Click Installation Script
# Supports: Linux, macOS
# =====================================================

echo "[INFO] FastReAct Nano One-Click Installation"
echo "============================================"

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed. Please install Python 3.10 or higher."
    echo ""
    echo "Visit: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "[OK] Found Python $PYTHON_VERSION"

# Check Python version (requires 3.10+)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "[ERROR] Python 3.10 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    OS="unknown"
fi

echo "[OK] Detected OS: $OS"

# Method 1: Try uv (recommended - much faster)
if command -v uv &> /dev/null; then
    echo ""
    echo "[INFO] Found uv, using uv for installation..."
    echo "[INFO] This is the recommended installation method."

    # Check if uv tool is already installed
    if uv tool list | grep -q "fastreact-nano"; then
        echo "[INFO] FastReAct Nano is already installed via uv"
        echo "[INFO] Upgrading to latest version..."
        uv tool upgrade fastreact-nano
    else
        echo "[INFO] Installing FastReAct Nano..."
        uv tool install fastreact-nano
    fi

    echo ""
    echo "[OK] Installation completed successfully!"
    echo ""
    echo "To run FastReAct Nano:"
    echo "  fastreact-nano"
    echo ""
    echo "To use CLI adapter:"
    echo "  fastreact 'your query here' --model gpt-4o-mini"
    echo ""
    exit 0
fi

# Method 2: Fall back to pip
echo ""
echo "[INFO] uv not found. Using pip for installation (slower)."
echo "[INFO] For faster installation, consider installing uv:"
echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
echo ""

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip3 is not installed. Please install pip."
    echo ""
    echo "For Ubuntu/Debian:"
    echo "  sudo apt-get install python3-pip"
    echo ""
    echo "For macOS:"
    echo "  python3 -m ensurepip --upgrade"
    exit 1
fi

# Install FastReAct Nano
echo "[INFO] Installing FastReAct Nano with pip..."
pip3 install --user fastreact-nano

# Create desktop shortcut (Linux only)
if [[ "$OS" == "linux" ]]; then
    DESKTOP_DIR="$HOME/.local/share/applications"
    if [ -d "$HOME/.local/share/applications" ] || mkdir -p "$HOME/.local/share/applications"; then
        cat > "$DESKTOP_DIR/fastreact-nano.desktop" <<EOF
[Desktop Entry]
Name=FastReAct Nano
Comment=Ultra-Lightweight Event-Driven AI Agent SDK
Exec=fastreact-nano
Icon=fastreact
Type=Application
Categories=Development;IDE;
Terminal=true
EOF
        echo "[OK] Created desktop shortcut"
    fi
fi

echo ""
echo "[OK] Installation completed successfully!"
echo ""
echo "To run FastReAct Nano:"
echo "  fastreact-nano"
echo ""
echo "To use CLI adapter:"
echo "  fastreact 'your query here' --model gpt-4o-mini"
echo ""
echo "Next steps:"
echo "  1. Set your API key: export FASTREACT_API_KEY='your-key'"
echo "  2. Run: fastreact-nano"
echo ""
