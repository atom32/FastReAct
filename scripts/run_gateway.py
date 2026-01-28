"""
启动 FastReAct WebSocket Gateway

运行此脚本启动 WebSocket 网关服务器，然后打开 public/index.html 进行测试。
"""

import os
import sys
import uvicorn

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastreact import FastReAct
from fastreact.tools import (
    SearchTool,
    CalculatorTool,
    WeatherTool,
    DateTimeTool,
    CodeExecutorTool,
)
from fastreact.gateway import GatewayServer

# 从环境变量读取 API Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
    print("例如: export OPENAI_API_KEY='your-api-key'")
    sys.exit(1)

# 读取配置（如果有）
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-4")

print("=" * 60)
print("🚀 FastReAct WebSocket Gateway")
print("=" * 60)
print(f"📡 API: {base_url}")
print(f"🤖 模型: {model}")
print(f"🔧 工具: 5 个内置工具")
print("=" * 60)

# 初始化 FastReAct
agent = FastReAct(
    api_key=api_key,
    base_url=base_url,
    model=model,
    tools=[
        SearchTool(),           # 搜索工具
        CalculatorTool(),       # 计算器
        WeatherTool(),          # 天气查询
        DateTimeTool(),         # 日期时间
        CodeExecutorTool(),     # 代码执行
    ],
    max_iterations=10,
    enable_cache=True,
    enable_deduplication=True,
)

# 包装为网关
gateway = GatewayServer(agent)

# 启动服务器
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"\n✅ 服务器启动中...")
    print(f"📍 WebSocket: ws://localhost:{port}/ws/{{session_id}}")
    print(f"🌐 前端页面: 打开 public/index.html")
    print(f"📊 健康检查: http://localhost:{port}/health")
    print(f"📋 会话列表: http://localhost:{port}/sessions")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()

    uvicorn.run(
        gateway.app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
