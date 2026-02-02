"""
Stateful Shell Tool - 持久化 Shell 会话工具

提供持久化的 Shell 会话，保持目录状态和环境变量。
适用于 Coding Agent 场景，支持连续的命令执行。
"""

import asyncio
import os
import sys
import subprocess
import threading
import time
from typing import Optional, Dict, Any
from queue import Queue, Empty

from ..core.tool import Tool


class StatefulShellTool(Tool):
    """
    持久化 Shell 会话工具

    核心特性：
    1. 持久化进程：使用 subprocess.Popen 维护长期运行的 shell
    2. 状态保持：cd、export 等命令的副作用会持续生效
    3. 超时控制：防止命令无限期挂起
    4. 跨平台：支持 Windows (cmd.exe) 和 Unix (bash)
    5. 自动截断：大型输出会被 engine 自动截断

    使用示例：
        shell = StatefulShellTool()
        await shell.execute_async("cd /tmp")
        await shell.execute_async("pwd")  # 输出: /tmp
        await shell.execute_async("ls -la")
    """

    # 每个会话只创建一个全局 shell 实例
    _global_shell: Optional['StatefulShellTool'] = None

    def __new__(cls, *args, **kwargs):
        """单例模式：每个进程只维护一个 shell 会话"""
        if cls._global_shell is None:
            instance = super().__new__(cls)
            cls._global_shell = instance
        return cls._global_shell

    def __init__(
        self,
        timeout: int = 30,
        shell: Optional[str] = None,
        working_dir: Optional[str] = None,
    ):
        """
        初始化持久化 Shell

        Args:
            timeout: 命令执行超时时间（秒），默认 30 秒
            shell: Shell 路径（自动检测平台）
            working_dir: 初始工作目录
        """
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 先设置所有属性，然后再调用 super().__init__()
        # 因为 super().__init__() 会调用 _get_parameters()，需要 self.timeout
        self.timeout = timeout
        self.working_dir = working_dir or os.getcwd()
        self._process: Optional[subprocess.Popen] = None
        self._read_thread: Optional[threading.Thread] = None
        self._output_queue: Queue = Queue()
        self._initialized = False  # 标记为未初始化

        # 自动检测平台和 shell
        if shell is None:
            if sys.platform == "win32":
                self.shell_path = "cmd.exe"
            else:
                # 优先使用 bash，否则使用 sh
                self.shell_path = os.environ.get("SHELL", "/bin/bash")
        else:
            self.shell_path = shell

        # 现在调用父类初始化
        super().__init__()
        self._initialized = True  # 标记为已初始化

    def _get_description(self) -> str:
        return """在持久化的 Shell 会话中执行命令

**核心特性**：
- **状态保持**：cd、export 等命令的副作用会持续生效
- **环境保持**：环境变量在命令之间保持不变
- **超时保护**：默认 30 秒超时，防止命令挂起

**常用场景**：
- 文件系统导航：cd, ls, pwd
- 代码操作：git commands, npm install, make
- 测试执行：pytest, npm test
- 文件查看：cat, grep, head, tail

**注意事项**：
- 这是持久化会话，每次命令都在之前的环境中执行
- 如需重置环境，请使用 new_session 参数
- 大量输出会被自动截断，使用 grep 或 head 查看特定内容
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Shell 命令",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认使用工具默认值",
                    "default": self.timeout,
                },
                "new_session": {
                    "type": "boolean",
                    "description": "是否创建新的 Shell 会话（重置所有状态）",
                    "default": False,
                },
            },
            "required": ["command"],
        }

    def _start_shell(self) -> None:
        """启动持久化 Shell 进程"""
        if self._process is not None and self._process.poll() is None:
            # Shell 已经在运行
            return

        try:
            # 创建 Shell 进程
            self._process = subprocess.Popen(
                [self.shell_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=False,  # 使用字节模式
                bufsize=0,  # 无缓冲
                cwd=self.working_dir,
                # Windows 需要 CREATE_NO_WINDOW 标志
                **(
                    {"creationflags": subprocess.CREATE_NO_WINDOW}
                    if sys.platform == "win32"
                    else {}
                ),
            )

            # 启动输出读取线程
            self._read_thread = threading.Thread(
                target=self._read_output, daemon=True
            )
            self._read_thread.start()

        except Exception as e:
            raise RuntimeError(f"Failed to start shell: {e}")

    def _read_output(self) -> None:
        """在后台线程中持续读取 Shell 输出"""
        if self._process is None:
            return

        try:
            while True:
                if self._process.poll() is not None:
                    # 进程已结束
                    break

                try:
                    line = self._process.stdout.readline()
                    if not line:
                        time.sleep(0.01)
                        continue

                    # 解码并放入队列
                    try:
                        decoded = line.decode('utf-8', errors='replace')
                        self._output_queue.put(decoded)
                    except Exception:
                        pass

                except Exception:
                    break

        except Exception:
            pass

    def _execute_sync(self, command: str, timeout: int) -> tuple[str, bool]:
        """
        同步执行命令

        Returns:
            (output, success)
        """
        # 确保 Shell 已启动
        self._start_shell()

        if self._process is None or self._process.poll() is not None:
            return "[ERROR] Shell process not available", False

        # 清空输出队列
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except Empty:
                break

        # 发送命令
        cmd_with_newline = command + "\n"
        try:
            self._process.stdin.write(cmd_with_newline.encode('utf-8'))
            self._process.stdin.flush()
        except Exception as e:
            return f"[ERROR] Failed to write command: {e}", False

        # 收集输出（带超时）
        output_lines = []
        start_time = time.time()
        last_output_time = start_time

        # 读取超时或检测到命令完成
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                # 超时
                if output_lines:
                    output_lines.append(f"\n[TIMEOUT] Command exceeded {timeout}s timeout")
                break

            # 尝试读取输出
            try:
                line = self._output_queue.get(timeout=0.1)
                output_lines.append(line)
                last_output_time = time.time()

                # 检测命令提示符（表示命令完成）
                # 简单的启发式：如果一段时间没有新输出，认为命令完成
                pass

            except Empty:
                # 没有新输出
                if time.time() - last_output_time > 0.5:
                    # 500ms 没有新输出，认为命令完成
                    break
                continue

        output = "".join(output_lines)

        # 移除命令回显（第一行通常是输入的命令）
        lines = output.splitlines()
        if lines and command in lines[0]:
            output = "\n".join(lines[1:])

        return output, True

    async def execute_async(
        self,
        command: str,
        timeout: Optional[int] = None,
        new_session: bool = False,
    ) -> str:
        """
        异步执行 Shell 命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒），None 使用默认值
            new_session: 是否创建新的 Shell 会话

        Returns:
            命令输出
        """
        # 处理 new_session
        if new_session:
            self._close_shell()

        # 使用默认超时
        if timeout is None:
            timeout = self.timeout

        # 在线程池中执行同步命令（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        output, success = await loop.run_in_executor(
            None, self._execute_sync, command, timeout
        )

        if not success:
            return output

        # 添加状态信息
        cwd_indicator = self._get_cwd_indicator()
        return f"""📁 {cwd_indicator}
$ {command}

{output}
"""

    def _get_cwd_indicator(self) -> str:
        """获取当前工作目录指示器"""
        # 对于简单的实现，我们返回一个通用指示器
        # 实际应用中可以执行 pwd 命令获取真实路径
        if sys.platform == "win32":
            return ">"
        else:
            return "~"

    def _close_shell(self) -> None:
        """关闭当前的 Shell 进程"""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

            self._process = None

        if self._read_thread is not None:
            # 线程是 daemon 的，会自动结束
            self._read_thread = None

    async def close(self) -> None:
        """关闭 Shell 会话"""
        self._close_shell()
        StatefulShellTool._global_shell = None


# 便捷函数：创建全局 shell 实例
_global_shell_instance: Optional[StatefulShellTool] = None


def get_stateful_shell() -> StatefulShellTool:
    """获取全局 Stateful Shell 实例（单例模式）"""
    global _global_shell_instance
    if _global_shell_instance is None:
        _global_shell_instance = StatefulShellTool()
    return _global_shell_instance
