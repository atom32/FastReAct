"""
Gateway 认证系统

支持多种认证方式：
- Static Token（静态令牌）
- Password（密码认证）
- JWT（JSON Web Token）
- API Key（API密钥）
"""

import os
import secrets
import jwt
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import WebSocket, status, HTTPException
import logging

logger = logging.getLogger(__name__)


class GatewayAuth:
    """Gateway 认证系统

    支持多种认证方式：
    1. Static Token - 静态令牌（最简单）
    2. Password - 密码认证（开发环境）
    3. JWT - JSON Web Token（生产推荐）
    4. API Key - API密钥（自动化集成）

    Usage:
        # 创建认证实例
        auth = GatewayAuth(
            token="static-token-here",
            password="password123",
            jwt_secret="your-secret-key"
        )

        # 验证 WebSocket 连接
        authenticated, user_id = auth.authenticate_websocket(
            websocket, token="xxx"
        )

        # 生成 JWT token
        token = auth.generate_token("user123", expires_in=3600)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        password: Optional[str] = None,
        jwt_secret: Optional[str] = None,
        enable_jwt: bool = True,
        api_keys: Optional[Dict[str, Dict]] = None
    ):
        """初始化认证系统

        Args:
            token: 静态令牌（默认从 GATEWAY_TOKEN 环境变量读取）
            password: 密码（默认从 GATEWAY_PASSWORD 环境变量读取）
            jwt_secret: JWT 密钥（默认从 JWT_SECRET 环境变量读取）
            enable_jwt: 是否启用 JWT 认证（默认 True）
            api_keys: API 密钥字典 {key: {"user_id": "...", "name": "..."}}
        """
        self.static_token = token or os.getenv("GATEWAY_TOKEN")
        self.password = password or os.getenv("GATEWAY_PASSWORD")
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET", secrets.token_hex(32))
        self.enable_jwt = enable_jwt
        self.api_keys = api_keys or {}

        # 会话存储 {session_id: {user_id, created_at, metadata}}
        self.active_sessions: Dict[str, Dict] = {}

        # 检查是否配置了任何认证方式（只有启用 JWT 不算配置，需要实际的 token/password/key）
        self.has_auth = bool(self.static_token or self.password or self.api_keys)

        if not self.has_auth:
            logger.warning("No authentication configured. Gateway will be open for development.")

    def generate_token(
        self,
        user_id: str,
        expires_in: int = 3600,
        metadata: Dict = None
    ) -> str:
        """生成 JWT token

        Args:
            user_id: 用户ID
            expires_in: 过期时间（秒），默认 1 小时
            metadata: 额外的元数据

        Returns:
            JWT token 字符串
        """
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
            "metadata": metadata or {}
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[Dict]:
        """验证 JWT token

        Args:
            token: JWT token 字符串

        Returns:
            解码后的 payload，验证失败返回 None
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def authenticate_websocket(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[Dict]]:
        """认证 WebSocket 连接

        优先级：
        1. Static Token
        2. Password
        3. JWT Token
        4. API Key

        Args:
            websocket: WebSocket 连接对象
            token: 认证令牌（可以是 static token 或 JWT）
            password: 密码
            api_key: API 密钥

        Returns:
            (是否认证成功, 用户ID/标识符, 元数据)
        """
        # 开发模式：无认证
        if not self.has_auth:
            return True, "anonymous", {"mode": "development"}

        # 检查静态 token
        if self.static_token and token == self.static_token:
            return True, "static_token", {"mode": "static_token"}

        # 检查密码
        if self.password and password == self.password:
            return True, "password", {"mode": "password"}

        # 检查 JWT token
        if self.enable_jwt and token:
            payload = self.verify_token(token)
            if payload:
                user_id = payload.get("user_id")
                metadata = payload.get("metadata", {})
                return True, user_id, {
                    "mode": "jwt",
                    **metadata
                }

        # 检查 API key
        if api_key and api_key in self.api_keys:
            key_info = self.api_keys[api_key]
            return True, key_info["user_id"], {
                "mode": "api_key",
                "name": key_info.get("name", "unknown")
            }

        # 所有认证方式都失败
        return False, None, None

    async def close_unauthorized(
        self,
        websocket: WebSocket,
        reason: str = "Unauthorized: Invalid or missing credentials"
    ):
        """关闭未授权的 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            reason: 关闭原因
        """
        try:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Error closing unauthorized connection: {e}")

    def create_session(
        self,
        user_id: str,
        metadata: Dict = None
    ) -> str:
        """创建会话

        Args:
            user_id: 用户ID
            metadata: 会话元数据

        Returns:
            会话ID
        """
        session_id = secrets.token_urlsafe(16)
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """验证会话

        Args:
            session_id: 会话ID

        Returns:
            会话是否有效
        """
        return session_id in self.active_sessions

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息，不存在返回 None
        """
        return self.active_sessions.get(session_id)

    def revoke_session(self, session_id: str) -> bool:
        """撤销会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功撤销
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            del self.active_sessions[session_id]
            logger.info(f"Revoked session {session_id} for user {session['user_id']}")
            return True
        return False

    def list_sessions(self, user_id: str = None) -> List[Dict]:
        """列出会话

        Args:
            user_id: 用户ID（可选，过滤特定用户的会话）

        Returns:
            会话列表
        """
        sessions = []
        for session_id, session_data in self.active_sessions.items():
            if user_id is None or session_data["user_id"] == user_id:
                sessions.append({
                    "session_id": session_id,
                    **session_data
                })
        return sessions

    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """清理过期会话

        Args:
            max_age_hours: 最大会话时长（小时）

        Returns:
            清理的会话数量
        """
        now = datetime.utcnow()
        expired_sessions = []

        for session_id, session_data in self.active_sessions.items():
            age = (now - session_data["created_at"]).total_seconds()
            if age > max_age_hours * 3600:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.revoke_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    def add_api_key(self, key: str, user_id: str, name: str = None):
        """添加 API 密钥

        Args:
            key: API 密钥
            user_id: 用户ID
            name: 密钥名称（可选）
        """
        self.api_keys[key] = {
            "user_id": user_id,
            "name": name or f"key-{user_id}",
            "created_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Added API key for user {user_id}")

    def remove_api_key(self, key: str) -> bool:
        """移除 API 密钥

        Args:
            key: API 密钥

        Returns:
            是否成功移除
        """
        if key in self.api_keys:
            del self.api_keys[key]
            logger.info(f"Removed API key")
            return True
        return False

    def get_stats(self) -> Dict:
        """获取认证统计信息

        Returns:
            统计信息字典
        """
        return {
            "has_auth": self.has_auth,
            "auth_methods": {
                "static_token": bool(self.static_token),
                "password": bool(self.password),
                "jwt": self.enable_jwt,
                "api_keys": len(self.api_keys) > 0
            },
            "active_sessions": len(self.active_sessions),
            "api_keys_count": len(self.api_keys)
        }


# HTTP 认证中间件（用于 FastAPI）

async def require_auth(
    auth: GatewayAuth,
    token: str = None,
    password: str = None,
    api_key: str = None
) -> Dict:
    """HTTP 认证依赖注入

    Usage:
        @app.get("/api/endpoint")
        async def endpoint(auth_data: Dict = Depends(require_auth)):
            user_id = auth_data["user_id"]
            ...

    Args:
        auth: GatewayAuth 实例
        token: 认证令牌
        password: 密码
        api_key: API 密钥

    Returns:
        认证信息字典

    Raises:
        HTTPException: 认证失败
    """
    # 使用 dummy WebSocket 对象进行认证
    class DummyWebSocket:
        async def close(self, code, reason):
            pass

    dummy_ws = DummyWebSocket()
    authenticated, user_id, metadata = auth.authenticate_websocket(
        dummy_ws, token=token, password=password, api_key=api_key
    )

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing credentials"
        )

    return {
        "user_id": user_id,
        "metadata": metadata
    }
