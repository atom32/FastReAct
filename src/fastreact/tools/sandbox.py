"""
沙箱工具

安全的代码执行工具，使用 Docker 容器隔离。
"""

import json
import logging
from typing import Dict, Any

from ..core.tool import Tool
from ..sandbox.docker import DockerSandbox, SandboxError

logger = logging.getLogger(__name__)


class ExecuteCodeTool(Tool):
    """Docker 沙箱代码执行工具

    在安全的 Docker 容器中执行代码。

    支持: Python, JavaScript, Bash, Java

    Example:
        result = await execute_code(
            code="print('Hello, World!')",
            language="python"
        )
    """

    def __init__(self, sandbox: DockerSandbox = None):
        """初始化工具

        Args:
            sandbox: DockerSandbox 实例（可选，默认创建新实例）
        """
        self.sandbox = sandbox or DockerSandbox()
        super().__init__()

    def _get_description(self):
        return "Execute code in a secure Docker sandbox"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash", "java"],
                    "description": "Programming language",
                    "default": "python"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30
                },
                "denylist": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Blocked keywords (e.g., ['os.system', 'subprocess'])",
                    "default": []
                }
            },
            "required": ["code"]
        }

    async def execute_async(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        denylist: list = None
    ) -> str:
        """在 Docker 沙箱中执行代码

        Args:
            code: 代码字符串
            language: 编程语言
            timeout: 超时时间（秒）
            denylist: 拒绝的关键词列表

        Returns:
            JSON 格式的执行结果
        """
        try:
            result = await self.sandbox.execute_code(
                code=code,
                language=language,
                timeout=timeout,
                denylist=denylist or []
            )

            return json.dumps(result, ensure_ascii=False, indent=2)

        except SandboxError as e:
            error_result = {
                "success": False,
                "error": f"Sandbox error: {str(e)}",
                "language": language
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "language": language
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)


class CreateSandboxTool(Tool):
    """创建持久化沙箱工具

    创建一个长期运行的 Docker 容器用于多次代码执行。

    Example:
        sandbox_id = await create_sandbox(
            session_id="user123",
            language="python"
        )

        # 后续可以在同一个沙箱中执行代码
        result = await execute_in_sandbox(
            session_id="user123",
            code="x = 1",
            language="python"
        )
    """

    def __init__(self, sandbox: DockerSandbox = None):
        """初始化工具

        Args:
            sandbox: DockerSandbox 实例
        """
        self.sandbox = sandbox or DockerSandbox()
        super().__init__()

    def _get_description(self):
        return "Create a persistent Docker sandbox container"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to identify the sandbox"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash", "java"],
                    "description": "Programming language",
                    "default": "python"
                },
                "persist": {
                    "type": "boolean",
                    "description": "Whether to persist the container after execution",
                    "default": False
                }
            },
            "required": ["session_id"]
        }

    async def execute_async(
        self,
        session_id: str,
        language: str = "python",
        persist: bool = False
    ) -> str:
        """创建持久化沙箱

        Args:
            session_id: 会话ID
            language: 编程语言
            persist: 是否持久化

        Returns:
            JSON 格式的结果
        """
        try:
            container_id = await self.sandbox.create_sandbox(
                session_id=session_id,
                language=language,
                persist=persist
            )

            result = {
                "success": True,
                "container_id": container_id,
                "session_id": session_id,
                "language": language
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)


class ExecuteInSandboxTool(Tool):
    """在持久化沙箱中执行代码

    在之前创建的沙箱容器中执行代码。

    Example:
        result = await execute_in_sandbox(
            session_id="user123",
            code="x = 1; print(x)",
            language="python"
        )
    """

    def __init__(self, sandbox: DockerSandbox = None):
        """初始化工具

        Args:
            sandbox: DockerSandbox 实例
        """
        self.sandbox = sandbox or DockerSandbox()
        super().__init__()

    def _get_description(self):
        return "Execute code in a persistent sandbox container"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID of the sandbox"
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash", "java"],
                    "description": "Programming language",
                    "default": "python"
                }
            },
            "required": ["session_id", "code"]
        }

    async def execute_async(
        self,
        session_id: str,
        code: str,
        language: str = "python"
    ) -> str:
        """在沙箱中执行代码

        Args:
            session_id: 会话ID
            code: 代码
            language: 编程语言

        Returns:
            JSON 格式的执行结果
        """
        try:
            result = await self.sandbox.execute_in_sandbox(
                session_id=session_id,
                code=code,
                language=language
            )

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)


class DestroySandboxTool(Tool):
    """销毁沙箱容器

    销毁持久化沙箱容器并释放资源。

    Example:
        result = await destroy_sandbox(session_id="user123")
    """

    def __init__(self, sandbox: DockerSandbox = None):
        """初始化工具

        Args:
            sandbox: DockerSandbox 实例
        """
        self.sandbox = sandbox or DockerSandbox()
        super().__init__()

    def _get_description(self):
        return "Destroy a persistent sandbox container"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID of the sandbox to destroy"
                }
            },
            "required": ["session_id"]
        }

    async def execute_async(self, session_id: str) -> str:
        """销毁沙箱

        Args:
            session_id: 会话ID

        Returns:
            JSON 格式的结果
        """
        try:
            await self.sandbox.destroy_sandbox(session_id)

            result = {
                "success": True,
                "session_id": session_id,
                "message": f"Sandbox {session_id} destroyed"
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
