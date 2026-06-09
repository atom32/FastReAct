#!/usr/bin/env python3
"""简单测试"""
import sys
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

sys.path = [p for p in sys.path if not ('FastReAct/src' in p and 'fastreact-nano' not in p)]

from fastreact import ask_sync

# 简单测试
result = ask_sync("你好")
print(f"Result: {result}")
