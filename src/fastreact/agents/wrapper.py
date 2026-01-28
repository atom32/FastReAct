"""
FastReAct 智能体包装类

将 FastReAct 引擎包装为智能体接口。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import Agent
from .. import FastReAct
from ..core.tool import Tool

logger = logging.getLogger(__name__)


class FastReActAgentWrapper(Agent):
    """FastReAct 智能体包装类

    将 FastReAct 引擎包装为智能体接口，使其可以作为智能体使用。
    """

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        fastreact: FastReAct,
        system_prompt: str = None,
        tools: List[Tool] = None,
        **kwargs
    ):
        """
        初始化包装智能体

        Args:
            name: 智能体名称
            role: 角色描述
            description: 功能描述
            fastreact: FastReAct 实例
            system_prompt: 自定义系统提示词（可选）
            tools: 工具列表
            **kwargs: 其他参数
        """
        super().__init__(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            tools=tools or [],
            **kwargs
        )

        self.fastreact = fastreact

    async def execute(
        self,
        task: str,
        context: Dict[str, Any] = None,
        tools: List[Tool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行任务

        Args:
            task: 任务描述
            context: 上下文信息
            tools: 可用工具列表
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        start_time = datetime.now()

        try:
            # 如果有自定义系统提示词，修改 FastReAct 的系统提示
            if self.system_prompt != self._get_default_system_prompt():
                # 临时保存原系统提示
                original_prompt = self.fastreact._build_system_prompt()

                # 注意：这里需要 FastReAct 支持动态设置系统提示
                # 如果不支持，就通过 context 传递
                pass

            # 准备历史记录（如果有）
            history = context.get("history", []) if context else []

            # 构建完整的查询（包含历史上下文）
            query = task
            if history:
                history_text = "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in history[-5:]  # 最近5条
                ])
                query = f"上下文:\n{history_text}\n\n当前任务:\n{task}"

            # 执行查询
            result = await self.fastreact.run_async(
                query=query,
                session_context=context or {}
            )

            # 更新统计
            elapsed = (datetime.now() - start_time).total_seconds()
            self.stats["tasks_completed"] += 1
            self.stats["total_time"] += elapsed

            return {
                "success": True,
                "result": result.get("answer", ""),
                "stats": result.get("stats", {}),
                "agent": self.name,
                "elapsed_time": elapsed
            }

        except Exception as e:
            # 记录错误
            self.stats["errors"] += 1
            logger.error(f"Agent {self.name} failed: {e}")

            return {
                "success": False,
                "result": None,
                "error": str(e),
                "agent": self.name,
                "error_type": type(e).__name__
            }


def create_agent_from_fastreact(
    name: str,
    role: str,
    description: str,
    fastreact: FastReAct,
    system_prompt: str = None
) -> FastReActAgentWrapper:
    """
    从 FastReAct 实例创建智能体

    Args:
        name: 智能体名称
        role: 角色描述
        description: 功能描述
        fastreact: FastReAct 实例
        system_prompt: 自定义系统提示词

    Returns:
        智能体实例
    """
    return FastReActAgentWrapper(
        name=name,
        role=role,
        description=description,
        fastreact=fastreact,
        system_prompt=system_prompt
    )
