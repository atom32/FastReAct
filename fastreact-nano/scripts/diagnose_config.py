#!/usr/bin/env python3
"""
诊断 API key 配置和内存问题
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("=" * 70)
print("FastReAct Nano - 诊断工具")
print("=" * 70)

# 1. 检查配置文件
print("\n[诊断 1] 配置文件检查")
print("-" * 70)

config_paths = [
    ("用户配置", Path.home() / ".fastreact" / "config.json"),
    ("项目配置", Path.cwd() / ".fastreact" / "config.json"),
    ("凭证文件", Path.home() / ".fastreact" / "credentials.json"),
]

for name, path in config_paths:
    exists = path.exists()
    print(f"\n{name}: {path}")
    print(f"  存在: {exists}")

    if exists:
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            # 检查 API key
            if "llm" in data:
                api_key = data["llm"].get("api_key", "")
                print(f"  API Key: {api_key[:30]}...")

                # 检查是否是环境变量引用
                if api_key.startswith("${"):
                    print(f"  [警告] API key 是环境变量引用，未解析！")
                elif not api_key or api_key.startswith("sk-your"):
                    print(f"  [错误] API key 无效！")
                else:
                    print(f"  [OK] API key 格式正常")

            # 检查 llm_api_keys
            if "llm_api_keys" in data:
                for provider, key in data["llm_api_keys"].items():
                    print(f"  {provider}: {key[:30]}...")
        except Exception as e:
            print(f"  [错误] 读取失败: {e}")

# 2. 检查环境变量
print("\n\n[诊断 2] 环境变量检查")
print("-" * 70)

env_vars = [
    "FASTRACT_MODEL",
    "FASTRACT_API_KEY",
    "FASTRACT_API_BASE",
    "OPENAI_API_KEY",
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"{var}: {value[:30]}...")
    else:
        print(f"{var}: (未设置)")

# 3. 测试 Config.load() 加载
print("\n\n[诊断 3] Config.load() 测试")
print("-" * 70)

from fastreact.core.config import Config

try:
    config = Config.load()
    print(f"[OK] Config 加载成功")
    print(f"  Model: {config.llm.model}")
    print(f"  API Base: {config.llm.api_base}")
    print(f"  API Key: {config.llm.api_key[:30] if config.llm.api_key else 'None'}...")

    if not config.llm.api_key or config.llm.api_key.startswith("sk-your"):
        print(f"  [错误] API key 无效！")
    elif config.llm.api_key.startswith("${"):
        print(f"  [错误] API key 是环境变量引用！")
    else:
        print(f"  [OK] API key 正常")

except Exception as e:
    print(f"[错误] Config 加载失败: {e}")

# 4. 测试 Credentials.load()
print("\n\n[诊断 4] Credentials.load() 测试")
print("-" * 70)

from fastreact.core.credentials import Credentials

try:
    creds = Credentials.load()
    print(f"[OK] Credentials 加载成功")

    siliconflow_key = creds.get("llm_api_keys.siliconflow")
    print(f"  SiliconFlow Key: {siliconflow_key[:30] if siliconflow_key else 'None'}...")

    if siliconflow_key and not siliconflow_key.startswith("${"):
        print(f"  [OK] SiliconFlow key 正常")
    else:
        print(f"  [错误] SiliconFlow key 无效")

except Exception as e:
    print(f"[错误] Credentials 加载失败: {e}")

# 5. 测试 Agent 创建
print("\n\n[诊断 5] Agent 创建测试")
print("-" * 70)

import tracemalloc

print("[INFO] 启用内存追踪...")
tracemalloc.start()

snapshot1 = tracemalloc.take_snapshot()

from fastreact import Agent

try:
    agent = Agent()
    snapshot2 = tracemalloc.take_snapshot()

    # 计算内存差异
    top_stats = snapshot2.compare_to(snapshot1, key_type='lineno')[:5]

    print(f"[OK] Agent 创建成功")
    print(f"\n[内存] Agent 创建后的内存分配 (Top 5):")
    for stat in top_stats:
        print(f"  {stat}")

    current, peak = tracemalloc.get_traced_memory()
    print(f"\n[内存] 当前使用: {current / 1024 / 1024:.2f} MB")
    print(f"[内存] 峰值: {peak / 1024 / 1024:.2f} MB")

except Exception as e:
    print(f"[错误] Agent 创建失败: {e}")

tracemalloc.stop()

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
