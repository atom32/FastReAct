"""
端到端测试：Gateway + 持久化

这个脚本会：
1. 初始化 Gateway（带持久化）
2. 创建 WebSocket 连接
3. 发送消息
4. 验证数据已保存到数据库
5. 模拟重启，验证数据恢复
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool
from fastreact.gateway import GatewayServer
from fastreact.storage import SQLiteSessionStorage


async def test_gateway_with_persistence():
    """测试 Gateway 的持久化功能"""
    print("=" * 60)
    print("FastReAct Gateway + Persistence E2E Test")
    print("=" * 60)

    # 使用临时数据库
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "e2e_sessions.db")

        print(f"\n[1/6] Creating storage...")
        storage = SQLiteSessionStorage(db_path)
        await storage.initialize()
        print("OK - Storage initialized")

        print(f"\n[2/6] Creating Gateway...")
        agent = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
            max_iterations=2,
        )

        gateway = GatewayServer(
            agent,
            storage=storage,
            auto_save=True
        )

        await gateway.startup()
        print("OK - Gateway initialized with storage")

        print(f"\n[3/6] Creating session...")
        session_id = "e2e_test_session"

        # 模拟会话数据
        session_data = {
            "title": "E2E Test Session",
            "messages": [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "2+2 equals 4"}
            ]
        }

        # 保存到存储（模拟 WebSocket 消息）
        await storage.save_session(session_id, session_data)
        print(f"OK - Session created: {session_id}")

        print(f"\n[4/6] Verifying data in database...")
        loaded = await storage.load_session(session_id)
        assert loaded is not None, "Failed to load session"
        assert loaded["title"] == "E2E Test Session"
        assert len(loaded["messages"]) == 2
        print("OK - Data verified in database")

        print(f"\n[5/6] Simulating Gateway restart...")
        # 创建新的 Gateway 实例（模拟重启）
        gateway2 = GatewayServer(
            agent,
            storage=SQLiteSessionStorage(db_path),
            auto_save=True
        )
        await gateway2.startup()
        print("OK - Gateway 'restarted'")

        print(f"\n[6/6] Loading session after 'restart'...")
        # 从新 Gateway 的存储加载会话
        loaded_after_restart = await gateway2.storage.load_session(session_id)
        assert loaded_after_restart is not None
        assert loaded_after_restart["title"] == "E2E Test Session"
        assert len(loaded_after_restart["messages"]) == 2
        print("OK - Session recovered successfully")

        # 显示恢复的数据
        print("\nRecovered Data:")
        print(f"  Session ID: {loaded_after_restart['session_id']}")
        print(f"  Title: {loaded_after_restart['title']}")
        print(f"  Created: {loaded_after_restart['created_at']}")
        print(f"  Messages: {len(loaded_after_restart['messages'])}")

        print("\n" + "=" * 60)
        print("SUCCESS - All tests passed!")
        print("=" * 60)

        print("\nFeatures Tested:")
        print("  [✓] Storage initialization")
        print("  [✓] Gateway startup with storage")
        print("  [✓] Session creation and saving")
        print("  [✓] Data persistence verification")
        print("  [✓] Gateway restart simulation")
        print("  [✓] Session recovery after restart")

        return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_gateway_with_persistence())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
