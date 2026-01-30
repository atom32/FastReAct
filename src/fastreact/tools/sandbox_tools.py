"""
Docker 沙箱工具 - 函数式定义

提供安全的代码执行环境，使用 Docker 容器隔离。
"""

import logging
from typing import Dict, Any, Optional, List
from .fn_registry import Tool

logger = logging.getLogger(__name__)


def create_sandbox_exec_tool() -> Tool:
    """创建沙箱代码执行工具

    在安全的 Docker 容器中执行代码。

    支持的语言：Python, JavaScript, Bash, Java

    需要安装：pip install docker
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

            sandbox = DockerSandbox()

            result = await sandbox.execute_code(
                code=code,
                language=language,
                timeout=timeout,
                denylist=denylist or []
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


def create_sandbox_tools() -> List[Tool]:
    """创建所有沙箱工具

    Returns:
        沙箱工具列表
    """
    return [
        create_sandbox_exec_tool(),
        # 未来可以添加：
        # - create_persistent_sandbox (持久化容器)
        # - destroy_sandbox (销毁容器)
    ]
