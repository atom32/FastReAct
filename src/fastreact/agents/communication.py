"""
Agent-to-Agent 通信工具

允许智能体之间相互通信和协作。
"""

import json
import logging
from typing import Dict, Any, List
from ..core.tool import Tool

logger = logging.getLogger(__name__)


class SessionsListTool(Tool):
    """列出活跃的智能体"""

    def __init__(self, router):
        """
        初始化工具

        Args:
            router: AgentRouter 实例
        """
        self.router = router
        super().__init__()

    def _get_description(self):
        return "列出所有可用的智能体及其能力"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }

    async def execute_async(self) -> str:
        """执行工具"""
        agents = self.router.list_agents()

        result = {
            "agents": agents,
            "count": len(agents),
            "default": self.router.default_agent.name if self.router.default_agent else None
        }

        return json.dumps(result, ensure_ascii=False, indent=2)


class SessionsSendTool(Tool):
    """向其他智能体发送消息并获取回复"""

    def __init__(self, router, gateway):
        """
        初始化工具

        Args:
            router: AgentRouter 实例
            gateway: GatewayServer 实例（用于获取智能体）
        """
        self.router = router
        self.gateway = gateway
        super().__init__()

    def _get_description(self):
        return "向另一个智能体发送消息并获取回复。可以用于智能体协作和任务委托。"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "目标智能体名称（如: researcher, coder, creator, general）",
                    "enum": ["researcher", "coder", "creator", "manager", "general"]
                },
                "message": {
                    "type": "string",
                    "description": "要发送的消息内容"
                },
                "context": {
                    "type": "object",
                    "description": "额外的上下文信息（可选）",
                    "additionalProperties": True
                },
                "reply_back": {
                    "type": "boolean",
                    "description": "是否需要将回复返回给用户",
                    "default": True
                }
            },
            "required": ["agent", "message"]
        }

    async def execute_async(
        self,
        agent: str,
        message: str,
        context: Dict[str, Any] = None,
        reply_back: bool = True
    ) -> str:
        """执行工具"""
        # 获取目标智能体
        target_agent = self.router.get_agent(agent)
        if not target_agent:
            return json.dumps({
                "error": f"找不到智能体 '{agent}'",
                "available_agents": list(self.router.agents.keys())
            }, ensure_ascii=False, indent=2)

        logger.info(f"Message from Gateway to {agent}: {message[:50]}...")

        # 执行智能体任务
        try:
            result = await target_agent.execute(
                task=message,
                context=context or {}
            )

            if result.get("success"):
                response = {
                    "from_agent": agent,
                    "response": result.get("result", ""),
                    "stats": result.get("stats", {}),
                    "success": True
                }
            else:
                response = {
                    "from_agent": agent,
                    "error": result.get("error", "Unknown error"),
                    "success": False
                }

            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Agent {agent} execution failed: {e}")
            return json.dumps({
                "from_agent": agent,
                "error": str(e),
                "success": False
            }, ensure_ascii=False, indent=2)


class SessionsHistoryTool(Tool):
    """获取会话历史"""

    def __init__(self, router):
        """
        初始化工具

        Args:
            router: AgentRouter 实例
        """
        self.router = router
        super().__init__()

    def _get_description(self):
        return "获取指定智能体或会话的历史记录"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "agent": {
                    "type": "string",
                    "description": "智能体名称（可选）"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回消息数量限制",
                    "default": 10
                }
            },
            "required": ["session_id"]
        }

    async def execute_async(
        self,
        session_id: str,
        agent: str = None,
        limit: int = 10
    ) -> str:
        """执行工具"""
        # 如果提供了智能体，查询该智能体的执行历史
        if agent:
            target_agent = self.router.get_agent(agent)
            if target_agent and hasattr(target_agent, "fastreact"):
                # 这里可以扩展为查询 FastReAct 的执行历史
                pass

        # 从 Gateway 存储获取会话历史
        if hasattr(self.router, 'gateway') and self.router.gateway:
            try:
                session = await self.router.gateway.storage.load_session(session_id)
                if session:
                    messages = session.get("messages", [])[-limit:]
                    return json.dumps({
                        "session_id": session_id,
                        "messages": messages,
                        "count": len(messages),
                        "total": len(session.get("messages", []))
                    }, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to load session history: {e}")

        return json.dumps({
            "error": f"找不到会话 '{session_id}' 或无法加载历史"
        }, ensure_ascii=False)


class ConsultAgentTool(Tool):
    """咨询其他智能体"""

    def __init__(self, router):
        """
        初始化工具

        Args:
            router: AgentRouter 实例
        """
        self.router = router
        super().__init__()

    def _get_description(self):
        return "咨询另一个智能体的意见。当你遇到不确定的问题，或需要其他专家的意见时使用。"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "要咨询的智能体名称",
                    "enum": ["researcher", "coder", "creator", "general"]
                },
                "question": {
                    "type": "string",
                    "description": "要咨询的问题"
                },
                "context": {
                    "type": "string",
                    "description": "背景信息（可选）"
                }
            },
            "required": ["agent", "question"]
        }

    async def execute_async(
        self,
        agent: str,
        question: str,
        context: str = ""
    ) -> str:
        """执行工具"""
        target_agent = self.router.get_agent(agent)
        if not target_agent:
            return f"错误：找不到智能体 '{agent}'"

        # 构建完整的查询
        full_query = f"背景：{context}\n\n问题：{question}" if context else question

        try:
            result = await target_agent.execute(
                task=full_query,
                context={}
            )

            if result.get("success"):
                return f"[{agent} 的建议]：\n\n{result.get('result', '')}"
            else:
                return f"[{agent} 回复失败]：{result.get('error', 'Unknown error')}"

        except Exception as e:
            return f"[{agent} 回复异常]：{str(e)}"
