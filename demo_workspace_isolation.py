"""
演示工作区隔离特性

展示在不同目录启动 FastReAct 如何自动隔离会话
"""

import os
import subprocess
import tempfile
from pathlib import Path


def demo_workspace_isolation():
    """演示工作区隔离"""

    print("\n" + "="*70)
    print("FastReAct 工作区隔离演示")
    print("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建三个"项目"
        projects = {
            "project-alpha": "分析Alpha市场数据",
            "project-beta": "开发Beta功能",
            "project-gamma": "测试Gamma模块"
        }

        for project_name, task in projects.items():
            project_dir = tmpdir / project_name
            project_dir.mkdir()

            # 模拟在该目录启动 FastReAct
            print(f"\n{'='*70}")
            print(f"项目: {project_name}")
            print(f"{'='*70}")
            print(f"目录: {project_dir}")
            print(f"任务: {task}")
            print(f"\n如果在这里运行:")
            print(f"  cd {project_dir}")
            print(f"  python -m fastreact.cli.main shell")
            print(f"\n会话将保存在:")
            print(f"  {project_dir / '.fastreact/'}")
            print(f"\n工作区 (workspace):")
            print(f"  {project_dir}")

        print(f"\n{'='*70}")
        print("总结")
        print(f"{'='*70}")
        print(f"\n三个项目的会话完全独立:")
        for project in projects.keys():
            project_dir = tmpdir / project
            print(f"  - {project_dir / '.fastreact/'}")

        print(f"\n{'='*70}")
        print("实际操作示例")
        print(f"{'='*70}")

        print("""
# 项目 A
cd ~/projects/alpha
python -m fastreact.cli.main shell
> run 分析市场数据
> exit
# 会话保存到: ~/projects/alpha/.fastreact/

# 项目 B（完全独立）
cd ~/projects/beta
python -m fastreact.cli.main shell
> run 开发新功能
> exit
# 会话保存到: ~/projects/beta/.fastreact/

# 回到项目 A（会自动提示恢复）
cd ~/projects/alpha
python -m fastreact.cli.main shell
# "Previous session detected:"
# "Continue? [Y/n]"
        """)


if __name__ == "__main__":
    demo_workspace_isolation()

    print(f"\n{'='*70}")
    print("验证：查看当前目录")
    print(f"{'='*70}")
    print(f"\n当前工作目录: {os.getcwd()}")
    print(f"FastReAct 会话目录: {Path.cwd() / '.fastreact'}")

    fastreact_dir = Path.cwd() / ".fastreact"
    if fastreact_dir.exists():
        print(f"\n当前目录已有 FastReAct 会话:")
        for file in fastreact_dir.iterdir():
            print(f"  - {file.name}")
    else:
        print(f"\n当前目录尚无 FastReAct 会话")
        print(f"运行 'python -m fastreact.cli.main shell' 将创建新会话")

    print()
