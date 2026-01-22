"""
FastReAct工具系统

提供工具基类和数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolCall:
    """工具调用"""

    name: str
    parameters: Dict[str, Any]
    call_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "parameters": self.parameters,
            "call_id": self.call_id,
        }


@dataclass
class ToolResult:
    """工具执行结果"""

    tool_name: str
    result: Any
    error: str = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
        }

    @property
    def is_success(self) -> bool:
        """是否执行成功"""
        return self.error is None


class Tool(ABC):
    """
    工具基类

    所有自定义工具都需要继承这个类并实现以下方法：
    - _get_description(): 工具描述
    - _get_parameters(): 参数schema（JSON Schema格式）
    - execute_async(): 异步执行方法
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.description = self._get_description()
        self.parameters = self._get_parameters()

    @abstractmethod
    def _get_description(self) -> str:
        """
        返回工具描述

        Returns:
            工具描述字符串（会显示给LLM）
        """
        pass

    @abstractmethod
    def _get_parameters(self) -> Dict[str, Any]:
        """
        返回参数schema（JSON Schema格式）

        Returns:
            参数schema字典

        示例:
            {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    }
                },
                "required": ["query"]
            }
        """
        pass

    @abstractmethod
    async def execute_async(self, **kwargs) -> Any:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果（可以是任意类型，会被转换为字符串）
        """
        pass

    def execute(self, **kwargs) -> Any:
        """
        同步执行工具（默认实现）

        默认使用asyncio.run调用异步方法
        子类可以重写这个方法提供更高效的同步实现
        """
        import asyncio

        return asyncio.run(self.execute_async(**kwargs))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def __repr__(self) -> str:
        return f"Tool(name={self.name})"
