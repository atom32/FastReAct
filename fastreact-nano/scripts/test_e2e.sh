#!/bin/bash
# FastReAct 多租户端到端测试一键启动脚本

set -e

# 颜色定义
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
RESET='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}${BLUE}=== FastReAct 多租户端到端测试 ===${RESET}\n"

# 检查依赖
echo -e "${BLUE}检查依赖...${RESET}"
if ! python -c "import websockets" 2>/dev/null; then
    echo -e "${RED}✗ 缺少依赖: websockets${RESET}"
    echo "安装: pip install websockets httpx"
    exit 1
fi

if ! python -c "import httpx" 2>/dev/null; then
    echo -e "${RED}✗ 缺少依赖: httpx${RESET}"
    echo "安装: pip install httpx"
    exit 1
fi

echo -e "${GREEN}✓ 依赖检查通过${RESET}\n"

# 设置环境变量
export GATEWAY_ADMIN_KEY="${GATEWAY_ADMIN_KEY:-test-admin-key}"

# 检查 Gateway 是否运行
echo -e "${BLUE}检查 Gateway 状态...${RESET}"
if curl -s http://localhost:9000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Gateway 正在运行${RESET}\n"
else
    echo -e "${YELLOW}⚠ Gateway 未运行${RESET}"
    echo -e "${YELLOW}请先启动 Gateway:${RESET}"
    echo "  cd fastreact-nano"
    echo "  python -m fastreact.adapters.gateway"
    echo ""
    read -p "是否现在启动 Gateway? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}启动 Gateway...${RESET}"
        cd fastreact-nano
        python -m fastreact.adapters.gateway &
        GATEWAY_PID=$!
        echo -e "${GREEN}✓ Gateway 已启动 (PID: $GATEWAY_PID)${RESET}\n"

        # 等待 Gateway 启动
        echo "等待 Gateway 就绪..."
        for i in {1..10}; do
            if curl -s http://localhost:9000/health > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Gateway 就绪${RESET}\n"
                break
            fi
            sleep 1
        done
    else
        echo -e "${RED}✗ 取消测试${RESET}"
        exit 1
    fi
fi

# 运行测试
echo -e "${BOLD}${BLUE}运行端到端测试...${RESET}\n"
cd "$(dirname "$0")/.."
python tests/integration/test_multitenant_e2e.py

# 测试结果
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}✓ 所有测试通过！${RESET}\n"

    echo -e "${BLUE}下一步:${RESET}"
    echo "  1. 查看生成的 Workspace:"
    echo "     ls -la ./workspaces/"
    echo ""
    echo "  2. 访问 Admin 面板:"
    echo "     open http://localhost:9000/admin"
    echo ""
    echo "  3. 启动前端测试用户登录:"
    echo "     cd ../fastreact-nano-web && npm run dev"
else
    echo -e "\n${RED}${BOLD}✗ 测试失败${RESET}\n"
    echo "请查看错误信息并修复问题"
    exit 1
fi

# 清理（如果启动了 Gateway）
if [ ! -z "$GATEWAY_PID" ]; then
    echo ""
    read -p "是否停止 Gateway? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $GATEWAY_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Gateway 已停止${RESET}"
    fi
fi
