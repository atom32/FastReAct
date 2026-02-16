"""
工具注册表 - 自动发现和加载工具

支持：
1. 自动扫描 tools 目录
2. 根据配置文件选择性加载
3. 工具依赖检查
4. 优雅降级
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Type, Optional, Any

from . import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表 - 自动发现和管理工具"""

    def __init__(self):
        self._tools: Dict[str, Type[Tool]] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}

    def discover_tools(self, package_name: str = "fastreact.tools") -> None:
        """
        自动发现并注册包中的所有工具

        Args:
            package_name: 要扫描的包名
        """
        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent

            # 扫描所有 Python 文件
            for py_file in package_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"{package_name}.{py_file.stem}"

                try:
                    module = importlib.import_module(module_name)

                    # 查找所有 Tool 子类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, Tool)
                            and obj is not Tool
                            and not obj.__name__.startswith("_")
                        ):
                            # 创建实例获取名称
                            try:
                                temp_instance = obj()
                                tool_name = temp_instance.name

                                self._tools[tool_name] = obj
                                self._tool_metadata[tool_name] = {
                                    "class": obj,
                                    "module": module_name,
                                    "file": str(py_file),
                                    "enabled": True,
                                }

                                logger.debug(f"Registered tool: {tool_name} from {module_name}")
                            except Exception as e:
                                logger.warning(f"Could not instantiate {name}: {e}")

                except Exception as e:
                    logger.warning(f"Failed to load module {module_name}: {e}")

            logger.info(f"Discovered {len(self._tools)} tools")

        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")

    def get_tool(self, name: str, **kwargs) -> Optional[Tool]:
        """
        获取工具实例

        Args:
            name: 工具名称
            **kwargs: 传递给工具构造函数的参数

        Returns:
            工具实例，如果不存在则返回 None
        """
        tool_class = self._tools.get(name)
        if not tool_class:
            return None

        try:
            return tool_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to instantiate tool {name}: {e}")
            return None

    def get_tools(
        self,
        tool_names: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Tool]:
        """
        批量获取工具实例

        Args:
            tool_names: 工具名称列表，None 表示获取所有
            config: 配置字典，用于传递 API key 等参数

        Returns:
            工具实例列表
        """
        if tool_names is None:
            tool_names = list(self._tools.keys())

        tools = []
        config = config or {}

        for name in tool_names:
            # 检查是否在配置中禁用
            tool_config = config.get(name, {})
            if tool_config.get("enabled", True):
                # 从配置获取参数
                tool_params = tool_config.get("params", {})

                tool = self.get_tool(name, **tool_params)
                if tool:
                    tools.append(tool)
                    logger.info(f"Loaded tool: {name}")
                else:
                    logger.warning(f"Failed to load tool: {name}")
            else:
                logger.info(f"Tool disabled in config: {name}")

        return tools

    def list_tools(self) -> List[str]:
        """返回所有已注册工具的名称列表"""
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具的元数据"""
        return self._tool_metadata.get(name)

    def list_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """返回所有工具的元数据"""
        return self._tool_metadata.copy()


# 全局单例
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册表（单例）"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _global_registry.discover_tools()
    return _global_registry


def load_tools_from_config(
    config: Dict[str, Any],
    registry: Optional[ToolRegistry] = None,
) -> List[Tool]:
    """
    根据配置文件加载工具

    Args:
        config: 配置字典，例如：
            {
                "tools": {
                    "builtin_enabled": true,
                    "available_tools": ["Calculator", "Search"],
                    "tavily": {"api_key": "..."}
                }
            }
        registry: 工具注册表，默认使用全局注册表

    Returns:
        工具实例列表
    """
    if registry is None:
        registry = get_registry()

    tools_config = config.get("tools", {})
    builtin_enabled = tools_config.get("builtin_enabled", True)
    available_tools = tools_config.get("available_tools", [])

    if not builtin_enabled:
        logger.info("Built-in tools disabled in config")
        return []

    # 如果没有指定工具列表，使用所有可用工具
    if not available_tools:
        available_tools = registry.list_tools()

    # 提取工具特定的配置
    tool_configs = {}
    for key, value in tools_config.items():
        if key not in ["builtin_enabled", "custom_tools_path", "available_tools"]:
            tool_configs[key] = value

    return registry.get_tools(tool_names=available_tools, config=tool_configs)
