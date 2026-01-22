"""
MCP工具适配器

将Biro的MCP工具格式转换为FastReAct的Tool格式
允许复用Biro的27个工具，无需修改原有代码
"""

import asyncio
import inspect
from typing import Any, Dict, Callable, Optional, Union, get_origin, get_args
from fastreact.core.tool import Tool


class MCPToolWrapper(Tool):
    """
    MCP工具包装器

    将Biro的MCP工具（装饰器注册的函数）包装为FastReAct的Tool对象
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化MCP工具包装器

        Args:
            name: 工具名称
            func: 工具函数（可以是同步或异步）
            description: 工具描述
            parameters: 参数schema（JSON Schema格式）
        """
        self._func = func
        self._name = name

        # 如果没有提供description，尝试从函数docstring获取
        if description is None:
            description = func.__doc__ or f"Tool: {name}"

        # 如果没有提供parameters，尝试从函数签名推断
        if parameters is None:
            parameters = self._infer_parameters(func)

        # 设置Tool基类需要的属性
        self.name = name
        self.description = description
        self.parameters = parameters

    def _infer_parameters(self, func: Callable) -> Dict[str, Any]:
        """
        从函数签名推断参数schema

        Args:
            func: 工具函数

        Returns:
            JSON Schema格式的参数定义
        """
        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param_name, param in sig.parameters.items():
            # 跳过self参数
            if param_name == "self":
                continue

            # 添加参数属性
            param_info = {"type": "string", "description": f"Parameter: {param_name}"}

            # 尝试从类型注解推断类型
            if param.annotation != inspect.Parameter.empty:
                param_annotation = param.annotation

                # 处理Optional类型
                if hasattr(param_annotation, "__origin__"):
                    from typing import get_origin, get_args

                    origin = get_origin(param_annotation)
                    if origin is Optional or origin is Union:
                        # Optional类型，参数非必需
                        pass
                    else:
                        # 其他泛型类型
                        param_info["type"] = self._python_type_to_json_type(param_annotation)
                else:
                    param_info["type"] = self._python_type_to_json_type(param_annotation)

            # 检查参数是否必需
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

            parameters["properties"][param_name] = param_info

        return parameters

    def _python_type_to_json_type(self, python_type) -> str:
        """
        将Python类型转换为JSON Schema类型

        Args:
            python_type: Python类型

        Returns:
            JSON Schema类型字符串
        """
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        # 处理Optional类型
        if hasattr(python_type, "__origin__"):
            origin = get_origin(python_type)
            if origin is Optional or origin is Union:
                # Optional[T] -> T的类型
                args = get_args(python_type)
                if args:
                    return self._python_type_to_json_type(args[0])

        # 直接映射
        return type_mapping.get(python_type, "string")

    def _get_description(self) -> str:
        """返回工具描述"""
        return self.description

    def _get_parameters(self) -> Dict[str, Any]:
        """返回参数schema"""
        return self.parameters

    async def execute_async(self, **kwargs) -> Any:
        """
        异步执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        try:
            # 检查函数是否是协程函数
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(**kwargs)
            else:
                # 同步函数，在线程池中执行以避免阻塞
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: self._func(**kwargs))

            return result

        except Exception as e:
            raise RuntimeError(f"Error executing tool {self._name}: {str(e)}")


class MCPToolRegistry:
    """
    MCP工具注册表

    管理所有MCP工具，提供注册和查找功能
    """

    def __init__(self):
        """初始化注册表"""
        self._tools: Dict[str, Tool] = {}

    def register_function(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tool:
        """
        注册函数为MCP工具

        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            parameters: 参数schema

        Returns:
            创建的Tool对象
        """
        tool = MCPToolWrapper(name, func, description, parameters)
        self._tools[name] = tool
        return tool

    def register_tool(self, tool: Tool) -> None:
        """
        注册Tool对象

        Args:
            tool: Tool对象
        """
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            Tool对象，如果不存在返回None
        """
        return self._tools.get(name)

    def get_all_tools(self) -> Dict[str, Tool]:
        """
        获取所有工具

        Returns:
            工具字典
        """
        return self._tools.copy()

    def list_tool_names(self) -> list:
        """
        列出所有工具名称

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """返回工具数量"""
        return len(self._tools)


# 全局工具注册表
_global_registry = MCPToolRegistry()


def register_mcp_tool(
    name: str,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
):
    """
    装饰器：注册函数为MCP工具

    这是Biro风格的装饰器，兼容现有代码

    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数schema（JSON Schema格式）

    Returns:
        装饰器函数

    示例:
        @register_mcp_tool("query_graph_rag")
        def query_graph_rag(entity: str, relation: Optional[str] = None):
            '''Query GraphRAG knowledge graph'''
            # 实现逻辑...
            return result
    """

    def decorator(func: Callable) -> Callable:
        # 注册到全局注册表
        _global_registry.register_function(name, func, description, parameters)

        # 返回原函数（不修改）
        return func

    return decorator


def get_global_registry() -> MCPToolRegistry:
    """
    获取全局工具注册表

    Returns:
        全局MCP工具注册表
    """
    return _global_registry


def export_tools_to_fastreact() -> list:
    """
    导出所有MCP工具为FastReAct Tool列表

    Returns:
        Tool对象列表
    """
    return list(_global_registry.get_all_tools().values())
