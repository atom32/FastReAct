"""
FastReAct 多智能体系统 - 基类和接口

支持多个专用智能体协作完成任务。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime


class Agent(ABC):
    """智能体基类

    所有智能体都应该继承这个类并实现 execute 方法。
    """

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        system_prompt: str = None,
        tools: List = None,
        model: str = None
    ):
        """
        初始化智能体

        Args:
            name: 智能体名称（唯一标识）
            role: 角色描述
            description: 功能描述
            system_prompt: 系统提示词（覆盖默认）
            tools: 工具列表
            model: 使用的模型（覆盖默认）
        """
        self.name = name
        self.role = role
        self.description = description
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.tools = tools or []
        self.model = model
        self.stats = {
            "tasks_completed": 0,
            "total_time": 0.0,
            "errors": 0
        }

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: Dict[str, Any] = None,
        tools: List = None,
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
            执行结果，包含：
                - success: 是否成功
                - result: 结果内容
                - stats: 统计信息
                - error: 错误信息（如果失败）
        """
        pass

    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        return f"""你是 {self.name}，{self.role}。

{self.description}

工作流程：
1. 理解任务目标
2. 分析任务需求
3. 使用可用工具完成任务
4. 提供清晰、准确的结果
"""

    async def chat(
        self,
        message: str,
        history: List[Dict] = None
    ) -> str:
        """
        简单对话接口

        Args:
            message: 用户消息
            history: 对话历史

        Returns:
            智能体回复
        """
        # 默认实现：使用 execute 方法
        result = await self.execute(
            task=message,
            context={"history": history or []}
        )
        return result.get("result", "")

    def get_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "tools": [tool.__class__.__name__ for tool in self.tools],
            "stats": self.stats
        }

    def __repr__(self) -> str:
        return f"Agent({self.name}, {self.role})"


class AgentTask:
    """智能体任务"""

    def __init__(
        self,
        task_id: str,
        description: str,
        agent_name: str,
        status: str = "pending",
        result: Any = None,
        error: str = None,
        created_at: datetime = None,
        completed_at: datetime = None
    ):
        self.task_id = task_id
        self.description = description
        self.agent_name = agent_name
        self.status = status  # pending, in_progress, completed, failed
        self.result = result
        self.error = error
        self.created_at = created_at or datetime.now()
        self.completed_at = completed_at

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "agent_name": self.agent_name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
