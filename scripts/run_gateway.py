"""
启动 FastReAct WebSocket Gateway

运行此脚本启动 WebSocket 网关服务器，然后打开 public/index.html 进行测试。
"""

import os
import sys
import asyncio
import uvicorn

# 设置 UTF-8 输出（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastreact import FastReAct
from fastreact.tools import (
    SearchTool,
    CalculatorTool,
    WeatherTool,
    HTTPTool,
)
from fastreact.gateway import GatewayServer
from fastreact.utils.config import get_config

# 优先从 config.json 读取配置，否则使用环境变量
try:
    config = get_config()
    llm_config = config.get_llm_config()

    api_key = llm_config.get('api_key')
    if not api_key:
        raise ValueError("api_key not found in config")

    base_url = llm_config.get('base_url', 'https://api.openai.com/v1')
    model = llm_config.get('model', 'gpt-4')

    config_source = "config.json"
except Exception as e:
    # 回退到环境变量
    print(f"[WARN] 无法从 config.json 读取配置: {e}")
    print("[INFO] 使用环境变量配置")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量或配置 config.json")
        print("例如: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4")
    config_source = "环境变量"

# 存储配置
storage_path = os.getenv("STORAGE_PATH", "./data/sessions.db")
auto_save = os.getenv("AUTO_SAVE", "true").lower() == "true"

print("=" * 60)
print("🚀 FastReAct WebSocket Gateway")
print("=" * 60)
print(f"📋 配置来源: {config_source}")
print(f"📡 API: {base_url}")
print(f"🤖 模型: {model}")
print(f"🔧 工具: 4 个内置工具")
print(f"💾 存储: SQLite ({storage_path})")
print(f"🔄 自动保存: {auto_save}")
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
        HTTPTool(),             # HTTP 请求
    ],
    max_iterations=10,
    enable_cache=True,
    enable_deduplication=True,
)

# 包装为网关
gateway = GatewayServer(
    agent,
    storage_path=storage_path,
    auto_save=auto_save
)

# 启动服务器
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    async def main():
        # 初始化存储
        try:
            await gateway.startup()
            print("\n✅ 存储初始化成功")
        except Exception as e:
            print(f"\n❌ 存储初始化失败: {e}")
            sys.exit(1)

        # 配置 uvicorn
        config = uvicorn.Config(
            gateway.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
        )
        server = uvicorn.Server(config)

        print(f"\n✅ 服务器启动中...")
        print(f"📍 WebSocket: ws://localhost:{port}/ws/{{session_id}}")
        print(f"🌐 前端页面: 打开 public/index.html")
        print(f"📊 健康检查: http://localhost:{port}/health")
        print(f"📋 会话列表: http://localhost:{port}/sessions")
        print("\n按 Ctrl+C 停止服务器")
        print("=" * 60)
        print()

        await server.serve()

    if sys.platform == "win32":
        # Windows 上使用 ProactorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
