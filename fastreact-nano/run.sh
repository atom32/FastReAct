#!/usr/bin/env python3
"""
FastReAct Nano - CLI 启动脚本
"""
import sys
from pathlib import Path

# 添加项目 src 目录到路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 清除可能冲突的旧路径
sys.path = [
    p for p in sys.path
    if not ('FastReAct/src' in p and 'fastreact-nano' not in p)
]

# 导入并运行 CLI
from fastreact.adapters.cli import app

if __name__ == "__main__":
    app()
