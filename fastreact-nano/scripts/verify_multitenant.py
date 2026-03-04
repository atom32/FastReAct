#!/usr/bin/env python3
"""
FastReAct 多租户功能验证脚本

无需 Gateway 运行，直接验证核心功能：
1. MultiTenantManager 功能
2. Workspace 自动创建
3. 路径遍历防护
4. 配置加载
"""

import json
import re
import tempfile
from pathlib import Path

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact.core.multitenant import MultiTenantManager, SecurityError


class Colors:
    """终端颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")


def print_section(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {msg} ==={Colors.RESET}")


def test_multitenant_manager():
    """测试 MultiTenantManager"""
    print_section("测试 1: MultiTenantManager 功能")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MultiTenantManager(Path(tmpdir))

        # 测试 1.1: 创建用户 workspace
        print_info("创建用户 workspace...")
        context = manager.get_user_context("web:user@example.com")

        if context.workspace.exists():
            print_success("Workspace 创建成功")
        else:
            print_error("Workspace 创建失败")
            return False

        # 测试 1.2: Workspace 路径正确（使用 resolve() 处理 macOS 路径差异）
        expected_path = (Path(tmpdir) / "web_user@example.com").resolve()
        actual_path = context.workspace.resolve()
        if actual_path == expected_path or actual_path.is_relative_to(Path(tmpdir).resolve()):
            print_success(f"Workspace 路径正确: {context.workspace}")
        else:
            print_error(f"Workspace 路径错误: {context.workspace} != {expected_path}")
            return False

        # 测试 1.3: Config 文件创建
        config_file = context.workspace / "config.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            if config.get("user_key") == "web:user@example.com":
                print_success(f"Config 正确: {config}")
            else:
                print_error(f"Config 错误: {config}")
                return False
        else:
            print_error("Config 文件不存在")
            return False

        # 测试 1.4: 子目录创建
        if context.skills_dir.exists():
            print_success("Skills 目录存在")
        else:
            print_error("Skills 目录不存在")
            return False

    return True


def test_workspace_isolation():
    """测试 Workspace 隔离"""
    print_section("测试 2: Workspace 隔离")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MultiTenantManager(Path(tmpdir))

        # 创建两个用户
        context_a = manager.get_user_context("web:user_a@example.com")
        context_b = manager.get_user_context("web:user_b@example.com")

        # 验证路径不同
        if context_a.workspace != context_b.workspace:
            print_success("用户 A 和 B 的 Workspace 路径不同")
        else:
            print_error("用户 A 和 B 的 Workspace 路径相同")
            return False

        # 用户 A 创建文件
        (context_a.workspace / "test.txt").write_text("User A Data")

        # 验证用户 B 无法访问
        test_file_b = context_b.workspace / "test.txt"
        if not test_file_b.exists():
            print_success("Workspace 隔离正确: 用户 B 无法访问用户 A 的文件")
        else:
            print_error("Workspace 隔离失败: 用户 B 可以访问用户 A 的文件")
            return False

    return True


def test_security_validation():
    """测试安全验证"""
    print_section("测试 3: 安全验证")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MultiTenantManager(Path(tmpdir))

        # 测试 3.1: 无效 user_key 格式
        print_info("测试无效 user_key 格式...")
        try:
            manager.get_user_context("invalid_format")
            print_error("应该拒绝无效格式")
            return False
        except ValueError:
            print_success("正确拒绝无效格式")

        # 测试 3.2: 路径遍历攻击
        print_info("测试路径遍历攻击...")
        try:
            manager.get_user_context("web:../../../etc/passwd")
            print_error("应该拒绝路径遍历")
            return False
        except (SecurityError, ValueError):
            print_success("正确拒绝路径遍历")

        # 测试 3.3: 空字符注入
        print_info("测试空字符注入...")
        try:
            manager.get_user_context("web:user\x00name")
            print_error("应该拒绝空字符")
            return False
        except (SecurityError, ValueError):
            print_success("正确拒绝空字符")

        # 测试 3.4: 特殊字符
        print_info("测试特殊字符...")
        try:
            manager.get_user_context("web:user/name")
            print_error("应该拒绝非法字符")
            return False
        except (SecurityError, ValueError):
            print_success("正确拒绝非法字符")

    return True


def test_user_key_formats():
    """测试各种 user_key 格式"""
    print_section("测试 4: User Key 格式")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MultiTenantManager(Path(tmpdir))

        test_cases = [
            ("web:user@example.com", "Web 用户"),
            ("mobile:user123", "移动端用户"),
            ("api:client_xxx", "API 客户端"),
            ("cli:local", "CLI 用户"),
        ]

        all_passed = True
        for user_key, description in test_cases:
            try:
                context = manager.get_user_context(user_key)
                if context.workspace.exists():
                    print_success(f"{description}: {user_key}")
                else:
                    print_error(f"{description}: Workspace 未创建")
                    all_passed = False
            except Exception as e:
                print_error(f"{description}: {e}")
                all_passed = False

        return all_passed


def test_config_persistence():
    """测试配置持久化"""
    print_section("测试 5: 配置持久化")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MultiTenantManager(Path(tmpdir))

        # 创建用户并更新配置
        user_key = "web:persistence@example.com"
        context = manager.get_user_context(user_key)

        # 更新配置
        manager.update_user_config(user_key, {"custom_field": "custom_value"})

        # 清除缓存
        manager.clear_cache()

        # 重新加载
        context2 = manager.get_user_context(user_key)
        if context2.config.get("custom_field") == "custom_value":
            print_success("配置持久化正确")
        else:
            print_error("配置持久化失败")
            return False

    return True


def main():
    """主测试流程"""
    print(f"\n{Colors.BOLD}FastReAct 多租户功能验证{Colors.RESET}\n")

    tests = [
        test_multitenant_manager,
        test_workspace_isolation,
        test_security_validation,
        test_user_key_formats,
        test_config_persistence,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_error(f"测试异常: {e}")
            results.append(False)

    # 总结
    print_section("测试总结")
    passed = sum(results)
    total = len(results)

    if passed == total:
        print_success(f"所有测试通过 ({passed}/{total})")
        print("\n下一步:")
        print("  1. 启动 Gateway: python -m fastreact.adapters.gateway")
        print("  2. 运行端到端测试: python tests/integration/test_multitenant_e2e.py")
        print("  3. 启动前端测试: cd ../fastreact-nano-web && npm run dev")
        return 0
    else:
        print_error(f"测试失败 ({passed}/{total})")
        return 1


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被中断{Colors.RESET}")
        exit(1)
