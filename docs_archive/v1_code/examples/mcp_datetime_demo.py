"""
连接到 Date and Time MCP 服务器演示

https://mcpservers.org/servers/chirag127/date-and-time-mcp-server
"""

import asyncio
import json
from fastreact import FastReAct
from fastreact.tools import MCPClientManager


async def main():
    print("=" * 60)
    print("Date and Time MCP Server Demo")
    print("=" * 60)

    # 读取 LLM 配置
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        default_provider = config.get("default_provider", "siliconflow")
        provider_config = config["llm"]["providers"].get(default_provider, {})
        llm_api_key = provider_config.get("api_key")
        llm_model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")

    except Exception as e:
        print(f"\n[ERROR] Config load failed: {e}")
        return

    # 创建 MCP 客户端管理器
    print("\n[*] Initializing MCP Client Manager...")
    manager = MCPClientManager()

    # 配置 Date and Time MCP 服务器
    # 注意：需要先安装并运行这个服务器
    print("\n[1] 检查 Date and Time MCP Server...")

    # 方式 1: 使用 npx 直接运行（推荐）
    mcp_config = {
        "dateTime": {
            "command": "npx",
            "args": [
                "-y",
                "@chirag127/date-and-time-mcp-server"
            ]
        }
    }

    # 保存配置到文件
    config_file = "mcp_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({"mcpServers": mcp_config}, f, indent=2, ensure_ascii=False)

    print(f"    [*] MCP 配置已保存到: {config_file}")
    print("    配置内容:")
    print(json.dumps(mcp_config, indent=6, ensure_ascii=False))

    # 加载配置
    print("\n[2] 加载 MCP 配置...")
    manager.load_config(config_file)

    # 连接到服务器
    print("\n[3] 连接到 MCP 服务器...")
    print("    (这将通过 npx 自动启动服务器)")

    try:
        # 连接到所有配置的服务器
        await manager.connect_all()

        # 列出可用的服务器
        servers = manager.list_servers()
        print(f"\n[OK] 已连接到 {len(servers)} 个服务器:")
        for server in servers:
            print(f"    - {server}")

        # 获取日期时间工具
        print("\n[4] 获取日期时间工具...")
        tools = await manager.get_server_tools("dateTime")

        print(f"\n[OK] 可用工具 ({len(tools)} 个):")
        for tool_name in tools:
            tool = tools[tool_name]
            print(f"    - {tool_name}")
            print(f"      描述: {tool.description[:80]}...")

        # 测试工具调用
        print("\n[5] 测试工具调用...")
        print("-" * 60)

        # 获取当前时间
        if "getCurrentDateTime" in tools:
            print("\n测试 getCurrentDateTime:")
            result = await tools["getCurrentDateTime"].execute_async(
                format="ISO",
                timezone="Asia/Shanghai"
            )
            print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # 获取时区信息
        if "getTimezoneInfo" in tools:
            print("\n测试 getTimezoneInfo:")
            result = await tools["getTimezoneInfo"].execute_async(
                timezone="Asia/Shanghai"
            )
            print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # 创建带有 MCP 工具的 Agent
        print("\n[6] 创建 FastReAct Agent...")
        agent = FastReAct(
            api_key=llm_api_key,
            model=llm_model,
            tools=list(tools.values()),  # 添加所有 MCP 工具
            max_iterations=5,
            verbose=False
        )

        print("[OK] Agent 已创建！\n")
        print("现在你可以问 AI 关于时间的问题，例如：")
        print("  - '现在几点了？'")
        print("  - '现在纽约是什么时间？'")
        print("  - '给我当前时间的 Unix 时间戳'")
        print("  - 'type quit' 退出\n")

        # 简单对话循环
        session_id = "mcp_datetime_session"

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n[BYE] Goodbye!")
                    break

                # 运行 Agent
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

    except Exception as e:
        print(f"\n[ERROR] 连接失败: {e}")
        print("\n可能的原因:")
        print("1. 未安装 Node.js (需要 Node.js 18+)")
        print("2. 未连接到互联网")
        print("3. npx 命令不可用")

        print("\n解决方案:")
        print("1. 安装 Node.js: https://nodejs.org/")
        print("2. 确保 npm/npx 可用")
        print("3. 检查网络连接")

        print("\n或者，你可以手动启动服务器:")
        print("  git clone https://github.com/chirag127/date-and-time-mcp-server.git")
        print("  cd date-and-time-mcp-server")
        print("  npm install")
        print("  npm run build")
        print("  npm start")
        print("  然后修改配置指向本地的 dist/index.js")

    finally:
        # 清理
        print("\n[*] 清理资源...")
        try:
            await manager.close_all()
            print("[OK] 已断开所有连接")
        except:
            pass


async def simple_test():
    """简单的工具测试（不需要 Agent）"""
    print("=" * 60)
    print("Simple MCP Tools Test")
    print("=" * 60)

    manager = MCPClientManager()

    # 配置
    mcp_config = {
        "mcpServers": {
            "dateTime": {
                "command": "npx",
                "args": ["-y", "@chirag127/date-and-time-mcp-server"]
            }
        }
    }

    with open("mcp_config.json", "w") as f:
        json.dump(mcp_config, f, indent=2)

    manager.load_config("mcp_config.json")

    print("\n[*] Connecting to MCP server...")
    await manager.connect_all()

    print("[OK] Connected!")

    # 获取工具
    tools = await manager.get_server_tools("dateTime")

    print(f"\n[*] Available tools: {list(tools.keys())}")

    # 测试当前时间
    if "getCurrentDateTime" in tools:
        print("\n[*] Testing getCurrentDateTime:")
        result = await tools["getCurrentDateTime"].execute_async(
            format="ISO",
            timezone="Asia/Shanghai"
        )
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    # 测试时区信息
    if "getTimezoneInfo" in tools:
        print("\n[*] Testing getTimezoneInfo:")
        result = await tools["getTimezoneInfo"].execute_async(
            timezone="Asia/Shanghai"
        )
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    # 测试多种格式
    formats_to_test = ["UNIX", "RFC2822", "HTTP", "SQL"]

    print("\n[*] Testing different formats:")
    for fmt in formats_to_test:
        try:
            result = await tools["getCurrentDateTime"].execute_async(
                format=fmt,
                timezone="UTC"
            )
            print(f"\n  {fmt}: {result.get('currentDateTime', 'N/A')}")
        except Exception as e:
            print(f"\n  {fmt}: Error - {e}")

    await manager.close_all()
    print("\n[OK] Test completed!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 简单测试
        asyncio.run(simple_test())
    else:
        # 完整演示
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
