"""
配置 mcp-datetime MCP 服务器

由于网络无法直接克隆，提供手动配置步骤
"""

import asyncio
import json
import os
import subprocess


async def setup_mcp_datetime_manually():
    """手动配置 mcp-datetime MCP 服务器"""

    print("=" * 60)
    print("Setup mcp-datetime MCP Server")
    print("=" * 60)

    server_dir = "mcp-datetime"

    # 步骤 1: 检查是否已有
    if os.path.exists(server_dir):
        print(f"\n[OK] 仓库目录已存在: {server_dir}")
    else:
        print(f"\n[1/5] 手动下载 mcp-datetime")
        print("-" * 60)
        print("请按以下步骤操作：")
        print()
        print("方式 A - 使用 GitHub Desktop:")
        print("  1. 打开 GitHub Desktop")
        print("  2. File > Clone Repository")
        print("  3. URL: https://github.com/ZeparHyfar/mcp-datetime")
        print("  4. 选择本地路径")
        print()
        print("方式 B - 使用命令行 (需要配置代理):")
        print("  git clone https://github.com/ZeparHyfar/mcp-datetime.git")
        print()
        print("方式 C - 下载 ZIP:")
        print("  1. 访问: https://github.com/ZeparHyfar/mcp-datetime")
        print("  2. 点击 Code > Download ZIP")
        print("  3. 解压到当前目录")

        input("\n完成后按回车继续...")

    # 步骤 2: 检查目录
    if not os.path.exists(server_dir):
        print(f"\n[ERROR] 目录 {server_dir} 不存在")
        print("请先完成步骤 1")
        return

    # 步骤 3: 安装依赖
    print(f"\n[2/5] 安装依赖...")
    os.chdir(server_dir)

    print("\n运行: npm install")
    result = subprocess.run(
        ["npm", "install"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] npm install 失败:")
        print(result.stderr)
        return

    print("[OK] 依赖安装成功")

    # 步骤 4: 构建
    print("\n[3/5] 构建项目...")
    result = subprocess.run(
        ["npm", "run", "build"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] 构建失败:")
        print(result.stderr)
        return

    print("[OK] 构建成功")

    # 返回上级目录
    os.chdir("..")

    # 步骤 5: 创建 MCP 配置
    print("\n[4/5] 创建 MCP 配置...")

    abs_path = os.path.abspath(f"{server_dir}/dist/index.js")

    mcp_config = {
        "mcpServers": {
            "datetime": {
                "command": "node",
                "args": [abs_path]
            }
        }
    }

    config_file = "mcp_datetime_config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2, ensure_ascii=False)

    print(f"[OK] 配置已保存: {config_file}")
    print("\n配置内容:")
    print(json.dumps(mcp_config, indent=2, ensure_ascii=False))

    # 步骤 6: 测试连接
    print("\n[5/5] 测试连接...")

    from fastreact.tools import MCPClientManager
    from fastreact import FastReAct

    manager = MCPClientManager()
    manager.load_config(config_file)

    print("\n[*] 连接到 MCP 服务器...")
    try:
        await manager.connect_all()

        servers = manager.list_servers()
        print(f"[OK] 已连接到 {len(servers)} 个服务器")

        # 获取工具
        tools = await manager.get_server_tools("datetime")

        print(f"\n[OK] 可用工具 ({len(tools)} 个):")
        for tool_name in tools:
            tool = tools[tool_name]
            print(f"\n  {tool_name}:")
            print(f"    {tool.description[:100]}...")
            if tool.parameters:
                print(f"    参数: {json.dumps(tool.parameters, indent=6, ensure_ascii=False)[:200]}...")

        # 测试工具调用
        print("\n" + "=" * 60)
        print("测试工具调用")
        print("=" * 60)

        if "get_current_datetime" in tools:
            print("\n[1] get_current_datetime (ISO format, UTC):")
            result = await tools["get_current_datetime"].execute_async(
                format="ISO",
                timezone="UTC"
            )
            print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if "get_current_datetime" in tools:
            print("\n[2] get_current_datetime (Asia/Shanghai):")
            result = await tools["get_current_datetime"].execute_async(
                format="ISO",
                timezone="Asia/Shanghai"
            )
            print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if "get_timezone_info" in tools:
            print("\n[3] get_timezone_info (America/New_York):")
            result = await tools["get_timezone_info"].execute_async(
                timezone="America/New_York"
            )
            print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        print("\n" + "=" * 60)
        print("[SUCCESS] mcp-datetime 服务器测试成功！")
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
            print(f"\n[WARN] 无法读取 LLM 配置: {e}")
            llm_api_key = None

        # 如果有 LLM API Key，启动 Agent
        if llm_api_key:
            print("\n" + "=" * 60)
            print("启动 Agent 对话")
            print("=" * 60)

            agent = FastReAct(
                api_key=llm_api_key,
                model=llm_model,
                tools=list(tools.values()),
                max_iterations=5,
                verbose=False
            )

            print("\nAgent 已就绪！你可以问:")
            print("  - '现在北京时间几点？'")
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

            await agent.close()

        else:
            print("\n[INFO] 未配置 LLM API Key")
            print("工具已成功连接并测试！")
            print("\n要使用 Agent 对话功能，请在 config.json 中配置 LLM API Key")

    except Exception as e:
        print(f"\n[ERROR] 连接或测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[*] 清理资源...")
        try:
            await manager.close_all()
            print("[OK] 已断开所有连接")
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(setup_mcp_datetime_manually())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
