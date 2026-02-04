"""
FastReAct 集成测试套件

运行四个"地狱难度"的复合测试用例，验证系统的集成能力：
1. Audit & Fix Loop - 跨领域工具链协作 + RAG 持久化
2. Context Stress Test - 长对话剪枝 + Token 优化
3. Brain Reload Test - 跨 Session 知识迁移
4. Tool Graph & Dependency Test - 工具拓扑逻辑约束

运行方法：
    python run_integration_tests.py              # 运行所有测试
    python run_integration_tests.py --test 1      # 只运行测试 1
    python run_integration_tests.py --test 2      # 只运行测试 2
    python run_integration_tests.py --test 3      # 只运行测试 3
    python run_integration_tests.py --test 4      # 只运行测试 4
"""
import sys
import asyncio
import argparse
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 导入测试模块
import test_integration_1_audit_fix
import test_integration_2_context_stress
import test_integration_3_brain_reload
import test_integration_4_tool_graph


def print_header(title):
    """打印测试标题"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def run_test(test_num):
    """运行指定的测试"""
    print_header(f"开始测试 {test_num}")

    tests = {
        1: ("Audit & Fix Loop", test_integration_1_audit_fix.test_audit_fix_loop),
        2: ("Context Stress Test", test_integration_2_context_stress.test_context_stress),
        3: ("Brain Reload Test", test_integration_3_brain_reload.test_brain_reload),
        4: ("Tool Graph & Dependency Test", test_integration_4_tool_graph.test_tool_graph),
    }

    if test_num not in tests:
        print(f"[ERROR] 无效的测试编号: {test_num}")
        return False

    test_name, test_func = tests[test_num]
    print(f"\n测试名称: {test_name}")
    print(f"测试描述: ", end="")

    descriptions = {
        1: "跨领域工具链协作 + RAG 持久化",
        2: "长对话剪枝 + Token 优化",
        3: "跨 Session 知识迁移",
        4: "工具拓扑逻辑约束",
    }
    print(descriptions[test_num])

    try:
        # 所有测试都是异步函数
        result = asyncio.run(test_func())

        if result:
            print_header(f"测试 {test_num} 通过")
            return True
        else:
            print_header(f"测试 {test_num} 失败")
            return False

    except Exception as e:
        print(f"\n[ERROR] 测试 {test_num} 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print_header("FastReAct 集成测试套件")
    print("""
这四个测试用例验证 FastReAct 的各个模块是否有机结合：

测试 1: Audit & Fix Loop
  - 测试内容: 跨领域工具链协作 + RAG 持久化
  - 验证点: 代码审查、互联网搜索、精准修复、跨会话记忆

测试 2: Context Stress Test
  - 测试内容: 长对话剪枝 + Token 优化
  - 验证点: Memory Flush、Token 减少、系统指令保留

测试 3: Brain Reload Test
  - 测试内容: 跨 Session 知识迁移
  - 验证点: Embedding 持久化、文件状态、知识检索

测试 4: Tool Graph & Dependency Test
  - 测试内容: 工具拓扑逻辑约束
  - 验证点: 逻辑顺序、数据流转、循环检测

预计时间: 12-18 分钟（包含模型加载）
    """)

    input("\n按 Enter 开始测试...")

    results = {}

    for test_num in [1, 2, 3, 4]:
        results[test_num] = run_test(test_num)

        if test_num < 4:
            print(f"\n等待 5 秒后继续下一个测试...")
            import time
            time.sleep(5)

    # 总结
    print_header("测试总结")
    print()

    for test_num, passed in results.items():
        test_names = {
            1: "Audit & Fix Loop",
            2: "Context Stress Test",
            3: "Brain Reload Test",
            4: "Tool Graph & Dependency Test",
        }
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} 测试 {test_num}: {test_names[test_num]}")

    print()
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\n总计: {total_passed}/{total_tests} 通过")

    if total_passed == total_tests:
        print("\n[SUCCESS] 所有测试通过！FastReAct 集成良好")
        return True
    else:
        print(f"\n[WARNING] {total_tests - total_passed} 个测试失败")
        return False


def main():
    parser = argparse.ArgumentParser(description="FastReAct 集成测试套件")
    parser.add_argument(
        "--test",
        type=int,
        choices=[1, 2, 3, 4],
        help="只运行指定的测试（1, 2, 3, 或 4）"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查测试所需功能是否齐全"
    )

    args = parser.parse_args()

    try:
        if args.check:
            # 功能检查
            print("运行功能检查...")
            import subprocess
            result = subprocess.run([sys.executable, "test_integration_check.py"], cwd=Path(__file__).parent)
            return result.returncode

        if args.test:
            # 运行单个测试
            success = run_test(args.test)
            exit_code = 0 if success else 1
        else:
            # 运行所有测试
            success = run_all_tests()
            exit_code = 0 if success else 1

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] 测试被用户中断")
        exit_code = 130  # 标准的 Ctrl+C 退出码
    except Exception as e:
        print(f"\n[ERROR] 测试运行异常: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        # 确保退出消息显示
        print(f"\n[EXIT] 测试程序退出，代码: {exit_code}")
        # 给系统一点时间刷新输出
        import time
        time.sleep(0.1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
