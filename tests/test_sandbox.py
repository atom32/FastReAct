"""
测试 Docker 沙箱系统
"""

import pytest
from fastreact.sandbox import DockerSandbox, SandboxError


@pytest.mark.asyncio
class TestDockerSandbox:
    """测试 DockerSandbox"""

    @pytest.fixture
    async def sandbox(self):
        """创建沙箱实例"""
        try:
            sandbox = DockerSandbox()
            yield sandbox
        except SandboxError:
            pytest.skip("Docker not available")

    async def test_initialize_sandbox(self, sandbox):
        """测试初始化沙箱"""
        assert sandbox is not None
        assert sandbox.client is not None

    async def test_execute_python_code(self, sandbox):
        """测试执行 Python 代码"""
        result = await sandbox.execute_code(
            code="print('Hello, World!')",
            language="python"
        )

        assert result["success"] is True
        assert "Hello, World!" in result["output"]
        assert result["language"] == "python"

    async def test_execute_javascript_code(self, sandbox):
        """测试执行 JavaScript 代码"""
        result = await sandbox.execute_code(
            code="console.log('Hello from Node!');",
            language="javascript"
        )

        assert result["success"] is True
        assert "Hello from Node!" in result["output"]

    async def test_execute_bash_code(self, sandbox):
        """测试执行 Bash 代码"""
        result = await sandbox.execute_code(
            code="echo 'Hello from Bash!'",
            language="bash"
        )

        assert result["success"] is True
        assert "Hello from Bash!" in result["output"]

    async def test_code_with_denied_keyword(self, sandbox):
        """测试拒绝列表"""
        result = await sandbox.execute_code(
            code="import os; os.system('rm -rf /')",
            language="python",
            denylist=["os.system", "subprocess"]
        )

        assert result["success"] is False
        assert "Blocked keyword" in result["error"]

    async def test_code_timeout(self, sandbox):
        """测试代码超时"""
        result = await sandbox.execute_code(
            code="import time; time.sleep(100)",
            language="python",
            timeout=2
        )

        assert result["success"] is False

    async def test_create_persistent_sandbox(self, sandbox):
        """测试创建持久化沙箱"""
        container_id = await sandbox.create_sandbox(
            session_id="test_session",
            language="python"
        )

        assert container_id is not None
        assert len(container_id) > 0
        assert "test_session" in sandbox.containers

    async def test_execute_in_persistent_sandbox(self, sandbox):
        """测试在持久化沙箱中执行"""
        # 创建沙箱
        await sandbox.create_sandbox(
            session_id="test_session",
            language="python"
        )

        # 执行代码
        result = await sandbox.execute_in_sandbox(
            session_id="test_session",
            code="x = 42",
            language="python"
        )

        assert result["success"] is True

        # 清理
        await sandbox.destroy_sandbox("test_session")

    async def test_execute_in_nonexistent_sandbox(self, sandbox):
        """测试在不存在的沙箱中执行"""
        result = await sandbox.execute_in_sandbox(
            session_id="nonexistent",
            code="print('test')",
            language="python"
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_destroy_sandbox(self, sandbox):
        """测试销毁沙箱"""
        await sandbox.create_sandbox(
            session_id="test_session",
            language="python"
        )

        await sandbox.destroy_sandbox("test_session")

        assert "test_session" not in sandbox.containers

    async def test_cleanup(self, sandbox):
        """测试清理所有沙箱"""
        await sandbox.create_sandbox("session1", "python")
        await sandbox.create_sandbox("session2", "python")

        assert len(sandbox.containers) == 2

        await sandbox.cleanup()

        assert len(sandbox.containers) == 0

    async def test_get_stats(self, sandbox):
        """测试获取统计信息"""
        stats = sandbox.get_stats()

        assert "active_containers" in stats
        assert "supported_languages" in stats
        assert "memory_limit" in stats
        assert "python" in stats["supported_languages"]

    async def test_list_images(self, sandbox):
        """测试列出镜像"""
        images = await sandbox.list_images()

        assert isinstance(images, list)

    async def test_error_handling(self, sandbox):
        """测试错误处理"""
        # 语法错误
        result = await sandbox.execute_code(
            code="print('missing quote",
            language="python"
        )

        assert result["success"] is False
        assert result.get("error") or result.get("exit_code") is not None
