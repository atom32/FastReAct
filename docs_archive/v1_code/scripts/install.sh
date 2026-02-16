#!/bin/bash
# FastReAct Installation Script

set -e

echo "=================================="
echo "FastReAct Installation Script"
echo "=================================="
echo ""

# Check Python version
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $PYTHON_VERSION"

# Check if python3.10+ is available
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "   ❌ Error: Python 3.10+ is required"
    echo "   Please install Python 3.10 or higher"
    exit 1
fi
echo "   ✅ Python version OK"
echo ""

# Install dependencies
echo "2. Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "   ✅ Dependencies installed"
else
    echo "   ⚠️  requirements.txt not found"
fi
echo ""

# Check Docker (optional)
echo "3. Checking Docker (for sandbox features)..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker found: $(docker --version)"
    if ! docker ps &> /dev/null; then
        echo "   ⚠️  Warning: Docker is not running. Start it to use sandbox features."
    fi
else
    echo "   ⚠️  Docker not found. Install it to use sandbox features."
    echo "   Visit: https://docs.docker.com/get-docker/"
fi
echo ""

# Create .env file
echo "4. Setting up configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ✅ Created .env from .env.example"
        echo "   ⚠️  Please edit .env and add your API key"
    else
        echo "   ⚠️  .env.example not found"
    fi
else
    echo "   ℹ️  .env already exists"
fi
echo ""

# Create workspace
echo "5. Creating workspace directory..."
mkdir -p workspace
echo "   ✅ Created workspace directory"
echo ""

# Initialize FastReAct
echo "6. Initializing FastReAct workspace..."
if [ -f "src/fastreact/cli/main.py" ]; then
    python3 -m fastreact.cli.main init --overwrite 2>/dev/null || echo "   ⚠️  Workspace init skipped"
else
    echo "   ⚠️  CLI not available yet"
fi
echo ""

echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   vim .env"
echo ""
echo "2. Start using FastReAct:"
echo "   # Interactive chat"
echo "   python -m fastreact.cli.main chat"
echo ""
echo "   # Single query"
echo "   python -m fastreact.cli.main run \"Your question here\""
echo ""
echo "   # With Docker"
echo "   docker-compose up"
echo ""
echo "3. For more information:"
echo "   - Read docs/QUICKSTART.md"
echo "   - Check examples/ directory"
echo "   - Visit: https://github.com/atom32/FastReAct"
echo ""
