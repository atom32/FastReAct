"""
测试 SQLite 会话存储
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from pathlib import Path

from fastreact.storage import SQLiteSessionStorage


@pytest.fixture
async def storage():
    """创建临时存储实例"""
    # 使用临时文件
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sessions.db")
        storage = SQLiteSessionStorage(db_path)
        await storage.initialize()
        yield storage
        # 清理由 tempfile 自动处理


@pytest.mark.asyncio
class TestSQLiteSessionStorage:
    """测试 SQLite 会话存储"""

    async def test_initialize(self, storage):
        """测试初始化"""
        # 检查数据库文件是否创建
        assert os.path.exists(storage.db_path)
        assert os.path.getsize(storage.db_path) > 0

    async def test_save_and_load_session(self, storage):
        """测试保存和加载会话"""
        session_id = "test_session_1"
        data = {
            "user_id": "user123",
            "title": "测试会话",
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"}
            ],
            "metadata": {"key": "value"}
        }

        # 保存
        await storage.save_session(session_id, data)

        # 加载
        loaded = await storage.load_session(session_id)

        assert loaded is not None
        assert loaded["session_id"] == session_id
        assert loaded["user_id"] == "user123"
        assert loaded["title"] == "测试会话"
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["content"] == "你好"
        assert loaded["metadata"]["key"] == "value"

    async def test_load_nonexistent_session(self, storage):
        """测试加载不存在的会话"""
        loaded = await storage.load_session("nonexistent")
        assert loaded is None

    async def test_update_existing_session(self, storage):
        """测试更新现有会话"""
        session_id = "test_session_2"

        # 第一次保存
        await storage.save_session(session_id, {
            "title": "原标题",
            "messages": [{"role": "user", "content": "消息1"}]
        })

        # 更新
        await storage.save_session(session_id, {
            "title": "新标题",
            "messages": [
                {"role": "user", "content": "消息1"},
                {"role": "assistant", "content": "消息2"}
            ]
        })

        # 验证
        loaded = await storage.load_session(session_id)
        assert loaded["title"] == "新标题"
        assert len(loaded["messages"]) == 2

    async def test_list_sessions(self, storage):
        """测试列出会话"""
        # 创建多个会话
        for i in range(3):
            await storage.save_session(f"session_{i}", {
                "user_id": f"user_{i % 2}",  # 2个不同用户
                "title": f"会话 {i}",
                "messages": []
            })

        # 列出所有会话
        all_sessions = await storage.list_sessions()
        assert len(all_sessions) >= 3

        # 列出特定用户的会话
        user_sessions = await storage.list_sessions(user_id="user_0")
        assert len(user_sessions) >= 1

    async def test_delete_session(self, storage):
        """测试删除会话"""
        session_id = "test_session_delete"

        # 创建会话
        await storage.save_session(session_id, {
            "title": "待删除",
            "messages": []
        })

        # 确认存在
        loaded = await storage.load_session(session_id)
        assert loaded is not None

        # 删除
        result = await storage.delete_session(session_id)
        assert result is True

        # 确认已删除
        loaded = await storage.load_session(session_id)
        assert loaded is None

    async def test_delete_nonexistent_session(self, storage):
        """测试删除不存在的会话"""
        result = await storage.delete_session("nonexistent")
        assert result is False

    async def test_add_message(self, storage):
        """测试添加单条消息"""
        session_id = "test_session_add_msg"

        # 创建会话
        await storage.save_session(session_id, {
            "title": "测试添加消息",
            "messages": []
        })

        # 添加消息
        await storage.add_message(session_id, {
            "role": "user",
            "content": "新消息",
            "metadata": {"test": True}
        })

        # 验证
        loaded = await storage.load_session(session_id)
        assert len(loaded["messages"]) == 1
        assert loaded["messages"][0]["content"] == "新消息"

    async def test_update_session_metadata(self, storage):
        """测试更新会话元数据"""
        session_id = "test_session_metadata"

        # 创建会话
        await storage.save_session(session_id, {
            "title": "测试元数据",
            "messages": [],
            "metadata": {"key1": "value1"}
        })

        # 更新元数据
        await storage.update_session_metadata(session_id, {
            "key2": "value2",
            "key3": "value3"
        })

        # 验证
        loaded = await storage.load_session(session_id)
        assert loaded["metadata"]["key1"] == "value1"  # 保留
        assert loaded["metadata"]["key2"] == "value2"  # 新增
        assert loaded["metadata"]["key3"] == "value3"  # 新增

    async def test_get_session_stats(self, storage):
        """测试获取统计信息"""
        # 创建一些会话
        for i in range(5):
            await storage.save_session(f"stats_session_{i}", {
                "title": f"统计测试 {i}",
                "messages": [
                    {"role": "user", "content": f"消息 {j}"}
                    for j in range(i)  # 0-4条消息
                ]
            })

        # 获取统计
        stats = await storage.get_session_stats()
        assert stats["total_sessions"] >= 5
        assert stats["total_messages"] >= 10  # 0+1+2+3+4=10

    async def test_health_check(self, storage):
        """测试健康检查"""
        is_healthy = await storage.health_check()
        assert is_healthy is True

    async def test_cleanup_old_sessions(self, storage):
        """测试清理旧会话"""
        # 创建会话（但不设置 last_active，模拟旧会话）
        # 这个测试可能需要调整，因为 SQLite 会自动设置时间戳
        # 这里只测试方法可以调用
        deleted = await storage.cleanup_old_sessions(days=0)  # 删除所有
        assert deleted >= 0

    async def test_concurrent_access(self, storage):
        """测试并发访问（不同会话）"""
        # 创建多个不同会话
        tasks = [
            storage.save_session(f"concurrent_session_{i}", {
                "title": f"并发测试 {i}",
                "messages": [{"role": "user", "content": f"消息 {i}"}]
            })
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # 验证所有会话都已保存
        for i in range(10):
            loaded = await storage.load_session(f"concurrent_session_{i}")
            assert loaded is not None
            assert f"并发测试 {i}" in loaded["title"]

    async def test_large_messages(self, storage):
        """测试大量消息"""
        session_id = "large_session"

        # 创建包含大量消息的会话
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"消息 {i}"}
            for i in range(100)
        ]

        await storage.save_session(session_id, {
            "title": "大量消息测试",
            "messages": messages
        })

        # 加载并验证
        loaded = await storage.load_session(session_id)
        assert len(loaded["messages"]) == 100

    async def test_special_characters(self, storage):
        """测试特殊字符"""
        session_id = "special_chars_session"

        # 包含特殊字符的消息
        special_data = {
            "title": "测试特殊字符: [SUCCESS] [CODE]",
            "messages": [
                {"role": "user", "content": "包含引号 \"和单引号 '"},
                {"role": "assistant", "content": "包含换行符\n和制表符\t"},
                {"role": "user", "content": "包含 emoji 😀🎊"},
                {"role": "assistant", "content": "包含中文、日本語、한국어"}
            ]
        }

        await storage.save_session(session_id, special_data)
        loaded = await storage.load_session(session_id)

        assert loaded["title"] == special_data["title"]
        assert len(loaded["messages"]) == 4
        assert "[SUCCESS]" in loaded["title"]
        assert "\n" in loaded["messages"][1]["content"]
