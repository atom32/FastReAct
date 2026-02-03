"""
Docker 沙箱

使用 Docker 容器提供安全的代码执行环境。
"""

import docker
from typing import Dict, Optional, List, Any
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    """沙箱错误基类"""
    pass


class DockerSandbox:
    """Docker 沙箱管理器

    使用 Docker 容器隔离执行代码，提供安全的执行环境。

    需要安装:
        pip install docker

    Usage:
        from fastreact.sandbox import DockerSandbox
        from fastreact.sandbox.config import SandboxConfig, get_preset_config, SandboxPreset

        # 方式 1: 使用默认配置
        sandbox = DockerSandbox()

        # 方式 2: 使用预设配置
        config = get_preset_config(SandboxPreset.SAFE)
        sandbox = DockerSandbox(config=config)

        # 方式 3: 使用自定义配置
        config = SandboxConfig(memory_limit="1g", cpu_limit=1.0)
        sandbox = DockerSandbox(config=config)

        # 执行代码
        result = await sandbox.execute_code(
            code="print('Hello, World!')",
            language="python"
        )

        print(result["output"])
        # Hello, World!
    """

    def __init__(self, config=None):
        """初始化 Docker 沙箱

        Args:
            config: SandboxConfig 对象（可选，使用默认配置）
        """
        try:
            self.client = docker.from_env()
            self.client.ping()  # 测试连接
        except Exception as e:
            raise SandboxError(
                f"Failed to connect to Docker: {e}. "
                "Please ensure Docker is installed and running."
            ) from e

        # 配置
        self.config = config

        # 容器池
        self.containers: Dict[str, docker.models.containers.Container] = {}

        # 支持的语言镜像
        self.image_map = {
            "python": "python:3.11-slim",
            "python3": "python:3.11-slim",
            "javascript": "node:18-alpine",
            "node": "node:18-alpine",
            "bash": "bash:5.2",
            "java": "openjdk:17-slim"
        }

        # 默认资源限制（如果没有配置）
        if config:
            self.default_limits = config.to_docker_kwargs()
        else:
            self.default_limits = {
                "mem_limit": "512m",
                "cpu_period": 100000,
                "cpu_quota": 50000,  # 50% CPU
                "network_disabled": False
            }

        logger.info("Docker sandbox initialized")

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        stdin: str = None,
        allowlist: List[str] = None,
        denylist: List[str] = None
    ) -> Dict:
        """在沙箱中执行代码

        Args:
            code: 要执行的代码
            language: 编程语言 (python, javascript, bash, java)
            timeout: 超时时间（秒）
            stdin: 标准输入
            allowlist: 允许的关键词列表
            denylist: 拒绝的关键词列表

        Returns:
            执行结果字典
            {
                "success": bool,
                "output": str,
                "error": str (如果失败),
                "exit_code": int (如果失败),
                "language": str,
                "timestamp": str
            }
        """
        # 选择镜像
        image = self.image_map.get(language, "python:3.11-slim")

        # 安全检查
        if denylist:
            for keyword in denylist:
                if keyword in code:
                    return {
                        "success": False,
                        "error": f"Blocked keyword: {keyword}",
                        "language": language,
                        "timestamp": datetime.utcnow().isoformat()
                    }

        try:
            # 构建命令
            command = self._build_command(code, language)

            # 获取环境变量
            env = self._get_environment(language)

            # 在线程池中运行同步的 Docker 命令，并设置超时
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        executor,
                        lambda: self.client.containers.run(
                            image,
                            command=command,
                            stdin_open=True if stdin else False,
                            environment=env,
                            **self.default_limits,
                            remove=True,
                            stdout=True,
                            stderr=True,
                            detach=False
                        )
                    ),
                    timeout=timeout
                )

            output = result.decode("utf-8") if isinstance(result, bytes) else result

            return {
                "success": True,
                "output": output,
                "language": language,
                "timestamp": datetime.utcnow().isoformat()
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Execution timed out after {timeout} seconds",
                "language": language,
                "timestamp": datetime.utcnow().isoformat()
            }
        except docker.errors.ContainerError as e:
            return {
                "success": False,
                "error": e.stderr.decode("utf-8") if e.stderr else str(e),
                "exit_code": e.exit_status,
                "language": language,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "language": language,
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_command(self, code: str, language: str) -> List[str]:
        """构建执行命令

        Args:
            code: 代码字符串
            language: 编程语言

        Returns:
            命令列表
        """
        if language in ("python", "python3"):
            # 使用 -c 参数执行代码
            # 需要正确处理代码中的引号
            return ["python", "-c", code]

        elif language in ("javascript", "node"):
            return ["node", "-e", code]

        elif language == "bash":
            return ["bash", "-c", code]

        elif language == "java":
            # Java 需要更复杂的处理
            # 这里简化为执行 bash 命令
            return ["bash", "-c", code]

        else:
            # 默认使用 bash
            return ["bash", "-c", code]

    def _get_environment(self, language: str) -> Dict[str, str]:
        """获取环境变量

        Args:
            language: 编程语言

        Returns:
            环境变量字典
        """
        env = {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NODE_ENV": "production"
        }

        return env

    async def create_sandbox(
        self,
        session_id: str,
        language: str = "python",
        persist: bool = False
    ) -> str:
        """创建持久化沙箱容器

        Args:
            session_id: 会话ID
            language: 编程语言
            persist: 是否持久化容器

        Returns:
            容器ID
        """
        image = self.image_map.get(language, "python:3.11-slim")

        try:
            # 运行一个保持容器运行的命令
            container = self.client.containers.run(
                image,
                command=["tail", "-f", "/dev/null"],
                detach=True,
                remove=not persist,
                name=f"sandbox_{session_id[:8]}",
                **self.default_limits
            )

            self.containers[session_id] = container

            logger.info(f"Created sandbox container: {container.id}")
            return container.id

        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise SandboxError(f"Failed to create sandbox: {e}") from e

    async def execute_in_sandbox(
        self,
        session_id: str,
        code: str,
        language: str = "python"
    ) -> Dict:
        """在持久化沙箱中执行代码

        Args:
            session_id: 会话ID
            code: 代码
            language: 编程语言

        Returns:
            执行结果字典
        """
        if session_id not in self.containers:
            return {
                "success": False,
                "error": "Sandbox not found",
                "language": language
            }

        container = self.containers[session_id]

        try:
            # 构建命令
            command = self._build_command(code, language)

            # 在容器中执行命令
            result = container.exec_run(command)

            output = result.output.decode("utf-8") if result.output else ""

            return {
                "success": result.exit_code == 0,
                "output": output,
                "exit_code": result.exit_code,
                "language": language
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "language": language
            }

    async def destroy_sandbox(self, session_id: str):
        """销毁沙箱容器

        Args:
            session_id: 会话ID
        """
        if session_id in self.containers:
            try:
                container = self.containers[session_id]
                container.stop(timeout=5)
                container.remove()
                del self.containers[session_id]
                logger.info(f"Destroyed sandbox for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to destroy sandbox: {e}")

    async def cleanup(self):
        """清理所有沙箱容器"""
        for session_id in list(self.containers.keys()):
            await self.destroy_sandbox(session_id)

        logger.info("Cleaned up all sandbox containers")

    def get_stats(self) -> Dict:
        """获取沙箱统计信息

        Returns:
            统计信息字典
        """
        return {
            "active_containers": len(self.containers),
            "supported_languages": list(self.image_map.keys()),
            "memory_limit": self.default_limits["mem_limit"],
            "cpu_limit": "50%"
        }

    async def list_images(self) -> List[Dict]:
        """列出可用的 Docker 镜像

        Returns:
            镜像信息列表
        """
        try:
            images = self.client.images.list()

            return [
                {
                    "id": image.id[:12],
                    "tags": image.tags
                }
                for image in images
                if image.tags  # 只返回有标签的镜像
            ]
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []

    async def pull_image(self, image: str):
        """拉取 Docker 镜像

        Args:
            image: 镜像名称（如 "python:3.11-slim"）
        """
        try:
            logger.info(f"Pulling image: {image}")
            self.client.images.pull(image)
            logger.info(f"Successfully pulled image: {image}")
        except Exception as e:
            logger.error(f"Failed to pull image {image}: {e}")
            raise SandboxError(f"Failed to pull image: {e}") from e
