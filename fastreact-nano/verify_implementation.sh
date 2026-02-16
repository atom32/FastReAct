#!/bin/bash
# Verification script for Docker + Streamlit implementation

echo "[INFO] FastReAct Nano v2.1.0 - Implementation Verification"
echo "=========================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "[ERROR] Not in FastReAct Nano directory"
    echo "Run this script from: /path/to/FastReAct/fastreact-nano"
    exit 1
fi

echo "[CHECK] Verifying Docker files..."
if [ -f ".dockerignore" ]; then
    echo "[OK] .dockerignore exists"
else
    echo "[ERROR] .dockerignore missing"
    exit 1
fi

if [ -f "Dockerfile" ]; then
    echo "[OK] Dockerfile exists"
else
    echo "[ERROR] Dockerfile missing"
    exit 1
fi

if [ -f "docker-compose.yml" ]; then
    echo "[OK] docker-compose.yml exists"
else
    echo "[ERROR] docker-compose.yml missing"
    exit 1
fi

if [ -f ".env.example" ]; then
    echo "[OK] .env.example exists"
else
    echo "[ERROR] .env.example missing"
    exit 1
fi

echo ""
echo "[CHECK] Verifying Streamlit web adapter..."
if [ -f "src/fastreact/adapters/web.py" ]; then
    echo "[OK] web.py exists"
    LINES=$(wc -l < src/fastreact/adapters/web.py)
    echo "[INFO] web.py has $LINES lines"
else
    echo "[ERROR] web.py missing"
    exit 1
fi

echo ""
echo "[CHECK] Verifying documentation..."
if [ -f "QUICKSTART_WEB.md" ]; then
    echo "[OK] QUICKSTART_WEB.md exists"
else
    echo "[ERROR] QUICKSTART_WEB.md missing"
    exit 1
fi

if [ -f "QUICKSTART_DOCKER.md" ]; then
    echo "[OK] QUICKSTART_DOCKER.md exists"
else
    echo "[ERROR] QUICKSTART_DOCKER.md missing"
    exit 1
fi

if [ -f "DOCKER_STREAMLIT_IMPLEMENTATION.md" ]; then
    echo "[OK] DOCKER_STREAMLIT_IMPLEMENTATION.md exists"
else
    echo "[ERROR] DOCKER_STREAMLIT_IMPLEMENTATION.md missing"
    exit 1
fi

echo ""
echo "[CHECK] Verifying configuration..."
if grep -q "web = \[" pyproject.toml; then
    echo "[OK] pyproject.toml has [web] dependencies"
else
    echo "[ERROR] pyproject.toml missing [web] dependencies"
    exit 1
fi

if grep -q "streamlit" pyproject.toml; then
    echo "[OK] pyproject.toml includes streamlit"
else
    echo "[ERROR] pyproject.toml missing streamlit"
    exit 1
fi

echo ""
echo "[CHECK] Verifying tests..."
if [ -f "tests/integration/test_web_adapter.py" ]; then
    echo "[OK] test_web_adapter.py exists"
else
    echo "[ERROR] test_web_adapter.py missing"
    exit 1
fi

echo ""
echo "[CHECK] Running web adapter tests..."
python3 -m pytest tests/integration/test_web_adapter.py -v --tb=short
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "[OK] All tests passed"
else
    echo "[ERROR] Tests failed"
    exit 1
fi

echo ""
echo "[CHECK] Verifying imports..."
python3 -c "from fastreact.adapters.web import WebSession, render_event, render_chat_interface" 2>&1
if [ $? -eq 0 ]; then
    echo "[OK] Web adapter imports successful"
else
    echo "[ERROR] Import failed"
    exit 1
fi

echo ""
echo "=========================================================="
echo "[SUCCESS] All verifications passed!"
echo ""
echo "Implementation complete: Docker + Streamlit Web UI"
echo ""
echo "Next steps:"
echo "  1. Try Streamlit locally:"
echo "     pip install -e '.[web]'"
echo "     streamlit run src/fastreact/adapters/web.py"
echo ""
echo "  2. Try Docker deployment:"
echo "     cp .env.example .env"
echo "     # Edit .env with your API key"
echo "     docker compose up -d web"
echo ""
echo "  3. Read the quickstart guides:"
echo "     - QUICKSTART_WEB.md"
echo "     - QUICKSTART_DOCKER.md"
echo ""
echo "Documentation: DOCKER_STREAMLIT_IMPLEMENTATION.md"
echo "=========================================================="
