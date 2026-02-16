#!/bin/bash
# 快速启动 WebSocket Gateway

echo "========================================"
echo "FastReAct WebSocket Gateway - 快速启动"
echo "========================================"
echo ""

# 检查 Python 版本
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python 版本: $PYTHON_VERSION"

# 检查依赖
echo ""
echo "检查依赖..."
pip list | grep -E "fastapi|uvicorn|websockets" > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ 依赖已安装"
else
    echo "✗ 缺少依赖，正在安装..."
    pip install -r requirements.txt
fi

# 检查 API Key
echo ""
if [ -z "$OPENAI_API_KEY" ]; then
    echo "✗ 错误: 请设置 OPENAI_API_KEY 环境变量"
    echo ""
    echo "例如:"
    echo "  export OPENAI_API_KEY='your-api-key'"
    echo ""
    exit 1
else
    echo "✓ API Key 已设置"
fi

# 启动服务器
echo ""
echo "========================================"
echo "启动服务器..."
echo "========================================"
echo ""

python scripts/run_gateway.py
