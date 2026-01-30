"""
FastReAct 存储层 - SQLite 实现

使用 SQLite 作为会话存储后端，适合单机部署和开发环境。
优点：零配置、单文件、跨平台、事务支持。
"""

import json
import aiosqlite
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path

from .base import SessionStorage


class SQLiteSessionStorage(SessionStorage):
    """SQLite 会话存储实现

    使用 SQLite 数据库存储会话数据。

    Args:
        db_path: 数据库文件路径（默认：./data/sessions.db）
    """

    def __init__(self, db_path: str = "./data/sessions.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """初始化数据库

        创建必要的表和索引。
        """
        # 确保数据目录存在
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # 启用外键约束
            await db.execute("PRAGMA foreign_keys = ON")

            # 创建会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建消息表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_last_active
                ON sessions(last_active DESC)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id, timestamp)
            """)

            await db.commit()

    async def save_session(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> None:
        """保存会话数据

        如果会话已存在则更新，否则创建新会话。

        Args:
            session_id: 会话 ID
            data: 会话数据
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 使用 UPSERT (INSERT ... ON CONFLICT) 来避免竞态条件
            # 这是原子操作，不会在并发环境下产生 UNIQUE 约束冲突
            await db.execute("""
                INSERT INTO sessions (session_id, user_id, title, metadata, updated_at, last_active)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    title = excluded.title,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP,
                    last_active = CURRENT_TIMESTAMP
            """, (
                session_id,
                data.get("user_id"),
                data.get("title", "新对话"),
                json.dumps(data.get("metadata", {}), ensure_ascii=False)
            ))

            # 如果有消息，保存消息
            messages = data.get("messages", [])
            if messages:
                # 先删除旧消息
                await db.execute(
                    "DELETE FROM messages WHERE session_id = ?",
                    (session_id,)
                )

                # 插入新消息
                for msg in messages:
                    await db.execute("""
                        INSERT INTO messages (session_id, role, content, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (
                        session_id,
                        msg.get("role", "user"),
                        msg.get("content", ""),
                        json.dumps(msg.get("metadata", {}), ensure_ascii=False)
                    ))

            await db.commit()

    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """加载会话数据

        Args:
            session_id: 会话 ID

        Returns:
            会话数据，如果不存在返回 None
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 加载会话基本信息
            async with db.execute("""
                SELECT session_id, user_id, title, metadata, created_at, updated_at, last_active
                FROM sessions
                WHERE session_id = ?
            """, (session_id,)) as cursor:
                session_row = await cursor.fetchone()

            if not session_row:
                return None

            # 加载消息
            messages = []
            async with db.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,)) as cursor:
                async for row in cursor:
                    messages.append({
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {}
                    })

            return {
                "session_id": session_row[0],
                "user_id": session_row[1],
                "title": session_row[2],
                "metadata": json.loads(session_row[3]) if session_row[3] else {},
                "created_at": session_row[4],
                "updated_at": session_row[5],
                "last_active": session_row[6],
                "messages": messages
            }

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出会话

        Args:
            user_id: 用户 ID（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            会话列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            if user_id:
                async with db.execute("""
                    SELECT session_id, user_id, title, created_at, last_active
                    FROM sessions
                    WHERE user_id = ?
                    ORDER BY last_active DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset)) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("""
                    SELECT session_id, user_id, title, created_at, last_active
                    FROM sessions
                    ORDER BY last_active DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset)) as cursor:
                    rows = await cursor.fetchall()

            return [
                {
                    "session_id": row[0],
                    "user_id": row[1],
                    "title": row[2],
                    "created_at": row[3],
                    "last_active": row[4]
                }
                for row in rows
            ]

    async def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """更新会话元数据

        Args:
            session_id: 会话 ID
            metadata: 新的元数据（会合并现有元数据）
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 获取现有元数据
            async with db.execute(
                "SELECT metadata FROM sessions WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                # 合并元数据
                existing = json.loads(row[0]) if row[0] else {}
                existing.update(metadata)

                # 更新
                await db.execute("""
                    UPDATE sessions
                    SET metadata = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (
                    json.dumps(existing, ensure_ascii=False),
                    session_id
                ))
                await db.commit()

    async def add_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> None:
        """添加单条消息到会话

        Args:
            session_id: 会话 ID
            message: 消息内容，包含：
                - role: 角色（user/assistant/system）
                - content: 内容
                - metadata: 元数据（可选）
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO messages (session_id, role, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                message.get("role", "user"),
                message.get("content", ""),
                json.dumps(message.get("metadata", {}), ensure_ascii=False)
            ))

            # 更新会话的最后活跃时间
            await db.execute("""
                UPDATE sessions
                SET last_active = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))

            await db.commit()

    async def get_session_stats(self) -> Dict[str, Any]:
        """获取存储统计信息

        Returns:
            包含以下字段的字典：
                - total_sessions: 总会话数
                - total_messages: 总消息数
                - active_sessions: 活跃会话数（24小时内活跃）
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 总会话数
            async with db.execute(
                "SELECT COUNT(*) FROM sessions"
            ) as cursor:
                total_sessions = (await cursor.fetchone())[0]

            # 总消息数
            async with db.execute(
                "SELECT COUNT(*) FROM messages"
            ) as cursor:
                total_messages = (await cursor.fetchone())[0]

            # 活跃会话数（24小时内活跃）
            one_day_ago = datetime.now() - timedelta(days=1)
            async with db.execute("""
                SELECT COUNT(*) FROM sessions
                WHERE last_active > ?
            """, (one_day_ago,)) as cursor:
                active_sessions = (await cursor.fetchone())[0]

            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "active_sessions": active_sessions
            }

    async def cleanup_old_sessions(
        self,
        days: int = 30
    ) -> int:
        """清理旧会话

        Args:
            days: 保留天数，默认30天

        Returns:
            删除的会话数
        """
        cutoff = datetime.now() - timedelta(days=days)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM sessions
                WHERE last_active < ?
            """, (cutoff,))
            await db.commit()
            return cursor.rowcount
