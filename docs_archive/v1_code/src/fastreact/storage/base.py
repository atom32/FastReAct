"""
FastReAct 存储层 - 抽象基类

支持多种存储后端：SQLite, PostgreSQL, Redis 等
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime


class SessionStorage(ABC):
    """会话存储抽象基类

    定义了会话存储的统一接口，支持多种存储后端。
    """

    @abstractmethod
    async def initialize(self) -> None:
        """初始化存储后端

        创建必要的表、索引等结构。
        """
        pass

    @abstractmethod
    async def save_session(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> None:
        """保存会话数据

        Args:
            session_id: 会话 ID
            data: 会话数据，包含以下字段：
                - user_id: 用户 ID（可选）
                - title: 会话标题
                - messages: 消息列表
                - metadata: 元数据（可选）
        """
        pass

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """加载会话数据

        Args:
            session_id: 会话 ID

        Returns:
            会话数据，如果不存在返回 None
        """
        pass

    @abstractmethod
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出会话

        Args:
            user_id: 用户 ID（可选，如果指定则只返回该用户的会话）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            会话列表，按最后活跃时间降序排列
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """更新会话元数据

        Args:
            session_id: 会话 ID
            metadata: 新的元数据
        """
        pass

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> None:
        """添加单条消息到会话

        Args:
            session_id: 会话 ID
            message: 消息内容
        """
        pass

    @abstractmethod
    async def get_session_stats(self) -> Dict[str, Any]:
        """获取存储统计信息

        Returns:
            包含以下字段的字典：
                - total_sessions: 总会话数
                - total_messages: 总消息数
                - active_sessions: 活跃会话数（24小时内活跃）
        """
        pass

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            存储后端是否正常工作
        """
        try:
            await self.get_session_stats()
            return True
        except Exception:
            return False
