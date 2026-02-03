"""
启动 FastReAct WebSocket Gateway

运行此脚本启动 WebSocket 网关服务器，然后打开 public/index.html 进行测试。
自动从 config.json 读取配置。
"""

import os
import sys
import asyncio
import uvicorn

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastreact import FastReAct
from fastreact.tools import create_all_tools
from fastreact.gateway import GatewayServer
from fastreact.utils.config import get_config

# 从 config.json 读取配置
config = get_config()
llm_config = config.get_llm_config()

# 启用工具分组（包括 deep_research）
enable_groups = ['file_ops', 'web', 'math', 'ai', 'code', 'system']

api_key = llm_config.get("api_key")
if not api_key or api_key == "YOUR_API_KEY_HERE":
    print("❌ 错误: 请在 config.json 中设置 api_key")
    print("💡 编辑 config.json 文件，填入你的 API Key")
    sys.exit(1)

base_url = llm_config.get("base_url", "https://api.openai.com/v1")
model = llm_config.get("model", "gpt-4")
provider_name = config.config.get("llm", {}).get("default_provider", "default")

# 存储配置
storage_path = os.getenv("STORAGE_PATH", "./data/sessions.db")
auto_save = os.getenv("AUTO_SAVE", "true").lower() == "true"

print("=" * 60)
print("🚀 FastReAct WebSocket Gateway")
print("=" * 60)
print(f"📡 提供商: {provider_name}")
print(f"🌐 API: {base_url}")
print(f"🤖 模型: {model}")
print(f"🔧 工具: 函数式自动加载")
print(f"💾 存储: SQLite ({storage_path})")
print(f"🔄 自动保存: {auto_save}")
print(f"📄 配置: config.json")
print("=" * 60)

# 🔥 使用工具分组系统
print("\n📦 使用工具分组系统加载工具...")

agent = FastReAct(
    api_key=api_key,
    base_url=base_url,
    model=model,
    enable_bootstrap=True,
    config=config.config,  # 传递完整配置，用于工具初始化
    # 启用工具分组（包括 deep_research）
    enable_groups=['file_ops', 'web', 'math', 'ai', 'code', 'system'],
    max_iterations=10,
    enable_cache=True,
    enable_deduplication=True,
)

print(f"✅ 成功加载 {len(agent.tools)} 个工具:")
for tool_name in agent.tools.keys():
    print(f"   - {tool_name}")

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
