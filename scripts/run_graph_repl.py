"""
GraphAgent REPL 启动脚本

运行智能任务规划 REPL：
    python scripts/run_graph_repl
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastreact.cli.graph_repl import run_graph_repl

if __name__ == '__main__':
    run_graph_repl()
