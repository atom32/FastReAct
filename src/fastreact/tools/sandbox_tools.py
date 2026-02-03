"""
Docker 沙箱工具 - 函数式定义

提供安全的代码执行环境，使用 Docker 容器隔离。
"""

import logging
from typing import Dict, Any, Optional, List
from .fn_registry import Tool

logger = logging.getLogger(__name__)

# 全局沙箱实例（单例）
_global_sandbox = None


def get_global_sandbox():
    """获取全局沙箱实例"""
    global _global_sandbox
    if _global_sandbox is None:
        try:
            from ..sandbox.docker import DockerSandbox
            from ..sandbox.config import get_preset_config, SandboxPreset

            # 使用默认安全配置
            config = get_preset_config(SandboxPreset.STANDARD)
            _global_sandbox = DockerSandbox(config=config)
            logger.info("Global sandbox initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize sandbox: {e}")
            _global_sandbox = None
    return _global_sandbox


def create_sandbox_exec_tool(sandbox=None) -> Tool:
    """创建沙箱代码执行工具

    在安全的 Docker 容器中执行代码。

    支持的语言：Python, JavaScript, Bash, Java

    需要安装：pip install docker

    Args:
        sandbox: DockerSandbox 实例（可选，使用全局实例）
    """
    async def execute(
        code: str,
        language: str = "python",
        timeout: int = 30,
        denylist: Optional[List[str]] = None
    ) -> str:
        """在 Docker 沙箱中执行代码"""
        try:
            from ..sandbox.docker import DockerSandbox, SandboxError

            sb = sandbox or get_global_sandbox()
            if not sb:
                return "沙箱未初始化，请确保 Docker 已安装并运行"

            # 使用沙箱配置的 denylist（如果提供）
            sandbox_denylist = denylist
            if sb.config and not sandbox_denylist:
                sandbox_denylist = sb.config.denylist

            result = await sb.execute_code(
                code=code,
                language=language,
                timeout=timeout,
                denylist=sandbox_denylist or []
            )

            # 格式化输出
            if result.get("success"):
                return f"""执行成功（{result['language']}）:

输出:
{result['output']}

时间: {result['timestamp']}"""
            else:
                return f"""执行失败: {result.get('error', 'Unknown error')}

退出码: {result.get('exit_code', 'N/A')}
语言: {result['language']}
时间: {result['timestamp']}"""

        except ImportError:
            return "沙箱功能需要安装 docker 库: pip install docker"
        except SandboxError as e:
            return f"沙箱错误: {str(e)}"
        except Exception as e:
            return f"执行失败: {str(e)}"

    return Tool(
        name="sandbox_exec",
        label="Sandbox Exec",
        group="code",  # V2: 添加到 code 分组
        description="""在安全的 Docker 容器中执行代码

**支持的语言**：
- python / python3: Python 3.11
- javascript / node: JavaScript (Node.js 18)
- bash: Bash 脚本
- java: Java 17

**安全特性**：
- Docker 容器隔离
- 资源限制（512MB 内存，50% CPU）
- 可选的关键词黑名单
- 自动超时控制

**使用场景**：
- 执行不可信的代码
- 测试代码片段
- 数据处理和转换
- 需要特定环境的任务

**示例**：
```python
# Python 计算
sandbox_exec(code="print(sum(range(101)))", language="python")

# JavaScript
sandbox_exec(code="console.log('Hello')", language="javascript")

# Bash 命令
sandbox_exec(code="echo 'Hello World'", language="bash")
```""",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的代码"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "python3", "javascript", "node", "bash", "java"],
                    "description": "编程语言",
                    "default": "python"
                },
                "timeout": {
                    "type": "integer",
                    "description": "执行超时时间（秒）",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 300
                },
                "denylist": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "禁止的关键词列表（如 ['os.system', 'subprocess']）",
                    "default": []
                }
            },
            "required": ["code"]
        },
        execute=execute,
    )


def create_persistent_sandbox_tool(sandbox=None) -> Tool:
    """创建持久化沙箱工具

    创建一个长期运行的容器，可以在多次执行之间保持状态。

    需要安装：pip install docker

    Args:
        sandbox: DockerSandbox 实例（可选，使用全局实例）
    """
    async def execute(
        session_id: str,
        language: str = "python",
        persist: bool = False
    ) -> str:
        """创建持久化沙箱容器"""
        try:
            from ..sandbox.docker import DockerSandbox, SandboxError

            sb = sandbox or get_global_sandbox()
            if not sb:
                return "沙箱未初始化"

            container_id = await sb.create_sandbox(
                session_id=session_id,
                language=language,
                persist=persist
            )

            return f"""[OK] 沙箱容器已创建

容器 ID: {container_id}
会话 ID: {session_id}
语言: {language}
持久化: {persist}

现在可以使用 execute_in_sandbox 在此容器中执行代码"""

        except Exception as e:
            return f"创建沙箱失败: {str(e)}"

    return Tool(
        name="create_persistent_sandbox",
        label="Create Persistent Sandbox",
        group="code",
        description="""创建一个持久化的 Docker 容器，可以在多次执行之间保持状态。

**使用场景**：
- 需要保持环境状态的连续任务
- 需要多次交互的调试会话
- 需要共享文件系统的任务

**参数**：
- session_id: 会话ID（用于标识容器）
- language: 编程语言
- persist: 是否持久化容器（False 则在会话结束后自动删除）

**示例**：
```python
# 创建持久化容器
create_persistent_sandbox(session_id="my_session", language="python")
```
""",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话ID（用于标识容器）"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "python3", "javascript", "node", "bash", "java"],
                    "description": "编程语言",
                    "default": "python"
                },
                "persist": {
                    "type": "boolean",
                    "description": "是否持久化容器（不会自动删除）",
                    "default": False
                }
            },
            "required": ["session_id"]
        },
        execute=execute,
    )


def create_execute_in_sandbox_tool(sandbox=None) -> Tool:
    """创建在持久化沙箱中执行的工具"""
    async def execute(
        session_id: str,
        code: str,
        language: str = "python"
    ) -> str:
        """在持久化沙箱中执行代码"""
        try:
            from ..sandbox.docker import DockerSandbox, SandboxError

            sb = sandbox or get_global_sandbox()
            if not sb:
                return "沙箱未初始化"

            result = await sb.execute_in_sandbox(
                session_id=session_id,
                code=code,
                language=language
            )

            if result.get("success"):
                return f"""执行成功:

{result['output']}"""
            else:
                return f"""执行失败: {result.get('error', 'Unknown error')}

退出码: {result.get('exit_code', 'N/A')}"""

        except Exception as e:
            return f"执行失败: {str(e)}"

    return Tool(
        name="execute_in_sandbox",
        label="Execute in Persistent Sandbox",
        group="code",
        description="""在已创建的持久化沙箱容器中执行代码。

**前提**：需要先使用 create_persistent_sandbox 创建容器

**参数**：
- session_id: 会话ID
- code: 要执行的代码
- language: 编程语言

**示例**：
```python
# 先创建容器
create_persistent_sandbox(session_id="my_session")

# 然后在容器中执行代码
execute_in_sandbox(session_id="my_session", code="x = 10")
execute_in_sandbox(session_id="my_session", code="print(x * 2)")
```
""",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话ID"
                },
                "code": {
                    "type": "string",
                    "description": "要执行的代码"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "python3", "javascript", "node", "bash", "java"],
                    "description": "编程语言",
                    "default": "python"
                }
            },
            "required": ["session_id", "code"]
        },
        execute=execute,
    )


def create_destroy_sandbox_tool(sandbox=None) -> Tool:
    """创建销毁沙箱工具"""
    async def execute(session_id: str) -> str:
        """销毁持久化沙箱容器"""
        try:
            from ..sandbox.docker import DockerSandbox, SandboxError

            sb = sandbox or get_global_sandbox()
            if not sb:
                return "沙箱未初始化"

            await sb.destroy_sandbox(session_id)

            return f"[OK] 沙箱容器已销毁: {session_id}"

        except Exception as e:
            return f"销毁沙箱失败: {str(e)}"

    return Tool(
        name="destroy_sandbox",
        label="Destroy Persistent Sandbox",
        group="code",
        description="""销毁持久化沙箱容器。

**参数**：
- session_id: 会话ID

**示例**：
```python
destroy_sandbox(session_id="my_session")
```
""",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话ID"
                }
            },
            "required": ["session_id"]
        },
        execute=execute,
    )


def create_sandbox_tools(sandbox=None) -> List[Tool]:
    """创建所有沙箱工具

    Args:
        sandbox: DockerSandbox 实例（可选）

    Returns:
        沙箱工具列表
    """
    return [
        create_sandbox_exec_tool(sandbox),
        create_persistent_sandbox_tool(sandbox),
        create_execute_in_sandbox_tool(sandbox),
        create_destroy_sandbox_tool(sandbox),
    ]
