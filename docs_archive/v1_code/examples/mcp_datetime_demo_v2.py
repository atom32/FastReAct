"""
MCP 日期时间服务器配置（使用本地安装）

由于 @chirag127/date-and-time-mcp-server 无法直接通过 npx 安装，
我们使用本地安装方式。
"""

import asyncio
import json
import subprocess
import os
from fastreact import FastReAct
from fastreact.tools import MCPClientManager


async def setup_local_server():
    """设置本地 MCP 服务器"""
    print("=" * 60)
    print("Setup Date and Time MCP Server (Local)")
    print("=" * 60)

    server_dir = "date-and-time-mcp-server"

    # 检查是否已存在
    if os.path.exists(server_dir):
        print(f"\n[*] 服务器目录已存在: {server_dir}")
        choice = input("是否要重新克隆？(y/N): ").strip().lower()
        if choice != 'y':
            print("[*] 使用现有安装")
            return server_dir
    else:
        print(f"\n[*] 克隆服务器...")
        result = subprocess.run(
            [
                "git", "clone",
                "https://github.com/chirag127/date-and-time-mcp-server.git"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[ERROR] 克隆失败: {result.stderr}")
            return None

        print("[OK] 克隆成功")

    # 安装依赖
    print("\n[*] 安装依赖...")
    os.chdir(server_dir)

    result = subprocess.run(
        ["npm", "install"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] npm install 失败: {result.stderr}")
        return None

    print("[OK] 依赖安装成功")

    # 构建
    print("\n[*] 构建项目...")
    result = subprocess.run(
        ["npm", "run", "build"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] 构建失败: {result.stderr}")
        return None

    print("[OK] 构建成功")

    # 返回上级目录
    os.chdir("..")

    return server_dir


async def demo_with_local_server():
    """使用本地服务器演示"""
    # 先设置服务器
    server_dir = await setup_local_server()

    if not server_dir:
        print("\n[ERROR] 无法设置服务器")
        print("\n替代方案：使用内置的时间工具")
        print("\n运行: python simple_chat.py")
        print("内置工具包括 GetCurrentTimeTool, GetDateInfoTool 等")
        return

    # 配置本地服务器
    abs_path = os.path.abspath(f"{server_dir}/dist/index.js")

    mcp_config = {
        "mcpServers": {
            "dateTime": {
                "command": "node",
                "args": [abs_path]
            }
        }
    }

    config_file = "mcp_config_local.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2, ensure_ascii=False)

    print(f"\n[*] MCP 配置已保存: {config_file}")
    print("\n配置内容:")
    print(json.dumps(mcp_config, indent=2, ensure_ascii=False))

    # 创建管理器并连接
    print("\n[*] 初始化 MCP 客户端...")
    manager = MCPClientManager()
    manager.load_config(config_file)

    print("\n[*] 连接到 MCP 服务器...")
    try:
        await manager.connect_all()

        servers = manager.list_servers()
        print(f"[OK] 已连接到 {len(servers)} 个服务器")

        # 获取工具
        print("\n[*] 获取工具...")
        tools = await manager.get_server_tools("dateTime")

        print(f"\n[OK] 可用工具: {list(tools.keys())}")

        # 测试工具
        print("\n[*] 测试工具调用...")

        if "getCurrentDateTime" in tools:
            print("\n1. getCurrentDateTime (Asia/Shanghai):")
            result = await tools["getCurrentDateTime"].execute_async(
                format="ISO",
                timezone="Asia/Shanghai"
            )
            print(f"   {json.dumps(result, indent=6, ensure_ascii=False)}")

        if "getCurrentDateTime" in tools:
            print("\n2. getCurrentDateTime (New York):")
            result = await tools["getCurrentDateTime"].execute_async(
                format="ISO",
                timezone="America/New_York"
            )
            print(f"   {json.dumps(result, indent=6, ensure_ascii=False)}")

        if "getTimezoneInfo" in tools:
            print("\n3. getTimezoneInfo (Asia/Shanghai):")
            result = await tools["getTimezoneInfo"].execute_async(
                timezone="Asia/Shanghai"
            )
            print(f"   {json.dumps(result, indent=6, ensure_ascii=False)}")

        print("\n[SUCCESS] MCP 服务器测试成功！")

        # 询问是否启动 Agent
        print("\n" + "=" * 60)
        choice = input("是否启动 Agent 对话？(y/N): ").strip().lower()

        if choice == 'y':
            await run_agent_with_mcp(manager, tools)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[*] 清理资源...")
        await manager.close_all()


async def run_agent_with_mcp(manager, tools):
    """运行带 MCP 工具的 Agent"""
    print("\n[*] 创建 FastReAct Agent...")

    # 读取 LLM 配置
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    default_provider = config.get("default_provider", "siliconflow")
    provider_config = config["llm"]["providers"].get(default_provider, {})
    llm_api_key = provider_config.get("api_key")
    llm_model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")

    agent = FastReAct(
        api_key=llm_api_key,
        model=llm_model,
        tools=list(tools.values()),
        max_iterations=5,
        verbose=False
    )

    print("[OK] Agent 已就绪！\n")
    print("你可以问:")
    print("  - '现在北京时间几点了？'")
    print("  - '纽约现在是什么时间？'")
    print("  - '给我当前时间的 ISO 格式'")
    print("  - 'type quit' 退出\n")

    session_id = "mcp_datetime_session"

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n[BYE] Goodbye!")
                break

            print("\nAI: ", end="", flush=True)
            response = await agent.run(
                query=user_input,
                session_id=session_id
            )
            print(response)

        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("请重试或输入 'quit' 退出")


async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║  Date and Time MCP Server - 本地安装演示              ║
╚══════════════════════════════════════════════════════════╝

由于 npm 包无法直接安装，将使用本地安装方式。

流程:
1. 克隆 GitHub 仓库
2. npm install 安装依赖
3. npm run build 构建
4. 连接本地服务器
5. 测试工具调用
""")

    await demo_with_local_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
