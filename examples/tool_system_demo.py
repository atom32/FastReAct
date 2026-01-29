"""
FastReAct 工具系统调用演示

演示 FastReAct 如何：
1. 自动调用工具（ReAct 模式）
2. 手动调用工具
3. 支持多种工具类型
4. MCP 服务器集成
"""

import asyncio
import json
from fastreact import FastReAct
from fastreact.tools import (
    CalculatorTool,
    GetCurrentTimeTool,
    TavilySearchTool,
)


async def demo_automatic_tool_calling():
    """演示 1: ReAct 自动工具调用"""
    print("=" * 60)
    print("Demo 1: ReAct Automatic Tool Calling")
    print("=" * 60)
    print("\nAI 会自动决定何时使用工具\n")

    # 读取配置
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    default_provider = config.get("default_provider", "siliconflow")
    provider_config = config["llm"]["providers"].get(default_provider, {})
    llm_api_key = provider_config.get("api_key")
    llm_model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")

    # 创建 Agent 并添加工具
    agent = FastReAct(
        api_key=llm_api_key,
        model=llm_model,
        tools=[
            CalculatorTool(),
            GetCurrentTimeTool(),
            TavilySearchTool(),
        ],
        verbose=False
    )

    # 示例问题
    questions = [
        "现在几点了？",
        "计算 (25 * 4) + 10",
        "100天后是什么日期？",
        "最新的AI新闻",
    ]

    for question in questions:
        print(f"\nQ: {question}")
        print("-" * 60)
        response = await agent.run(question, session_id="demo1")
        print(f"A: {response}\n")

    await agent.close()


async def demo_manual_tool_calling():
    """演示 2: 手动调用工具"""
    print("\n" + "=" * 60)
    print("Demo 2: Manual Tool Calling")
    print("=" * 60)
    print("\n直接调用工具，不经过 Agent\n")

    # 1. 获取当前时间
    print("\n[1] GetCurrentTimeTool:")
    time_tool = GetCurrentTimeTool()
    current_time = await time_tool.execute_async()
    print(f"当前时间: {current_time}")

    # 2. 计算器
    print("\n[2] CalculatorTool:")
    calc_tool = CalculatorTool()
    result = await calc_tool.execute_async(expression="2 * (5 + 3)")
    print(f"2 * (5 + 3) = {result}")

    # 3. 日期计算
    print("\n[3] DateTimeCalcTool:")
    from fastreact.tools import DateTimeCalcTool
    date_tool = DateTimeCalcTool()
    date_result = await date_tool.execute_async(
        operation="add_days",
        days=100
    )
    print(f"{date_result}")

    # 4. Tavily 搜索
    print("\n[4] TavilySearchTool:")
    search_tool = TavilySearchTool()
    search_result = await search_tool.execute_async(
        query="Python教程",
        max_results=3
    )
    print(f"搜索结果:\n{search_result}")

    await search_tool.close()


async def demo_tool_definitions():
    """演示 3: 查看工具定义"""
    print("\n" + "=" * 60)
    print("Demo 3: Tool Definitions")
    print("=" * 60)
    print("\n查看工具的参数和描述\n")

    tools = [
        CalculatorTool(),
        GetCurrentTimeTool(),
        TavilySearchTool(),
    ]

    for tool in tools:
        print(f"\n工具名称: {tool.name}")
        print("-" * 60)
        print(f"描述: {tool.description}")
        print(f"参数定义:")
        print(json.dumps(tool.parameters, indent=2, ensure_ascii=False))


async def demo_custom_tool():
    """演示 4: 创建自定义工具"""
    print("\n" + "=" * 60)
    print("Demo 4: Custom Tool Creation")
    print("=" * 60)
    print("\n创建一个简单的自定义工具\n")

    from fastreact.core.tool import Tool

    class UppercaseTool(Tool):
        """文本转大写工具"""

        def _get_description(self):
            return """将文本转换为大写字母

输入一段文本，返回其大写形式。
"""

        def _get_parameters(self):
            return {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要转换的文本",
                    }
                },
                "required": ["text"],
            }

        async def execute_async(self, text: str) -> str:
            return text.upper()

    # 使用自定义工具
    tool = UppercaseTool()
    result = await tool.execute_async(text="hello world")
    print(f"输入: 'hello world'")
    print(f"输出: '{result}'")

    # 集成到 Agent
    print("\n集成到 Agent:")
    agent = FastReAct(
        api_key="test-key",
        model="gpt-4",
        tools=[tool],
        max_iterations=2
    )


def demo_mcp_integration():
    """演示 5: MCP 服务器集成"""
    print("\n" + "=" * 60)
    print("Demo 5: MCP Server Integration")
    print("=" * 60)
    print("""
FastReAct 支持 MCP (Model Context Protocol) 服务器集成。

MCP 是一个开放协议，允许连接外部工具服务器。

使用方式:

1. 配置 MCP 服务器 (mcp_config.json):
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}

2. Python 代码中连接:
from fastreact.tools import MCPClientManager

manager = MCPClientManager()
manager.load_config("mcp_config.json")

# 连接到服务器
await manager.connect_all()

# 获取工具
tools = await manager.get_server_tools("filesystem")

3. 工具会自动注册为 FastReAct 工具

可用的 MCP 服务器:
- filesystem: 文件系统操作
- github: GitHub 仓库操作
- postgres: PostgreSQL 数据库
- brave-search: Brave 搜索引擎
- google-maps: Google 地图
- 更多...

文档: https://modelcontextprotocol.io/
""")


async def main():
    """运行所有演示"""
    print("""
╔══════════════════════════════════════════════════════════╗
║     FastReAct 工具系统调用方式演示                  ║
╚══════════════════════════════════════════════════════════╝

本演示展示:
1. ReAct 自动工具调用
2. 手动调用工具
3. 查看工具定义
4. 创建自定义工具
5. MCP 服务器集成
""")

    # 运行演示
    await demo_automatic_tool_calling()
    await demo_manual_tool_calling()
    await demo_tool_definitions()
    await demo_custom_tool()
    demo_mcp_integration()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n总结:")
    print("✅ FastReAct 自动决定何时使用工具 (ReAct)")
    print("✅ 支持手动调用工具")
    print("✅ 工具有清晰的参数定义")
    print("✅ 可以轻松创建自定义工具")
    print("✅ 支持 MCP 服务器集成")
    print("\n提示:")
    print("- 工具通过 tools 参数传递给 FastReAct")
    print("- AI 会根据问题自动选择合适的工具")
    print("- 也可以直接调用工具，不经过 Agent")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n演示已停止")
