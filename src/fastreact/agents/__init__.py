"""
FastReAct 多智能体系统

支持多个专用智能体协作完成任务。
"""

from .base import Agent, AgentTask
from .router import AgentRouter
from .specialized import (
    ResearchAgent,
    CodeAgent,
    CreativeAgent,
    ManagerAgent,
    GeneralAgent
)
from .wrapper import FastReActAgentWrapper, create_agent_from_fastreact
from .communication import (
    SessionsListTool,
    SessionsSendTool,
    SessionsHistoryTool,
    ConsultAgentTool
)

__all__ = [
    "Agent",
    "AgentTask",
    "AgentRouter",
    "ResearchAgent",
    "CodeAgent",
    "CreativeAgent",
    "ManagerAgent",
    "GeneralAgent",
    "FastReActAgentWrapper",
    "create_agent_from_fastreact",
    "SessionsListTool",
    "SessionsSendTool",
    "SessionsHistoryTool",
    "ConsultAgentTool",
]
