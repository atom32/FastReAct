#!/usr/bin/env python3
"""
飞书配置测试脚本
验证 App ID 和 App Secret 是否正确，以及是否能获取访问令牌
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

# Load config
config_path = Path.home() / ".fastreact" / "config.json"
with open(config_path) as f:
    config = json.load(f)

app_id = config["feishu"]["app_id"]
app_secret = config["feishu"]["app_secret"]

print("=" * 60)
print("飞书配置测试")
print("=" * 60)
print(f"App ID: {app_id}")
print(f"App Secret: {app_secret[:10]}...")
print()

# Test 1: Get tenant access token
print("[TEST 1] 获取租户访问令牌...")
try:
    response = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={
            "app_id": app_id,
            "app_secret": app_secret
        },
        timeout=10.0
    )
    data = response.json()

    if data.get("code") == 0:
        token = data.get("tenant_access_token")
        print(f"✅ 成功获取访问令牌: {token[:20]}...")
    else:
        print(f"❌ 获取访问令牌失败: {data}")
        sys.exit(1)
except Exception as e:
    print(f"❌ 请求失败: {e}")
    sys.exit(1)

# Test 2: Get bot info
print()
print("[TEST 2] 获取机器人信息...")
try:
    response = httpx.get(
        "https://open.feishu.cn/open-apis/bot/v3/info",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10.0
    )
    data = response.json()

    if data.get("code") == 0:
        bot_name = data.get("data", {}).get("bot", {}).get("name")
        print(f"✅ 机器人名称: {bot_name}")
        print(f"✅ App ID 有效")
    else:
        print(f"❌ 获取机器人信息失败: {data}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print()
print("=" * 60)
print("配置测试完成")
print("=" * 60)
print()
print("如果以上测试都通过，说明 App ID 和 Secret 配置正确。")
print("问题可能在于：")
print("1. 飞书后台事件订阅未正确配置")
print("2. 机器人未发布或未添加到聊天")
print("3. 发送消息时没有@机器人（群聊中必须@）")
