"""
FastReAct Coding Agent - 核心功能演示

展示 FastReAct v1.0.0 的 4 大 Coding Agent 核心工具：
1. Repository Map - 代码库"上帝视角"
2. Stateful Shell - 持久化 Shell 会话
3. Edit File - 精准代码编辑
4. Tool Result Pruning - 自动 Context 管理

运行此脚本查看完整演示。
"""
import sys
import os
import io
import asyncio

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

from fastreact.tools import (
    create_shell_tool,
    create_ls_repo_tool,
    create_edit_file_tool,
)
from fastreact.core.engine import prune_tool_output


async def main():
    """演示所有 4 个核心工具"""
    print("=" * 80)
    print("FastReAct v1.0.0 - Coding Agent 核心功能演示")
    print("=" * 80)

    # 1. Repository Map
    print("\n📁 Repository Map - 查看项目结构")
    print("-" * 80)
    ls_repo = create_ls_repo_tool()
    repo_map = await ls_repo.execute()
    print(repo_map[:600])

    # 2. Stateful Shell
    print("\n💻 Stateful Shell - 持久化会话")
    print("-" * 80)
    shell = create_shell_tool()
    result = await shell.execute("pwd && echo 'Hello' && ls README.md")
    print(result[:400])

    # 3. Edit File
    print("\n📝 Edit File - 精准编辑")
    print("-" * 80)

    # 创建测试文件
    test_file = "demo_test.py"
    with open(test_file, 'w') as f:
        f.write('def old_function():\n    pass\n')

    # 编辑文件
    edit_tool = create_edit_file_tool()
    result = await edit_tool.execute(
        path=test_file,
        search_block='def old_function():\n    pass',
        replace_block='def new_function():\n    """Improved version"""\n    return True'
    )
    print(result[:500])

    # 清理
    os.remove(test_file)
    if os.path.exists(test_file + ".bak"):
        os.remove(test_file + ".bak")

    # 4. Tool Result Pruning
    print("\n✂️ Tool Result Pruning - 防止 Context 爆炸")
    print("-" * 80)
    large = "\n".join([f"Line {i}" for i in range(200)])
    pruned = prune_tool_output(large)
    print(f"原始: {len(large.splitlines())} 行 → 截断: {len(pruned.splitlines())} 行")

    # 总结
    print("\n" + "=" * 80)
    print("✅ FastReAct Coding Agent - 完整能力已就绪！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
