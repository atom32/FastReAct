#!/bin/bash
# 快速启动飞书 Bot (SDK 模式 - 推荐)

# 解析参数
VERBOSE=false
SHOW_LOGS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [-v|--verbose] [-l|--logs]"
            echo ""
            echo "选项:"
            echo "  -v, --verbose    启用详细日志输出"
            echo "  -l, --logs       启动后显示实时日志"
            echo "  -h, --help       显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 -h 查看帮助"
            exit 1
            ;;
    esac
done

echo "=== FastReAct Feishu Bot (SDK 模式) 启动脚本 ==="
echo ""

if [ "$VERBOSE" = true ]; then
    echo "[VERBOSE] 详细日志模式已启用"
    echo ""
fi

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import lark_oapi" 2>/dev/null; then
    echo "❌ 缺少 lark-oapi SDK"
    echo ""
    echo "安装命令:"
    echo "  pip install lark-oapi>=1.5.0"
    echo ""
    exit 1
fi

echo "✅ lark-oapi SDK 已安装"

# 检查配置
CONFIG_FILE="$HOME/.fastreact/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  配置文件不存在: $CONFIG_FILE"
    echo ""
    echo "请先创建配置文件，包含以下内容："
    echo ""
    cat <<'EOF'
{
  "feishu": {
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "your_app_secret",
    "connection_mode": "sdk",
    "enable_multitenant": true,
    "auto_reconnect": true,
    "log_level": "info"
  }
}
EOF
    echo ""
    echo "创建配置文件："
    echo "  mkdir -p ~/.fastreact"
    echo "  nano ~/.fastreact/config.json"
    echo ""
    exit 1
fi

echo "✅ 配置文件存在"

# 检查配置内容
APP_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu'].get('app_id', ''))" 2>/dev/null)

if [ -z "$APP_ID" ] || [ "$APP_ID" == "your_app_id" ]; then
    echo "⚠️  飞书配置未完成"
    echo ""
    echo "请在配置文件中设置以下信息："
    echo "  • app_id: 飞书应用 ID"
    echo "  • app_secret: 飞书应用密钥"
    echo ""
    echo "配置文件: $CONFIG_FILE"
    exit 1
fi

echo "✅ 飞书配置完成"
echo "   App ID: $APP_ID"
echo ""

# 停止旧进程（如果存在）
if pgrep -f "fastreact.adapters.feishu" > /dev/null; then
    echo "停止旧的飞书进程..."
    pkill -f "fastreact.adapters.feishu"
    sleep 1
fi

# 启动飞书 Bot (SDK 模式)
echo "🚀 启动飞书 Bot (SDK 模式，基于 Lark SDK)..."
if [ "$VERBOSE" = true ]; then
    echo "   [VERBOSE] 详细日志已启用"
fi
echo ""

# 切换到项目根目录（scripts 的上一级）
cd "$(dirname "$0")/.."

# 设置详细日志环境变量
if [ "$VERBOSE" = true ]; then
    export FEISHU_VERBOSE=true
    export FASTRACT_LOG_LEVEL=debug
    # 在后台启动，但将输出重定向到日志文件
    python3 -m fastreact.adapters.feishu_sdk > ~/.fastreact/logs/feishu.log 2>&1 &
else
    python3 -m fastreact.adapters.feishu_sdk > ~/.fastreact/logs/feishu.log 2>&1 &
fi
FEISHU_PID=$!

echo "✅ 飞书 Bot 已启动 (PID: $FEISHU_PID)"
echo ""

# 等待进程初始化
sleep 2

# 检查进程是否还在运行
if ps -p $FEISHU_PID > /dev/null; then
    echo "✅ 进程运行中"
    echo ""
    echo "特性:"
    echo "  • 无需公网 IP (内网即可)"
    echo "  • WebSocket 长连接"
    echo "  • 自动重连"
    echo "  • 多租户用户隔离"
    echo ""
    echo "日志文件: ~/.fastreact/logs/feishu.log"
    echo ""

    # 如果用户要求显示日志
    if [ "$SHOW_LOGS" = true ]; then
        echo "查看实时日志（Ctrl+C 退出，不会停止 Bot）:"
        echo ""
        tail -f ~/.fastreact/logs/feishu.log
    else
        echo "查看日志命令:"
        echo "  tail -f ~/.fastreact/logs/feishu.log"
        echo ""
        echo "或者使用 -l 参数启动时自动显示日志:"
        echo "  ./scripts/start_feishu_bot.sh -l"
    fi
else
    echo "❌ 进程启动失败"
    echo ""
    echo "查看错误日志:"
    echo "  cat ~/.fastreact/logs/feishu.log"
    exit 1
fi
