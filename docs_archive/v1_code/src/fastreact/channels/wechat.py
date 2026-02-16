"""
微信通道

支持微信公众号集成。
"""

import os
import json
import hashlib
import time
import logging
from typing import Dict, Optional
import asyncio
from datetime import datetime, timedelta

from .base import Channel, ChannelConnectionError, ChannelMessageError

logger = logging.getLogger(__name__)


class WeChatChannel(Channel):
    """微信公众号通道

    支持微信公众号消息接收和客服消息发送。

    需要安装:
        pip install httpx

    使用前准备:
        1. 注册微信公众号（服务号）
        2. 获取 AppID 和 AppSecret
        3. 配置服务器地址（URL）
        4. 启用"服务器配置"

    Usage:
        from fastreact.channels.wechat import WeChatChannel

        channel = WeChatChannel(
            app_id="YOUR_APP_ID",
            app_secret="YOUR_APP_SECRET",
            token="YOUR_TOKEN",
            encoding_aes_key="YOUR_ENCODING_AES_KEY"  # 可选
        )
        await channel.start()
    """

    def __init__(
        self,
        app_id: str = None,
        app_secret: str = None,
        token: str = None,
        encoding_aes_key: str = None,
        gateway_url: str = "ws://localhost:8000",
        config: Dict = None
    ):
        """初始化微信通道

        Args:
            app_id: 微信公众号 AppID（默认从 WECHAT_APP_ID 环境变量读取）
            app_secret: 微信公众号 AppSecret（默认从 WECHAT_APP_SECRET 环境变量读取）
            token: 服务器配置 Token（默认从 WECHAT_TOKEN 环境变量读取）
            encoding_aes_key: 消息加密密钥（可选，默认从 WECHAT_ENCODING_AES_KEY 环境变量读取）
            gateway_url: Gateway WebSocket URL
            config: 额外配置
        """
        super().__init__(
            name="wechat",
            gateway_url=gateway_url,
            config=config
        )

        # 从环境变量或参数读取配置
        self.app_id = app_id or os.getenv("WECHAT_APP_ID")
        self.app_secret = app_secret or os.getenv("WECHAT_APP_SECRET")
        self.token = token or os.getenv("WECHAT_TOKEN")
        self.encoding_aes_key = encoding_aes_key or os.getenv("WECHAT_ENCODING_AES_KEY")

        # 验证必需参数
        if not self.app_id:
            raise ValueError("WECHAT_APP_ID is required")
        if not self.app_secret:
            raise ValueError("WECHAT_APP_SECRET is required")
        if not self.token:
            raise ValueError("WECHAT_TOKEN is required")

        # Access token 管理
        self.access_token = None
        self.token_expires_at = None

        # HTTP 客户端
        self.http_client = None

        # FastAPI app（用于接收微信推送）
        self.app = None
        self.server = None

    async def start(self):
        """启动微信通道"""
        try:
            # 动态导入 httpx
            import httpx

            # 创建 HTTP 客户端
            self.http_client = httpx.AsyncClient(timeout=30.0)

            # 获取 access_token
            await self._refresh_access_token()

            # 创建 FastAPI app（用于接收微信消息）
            self._create_fastapi_app()

            self.running = True
            logger.info("WeChat channel started successfully")

        except ImportError as e:
            raise ImportError(
                "httpx is required. "
                "Install it with: pip install httpx"
            ) from e
        except Exception as e:
            raise ChannelConnectionError(f"Failed to start WeChat channel: {e}") from e

    async def stop(self):
        """停止微信通道"""
        if self.server:
            try:
                # 停止 FastAPI 服务器
                import asyncio
                self.server.should_exit = True
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error stopping WeChat server: {e}")

        if self.http_client:
            try:
                await self.http_client.aclose()
            except Exception as e:
                logger.error(f"Error closing HTTP client: {e}")

        self.running = False
        logger.info("WeChat channel stopped")

    def _create_fastapi_app(self):
        """创建 FastAPI 应用（用于接收微信推送）"""
        try:
            from fastapi import FastAPI, Request, Response
            from fastapi.responses import PlainTextResponse

            app = FastAPI()

            @app.get("/wechat")
            async def wechat_verify(
                signature: str,
                timestamp: str,
                nonce: str,
                echostr: str
            ):
                """微信服务器验证

                首次配置服务器地址时，微信会发送 GET 请求进行验证。
                """
                # 验证签名
                if self._verify_signature(signature, timestamp, nonce):
                    logger.info("WeChat server verification passed")
                    return PlainTextResponse(echostr)
                else:
                    logger.warning("WeChat server verification failed")
                    return PlainTextResponse("Invalid signature", status_code=403)

            @app.post("/wechat")
            async def wechat_message(request: Request):
                """接收微信消息推送"""
                try:
                    body = await request.body()

                    # 解析 XML 消息
                    message = self._parse_xml_message(body)

                    if message:
                        # 转发到 Gateway
                        await self._forward_to_gateway(
                            user_id=message["FromUserName"],
                            message=message.get("Content", ""),
                            metadata=message
                        )

                    # 返回成功（防止微信重复推送）
                    return PlainTextResponse("success")

                except Exception as e:
                    logger.error(f"Error processing WeChat message: {e}")
                    return PlainTextResponse("success")  # 即使出错也返回 success

            self.app = app

        except ImportError:
            logger.warning(
                "FastAPI is not installed. WeChat webhook will not be available. "
                "Install it with: pip install fastapi uvicorn"
            )

    def _verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """验证微信签名

        Args:
            signature: 微信签名
            timestamp: 时间戳
            nonce: 随机数

        Returns:
            验证是否通过
        """
        # 按字典序排序
        tmp_list = [self.token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = "".join(tmp_list)

        # SHA1 加密
        tmp_str = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()

        # 对比签名
        return tmp_str == signature

    def _parse_xml_message(self, body: bytes) -> Optional[Dict]:
        """解析微信 XML 消息

        Args:
            body: 消息体（XML 格式）

        Returns:
            解析后的消息字典
        """
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(body)

            message = {}
            for child in root:
                message[child.tag] = child.text

            return message

        except Exception as e:
            logger.error(f"Error parsing WeChat XML message: {e}")
            return None

    async def _refresh_access_token(self):
        """刷新 access_token"""
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }

        response = await self.http_client.get(url, params=params)
        data = response.json()

        if "access_token" in data:
            self.access_token = data["access_token"]
            # 提前 5 分钟刷新
            self.token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)
            logger.info("WeChat access token refreshed successfully")
        else:
            raise ChannelConnectionError(f"Failed to get access token: {data}")

    async def _ensure_access_token(self):
        """确保 access_token 有效"""
        if not self.access_token or not self.token_expires_at or datetime.now() >= self.token_expires_at:
            await self._refresh_access_token()

    # ====== 公共接口 ======

    async def send_message(
        self,
        user_id: str,
        message: str,
        msg_type: str = "text",
        **kwargs
    ):
        """发送消息给用户

        Args:
            user_id: 微信 OpenID
            message: 消息内容
            msg_type: 消息类型 ("text", "image", "voice", "video", "news" 等)
            **kwargs: 额外参数
        """
        await self._ensure_access_token()

        if msg_type == "text":
            await self._send_text_message(user_id, message)
        elif msg_type == "image":
            await self._send_media_message(user_id, "image", message, **kwargs)
        elif msg_type == "voice":
            await self._send_media_message(user_id, "voice", message, **kwargs)
        elif msg_type == "video":
            await self._send_media_message(user_id, "video", message, **kwargs)
        elif msg_type == "news":
            await self._send_news_message(user_id, message, **kwargs)
        else:
            raise ChannelMessageError(f"Unsupported message type: {msg_type}")

    async def _send_text_message(self, user_id: str, message: str):
        """发送文本消息"""
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={self.access_token}"

        data = {
            "touser": user_id,
            "msgtype": "text",
            "text": {
                "content": message
            }
        }

        response = await self.http_client.post(url, json=data)
        result = response.json()

        if result.get("errcode") != 0:
            raise ChannelMessageError(f"Failed to send message: {result}")

        logger.debug(f"Sent text message to WeChat user {user_id}")

    async def _send_media_message(
        self,
        user_id: str,
        media_type: str,
        media_id: str,
        **kwargs
    ):
        """发送媒体消息

        Args:
            user_id: 用户 OpenID
            media_type: 媒体类型 ("image", "voice", "video" 等)
            media_id: 媒体 ID（需要先上传素材获取）
            **kwargs: 额外参数
        """
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={self.access_token}"

        data = {
            "touser": user_id,
            "msgtype": media_type,
            media_type: {
                "media_id": media_id
            }
        }

        # 添加视频缩略图（必需）
        if media_type == "video" and "thumb_media_id" in kwargs:
            data[media_type]["thumb_media_id"] = kwargs["thumb_media_id"]

        response = await self.http_client.post(url, json=data)
        result = response.json()

        if result.get("errcode") != 0:
            raise ChannelMessageError(f"Failed to send media message: {result}")

        logger.debug(f"Sent {media_type} message to WeChat user {user_id}")

    async def _send_news_message(self, user_id: str, articles: list, **kwargs):
        """发送图文消息

        Args:
            user_id: 用户 OpenID
            articles: 图文消息列表 [{"title": "", "description": "", "url": "", "picurl": ""}]
            **kwargs: 额外参数
        """
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={self.access_token}"

        data = {
            "touser": user_id,
            "msgtype": "news",
            "news": {
                "articles": articles
            }
        }

        response = await self.http_client.post(url, json=data)
        result = response.json()

        if result.get("errcode") != 0:
            raise ChannelMessageError(f"Failed to send news message: {result}")

        logger.debug(f"Sent news message to WeChat user {user_id}")

    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息

        Args:
            user_id: 微信 OpenID

        Returns:
            用户信息字典
        """
        await self._ensure_access_token()

        url = f"https://api.weixin.qq.com/cgi-bin/user/info"
        params = {
            "access_token": self.access_token,
            "openid": user_id,
            "lang": "zh_CN"
        }

        try:
            response = await self.http_client.get(url, params=params)
            data = response.json()

            if data.get("errcode") == 0:
                return {
                    "openid": data.get("openid"),
                    "nickname": data.get("nickname"),
                    "sex": data.get("sex"),
                    "province": data.get("province"),
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "headimgurl": data.get("headimgurl"),
                    "subscribe_time": data.get("subscribe_time"),
                    "subscribe": data.get("subscribe")
                }
            else:
                logger.error(f"Failed to get user info: {data}")
                return {}

        except Exception as e:
            logger.error(f"Error getting WeChat user info: {e}")
            return {}

    async def upload_media(self, media_type: str, file_path: str) -> str:
        """上传永久素材

        Args:
            media_type: 媒体类型 ("image", "voice", "video", "thumb")
            file_path: 文件路径

        Returns:
            media_id
        """
        await self._ensure_access_token()

        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={self.access_token}&type={media_type}"

        try:
            with open(file_path, "rb") as f:
                files = {"media": f}
                response = await self.http_client.post(url, files=files)
                data = response.json()

            if "media_id" in data:
                logger.info(f"Uploaded {media_type} material: {data['media_id']}")
                return data["media_id"]
            else:
                raise ChannelMessageError(f"Failed to upload media: {data}")

        except Exception as e:
            raise ChannelMessageError(f"Error uploading media: {e}") from e

    def get_stats(self) -> Dict:
        """获取通道统计信息"""
        base_stats = super().get_stats()
        return {
            **base_stats,
            "app_id": self.app_id,
            "access_token_valid": self.access_token is not None,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
        }

    # ====== 辅助方法 ======

    def get_asgi_app(self):
        """获取 ASGI 应用（用于与现有 FastAPI 应用集成）"""
        return self.app

    async def run_server(self, host: str = "0.0.0.0", port: int = 8001):
        """运行 FastAPI 服务器

        Args:
            host: 监听地址
            port: 监听端口
        """
        if not self.app:
            raise RuntimeError("FastAPI app not created. Import fastapi first.")

        import uvicorn

        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        self.server = uvicorn.Server(config)

        await self.server.serve()


class WeChatWorkChannel(WeChatChannel):
    """企业微信通道

    支持企业微信应用消息推送。

    企业微信文档: https://developer.work.weixin.qq.com/document/path/90665

    Usage:
        from fastreact.channels.wechat import WeChatWorkChannel

        channel = WeChatWorkChannel(
            corp_id="YOUR_CORP_ID",
            agent_id=1001,
            secret="YOUR_SECRET"
        )
        await channel.start()
    """

    def __init__(
        self,
        corp_id: str = None,
        agent_id: int = None,
        secret: str = None,
        gateway_url: str = "ws://localhost:8000",
        config: Dict = None
    ):
        """初始化企业微信通道

        Args:
            corp_id: 企业 ID
            agent_id: 应用 ID
            secret: 应用 Secret
            gateway_url: Gateway WebSocket URL
            config: 额外配置
        """
        # 调用父类 Channel 的 __init__，而不是 WeChatChannel 的
        Channel.__init__(
            self,
            name="wechat_work",
            gateway_url=gateway_url,
            config=config
        )

        # 企业微信特有的配置
        self.corp_id = corp_id or os.getenv("WECHAT_WORK_CORP_ID")
        self.agent_id = agent_id or os.getenv("WECHAT_WORK_AGENT_ID")
        self.app_secret = secret or os.getenv("WECHAT_WORK_SECRET")
        self.app_id = self.corp_id  # 为了兼容父类方法

        if not self.corp_id:
            raise ValueError("WECHAT_WORK_CORP_ID is required")
        if not self.app_secret:
            raise ValueError("WECHAT_WORK_SECRET is required")
        if not self.agent_id:
            raise ValueError("WECHAT_WORK_AGENT_ID is required")

        # Access token 管理
        self.access_token = None
        self.token_expires_at = None

        # HTTP 客户端
        self.http_client = None

        # FastAPI app（用于接收微信推送）
        self.app = None
        self.server = None

    async def _refresh_access_token(self):
        """刷新企业微信 access_token"""
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.app_secret  # 这里用 app_secret 存储企业应用的 secret
        }

        response = await self.http_client.get(url, params=params)
        data = response.json()

        if data.get("errcode") == 0 and "access_token" in data:
            self.access_token = data["access_token"]
            # 提前 5 分钟刷新
            self.token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)
            logger.info("WeChat Work access token refreshed successfully")
        else:
            raise ChannelConnectionError(f"Failed to get WeChat Work access token: {data}")

    async def send_message(
        self,
        user_id: str,
        message: str,
        msg_type: str = "text",
        **kwargs
    ):
        """发送企业微信应用消息

        Args:
            user_id: 企业成员 UserID
            message: 消息内容
            msg_type: 消息类型 ("text", "image", "voice", "video", "file", "textcard", "news", "mpnews" 等)
            **kwargs: 额外参数
        """
        await self._ensure_access_token()

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.access_token}"

        # 企业微信消息格式
        data = {
            "touser": user_id,
            "msgtype": msg_type,
            "agentid": self.agent_id,
        }

        if msg_type == "text":
            data["text"] = {"content": message}
        elif msg_type == "textcard":
            # 文本卡片消息
            data["textcard"] = {
                "title": kwargs.get("title", "消息通知"),
                "description": message,
                "url": kwargs.get("url", ""),
                "btntxt": kwargs.get("btntxt", "详情")
            }
        elif msg_type == "news":
            # 图文消息
            data["news"] = {
                "articles": kwargs.get("articles", [])
            }
        # 其他消息类型...

        response = await self.http_client.post(url, json=data)
        result = response.json()

        if result.get("errcode") != 0:
            raise ChannelMessageError(f"Failed to send WeChat Work message: {result}")

        logger.debug(f"Sent message to WeChat Work user {user_id}")
