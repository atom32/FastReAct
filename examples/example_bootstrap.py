"""
Bootstrap 配置系统演示

展示如何使用 Bootstrap 配置系统自定义 Agent 行为。
"""

import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import FastReAct
from fastreact.bootstrap import init_workspace, BootstrapLoader


def demo_init_workspace():
    """演示：初始化工作区"""
    print("=" * 60)
    print("演示 1: 初始化工作区")
    print("=" * 60)

    # 初始化工作区（会在当前目录创建 .fastreact_workspace/）
    manager = init_workspace(workspace="./.fastreact_workspace_demo", overwrite=True)

    print(f"工作区路径: {manager.workspace}")
    print(f"创建的文件: {', '.join(manager.list_files())}")
    print()


def demo_load_bootstrap():
    """演示：加载 Bootstrap 配置"""
    print("=" * 60)
    print("演示 2: 加载 Bootstrap 配置")
    print("=" * 60)

    # 创建 Bootstrap 加载器
    loader = BootstrapLoader(workspace="./.fastreact_workspace_demo")

    # 加载配置
    files = loader.load()

    print(f"已加载的文件: {list(files.keys())}")

    for name, content in files.items():
        preview = content[:100] + "..." if len(content) > 100 else content
        print(f"\n[{name.upper()}]")
        print(preview)

    print()


def demo_build_system_prompt():
    """演示：构建自定义系统提示"""
    print("=" * 60)
    print("演示 3: 构建自定义系统提示")
    print("=" * 60)

    loader = BootstrapLoader(workspace="./.fastreact_workspace_demo")

    base_prompt = "你是一个有帮助的 AI 助手。"
    enhanced_prompt = loader.build_system_prompt(base_prompt)

    print("基础系统提示:")
    print(base_prompt)
    print()

    print("增强后的系统提示（前500字符）:")
    print(enhanced_prompt[:500] + "...")
    print()


def demo_customize_agent():
    """演示：自定义 Agent 人格"""
    print("=" * 60)
    print("演示 4: 自定义 Agent 人格")
    print("=" * 60)

    # 修改 SOUL.md 来自定义人格
    manager = BootstrapLoader("./.fastreact_workspace_demo").workspace

    custom_soul = """# 我的高级编程助手人格

你是一位**资深编程专家**，专注于 Python 开发。

## 特点
- 精通 Python、JavaScript、Go
- 熟悉系统架构和设计模式
- 代码风格追求简洁和可维护性

## 代码风格
- 遵循 PEP 8
- 优先使用类型提示
- 编写清晰的文档字符串
"""

    soul_file = manager / "SOUL.md"
    soul_file.write_text(custom_soul, encoding='utf-8')

    print("已自定义 SOUL.md")
    print(f"新的人格定义: {custom_soul[:100]}...")
    print()


async def demo_agent_with_bootstrap():
    """演示：使用 Bootstrap 配置运行 Agent"""
    print("=" * 60)
    print("演示 5: 使用 Bootstrap 配置运行 Agent")
    print("=" * 60)

    # 注意：需要配置 API Key 才能运行
    print("注意：此演示需要有效的 API Key")
    print("如果要运行，请在 config.json 中设置 api_key")
    print()

    # 示例代码（不会实际运行，因为没有 API Key）
    example_code = """
from fastreact import FastReAct

# 创建 Agent（自动启用 Bootstrap）
agent = FastReAct(
    api_key="your-api-key",
    model="gpt-4",
    enable_bootstrap=True,  # 启用 Bootstrap（默认）
    workspace="./.fastreact_workspace_demo"
)

# 运行查询
result = await agent.run_async(
    query="请用 Python 写一个快速排序"
)

print(result['answer'])
"""

    print("示例代码:")
    print(example_code)
    print()


def demo_reload_bootstrap():
    """演示：重新加载 Bootstrap 配置"""
    print("=" * 60)
    print("演示 6: 重新加载 Bootstrap 配置")
    print("=" * 60)

    loader = BootstrapLoader(workspace="./.fastreact_workspace_demo")

    # 第一次加载
    files1 = loader.load()
    print(f"第一次加载: {len(files1)} 个文件")

    # 修改文件
    workspace = loader.workspace
    agents_file = workspace / "AGENTS.md"
    agents_file.write_text("# Updated Rules\\n\\n新规则：更简洁的回答。", encoding='utf-8')

    # 重新加载
    files2 = loader.reload()
    print(f"重新加载后: {len(files2)} 个文件")
    print(f"AGENTS.md 内容: {files2['agents']}")
    print()


def main():
    """运行所有演示"""
    try:
        demo_init_workspace()
        demo_load_bootstrap()
        demo_build_system_prompt()
        demo_customize_agent()
        demo_agent_with_bootstrap()
        demo_reload_bootstrap()

        print("=" * 60)
        print("所有演示完成！")
        print("=" * 60)
        print()
        print("下一步：")
        print("1. 查看 .fastreact_workspace_demo/ 目录中的配置文件")
        print("2. 根据需要修改 AGENTS.md, SOUL.md, TOOLS.md")
        print("3. 在代码中使用 FastReAct(enable_bootstrap=True)")
        print()
        print("清理：")
        print("删除演示工作区: rm -rf .fastreact_workspace_demo")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
