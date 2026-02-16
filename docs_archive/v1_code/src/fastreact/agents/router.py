"""
智能体路由器 - 根据任务类型自动路由到合适的智能体
"""

import re
import logging
from typing import Dict, List, Optional, Any
from .base import Agent

logger = logging.getLogger(__name__)


class AgentRouter:
    """智能体路由器

    根据任务类型、会话绑定或用户选择，将任务路由到合适的智能体。
    """

    def __init__(self):
        """初始化路由器"""
        self.agents: Dict[str, Agent] = {}
        self.session_agent_map: Dict[str, str] = {}  # session_id -> agent_name
        self.default_agent = None

        # 关键词映射
        self.keyword_patterns = {
            "coder": [
                "代码", "编程", "程序", "函数", "api", "debug",
                "bug", "错误", "调试", "开发", "算法", "数据结构",
                "code", "programming", "function", "debug", "error"
            ],
            "researcher": [
                "搜索", "研究", "分析", "数据", "报告", "统计",
                "信息", "查找", "调查", "总结", "overview",
                "search", "research", "analyze", "data", "report"
            ],
            "creator": [
                "写", "创作", "文案", "内容", "文章", "设计",
                "创意", "广告", "营销", "品牌", "叙述",
                "write", "create", "content", "design", "creative"
            ]
        }

    def register_agent(self, agent: Agent) -> None:
        """
        注册智能体

        Args:
            agent: 智能体实例
        """
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.role})")

        # 设置默认智能体
        if agent.name == "general":
            self.default_agent = agent
        elif self.default_agent is None:
            self.default_agent = agent

    def route(
        self,
        task: str,
        session_id: Optional[str] = None,
        force_agent: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> Agent:
        """
        路由到合适的智能体

        Args:
            task: 任务描述
            session_id: 会话 ID（用于会话绑定）
            force_agent: 强制指定的智能体名称
            context: 额外上下文

        Returns:
            选定的智能体
        """
        # 1. 强制指定智能体
        if force_agent:
            if force_agent in self.agents:
                logger.debug(f"Using forced agent: {force_agent}")
                return self.agents[force_agent]
            else:
                logger.warning(f"Forced agent '{force_agent}' not found, using default")

        # 2. 使用会话绑定的智能体
        if session_id and session_id in self.session_agent_map:
            agent_name = self.session_agent_map[session_id]
            if agent_name in self.agents:
                logger.debug(f"Using session-bound agent: {agent_name} for session {session_id}")
                return self.agents[agent_name]

        # 3. 基于任务类型自动路由
        agent_name = self._classify_task(task)
        if agent_name and agent_name in self.agents:
            logger.info(f"Routed task to {agent_name}: {task[:50]}...")
            return self.agents[agent_name]

        # 4. 使用默认智能体
        logger.debug(f"Using default agent for task: {task[:50]}...")
        return self.default_agent

    def _classify_task(self, task: str) -> Optional[str]:
        """
        分类任务到合适的智能体

        Args:
            task: 任务描述

        Returns:
            智能体名称，如果无法分类则返回 None
        """
        task_lower = task.lower()

        # 计算每个智能体的匹配分数
        scores = {}
        for agent_name, keywords in self.keyword_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in task_lower:
                    score += 1
            if score > 0:
                scores[agent_name] = score

        # 返回分数最高的智能体
        if scores:
            best_agent = max(scores.items(), key=lambda x: x[1])[0]
            logger.debug(f"Task classification scores: {scores} -> {best_agent}")
            return best_agent

        return None

    def bind_session_agent(
        self,
        session_id: str,
        agent_name: str
    ) -> bool:
        """
        绑定会话到特定智能体

        Args:
            session_id: 会话 ID
            agent_name: 智能体名称

        Returns:
            是否绑定成功
        """
        if agent_name not in self.agents:
            logger.warning(f"Cannot bind to unknown agent: {agent_name}")
            return False

        self.session_agent_map[session_id] = agent_name
        logger.info(f"Bound session {session_id} to agent {agent_name}")
        return True

    def unbind_session(self, session_id: str) -> bool:
        """
        解绑会话

        Args:
            session_id: 会话 ID

        Returns:
            是否解绑成功
        """
        if session_id in self.session_agent_map:
            del self.session_agent_map[session_id]
            logger.info(f"Unbound session {session_id}")
            return True
        return False

    def get_session_agent(self, session_id: str) -> Optional[str]:
        """
        获取会话绑定的智能体

        Args:
            session_id: 会话 ID

        Returns:
            智能体名称，如果未绑定则返回 None
        """
        return self.session_agent_map.get(session_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的智能体

        Returns:
            智能体信息列表
        """
        return [agent.get_info() for agent in self.agents.values()]

    def get_agent(self, name: str) -> Optional[Agent]:
        """
        获取指定智能体

        Args:
            name: 智能体名称

        Returns:
            智能体实例，如果不存在则返回 None
        """
        return self.agents.get(name)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取路由器统计信息

        Returns:
            统计信息
        """
        return {
            "total_agents": len(self.agents),
            "active_sessions": len(self.session_agent_map),
            "default_agent": self.default_agent.name if self.default_agent else None,
            "agents": list(self.agents.keys())
        }
