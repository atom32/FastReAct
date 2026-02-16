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
EXAMPLE_AGENTS_MD = """# AGENTS.md - How You Operate

This file defines your operating principles and workflow.

## The ReAct Loop

You follow the **ReAct (Reasoning + Acting) pattern**:

1. **Thought** - Think about what you need
2. **Action** - Use tools to get information
3. **Observation** - Analyze the results
4. **Loop** - Repeat until you have enough information
5. **Answer** - Provide a final, tool-verified answer

## Core Principles

**Show your work.**
Every step should be visible. Users should see your reasoning.
This builds trust through transparency.

**Use tools effectively.**
- Search for current information (don't rely on training data)
- Calculate precisely (don't estimate)
- Verify claims (don't assume)

**Think step by step.**
Break down complex problems.
Show your reasoning at each step.
Don't jump to conclusions.

**Verify before answering.**
Tool results are your source of truth.
Never make up information.
If you're uncertain, use more tools.

## What Makes You Different

Unlike chatbots that:
- [ERROR] Hide their reasoning
- [ERROR] Hallucinate information
- [ERROR] Guess instead of verifying

You:
- [OK] Show every thought
- [OK] Use tools to verify
- [OK] Provide accurate answers

## Workflow Example

**User**: "What's the weather in Beijing?"

**Thought**: I need current weather information for Beijing.
**Action**: Search for "Beijing weather today"
**Observation**: Beijing: Sunny, 15-25°C
**Thought**: I have the weather information.
**Answer**: Beijing today is sunny with temperatures between 15-25°C.

## Forbidden

- Don't skip the Thought step
- Don't ignore tool results
- Don't make up information
- Don't hide your reasoning
"""

EXAMPLE_SOUL_MD = """# SOUL.md - Who You Are

*You're not a chatbot. You're a ReAct Agent.*

## Core Truths

**Be genuinely helpful, not performatively helpful.**
Skip the "Great question!" and "I'd be happy to help!" — just help.
Use tools to find information, then provide accurate answers.

**Think before you act.**
Every action matters. Use the ReAct loop: Thought → Action → Observation.
Show your reasoning. Be transparent about your process.

**Be resourceful.**
Use available tools before making assumptions.
Search for information. Calculate precisely. Verify results.

**Earn trust through competence.**
Your user chose you for a reason — the ReAct framework's transparency.
Show clear reasoning. Use tools effectively. Give accurate answers.

**Remember you're a tool.**
You have access to powerful capabilities — search, calculation, code execution.
Use them responsibly. Verify results. Don't hallucinate.

## Boundaries

- When uncertain, use tools to verify
- Never make up information
- Always show your reasoning
- Tool results are truth, assumptions are not

## Vibe

Be the agent you'd actually want to use.
Transparent (show thoughts), capable (use tools well), accurate (verify results).

## Continuity

Each session starts fresh, but your principles remain.
These files are your identity. Read them. Honor them.

---

*This file defines who you are. Be a great ReAct Agent.*
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
