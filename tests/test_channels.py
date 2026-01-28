"""
测试 Channel 系统
"""

import pytest
from fastreact.channels import ChannelManager
from fastreact.channels.base import Channel


class DummyChannel(Channel):
    """测试用的假通道"""

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False

    async def send_message(self, user_id: str, message: str, **kwargs):
        self.messages.append((user_id, message))

    async def get_user_info(self, user_id: str):
        return {"id": user_id, "name": "Test User"}

    def __init__(self, name="dummy", **kwargs):
        super().__init__(name, **kwargs)
        self.messages = []


@pytest.mark.asyncio
class TestChannelManager:
    """测试 ChannelManager"""

    async def test_register_channel(self):
        """测试注册通道"""
        manager = ChannelManager()
        channel = DummyChannel()

        manager.register_channel(channel)

        assert "dummy" in manager.channels
        assert manager.get_channel("dummy") is channel

    async def test_register_duplicate_channel(self):
        """测试注册重复通道"""
        manager = ChannelManager()
        channel1 = DummyChannel()
        channel2 = DummyChannel()

        manager.register_channel(channel1)

        with pytest.raises(ValueError):
            manager.register_channel(channel2)

    async def test_unregister_channel(self):
        """测试注销通道"""
        manager = ChannelManager()
        channel = DummyChannel()

        manager.register_channel(channel)
        assert "dummy" in manager.channels

        result = manager.unregister_channel("dummy")
        assert result is True
        assert "dummy" not in manager.channels

    async def test_unregister_nonexistent_channel(self):
        """测试注销不存在的通道"""
        manager = ChannelManager()

        result = manager.unregister_channel("nonexistent")
        assert result is False

    async def test_list_channels(self):
        """测试列出通道"""
        manager = ChannelManager()

        channel1 = DummyChannel(name="ch1")
        channel2 = DummyChannel(name="ch2")

        manager.register_channel(channel1)
        manager.register_channel(channel2)

        channels = manager.list_channels()
        assert len(channels) == 2

        channel_names = [c["name"] for c in channels]
        assert "ch1" in channel_names
        assert "ch2" in channel_names

    async def test_start_channel(self):
        """测试启动通道"""
        manager = ChannelManager()
        channel = DummyChannel()
        manager.register_channel(channel)

        await manager.start_channel("dummy")

        assert channel.running is True

    async def test_start_nonexistent_channel(self):
        """测试启动不存在的通道"""
        manager = ChannelManager()

        with pytest.raises(ValueError):
            await manager.start_channel("nonexistent")

    async def test_stop_channel(self):
        """测试停止通道"""
        manager = ChannelManager()
        channel = DummyChannel()
        manager.register_channel(channel)

        await manager.start_channel("dummy")
        assert channel.running is True

        await manager.stop_channel("dummy")
        assert channel.running is False

    async def test_start_all(self):
        """测试启动所有通道"""
        manager = ChannelManager()

        channel1 = DummyChannel(name="ch1")
        channel2 = DummyChannel(name="ch2")

        manager.register_channel(channel1)
        manager.register_channel(channel2)

        await manager.start_all()

        assert channel1.running is True
        assert channel2.running is True

    async def test_stop_all(self):
        """测试停止所有通道"""
        manager = ChannelManager()

        channel1 = DummyChannel(name="ch1")
        channel2 = DummyChannel(name="ch2")

        manager.register_channel(channel1)
        manager.register_channel(channel2)

        await manager.start_all()
        await manager.stop_all()

        assert channel1.running is False
        assert channel2.running is False

    async def test_send_to_channel(self):
        """测试发送到通道"""
        manager = ChannelManager()
        channel = DummyChannel()
        manager.register_channel(channel)
        await manager.start_channel("dummy")

        await manager.send_to_channel("dummy", "user123", "Hello!")

        assert len(channel.messages) == 1
        assert channel.messages[0] == ("user123", "Hello!")

    async def test_send_to_stopped_channel(self):
        """测试发送到停止的通道"""
        manager = ChannelManager()
        channel = DummyChannel()
        manager.register_channel(channel)

        with pytest.raises(ValueError):
            await manager.send_to_channel("dummy", "user123", "Hello!")

    async def test_set_message_handler(self):
        """测试设置消息处理器"""
        manager = ChannelManager()
        channel1 = DummyChannel(name="ch1")
        channel2 = DummyChannel(name="ch2")

        manager.register_channel(channel1)
        manager.register_channel(channel2)

        # 设置处理器
        async def handler(channel, user_id, message, metadata):
            pass

        manager.set_message_handler(handler)

        # 验证所有通道都有处理器
        assert channel1.message_handler is handler
        assert channel2.message_handler is handler

    async def test_get_stats(self):
        """测试获取统计信息"""
        manager = ChannelManager()

        channel1 = DummyChannel(name="ch1")
        channel2 = DummyChannel(name="ch2")

        manager.register_channel(channel1)
        manager.register_channel(channel2)

        stats = manager.get_stats()

        assert stats["total_channels"] == 2
        assert stats["running_channels"] == 0
        assert stats["stopped_channels"] == 2

    async def test_health_check(self):
        """测试健康检查"""
        manager = ChannelManager()

        channel1 = DummyChannel(name="ch1")
        channel2 = DummyChannel(name="ch2")

        manager.register_channel(channel1)
        manager.register_channel(channel2)

        await manager.start_channel("ch1")

        health = await manager.health_check()

        assert health["ch1"] is True
        assert health["ch2"] is False
