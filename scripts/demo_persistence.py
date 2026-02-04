"""
演示会话持久化功能

这个脚本会：
1. 创建一个会话并添加消息
2. 保存到数据库
3. 模拟重启：重新加载数据库
4. 验证数据恢复成功
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact.storage import SQLiteSessionStorage


async def demo_persistence():
    """演示持久化功能"""
    print("=" * 60)
    print("FastReAct 会话持久化演示")
    print("=" * 60)

    # 使用临时文件
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "demo_sessions.db")

        print(f"\n📂 数据库路径: {db_path}")

        # ========== 步骤 1: 初始化存储 ==========
        print("\n[NEW] 步骤 1: 初始化存储...")
        storage = SQLiteSessionStorage(db_path)
        await storage.initialize()
        print("[OK] 存储初始化成功")

        # ========== 步骤 2: 创建会话 ==========
        print("\n[NEW] 步骤 2: 创建会话并添加消息...")
        session_id = "demo_session_123"

        await storage.save_session(session_id, {
            "user_id": "user_456",
            "title": "AI 研究讨论",
            "messages": [
                {
                    "role": "user",
                    "content": "什么是人工智能？",
                    "timestamp": "2026-01-28T10:00:00"
                },
                {
                    "role": "assistant",
                    "content": "人工智能（AI）是计算机科学的一个分支...",
                    "timestamp": "2026-01-28T10:00:05"
                },
                {
                    "role": "user",
                    "content": "AI有哪些应用场景？",
                    "timestamp": "2026-01-28T10:00:15"
                },
                {
                    "role": "assistant",
                    "content": "AI有很多应用场景：\n1. 自然语言处理\n2. 计算机视觉\n3. 智能推荐...",
                    "timestamp": "2026-01-28T10:00:20"
                }
            ],
            "metadata": {
                "model": "gpt-4",
                "total_tokens": 1500
            }
        })

        print(f"[OK] 会话已保存: {session_id}")
        print(f"   - 标题: AI 研究讨论")
        print(f"   - 消息数: 4")

        # ========== 步骤 3: 查看存储统计 ==========
        print("\n[NEW] 步骤 3: 查看存储统计...")
        stats = await storage.get_session_stats()
        print(f"[STATS] 存储统计:")
        print(f"   - 总会话数: {stats['total_sessions']}")
        print(f"   - 总消息数: {stats['total_messages']}")
        print(f"   - 活跃会话: {stats['active_sessions']}")

        # ========== 步骤 4: 模拟重启 - 创建新的存储实例 ==========
        print("\n[NEW] 步骤 4: 模拟 Gateway 重启...")
        print("   (创建新的存储实例，模拟重启)")
        storage2 = SQLiteSessionStorage(db_path)
        await storage2.initialize()
        print("[OK] 新存储实例已初始化")

        # ========== 步骤 5: 加载会话 ==========
        print("\n[NEW] 步骤 5: 从数据库加载会话...")
        loaded_session = await storage2.load_session(session_id)

        if loaded_session:
            print(f"[OK] 会话加载成功!")
            print(f"   - 会话ID: {loaded_session['session_id']}")
            print(f"   - 用户ID: {loaded_session['user_id']}")
            print(f"   - 标题: {loaded_session['title']}")
            print(f"   - 创建时间: {loaded_session['created_at']}")
            print(f"   - 最后活跃: {loaded_session['last_active']}")
            print(f"   - 消息数: {len(loaded_session['messages'])}")
            print(f"   - 元数据: {loaded_session['metadata']}")

            # 显示历史消息
            print("\n📜 历史消息:")
            for i, msg in enumerate(loaded_session['messages'], 1):
                role = msg['role'].upper()
                content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                print(f"   {i}. [{role}] {content}")
        else:
            print("[ERROR] 会话加载失败")
            return

        # ========== 步骤 6: 添加新消息 ==========
        print("\n[NEW] 步骤 6: 继续对话，添加新消息...")
        await storage2.add_message(session_id, {
            "role": "user",
            "content": "谢谢你的解释！",
            "timestamp": "2026-01-28T10:01:00"
        })

        print("[OK] 新消息已添加")

        # 验证消息数量
        updated_session = await storage2.load_session(session_id)
        print(f"   - 当前消息数: {len(updated_session['messages'])}")

        # ========== 步骤 7: 列出所有会话 ==========
        print("\n[NEW] 步骤 7: 列出所有会话...")
        sessions = await storage2.list_sessions()
        print(f"📋 找到 {len(sessions)} 个会话:")
        for session in sessions:
            print(f"   - {session['session_id']}: {session['title']}")

        # ========== 步骤 8: 更新元数据 ==========
        print("\n[NEW] 步骤 8: 更新会话元数据...")
        await storage2.update_session_metadata(session_id, {
            "tags": ["AI", "研究", "讨论"],
            "priority": "high",
            "archived": False
        })
        print("[OK] 元数据已更新")

        # 验证元数据
        final_session = await storage2.load_session(session_id)
        print(f"   - 标签: {final_session['metadata'].get('tags')}")
        print(f"   - 优先级: {final_session['metadata'].get('priority')}")

        # ========== 步骤 9: 健康检查 ==========
        print("\n[NEW] 步骤 9: 存储健康检查...")
        is_healthy = await storage2.health_check()
        print(f"{'[OK]' if is_healthy else '[ERROR]'} 存储状态: {'健康' if is_healthy else '异常'}")

        # ========== 步骤 10: 清理演示 ==========
        print("\n[NEW] 步骤 10: 清理演示...")
        deleted = await storage2.delete_session(session_id)
        print(f"[OK] 会话已删除: {deleted}")

        # 验证删除
        stats_after = await storage2.get_session_stats()
        print(f"   - 剩余会话数: {stats_after['total_sessions']}")

    print("\n" + "=" * 60)
    print("[SUCCESS] 演示完成！会话持久化功能正常工作")
    print("=" * 60)
    print("\n[INFO] 关键特性:")
    print("   [OK] 数据持久化到 SQLite")
    print("   [OK] 重启后自动恢复")
    print("   [OK] 增量保存消息")
    print("   [OK] 元数据管理")
    print("   [OK] 健康检查")
    print()


if __name__ == "__main__":
    asyncio.run(demo_persistence())
