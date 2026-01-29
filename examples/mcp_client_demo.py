"""
FastReAct 作为 MCP 客户端 - 演示

测试 FastReAct 连接到外部 MCP 服务器的能力
"""

import asyncio
import json
from fastreact.tools import MCPClientManager


async def test_mcp_client_capability():
    """测试 MCP 客户端功能"""
    print("=" * 60)
    print("FastReAct MCP Client Capability Test")
    print("=" * 60)

    print("""
FastReAct 支持 MCP (Model Context Protocol) 客户端功能。

架构:
    FastReAct (MCP Client) → MCP Server → 提供工具

可以连接的 MCP 服务器类型:
    1. stdio 模式: 通过标准输入/输出通信
    2. HTTP 模式: 通过 HTTP 请求通信
    3. SSE 模式: 通过 Server-Sent Events 通信

尝试连接的服务器:
    - Date and Time MCP Server
    - Filesystem MCP Server
    - GitHub MCP Server
    - Brave Search MCP Server
    等...
""")

    # 尝试多种方式连接日期时间服务器
    configs_to_try = [
        {
            "name": "方式 1: npx 直接安装",
            "config": {
                "mcpServers": {
                    "dateTime": {
                        "command": "npx",
                        "args": ["-y", "@chirag127/date-and-time-mcp-server"]
                    }
                }
            }
        },
        {
            "name": "方式 2: 使用 smithery CLI",
            "config": {
                "mcpServers": {
                    "dateTime": {
                        "command": "npx",
                        "args": ["-y", "@smithery/cli", "run", "@chirag127/date-and-time-mcp-server"]
                    }
                }
            }
        },
        {
            "name": "方式 3: HTTP 模式（如果有 URL）",
            "config": {
                "mcpServers": {
                    "dateTime": {
                        "url": "https://example-mcp-server.com",  # 需要实际的 URL
                        "headers": {}
                    }
                }
            }
        }
    ]

    manager = MCPClientManager()

    for attempt in configs_to_try:
        print(f"\n{'=' * 60}")
        print(f"{attempt['name']}")
        print('=' * 60)

        try:
            # 保存配置
            config_file = f"mcp_config_{len(configs_to_try)}.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(attempt['config'], f, indent=2, ensure_ascii=False)

            # 加载并连接
            manager.load_config(config_file)

            print("[*] 尝试连接...")
            await manager.connect_all()

            print("[OK] 连接成功！")

            servers = manager.list_servers()
            print(f"[*] 已连接服务器: {servers}")

            # 尝试获取工具
            for server in servers:
                print(f"\n[*] 获取服务器 '{server}' 的工具...")
                try:
                    tools = await manager.get_server_tools(server)
                    print(f"[OK] 找到 {len(tools)} 个工具:")
                    for tool_name in tools:
                        print(f"    - {tool_name}")
                        print(f"      描述: {tools[tool_name].description[:80]}...")

                    # 测试调用一个工具
                    if "getCurrentDateTime" in tools:
                        print(f"\n[*] 测试调用 getCurrentDateTime...")
                        result = await tools["getCurrentDateTime"].execute_async(
                            format="ISO",
                            timezone="Asia/Shanghai"
                        )
                        print(f"[OK] 结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

                    # 成功后就停止
                    print("\n[SUCCESS] FastReAct MCP 客户端工作正常！")
                    print("\n可以:")
                    print("1. 列出可用工具: await manager.get_server_tools('serverName')")
                    print("2. 调用工具: await tools['toolName'].execute_async(params)")
                    print("3. 添加到 Agent: agent = FastReAct(tools=list(tools.values()))")

                    await manager.close_all()
                    return

                except Exception as e:
                    print(f"[ERROR] 获取工具失败: {e}")

            await manager.close_all()

        except Exception as e:
            print(f"[FAILED] {e}")
            continue


async def demo_builtin_mcp_servers():
    """演示内置 MCP 客户端功能"""
    print("\n" + "=" * 60)
    print("FastReAct MCP 客户端功能演示")
    print("=" * 60)

    print("""
FastReAct 的 MCP 客户端功能:

1. **连接管理器** (MCPClientManager):
   - 管理多个 MCP 服务器连接
   - 自动处理连接生命周期
   - 工具发现和注册

2. **支持的服务器类型**:
   - stdio: 通过标准输入/输出通信
   - HTTP (SSE): 通过 HTTP 请求通信

3. **使用流程**:
   a) 配置服务器 (mcp_config.json)
   b) 加载配置: manager.load_config("mcp_config.json")
   c) 连接服务器: await manager.connect_all()
   d) 获取工具: tools = await manager.get_server_tools("serverName")
   e) 使用工具: result = await tools["toolName"].execute_async(params)

4. **集成到 Agent**:
   agent = FastReact(tools=list(tools.values()))
   # AI 会自动选择合适的 MCP 工具

5. **关闭连接**:
   await manager.close_all()
""")


async def test_with_alternative_servers():
    """测试其他可用的 MCP 服务器"""
    print("\n" + "=" * 60)
    print("测试其他 MCP 服务器")
    print("=" * 60)

    # 其他可测试的 MCP 服务器
    alternative_servers = [
        {
            "name": "Filesystem MCP Server",
            "config": {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "D:\\FastReAct"]
                    }
                }
            },
            "notes": "需要提供允许访问的目录路径"
        },
        {
            "name": "Memory MCP Server",
            "config": {
                "mcpServers": {
                    "memory": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-memory"]
                    }
                }
            },
            "notes": "提供内存存储功能"
        }
    ]

    print("\n可尝试的其他 MCP 服务器:")
    for server in alternative_servers:
        print(f"\n{server['name']}")
        print(f"  说明: {server['notes']}")
        print(f"  配置: {json.dumps(server['config'], indent=6)}")


async def show_mcp_client_code_example():
    """展示 MCP 客户端代码示例"""
    print("\n" + "=" * 60)
    print("MCP 客户端代码示例")
    print("=" * 60)

    example_code = '''
# 1. 配置 MCP 服务器 (mcp_config.json)
{
  "mcpServers": {
    "dateTime": {
      "command": "npx",
      "args": ["-y", "@chirag127/date-and-time-mcp-server"]
    }
  }
}

# 2. Python 代码中使用
from fastreact.tools import MCPClientManager

async def use_mcp_server():
    # 创建管理器
    manager = MCPClientManager()

    # 加载配置
    manager.load_config("mcp_config.json")

    # 连接所有服务器
    await manager.connect_all()

    # 获取工具
    tools = await manager.get_server_tools("dateTime")

    # 使用工具
    result = await tools["getCurrentDateTime"].execute_async(
        format="ISO",
        timezone="Asia/Shanghai"
    )
    print(result)

    # 集成到 FastReAct Agent
    from fastreact import FastReAct
    agent = FastReAct(
        api_key="your-api-key",
        model="deepseek-ai/DeepSeek-V3",
        tools=list(tools.values())
    )

    # AI 可以使用 MCP 工具
    response = await agent.run("现在北京时间几点？")
    print(response)

    # 清理
    await manager.close_all()
    await agent.close()

# 运行
asyncio.run(use_mcp_server())
'''

    print(example_code)


async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║     FastReAct 作为 MCP 客户端                        ║
╚══════════════════════════════════════════════════════════╝

目标: 测试 FastReAct 通过 MCP 协议使用外部服务
""")

    # 1. 展示 MCP 客户端功能
    await demo_builtin_mcp_servers()

    # 2. 测试连接
    print("\n\n" + "=" * 60)
    print("开始测试连接...")
    print("=" * 60)

    await test_mcp_client_capability()

    # 3. 展示其他可用的服务器
    await test_with_alternative_servers()

    # 4. 展示代码示例
    await show_mcp_client_code_example()

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("""
✅ FastReAct 支持 MCP 客户端功能
✅ 可以连接到外部 MCP 服务器
✅ 自动发现和注册工具
✅ 与 Agent 无缝集成

⚠️ 当前问题:
   - @chirag127/date-and-time-mcp-server 包无法直接安装
   - 可能需要手动安装或使用其他方式运行

💡 建议:
   1. 尝试其他 MCP 服务器（如 filesystem, memory）
   2. 等待该服务器修复 npm 发布问题
   3. 或使用 FastReAct 内置的时间工具
""")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
