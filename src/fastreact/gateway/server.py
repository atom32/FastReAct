"""
WebSocket Gateway Server

提供实时双向通信接口，支持会话管理和进度追踪。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional, Callable
from datetime import datetime
import uuid
import json

from fastreact import FastReAct


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

    def __init__(self, agent: FastReAct):
        """
        初始化网关

        Args:
            agent: FastReAct 实例
        """
        self.agent = agent
        self.sessions: Dict[str, Dict] = {}
        self.app = app

        # 注册路由
        self._register_routes()

    def _register_routes(self):
        """注册路由"""

        @app.get("/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "active_sessions": len(self.sessions)
            }

        @app.get("/sessions")
        async def list_sessions():
            """列出所有会话"""
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
                "total": len(self.sessions)
            }

        @app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            """WebSocket 端点"""
            await websocket.accept()

            # 初始化或恢复会话
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "messages": [],
                    "context": {},
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "last_active": datetime.now().isoformat(),
                        "websocket": websocket
                    }
                }
                # 发送欢迎消息
                await websocket.send_json({
                    "type": "system",
                    "message": f"会话已创建: {session_id}",
                    "session_id": session_id
                })
            else:
                # 恢复现有会话
                session = self.sessions[session_id]
                session["metadata"]["websocket"] = websocket
                await websocket.send_json({
                    "type": "system",
                    "message": f"会话已恢复: {session_id}",
                    "session_id": session_id
                })

                # 发送历史消息（最近 20 条）
                recent_messages = session["messages"][-20:]
                for msg in recent_messages:
                    await websocket.send_json({
                        "type": "history",
                        "message": msg
                    })

            session = self.sessions[session_id]

            try:
                while True:
                    # 接收消息
                    data = await websocket.receive_json()

                    if "query" not in data:
                        await websocket.send_json({
                            "type": "error",
                            "error": "Missing 'query' field"
                        })
                        continue

                    query = data["query"]

                    # 记录用户消息
                    user_message = {
                        "role": "user",
                        "content": query,
                        "timestamp": datetime.now().isoformat()
                    }
                    session["messages"].append(user_message)
                    session["metadata"]["last_active"] = datetime.now().isoformat()

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

                        # 发送最终答案
                        await websocket.send_json({
                            "type": "answer",
                            "answer": result["answer"],
                            "stats": result.get("stats", {}),
                            "iteration": result.get("iteration", 0)
                        })

                    except Exception as e:
                        # 执行出错
                        await websocket.send_json({
                            "type": "error",
                            "error": str(e),
                            "details": type(e).__name__
                        })

                        # 记录错误消息
                        session["messages"].append({
                            "role": "system",
                            "content": f"错误: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        })

            except WebSocketDisconnect:
                print(f"Session {session_id} disconnected")
                # 清理 websocket 引用
                if session_id in self.sessions:
                    self.sessions[session_id]["metadata"].pop("websocket", None)

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
