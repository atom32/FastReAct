"""
WebSocket Gateway Server

提供实时双向通信接口，支持会话管理和进度追踪。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional, Callable
from datetime import datetime
import uuid
import json
import logging

from fastreact import FastReAct
from ..storage import SessionStorage, SQLiteSessionStorage
from .auth import GatewayAuth
from .protocol import ProtocolValidator, MessageBuilder, ErrorCode
from .dedup import DedupCache

logger = logging.getLogger(__name__)


app = FastAPI(
    title="FastReAct Gateway",
    description="WebSocket Gateway for FastReAct Agent",
    version="0.1.0"
)

# CORS 配置（允许所有来源，生产环境应限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GatewayServer:
    """WebSocket 网关服务器"""

    def __init__(
        self,
        agent: FastReAct,
        storage: Optional[SessionStorage] = None,
        storage_path: str = "./data/sessions.db",
        auto_save: bool = True,
        auth: Optional[GatewayAuth] = None,
        enable_protocol_validation: bool = True,
        dedup_ttl: int = 300
    ):
        """
        初始化网关

        Args:
            agent: FastReAct 实例
            storage: 会话存储后端（默认使用 SQLite）
            storage_path: SQLite 数据库文件路径
            auto_save: 是否自动保存会话（默认 True）
            auth: 认证系统实例（默认 None，开发模式）
            enable_protocol_validation: 是否启用协议验证（默认 True）
            dedup_ttl: 去重缓存TTL（秒，默认 5 分钟）
        """
        self.agent = agent
        self.storage = storage or SQLiteSessionStorage(storage_path)
        self.auto_save = auto_save
        self.sessions: Dict[str, Dict] = {}  # 内存缓存
        self.app = app
        self._initialized = False

        # 认证系统
        self.auth = auth or GatewayAuth()

        # 协议验证器
        self.validator = ProtocolValidator() if enable_protocol_validation else None
        self.builder = MessageBuilder()

        # 去重缓存
        self.dedup = DedupCache(ttl=dedup_ttl)

        # 事件序列号
        self._event_seq = 0
        self._state_version = 0

        # 注册路由
        self._register_routes()

    async def startup(self):
        """启动网关，初始化存储"""
        if not self._initialized:
            try:
                await self.storage.initialize()
                self._initialized = True
                logger.info(f"Gateway storage initialized: {self.storage.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to initialize storage: {e}")
                raise

    def _register_routes(self):
        """注册路由"""

        @app.get("/health")
        async def health_check():
            """健康检查"""
            storage_healthy = self._initialized and await self.storage.health_check()
            auth_stats = self.auth.get_stats()

            return {
                "status": "healthy" if storage_healthy else "degraded",
                "timestamp": datetime.now().isoformat(),
                "active_sessions": len(self.sessions),
                "storage": {
                    "type": self.storage.__class__.__name__,
                    "healthy": storage_healthy
                },
                "auth": auth_stats,
                "dedup": self.dedup.get_stats()
            }

        @app.get("/sessions")
        async def list_sessions(limit: int = 50, offset: int = 0):
            """列出所有会话"""
            # 从存储获取所有会话
            try:
                stored_sessions = await self.storage.list_sessions(limit=limit, offset=offset)
                return {
                    "sessions": stored_sessions,
                    "total": len(stored_sessions),
                    "active_in_memory": len(self.sessions)
                }
            except Exception as e:
                logger.error(f"Failed to list sessions: {e}")
                # 降级到内存中的会话
                return {
                    "sessions": [
                        {
                            "session_id": session_id,
                            "message_count": len(session["messages"]),
                            "created_at": session["metadata"].get("created_at"),
                            "last_active": session["metadata"].get("last_active")
                        }
                        for session_id, session in self.sessions.items()
                    ],
                    "total": len(self.sessions),
                    "note": "Showing in-memory sessions only"
                }

        @app.websocket("/ws/{session_id}")
        async def websocket_endpoint(
            websocket: WebSocket,
            session_id: str,
            token: Optional[str] = Query(None),
            password: Optional[str] = Query(None),
            api_key: Optional[str] = Query(None)
        ):
            """WebSocket 端点

            Args:
                websocket: WebSocket 连接
                session_id: 会话ID
                token: 认证令牌（Query 参数）
                password: 密码（Query 参数）
                api_key: API 密钥（Query 参数）
            """
            # 认证检查
            authenticated, user_id, auth_metadata = self.auth.authenticate_websocket(
                websocket,
                token=token,
                password=password,
                api_key=api_key
            )

            if not authenticated:
                logger.warning(f"Failed authentication attempt for session {session_id}")
                await self.auth.close_unauthorized(websocket)
                return

            # 认证成功，记录日志
            logger.info(f"Session {session_id} authenticated: user={user_id}, mode={auth_metadata.get('mode')}")

            # 接受连接
            await websocket.accept()

            # 发送认证成功事件
            self._event_seq += 1
            self._state_version += 1
            auth_event = self.builder.create_event(
                event_type="presence",
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "authenticated": True,
                    "auth_mode": auth_metadata.get("mode")
                },
                seq=self._event_seq,
                state_version=self._state_version
            )
            await websocket.send_json(auth_event)

            # 尝试从存储加载会话
            stored_session = None
            if self._initialized:
                try:
                    stored_session = await self.storage.load_session(session_id)
                    logger.info(f"Loaded session {session_id} from storage")
                except Exception as e:
                    logger.warning(f"Failed to load session {session_id} from storage: {e}")

            # 初始化或恢复会话
            if stored_session:
                # 从存储恢复的会话
                self.sessions[session_id] = {
                    "messages": stored_session.get("messages", []),
                    "context": {},
                    "metadata": {
                        "created_at": stored_session.get("created_at"),
                        "last_active": stored_session.get("last_active"),
                        "title": stored_session.get("title", "恢复的会话"),
                        "websocket": websocket
                    }
                }
                session = self.sessions[session_id]

                # 发送恢复消息
                await websocket.send_json({
                    "type": "system",
                    "message": f"会话已恢复: {session_id}",
                    "session_id": session_id,
                    "messages_count": len(session["messages"])
                })

                # 发送历史消息（最近 20 条）
                recent_messages = session["messages"][-20:]
                for msg in recent_messages:
                    await websocket.send_json({
                        "type": "history",
                        "message": msg
                    })
            elif session_id not in self.sessions:
                # 新会话
                self.sessions[session_id] = {
                    "messages": [],
                    "context": {},
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "last_active": datetime.now().isoformat(),
                        "title": "新对话",
                        "websocket": websocket
                    }
                }
                session = self.sessions[session_id]

                # 发送欢迎消息
                await websocket.send_json({
                    "type": "system",
                    "message": f"会话已创建: {session_id}",
                    "session_id": session_id
                })
            else:
                # 内存中的会话
                session = self.sessions[session_id]
                session["metadata"]["websocket"] = websocket
                await websocket.send_json({
                    "type": "system",
                    "message": f"会话已恢复: {session_id}",
                    "session_id": session_id
                })

            session = self.sessions[session_id]

            try:
                while True:
                    # 接收消息
                    data = await websocket.receive_json()

                    # 初始化变量
                    request_id = None
                    idempotency_key = None

                    # 协议验证（如果启用）
                    if self.validator:
                        try:
                            # 尝试验证为请求消息
                            if data.get("type") == "req":
                                validated_msg = self.validator.validate_request(data)

                                # 检查幂等性
                                if "idempotency_key" in validated_msg.dict():
                                    idempotency_key = validated_msg.idempotency_key
                                    is_dup, cached_response = await self.dedup.check_and_store(
                                        idempotency_key
                                    )

                                    if is_dup and cached_response:
                                        # 返回缓存响应
                                        await websocket.send_json(cached_response)
                                        logger.info(f"Returned cached response for idempotency key: {idempotency_key}")
                                        continue

                                # 提取查询参数
                                query = validated_msg.params.get("query") or validated_msg.params.get("task")
                                request_id = validated_msg.id
                                idempotency_key = validated_msg.idempotency_key

                            else:
                                # 旧格式兼容（直接 query）
                                if "query" not in data:
                                    error_response = self.builder.create_error_response(
                                        request_id=data.get("id", "unknown"),
                                        error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                                        error_message="Missing 'query' field or invalid message format"
                                    )
                                    await websocket.send_json(error_response)
                                    continue

                                query = data["query"]
                                request_id = data.get("id", str(uuid.uuid4()))
                                idempotency_key = data.get("idempotency_key")

                        except ValueError as e:
                            # 验证失败
                            error_response = self.builder.create_error_response(
                                request_id=data.get("id", "unknown"),
                                error_code=ErrorCode.VALIDATION_ERROR,
                                error_message=str(e)
                            )
                            await websocket.send_json(error_response)
                            logger.warning(f"Message validation failed: {e}")
                            continue
                    else:
                        # 验证禁用，使用旧格式
                        if "query" not in data:
                            await websocket.send_json({
                                "type": "error",
                                "error": "Missing 'query' field"
                            })
                            continue

                        query = data["query"]
                        request_id = str(uuid.uuid4())
                        idempotency_key = data.get("idempotency_key")

                    # 记录用户消息
                    user_message = {
                        "role": "user",
                        "content": query,
                        "timestamp": datetime.now().isoformat()
                    }
                    session["messages"].append(user_message)
                    session["metadata"]["last_active"] = datetime.now().isoformat()

                    # 自动保存到存储
                    if self.auto_save and self._initialized:
                        try:
                            await self.storage.add_message(session_id, user_message)
                        except Exception as e:
                            logger.warning(f"Failed to save user message: {e}")

                    # 发送"思考中"状态
                    await websocket.send_json({
                        "type": "status",
                        "status": "thinking",
                        "message": "正在思考..."
                    })

                    # 定义步骤回调
                    async def step_callback(step):
                        """实时发送执行步骤"""
                        try:
                            # 发送思考过程
                            if hasattr(step, 'thought') and step.thought:
                                await websocket.send_json({
                                    "type": "thought",
                                    "iteration": getattr(step, 'iteration', 0),
                                    "content": step.thought
                                })

                            # 发送工具调用
                            if hasattr(step, 'tool_calls') and step.tool_calls:
                                await websocket.send_json({
                                    "type": "action",
                                    "iteration": getattr(step, 'iteration', 0),
                                    "tool_calls": [
                                        {
                                            "name": tc.name,
                                            "parameters": tc.parameters
                                        }
                                        for tc in step.tool_calls
                                    ]
                                })

                            # 发送观察结果
                            if hasattr(step, 'observation') and step.observation:
                                await websocket.send_json({
                                    "type": "observation",
                                    "iteration": getattr(step, 'iteration', 0),
                                    "content": str(step.observation)[:500]  # 限制长度
                                })
                        except Exception as e:
                            # 回调失败不影响主流程
                            print(f"Step callback error: {e}")

                    # 执行查询（带会话上下文和步骤回调）
                    try:
                        result = await self.agent.run_async(
                            query=query,
                            session_context=session.get("context", {}),
                            step_callback=step_callback
                        )

                        # 保存助手回复
                        assistant_message = {
                            "role": "assistant",
                            "content": result["answer"],
                            "timestamp": datetime.now().isoformat(),
                            "stats": result.get("stats", {})
                        }
                        session["messages"].append(assistant_message)

                        # 自动保存到存储
                        if self.auto_save and self._initialized:
                            try:
                                await self.storage.add_message(session_id, assistant_message)
                            except Exception as e:
                                logger.warning(f"Failed to save assistant message: {e}")

                        # 发送最终答案
                        response = self.builder.create_success_response(
                            request_id=request_id,
                            payload={
                                "type": "answer",
                                "answer": result["answer"],
                                "stats": result.get("stats", {}),
                                "iteration": result.get("iteration", 0)
                            }
                        )

                        # 如果有幂等性密钥，缓存响应
                        if idempotency_key:
                            await self.dedup.set(idempotency_key, response)

                        await websocket.send_json(response)

                    except Exception as e:
                        # 执行出错
                        error_response = self.builder.create_error_response(
                            request_id=request_id,
                            error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                            error_message=str(e),
                            details={"exception_type": type(e).__name__}
                        )

                        # 如果有幂等性密钥，缓存错误响应
                        if idempotency_key:
                            await self.dedup.set(idempotency_key, error_response)

                        await websocket.send_json(error_response)

                        # 记录错误消息
                        session["messages"].append({
                            "role": "system",
                            "content": f"错误: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        })

            except WebSocketDisconnect:
                logger.info(f"Session {session_id} disconnected")
                # 清理 websocket 引用并保存会话
                if session_id in self.sessions:
                    self.sessions[session_id]["metadata"].pop("websocket", None)

                    # 保存会话到存储
                    if self.auto_save and self._initialized:
                        try:
                            session = self.sessions[session_id]
                            await self.storage.save_session(session_id, {
                                "title": session["metadata"].get("title", "对话"),
                                "messages": session["messages"],
                                "metadata": {
                                    "created_at": session["metadata"].get("created_at"),
                                    "last_active": session["metadata"].get("last_active")
                                }
                            })
                            logger.info(f"Saved session {session_id} to storage")
                        except Exception as e:
                            logger.warning(f"Failed to save session on disconnect: {e}")

            except Exception as e:
                print(f"Session {session_id} error: {e}")
                await websocket.close()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        return self.sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_messages = sum(
            len(session["messages"])
            for session in self.sessions.values()
        )

        return {
            "active_sessions": len(self.sessions),
            "total_messages": total_messages,
            "sessions": [
                {
                    "session_id": session_id,
                    "message_count": len(session["messages"]),
                    "created_at": session["metadata"].get("created_at"),
                    "last_active": session["metadata"].get("last_active")
                }
                for session_id, session in self.sessions.items()
            ]
        }
