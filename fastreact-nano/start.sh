#!/bin/bash
# FastReAct Nano - 快速启动脚本

echo "============================================================"
echo "  FastReAct Nano v2.1 - SiliconFlow Edition"
echo "============================================================"
echo ""

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "[ERROR] 未找到 config.json 配置文件"
    echo ""
    echo "请先创建配置文件："
    echo "  cp config.simple.json config.json"
    echo "  然后编辑 config.json 填入你的 API Key"
    exit 1
fi

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] 未找到 Python 3"
    echo "请先安装 Python 3.10 或更高版本"
    exit 1
fi

SERVICE_PORT=$(python3 - <<'PY'
import json
from pathlib import Path

try:
    data = json.loads(Path("config.json").read_text(encoding="utf-8"))
except Exception:
    print("18741")
else:
    print(int((data.get("service") or {}).get("port") or 18741))
PY
)

# 检查依赖
echo "[INFO] 检查依赖..."
python3 -c "import sys; sys.path.insert(0, 'src'); from fastreact import Config" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARN] 依赖未完全安装，正在安装..."
    pip3 install litellm openai httpx pyyaml typer rich fastapi uvicorn
fi

echo ""
echo "选择启动模式："
echo ""
echo "  [1] CLI 命令行界面（推荐）"
echo "      交互式对话，有美化输出"
echo ""
echo "  [2] HTTP API 服务器"
echo "      端口 ${SERVICE_PORT}，适合 API 调用"
echo ""
echo ""
read -p "请输入选择 [1-2]: " choice

case $choice in
    1)
        echo ""
        echo "启动 CLI 命令行界面..."
        echo ""
        python3 -m fastreact.adapters.cli
        ;;
    2)
        echo ""
        echo "启动 HTTP API 服务器..."
        echo "访问 http://localhost:${SERVICE_PORT} 查看 API 文档"
        echo ""
        python3 -m fastreact.adapters.http --config config.json
        ;;
    *)
        echo "[ERROR] 无效选择"
        exit 1
        ;;
esac
