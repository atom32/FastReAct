#!/usr/bin/env python
"""
FastReAct Nano - 快速验证脚本

Run this to verify your installation is working correctly.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_imports():
    """Test 1: 验证导入"""
    print_section("Test 1: 验证导入")

    try:
        from fastreact import (
            Agent,
            ask_sync,
            Config,
        )
        print("[OK] 所有核心模块导入成功")
        return True
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
        print("\n请确保已正确安装:")
        print("  cd fastreact-nano")
        print("  pip install -e .")
        return False


async def test_agent_creation():
    """Test 2: 验证Agent创建"""
    print_section("Test 2: 验证Agent创建")

    try:
        from fastreact import Agent

        agent = Agent()

        # 验证工具
        tools = agent.list_tools()
        print(f"[OK] 可用工具: {tools}")

        # 验证skills
        skills = agent.list_skills()
        print(f"[OK] 可用skills: {skills}")

        return True
    except Exception as e:
        print(f"[ERROR] Agent创建失败: {e}")
        return False


async def test_sync_query():
    """Test 3: 验证同步查询"""
    print_section("Test 3: 验证同步查询")

    try:
        from fastreact import ask_sync

        print("[INFO] 发送测试查询...")
        response = ask_sync("What is 1+1?")

        if response:
            print(f"[OK] 收到响应: {response[:100]}...")
            return True
        else:
            print("[ERROR] 没有收到响应")
            return False

    except Exception as e:
        print(f"[ERROR] 同步查询失败: {e}")
        print("\n请检查API Key是否设置:")
        print("  export FASTRACT_API_KEY=sk-xxx")
        print("  export FASTRACT_MODEL=gpt-4o-mini")
        return False


async def test_agent_run():
    """Test 4: 验证Agent运行"""
    print_section("Test 4: 验证Agent运行")

    try:
        from fastreact import Agent

        agent = Agent()

        print("[INFO] 发送Agent查询...")
        response = await agent.run(
            "List available tools"
        )

        if response:
            print(f"[OK] Agent响应: {response[:100]}...")
            return True
        else:
            print("[ERROR] Agent没有响应")
            return False

    except Exception as e:
        print(f"[ERROR] Agent运行失败: {e}")
        return False


async def test_config():
    """Test 5: 验证配置"""
    print_section("Test 5: 验证配置")

    try:
        from fastreact import Config

        config = Config.from_env()

        print(f"[OK] 模型: {config.llm.model}")
        print(f"[OK] 最大迭代: {config.react.max_iterations}")
        print(f"[OK] 启用Steering: {config.react.enable_steering}")
        print(f"[OK] 启用Follow-up: {config.react.enable_followup}")

        return True
    except Exception as e:
        print(f"[ERROR] 配置验证失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                            ║
║        FastReAct Nano v2.0 - 快速验证脚本                 ║
║                                                            ║
╚══════════════════════════════════════════════════════════════╝

此脚本将验证您的安装是否正常工作。
    """)

    tests = [
        ("导入验证", test_imports, False),
        ("Agent创建", test_agent_creation, True),
        ("配置验证", test_config, False),
        ("同步查询", test_sync_query, True),
        ("Agent运行", test_agent_run, True),
    ]

    results = []

    for name, test_func, is_async in tests:
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name} 测试异常: {e}")
            results.append((name, False))

    # 总结
    print_section("测试总结")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n测试结果: {passed}/{total} 通过\n")

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print()

    if passed == total:
        print("[SUCCESS] 🎉 所有测试通过！FastReAct Nano 已就绪。")
        print("\n下一步:")
        print("  • 运行测试: pytest tests/ -v")
        print("  • 使用CLI: fastreact \"你的问题\"")
        print("  • 查看文档: cat USAGE.md")
        return 0
    else:
        print("[WARNING] ⚠️  部分测试失败，请检查配置。")
        print("\n获取帮助:")
        print("  • 查看文档: cat GETTING_STARTED.md")
        print("  • 查看项目状态: cat PROJECT_STATUS.md")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
