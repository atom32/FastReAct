"""
工作区管理器

负责初始化工作区和创建示例配置文件。
"""

import os
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


# 示例配置文件内容
EXAMPLE_AGENTS_MD = """# Agent 操作指令

这个文件定义了 Agent 的基本操作原则和工作流程。

## 核心原则

1. **准确性优先** - 确保所有信息准确无误
2. **工具使用** - 积极使用可用工具获取信息
3. **逐步推理** - 清晰展示思考过程
4. **结果验证** - 验证工具返回的结果

## 工作流程

1. 理解用户需求
2. 分析需要什么信息
3. 选择合适的工具
4. 执行并分析结果
5. 综合给出答案

## 禁止行为

- 不得编造信息
- 不得忽略工具结果
- 不得跳过推理步骤
"""

EXAMPLE_SOUL_MD = """# Agent 人格定义

这个文件定义了 Agent 的人格、语气和行为边界。

## 人格

你是一个**友好、专业的 AI 助手**，名为 FastReAct。

### 特点

- **专业**：在专业领域表现出深度知识
- **友好**：使用温暖、亲切的语言
- **耐心**：详细解释复杂概念
- **诚实**：不确定时明确说明

## 语气

- 清晰简洁
- 避免过于技术化
- 适当使用例子
- 保持积极态度

## 边界

- 不涉及政治、宗教等敏感话题
- 不提供可能造成伤害的建议
- 尊重用户隐私
- 遵守法律和道德标准

## 语言风格

- 使用中文（除非用户明确要求英文）
- 避免使用表情符号（除非合适）
- 用词准确、专业
- 句子结构清晰
"""

EXAMPLE_TOOLS_MD = """# 工具使用指南

这个文件提供了如何有效使用可用工具的指导。

## 通用原则

1. **优先使用工具** - 不要仅依靠训练数据
2. **并行调用** - 独立的工具可以并行调用
3. **参数准确** - 确保工具参数正确
4. **结果分析** - 仔细分析工具返回的结果

## 可用工具

### 搜索工具 (search)
- **用途**：搜索网络信息
- **何时使用**：需要最新信息或特定事实
- **参数**：搜索查询字符串

### 计算器 (calculator)
- **用途**：执行数学计算
- **何时使用**：需要精确计算结果
- **参数**：数学表达式

### 日期时间 (datetime)
- **用途**：获取当前时间和日期信息
- **何时使用**：需要时间相关信息

## 最佳实践

- 信息不足时，先使用搜索工具
- 需要计算时，使用计算器而非估算
- 多个独立查询可以并行执行
- 验证工具结果的合理性
"""

EXAMPLE_WORKSPACE_MD = """# 工作区配置

这个文件定义了工作区的特定配置和上下文。

## 工作区信息

- **名称**：默认工作区
- **创建时间**：{timestamp}
- **用途**：FastReAct Agent 配置

## 项目上下文

你可以在这里添加项目特定的信息：

- 项目背景
- 常用术语
- 团队规范
- 参考资料

## 示例

### 如果这是一个软件开发工作区：

本项目使用 Python 3.11+，采用异步编程模式。
主要框架：FastAPI, Pydantic
代码风格：Black, Ruff

### 如果这是一个研究工作区：

研究领域：人工智能和机器学习
重点关注：大语言模型、Agent 系统
"""

DEFAULT_CONFIG_JSON = """{
  "profile": "default",
  "llm": {
    "providers": {
      "openai": {
        "api_key": "your-api-key-here",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4-turbo-preview"
      }
    },
    "default_provider": "openai"
  },
  "agent": {
    "max_iterations": 10,
    "temperature": 0.7,
    "enable_cache": true,
    "timeout": 120
  },
  "logging": {
    "level": "INFO",
    "enable_file_logging": true,
    "log_dir": "logs"
  },
  "bootstrap": {
    "enable": true,
    "workspace": "~/.fastreact",
    "auto_reload": false
  }
}
"""


class WorkspaceManager:
    """
    工作区管理器

    负责创建、初始化和管理工作区。
    """

    def __init__(self, workspace: Optional[str] = None):
        """
        初始化工作区管理器

        Args:
            workspace: 工作区路径，默认为 ~/.fastreact
        """
        self.workspace = Path(workspace or os.path.expanduser("~/.fastreact")).resolve()
        logger.info(f"Workspace manager: {self.workspace}")

    def create_workspace(self, overwrite: bool = False) -> bool:
        """
        创建工作区目录和示例文件

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            是否成功创建
        """
        try:
            # 创建目录
            self.workspace.mkdir(parents=True, exist_ok=True)

            # 创建示例文件
            created_files = []

            files_to_create = {
                "AGENTS.md": EXAMPLE_AGENTS_MD,
                "SOUL.md": EXAMPLE_SOUL_MD,
                "TOOLS.md": EXAMPLE_TOOLS_MD,
                "WORKSPACE.md": EXAMPLE_WORKSPACE_MD.format(
                    timestamp=__import__('datetime').datetime.now().isoformat()
                ),
                "config.json": DEFAULT_CONFIG_JSON,
            }

            for filename, content in files_to_create.items():
                path = self.workspace / filename

                # 如果文件已存在且不覆盖，跳过
                if path.exists() and not overwrite:
                    logger.debug(f"File already exists, skipping: {filename}")
                    continue

                # 写入文件
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)

                created_files.append(filename)
                logger.info(f"Created: {filename}")

            if created_files:
                logger.info(f"Workspace created with {len(created_files)} files")
            else:
                logger.info("Workspace already exists (no files overwritten)")

            return True

        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            return False

    def list_files(self) -> List[str]:
        """
        列出工作区中的所有文件

        Returns:
            文件名列表
        """
        if not self.workspace.exists():
            return []

        return [f.name for f in self.workspace.iterdir() if f.is_file()]

    def file_exists(self, filename: str) -> bool:
        """
        检查文件是否存在

        Args:
            filename: 文件名

        Returns:
            是否存在
        """
        return (self.workspace / filename).exists()

    def get_file_path(self, filename: str) -> Path:
        """
        获取文件的完整路径

        Args:
            filename: 文件名

        Returns:
            文件路径
        """
        return self.workspace / filename

    def read_file(self, filename: str) -> Optional[str]:
        """
        读取文件内容

        Args:
            filename: 文件名

        Returns:
            文件内容，如果不存在或读取失败则返回 None
        """
        path = self.workspace / filename

        if not path.exists():
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            return None

    def write_file(self, filename: str, content: str) -> bool:
        """
        写入文件

        Args:
            filename: 文件名
            content: 文件内容

        Returns:
            是否成功
        """
        try:
            path = self.workspace / filename

            # 确保目录存在
            self.workspace.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Wrote: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error writing {filename}: {e}")
            return False

    def delete_file(self, filename: str) -> bool:
        """
        删除文件

        Args:
            filename: 文件名

        Returns:
            是否成功
        """
        try:
            path = self.workspace / filename

            if path.exists():
                path.unlink()
                logger.info(f"Deleted: {filename}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting {filename}: {e}")
            return False

    def clear_workspace(self) -> bool:
        """
        清空工作区（删除所有文件）

        Returns:
            是否成功
        """
        try:
            for filename in self.list_files():
                self.delete_file(filename)

            logger.info("Workspace cleared")
            return True

        except Exception as e:
            logger.error(f"Error clearing workspace: {e}")
            return False


def init_workspace(
    workspace: Optional[str] = None,
    overwrite: bool = False
) -> WorkspaceManager:
    """
    初始化工作区（便捷函数）

    Args:
        workspace: 工作区路径
        overwrite: 是否覆盖已存在的文件

    Returns:
        WorkspaceManager 实例

    Examples:
        >>> from fastreact.bootstrap import init_workspace
        >>> manager = init_workspace()
        >>> print(f"Workspace: {manager.workspace}")
    """
    manager = WorkspaceManager(workspace)
    manager.create_workspace(overwrite=overwrite)
    return manager
