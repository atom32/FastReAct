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
import shutil
from typing import Optional, Dict, Any, Tuple
from queue import Queue, Empty

from ..core.tool import Tool


def _detect_shell_path() -> Tuple[str, str]:
    """
    智能检测 Shell 环境
    优先级: Unix Bash -> Windows Git Bash -> Windows PowerShell -> Windows CMD

    Returns:
        (shell_path, shell_type): shell 路径和类型标识

    Shell Type 说明:
        - bash: Unix/Linux/macOS 原生 bash
        - git-bash: Windows Git Bash (最兼容 LLM)
        - powershell: Windows PowerShell (支持 ls, cat, rm 等别名)
        - cmd: Windows CMD (最后选择，兼容性最差)
    """
    # 非 Windows 平台：直接使用 bash
    if sys.platform != "win32":
        shell_path = os.environ.get("SHELL", "/bin/bash")
        return shell_path, "bash"

    # [Windows 策略 1] 优先寻找 Git Bash (最兼容 LLM)
    # 先检查 PATH 环境变量
    git_bash_in_path = shutil.which("bash")
    if git_bash_in_path:
        return git_bash_in_path, "git-bash"

    # 再检查常见安装路径
    possible_git_bash = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Programs\Git\bin\bash.exe",
    ]
    for path in possible_git_bash:
        expanded_path = os.path.expandvars(path)
        if os.path.exists(expanded_path):
            return expanded_path, "git-bash"

    # [Windows 策略 2] 回退到 PowerShell (次兼容，支持 ls, cat, rm 等别名)
    powershell_path = shutil.which("powershell")
    if powershell_path:
        return powershell_path, "powershell"

    # [Windows 策略 3] 最后的无奈：CMD
    return "cmd.exe", "cmd"


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
        self._current_cwd: Optional[str] = None  # 追踪当前工作目录
        self._process: Optional[subprocess.Popen] = None
        self._read_thread: Optional[threading.Thread] = None
        self._output_queue: Queue = Queue()
        self._initialized = False  # 标记为未初始化

        # 智能检测 Shell 环境（支持 Git Bash, PowerShell 降级）
        if shell is None:
            self.shell_path, self.shell_type = _detect_shell_path()
        else:
            self.shell_path = shell
            # 根据 shell_path 推断类型
            if "bash" in shell.lower():
                self.shell_type = "git-bash" if sys.platform == "win32" else "bash"
            elif "powershell" in shell.lower() or shell.endswith("pwsh.exe"):
                self.shell_type = "powershell"
            elif "cmd" in shell.lower() or shell == "cmd.exe":
                self.shell_type = "cmd"
            else:
                self.shell_type = "unknown"

        # Repo Map 集成：目录变化回调
        self._on_cwd_change: Optional[callable] = None

        # 现在调用父类初始化
        super().__init__()
        self._initialized = True  # 标记为已初始化

    def _get_description(self) -> str:
        # 动态生成描述，包含当前 Shell 类型信息
        shell_hints = {
            "bash": "使用标准 Linux/Unix bash 命令（ls, grep, find, cat 等）",
            "git-bash": "Windows 环境下的 Git Bash，完全兼容 Linux 命令（ls, grep, find, cat 等）",
            "powershell": "Windows PowerShell，支持常见别名（ls, cat, rm, cp 等），但避免复杂 bash 管道和 markdown 格式",
            "cmd": "Windows CMD，使用 DOS 命令（dir, type, findstr 等），兼容性最差",
        }

        hint = shell_hints.get(self.shell_type, f"检测到 Shell 类型: {self.shell_type}")

        # Python 命令提示（平台特定）
        if sys.platform == "win32":
            python_cmd = "python"
            python_hint = "重要：在 Windows 上使用 'python' 而不是 'python3'"
        else:
            python_cmd = "python3"
            python_hint = "使用 'python3' 运行 Python 脚本"

        return f"""在持久化的 Shell 会话中执行命令

**当前环境**：
- 平台: {sys.platform}
- Shell 类型: {self.shell_type}
- Shell 路径: {self.shell_path}

**命令提示**：
- {hint}
- {python_hint}

**核心特性**：
- **状态保持**：cd、export 等命令的副作用会持续生效
- **环境保持**：环境变量在命令之间保持不变
- **超时保护**：默认 30 秒超时，防止命令挂起

**常用场景**：
- 文件系统导航：cd, ls/dir, pwd
- Python 脚本：{python_cmd} script.py
- 代码操作：git commands, npm install, make
- 测试执行：pytest, npm test
- 文件查看：cat/type, grep/findstr, head

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

        # 检测 cd 命令并更新 cwd
        old_cwd = self._current_cwd
        if command.strip().startswith("cd ") or command.strip() == "cd":
            # 尝试获取新的 cwd
            new_cwd = self._get_actual_cwd()
            if new_cwd and new_cwd != old_cwd:
                self._current_cwd = new_cwd
                # 触发回调（通知 RepoMap 更新）
                if self._on_cwd_change:
                    try:
                        if asyncio.iscoroutinefunction(self._on_cwd_change):
                            asyncio.create_task(self._on_cwd_change(new_cwd))
                        else:
                            self._on_cwd_change(new_cwd)
                    except Exception as e:
                        logger.warning(f"CWD change callback failed: {e}")

        # 添加状态信息
        cwd_display = self._current_cwd or self._get_cwd_indicator()
        return f"""📁 {cwd_display}
$ {command}

{output}
"""

    def _get_actual_cwd(self) -> Optional[str]:
        """获取实际的工作目录"""
        try:
            # 执行 pwd 命令获取当前目录
            if sys.platform == "win32":
                # Windows: 使用 cd 命令
                result, _ = self._execute_sync("cd", timeout=5)
            else:
                # Unix: 使用 pwd
                result, _ = self._execute_sync("pwd", timeout=5)

            # 解析结果（去除 ANSI 码和多余字符）
            lines = result.strip().splitlines()
            if lines:
                # 取最后一行有效输出
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith("$") and not line.startswith("["):
                        return line

            return None
        except Exception:
            return None

    def set_cwd_callback(self, callback: callable) -> None:
        """
        设置目录变化回调

        Args:
            callback: 当 cwd 变化时调用的函数，签名为 callback(new_cwd: str)
        """
        self._on_cwd_change = callback

    @property
    def current_cwd(self) -> Optional[str]:
        """获取当前工作目录"""
        return self._current_cwd or self.working_dir

    def _get_cwd_indicator(self) -> str:
        """获取当前工作目录指示器"""
        # 返回实际 cwd 或通用指示器
        return self._current_cwd or (">" if sys.platform == "win32" else "~")

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
