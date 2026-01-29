"""
微信通道集成示例

演示如何使用微信公众号和企业微信通道。
"""

import asyncio
import os
from fastreact import FastReAct
from fastreact.channels import ChannelManager
from fastreact.channels.wechat import WeChatChannel, WeChatWorkChannel


async def example_wechat_mp():
    """微信公众号集成示例"""
    print("=" * 60)
    print("微信公众号集成示例")
    print("=" * 60)

    # 1. 创建 FastReAct Agent
    agent = FastReAct(
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("LLM_MODEL", "gpt-4"),
    )

    # 2. 创建微信通道
    wechat_channel = WeChatChannel(
        app_id=os.getenv("WECHAT_APP_ID"),
        app_secret=os.getenv("WECHAT_APP_SECRET"),
        token=os.getenv("WECHAT_TOKEN"),
        encoding_aes_key=os.getenv("WECHAT_ENCODING_AES_KEY"),  # 可选
        gateway_url="ws://localhost:8000"
    )

    # 3. 创建通道管理器
    manager = ChannelManager()
    manager.register_channel(wechat_channel)

    # 设置消息处理器（将消息转发给 Agent）
    async def handle_message(channel: str, user_id: str, message: str, metadata: dict):
        """处理来自微信的消息"""
        print(f"\n收到消息:")
        print(f"  通道: {channel}")
        print(f"  用户: {user_id}")
        print(f"  消息: {message}")
        print(f"  元数据: {metadata}")

        # 调用 Agent 处理
        response = await agent.run(
            query=message,
            session_id=user_id  # 使用 user_id 作为会话 ID
        )

        # 发送回复
        await wechat_channel.send_message(user_id, response)

    wechat_channel.set_message_handler(handle_message)

    # 4. 启动通道
    print("\n启动微信通道...")
    await wechat_channel.start()

    # 启动 webhook 服务器
    print("启动 webhook 服务器（监听端口 8001）...")
    print("请在微信公众号后台配置服务器地址: http://your-domain.com:8001/wechat")

    try:
        await wechat_channel.run_server(host="0.0.0.0", port=8001)
    except KeyboardInterrupt:
        print("\n停止服务器...")
        await wechat_channel.stop()


async def example_wechat_work():
    """企业微信应用集成示例"""
    print("\n" + "=" * 60)
    print("企业微信应用集成示例")
    print("=" * 60)

    # 1. 创建 FastReAct Agent
    agent = FastReAct(
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("LLM_MODEL", "gpt-4"),
    )

    # 2. 创建企业微信通道
    work_channel = WeChatWorkChannel(
        corp_id=os.getenv("WECHAT_WORK_CORP_ID"),
        agent_id=int(os.getenv("WECHAT_WORK_AGENT_ID", "1001")),
        secret=os.getenv("WECHAT_WORK_SECRET"),
        gateway_url="ws://localhost:8000"
    )

    # 3. 启动通道
    print("\n启动企业微信通道...")
    await work_channel.start()

    # 4. 发送测试消息
    test_user_id = os.getenv("WECHAT_WORK_TEST_USER_ID")
    if test_user_id:
        print(f"发送测试消息给用户: {test_user_id}")

        # 发送文本消息
        await work_channel.send_message(
            user_id=test_user_id,
            message="你好！这是来自 FastReAct 的测试消息。"
        )

        # 发送文本卡片消息
        await work_channel.send_message(
            user_id=test_user_id,
            msg_type="textcard",
            message="点击查看详情",
            title="重要通知",
            url="https://example.com"
        )

    # 5. 获取用户信息
    if test_user_id:
        user_info = await work_channel.get_user_info(test_user_id)
        print(f"用户信息: {user_info}")

    # 6. 停止通道
    await work_channel.stop()


async def example_combined_channels():
    """多通道集成示例（同时使用微信、Telegram、Slack）"""
    print("\n" + "=" * 60)
    print("多通道集成示例")
    print("=" * 60)

    from fastreact.channels.telegram import TelegramChannel

    # 1. 创建 Agent
    agent = FastReAct(
        api_key=os.getenv("LLM_API_KEY"),
        model=os.getenv("LLM_MODEL", "gpt-4"),
    )

    # 2. 创建多个通道
    manager = ChannelManager()

    # 微信公众号
    if os.getenv("WECHAT_APP_ID"):
        wechat = WeChatChannel(
            app_id=os.getenv("WECHAT_APP_ID"),
            app_secret=os.getenv("WECHAT_APP_SECRET"),
            token=os.getenv("WECHAT_TOKEN")
        )
        manager.register_channel(wechat)

    # Telegram
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        telegram = TelegramChannel(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN")
        )
        manager.register_channel(telegram)

    # 3. 统一消息处理器
    async def handle_message(channel: str, user_id: str, message: str, metadata: dict):
        """统一处理所有通道的消息"""
        print(f"\n[{channel.upper()}] {user_id}: {message}")

        # Agent 处理
        response = await agent.run(
            query=message,
            session_id=f"{channel}:{user_id}"  # 包含通道信息
        )

        # 根据通道发送回复
        if channel == "wechat":
            await manager.channels["wechat"].send_message(user_id, response)
        elif channel == "telegram":
            await manager.channels["telegram"].send_message(user_id, response)

    # 设置处理器
    for channel in manager.channels.values():
        channel.set_message_handler(handle_message)

    # 4. 启动所有通道
    print("\n启动所有通道...")
    await manager.start_all()

    print("所有通道已启动！")
    print("支持的平台:")
    for name, channel in manager.channels.items():
        print(f"  - {name}: {'✓' if channel.running else '✗'}")

    # 保持运行
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n停止所有通道...")
        await manager.stop_all()


async def example_upload_media():
    """上传媒体素材示例"""
    print("\n" + "=" * 60)
    print("上传媒体素材示例")
    print("=" * 60)

    channel = WeChatChannel(
        app_id=os.getenv("WECHAT_APP_ID"),
        app_secret=os.getenv("WECHAT_APP_SECRET"),
        token=os.getenv("WECHAT_TOKEN")
    )

    await channel.start()

    # 上传图片
    image_path = "path/to/image.jpg"
    if os.path.exists(image_path):
        media_id = await channel.upload_media("image", image_path)
        print(f"图片上传成功，media_id: {media_id}")

        # 发送图片消息
        test_user = os.getenv("WECHAT_TEST_USER_ID")
        if test_user:
            await channel.send_message(
                user_id=test_user,
                msg_type="image",
                message=media_id
            )
            print(f"图片已发送给用户: {test_user}")

    await channel.stop()


async def example_user_info():
    """获取用户信息示例"""
    print("\n" + "=" * 60)
    print("获取用户信息示例")
    print("=" * 60)

    channel = WeChatChannel(
        app_id=os.getenv("WECHAT_APP_ID"),
        app_secret=os.getenv("WECHAT_APP_SECRET"),
        token=os.getenv("WECHAT_TOKEN")
    )

    await channel.start()

    test_user = os.getenv("WECHAT_TEST_USER_ID")
    if test_user:
        user_info = await channel.get_user_info(test_user)

        print("用户信息:")
        print(f"  昵称: {user_info.get('nickname')}")
        print(f"  省份: {user_info.get('province')}")
        print(f"  城市: {user_info.get('city')}")
        print(f"  头像: {user_info.get('headimgurl')}")

    await channel.stop()


# ====== 主程序 ======

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example = sys.argv[1]
    else:
        example = "mp"  # 默认运行公众号示例

    examples = {
        "mp": example_wechat_mp,
        "work": example_wechat_work,
        "combined": example_combined_channels,
        "upload": example_upload_media,
        "user": example_user_info
    }

    if example in examples:
        asyncio.run(examples[example]())
    else:
        print(f"未知示例: {example}")
        print(f"可用示例: {', '.join(examples.keys())}")
        print("\n使用方法:")
        print("  python wechat_integration.py mp        # 微信公众号")
        print("  python wechat_integration.py work      # 企业微信")
        print("  python wechat_integration.py combined  # 多通道集成")
        print("  python wechat_integration.py upload    # 上传媒体")
        print("  python wechat_integration.py user      # 获取用户信息")
