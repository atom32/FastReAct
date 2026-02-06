"""
UnifiedAgent REPL - 统一入口 REPL

遵循 CLAUDE.md 规则：
- No emoji in code
- No hardcoded paths
- Use existing infrastructure (events, session resume)
- Single entry point for both toC and toB

Architecture:
    User Input
        ↓
    ComplexityEvaluator (reuse)
        ↓
    Auto Router
        ↓
    ┌───┴────┬─────────┬─────────┐
    │ REACT  │ GRAPH   │ IEL     │
    │        │ AGENT   │         │
    └───┬────┴─────────┴─────────┘
        ↓
    EventManager (reuse)
        ↓
    UnifiedRenderer
        ├─ REPLRenderer (toC)
        └─ GatewayRenderer (toB)
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

# Windows UTF-8 设置
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ============================================================================
# Import existing infrastructure
# ============================================================================

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.json import JSON
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.console import Console as RichConsole

    # Sprint 3.6: 智能终端检测 - 检测是否支持ANSI颜色
    import os
    import sys

    def _supports_ansi():
        """检测终端是否支持ANSI颜色码"""
        # Windows Terminal, VS Code, PowerShell 7+ 支持ANSI
        if os.environ.get("WT_SESSION"):  # Windows Terminal
            return True
        if os.environ.get("TERM_PROGRAM"):  # VS Code, iTerm等
            return True

        # PowerShell 7+ 支持 ANSI
        if "pwsh" in os.environ.get("PSModulePath", ""):
            return True

        # 检测Windows版本（Windows 10 build 14931+ 支持ANSI）
        if sys.platform == "win32":
            try:
                import platform
                version = platform.version()
                # Windows 10 build 14931+ 支持ANSI
                if int(version.split(".")[-1]) >= 14931:
                    return True
            except:
                pass

        # 其他情况保守估计不支持
        return False

    # 根据终端支持情况初始化Console
    if _supports_ansi():
        console = RichConsole()  # 支持颜色
    else:
        console = RichConsole(force_terminal=True, legacy_windows=True)  # 兼容模式
except ImportError:
    console = None
    Live = None

# ============================================================================
# Sprint 3: Non-blocking IEL support
# ============================================================================

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
    PromptSession = None
    patch_stdout = None

# ============================================================================
# Reuse existing components
# ============================================================================

# ============================================================================
# Reuse existing components
# ============================================================================

from fastreact.observability.events import (
    LifecycleEvent,
    AssistantEvent,
    ToolEvent,
    AgentEvent,
    EventManager,
)

# ============================================================================
# LLMDriver - 统一 LLM 调用中间层
# ============================================================================

from fastreact.llm import LLMDriver, LLMDriverConfig, create_llm_driver_from_config


# ============================================================================
# Complexity Evaluator - LLM 驱动的任务复杂度评估
# ============================================================================

class ComplexityEvaluator:
    """
    评估任务复杂度，决定使用哪种执行模式

    设计原则：
    1. LLM 为主（智能评估）
    2. 硬编码为 fallback（当 LLM 不可用时）
    3. 缓存结果（避免重复调用）

    迁移到 LLMDriver:
        - 旧版: 接收 llm_client (AsyncOpenAI)
        - 新版: 接收 llm_driver (LLMDriver)
    """

    def __init__(self, llm_driver=None):
        """
        初始化评估器

        Args:
            llm_driver: LLM Driver（可选，为 None 时使用 fallback）
        """
        self.llm_driver = llm_driver
        self.cache = {}  # 查询缓存

    async def evaluate(self, query: str) -> Dict[str, Any]:
        """
        评估查询复杂度

        优先使用 LLM 评估，fallback 到硬编码规则

        Returns:
            {
                "complexity": "simple" | "medium" | "complex",
                "score": 0.0-1.0,
                "reasons": [...],
                "suggested_mode": "react" | "graph_agent" | "iel",
                "method": "llm" | "fallback"
            }
        """
        # 检查缓存
        cache_key = hash(query)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 尝试 LLM 评估
        if self.llm_driver is not None:
            try:
                result = await self._evaluate_with_llm(query)
                self.cache[cache_key] = result
                return result
            except Exception as e:
                if console:
                    console.print(f"[WARNING] LLM evaluation failed: {e}, using fallback")
                # Fallback 到硬编码规则
                pass

        # Fallback：硬编码规则评估
        result = await self._evaluate_with_rules(query)
        result["method"] = "fallback"
        self.cache[cache_key] = result
        return result

    async def _evaluate_with_llm(self, query: str) -> Dict[str, Any]:
        """
        使用 LLM 评估复杂度

        让 LLM 判断：
        1. 任务复杂度（simple/medium/complex）
        2. 需要的工具数量
        3. 是否需要多步骤执行
        4. 推荐的执行模式

        Returns:
            评估结果字典
        """
        import json

        # 构造提示词
        prompt = f"""你是一个任务复杂度评估专家。请分析用户查询的复杂度。

用户查询：{query}

请从以下维度评估：

1. **步骤数量**：需要多少个独立步骤？
   - 1-2 步：简单
   - 3-5 步：中等
   - 6+ 步：复杂

2. **依赖关系**：步骤之间是否有依赖？
   - 无依赖：简单
   - 简单依赖：中等
   - 复杂依赖（条件/循环）：复杂

3. **工具调用**：需要调用多少个工具？
   - 0-1 个：简单
   - 2-3 个：中等
   - 4+ 个：复杂

4. **不确定性**：任务是否需要动态调整？
   - 确定性：简单
   - 部分不确定：中等
   - 高度不确定：复杂

请返回 JSON 格式：
{{
    "complexity": "simple" | "medium" | "complex",
    "score": 0.0-1.0,
    "estimated_steps": 数字,
    "estimated_tools": 数字,
    "reasons": ["原因1", "原因2", ...],
    "suggested_mode": "react" | "graph_agent" | "iel"
}}

模式选择规则：
- simple → react
- medium → graph_agent
- complex → iel
"""

        try:
            # 使用 LLMDriver（统一中间层）
            messages = [
                {
                    "role": "system",
                    "content": "你是一个任务复杂度评估专家。请严格按照 JSON 格式返回结果。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # 调用 LLMDriver（自动重试、缓存、日志）
            response = await self.llm_driver.chat(
                messages=messages,
                temperature=0.3,  # 较低温度，更确定的输出
            )

            # 提取响应
            llm_output = response.content

            # 解析 JSON
            # 尝试提取 JSON（可能被包裹在 ```json 中）
            import re

            json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = llm_output.strip()

            result = json.loads(json_str)

            # 验证和标准化
            result = self._validate_and_normalize(result)

            # 添加方法标记
            result["method"] = "llm"

            return result

        except json.JSONDecodeError as e:
            if console:
                console.print(f"[WARNING] Failed to parse LLM response: {e}")
            raise
        except Exception as e:
            if console:
                console.print(f"[WARNING] LLM evaluation error: {e}")
            raise

    def _validate_and_normalize(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和标准化 LLM 返回的结果

        确保所有必需字段存在且值有效
        """
        # 验证 complexity
        valid_complexities = ["simple", "medium", "complex"]
        if "complexity" not in result or result["complexity"] not in valid_complexities:
            # 根据 score 推断
            score = result.get("score", 0.5)
            if score < 0.4:
                result["complexity"] = "simple"
            elif score < 0.7:
                result["complexity"] = "medium"
            else:
                result["complexity"] = "complex"

        # 验证 score
        if "score" not in result:
            # 根据 complexity 映射
            complexity_map = {"simple": 0.2, "medium": 0.5, "complex": 0.8}
            result["score"] = complexity_map.get(result["complexity"], 0.5)
        else:
            result["score"] = max(0.0, min(1.0, result["score"]))

        # 验证 suggested_mode
        valid_modes = ["react", "graph_agent", "iel"]
        if "suggested_mode" not in result or result["suggested_mode"] not in valid_modes:
            # 根据 complexity 推断
            mode_map = {
                "simple": "react",
                "medium": "graph_agent",
                "complex": "iel"
            }
            result["suggested_mode"] = mode_map.get(result["complexity"], "react")

        # 确保 reasons 存在
        if "reasons" not in result or not isinstance(result["reasons"], list):
            result["reasons"] = []

        # 添加默认字段
        result.setdefault("estimated_steps", 0)
        result.setdefault("estimated_tools", 0)

        return result

    async def _evaluate_with_rules(self, query: str) -> Dict[str, Any]:
        """
        使用硬编码规则评估复杂度（Fallback）

        当 LLM 不可用时使用

        Returns:
            评估结果字典
        """
        import re

        factors = []
        score = 0.0

        # 因子 1：查询长度
        if len(query) > 200:
            factors.append("长查询")
            score += 0.2

        # 因子 2：多步骤关键词
        multi_step_keywords = [
            "然后", "之后", "接着", "再", "最后",
            "首先", "其次", "最后",
            "分析", "生成", "比较", "总结", "重构"
        ]
        found_keywords = [kw for kw in multi_step_keywords if kw in query]
        if found_keywords:
            factors.append(f"多步骤关键词: {', '.join(found_keywords)}")
            score += 0.3 * len(found_keywords)

        # 因子 3：工具数量估算
        tool_keywords = {
            "搜索": "search", "查找": "search",
            "计算": "calculator", "分析": "analyze",
            "编辑": "edit", "修改": "edit",
            "创建": "create", "生成": "generate",
            "测试": "test", "运行": "run",
            "保存": "save", "写入": "write",
        }
        found_tools = set()
        for keyword, tool_type in tool_keywords.items():
            if keyword in query:
                found_tools.add(tool_type)

        if len(found_tools) >= 3:
            factors.append(f"多个工具: {', '.join(found_tools)}")
            score += 0.4

        # 因子 4：条件/循环关键词
        conditional_keywords = ["如果", "否则", "当", "直到", "循环", "每个", "对于"]
        if any(kw in query for kw in conditional_keywords):
            factors.append("包含条件或循环逻辑")
            score += 0.3

        # 因子 5：文件操作关键词
        file_keywords = ["文件", "项目", "代码", "重构", "修改所有", "批量"]
        if any(kw in query for kw in file_keywords):
            factors.append("涉及文件操作")
            score += 0.2

        # 因子 6：数字/参数关键词
        if re.search(r'\d+.*个|批量|所有', query):
            factors.append("批量操作")
            score += 0.2

        # 归一化分数
        score = min(score, 1.0)

        # 判定复杂度
        if score < 0.4:
            complexity = "simple"
            suggested_mode = "react"
        elif score < 0.7:
            complexity = "medium"
            suggested_mode = "graph_agent"
        else:
            complexity = "complex"
            suggested_mode = "iel"

        return {
            "complexity": complexity,
            "score": score,
            "estimated_steps": 0,
            "estimated_tools": len(found_tools),
            "reasons": factors,
            "suggested_mode": suggested_mode,
        }

# ============================================================================
# Unified Agent State - 使用 SESSION_RESUME 机制
# ============================================================================

class UnifiedAgentState:
    """
    统一 Agent 状态

    复用原则：
    - 使用 .fastreact/sessions/ 存储会话
    - 与 SESSION_RESUME 机制兼容
    """

    def __init__(self, session_dir: Optional[Path] = None):
        """初始化状态"""
        if session_dir is None:
            session_dir = Path.cwd() / ".fastreact" / "sessions"

        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 执行模式
        self.execution_mode = "auto"  # auto | react | graph_agent | iel

        # Agent 实例（延迟初始化）
        self.react_agent = None
        self.graph_agent = None
        self.iel_loop = None

        # 配置（使用统一的配置系统）
        self.config = {
            "auto_confirm_plan": True,
            "show_plan_details": True,
            "enable_streaming": True,
            "auto_snapshot": True,
            "git_integration": False,  # Phase 2
        }

        # 统计
        self.stats = {
            "total_queries": 0,
            "react_queries": 0,
            "graph_agent_queries": 0,
            "iel_queries": 0,
            "plan_rejections": 0,
        }

        # 对话历史（修复：SESSION_RESUME）
        self.history = []  # List of message dicts
        self.session_context = {
            "session_id": None,
            "history": [],
        }

        # 事件管理器（复用）
        self.event_manager = EventManager()

        # 当前会话文件路径（修复：避免每次创建新文件）
        self._current_session_path: Optional[Path] = None

    def get_session_path(self) -> Path:
        """获取当前会话文件路径（复用现有路径或创建新路径）"""
        if self._current_session_path:
            return self._current_session_path

        # 创建新路径（仅首次）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_session_path = self.session_dir / f"unified_{timestamp}.json"
        return self._current_session_path

    def save_session(self) -> Optional[Path]:
        """保存会话到文件（更新同一文件）"""
        import json

        session_path = self.get_session_path()  # 复用现有路径

        # 修复：保存对话历史
        session_data = {
            "timestamp": datetime.now().isoformat(),
            "execution_mode": self.execution_mode,
            "stats": self.stats.copy(),
            "config": self.config.copy(),
            "history": self.history,  # ← 修复：保存历史
            "session_id": self.session_context.get("session_id"),
        }

        try:
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            return session_path

        except Exception as e:
            if console:
                console.print(f"[ERROR] Failed to save session: {e}")
            return None

    def load_session(self, session_path: Path) -> bool:
        """从文件加载会话"""
        import json

        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            self.execution_mode = session_data.get("execution_mode", "auto")
            self.stats.update(session_data.get("stats", {}))
            self.config.update(session_data.get("config", {}))

            # 修复：恢复对话历史
            self.history = session_data.get("history", [])
            self.session_context["history"] = self.history.copy()
            self.session_context["session_id"] = session_data.get("session_id")

            # 修复：设置当前会话路径，后续保存将更新此文件
            self._current_session_path = session_path

            return True

        except Exception as e:
            if console:
                console.print(f"[ERROR] Failed to load session: {e}")
            return False

# ============================================================================
# Unified REPL
# ============================================================================

class UnifiedAgentREPL:
    """
    统一 Agent REPL

    设计原则：
    1. 统一入口（toC 和 toB 使用相同逻辑）
    2. 自动路由（根据复杂度选择模式）
    3. 事件驱动（使用 EventManager）
    4. 状态持久化（使用 SESSION_RESUME）
    """

    def __init__(self, session_to_load: Optional[Path] = None):
        """初始化 REPL"""
        # 状态（复用 SESSION_RESUME 机制）
        self.state = UnifiedAgentState()

        # 运行时状态
        self.running = True
        self.session_to_load = session_to_load

        # 评估器（延迟初始化，需要 llm_client）
        self.complexity_evaluator = None

        # Console
        self.console = console

        # 强制文本模式标志（用于不支持ANSI的终端）
        self.force_text_mode = os.environ.get("FASTREACT_TEXT_MODE", "").lower() in ("1", "true", "yes")

        # 命令映射
        self.commands = {
            'help': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'run': self.cmd_run,
            'mode': self.cmd_mode,
            'stats': self.cmd_stats,
            'clear': self.cmd_clear,
            'history': self.cmd_history,
            'save': self.cmd_save,
            'tools': self.cmd_tools,  # 新增：列出所有工具
        }

    # ========================================================================
    # 主循环
    # ========================================================================

    async def run_async(self):
        """运行 REPL"""
        self.print_welcome()

        # 加载会话
        if self.session_to_load:
            if self.state.load_session(self.session_to_load):
                self.print_success(f"会话已加载: {self.session_to_load.name}")

        # 主循环
        while self.running:
            try:
                # 读取命令
                command = input(self.get_prompt())

                if not command.strip():
                    continue

                # 执行命令（检查返回值，False 表示退出）
                should_continue = await self.execute_command(command)
                if not should_continue:
                    break

            except EOFError:
                break
            except KeyboardInterrupt:
                print()

    def get_prompt(self) -> str:
        """获取提示符（无 emoji）"""
        mode_display = {
            "auto": "[AUTO]",
            "react": "[REACT]",
            "graph_agent": "[GRAPH]",
            "iel": "[IEL]",
        }

        mode_tag = mode_display.get(self.state.execution_mode, "[UNKNOWN]")
        query_count = self.state.stats["total_queries"]

        return f"FastReAct{mode_tag} Q{query_count} >> "

    def print_welcome(self):
        """打印欢迎信息（无 emoji，跨平台兼容）"""
        if self.console:
            self.console.print()
            self.console.print(Panel(
                """FastReAct UnifiedAgent REPL

[Features]
- Automatic task complexity evaluation
- GraphAgent auto-generates execution plans
- User confirmation before execution
- IEL snapshots and auto-rollback

Type /help for commands""",
                title="Welcome",
                border_style="cyan"
            ))
            self.console.print()
        else:
            print()
            print("=" * 60)
            print("FastReAct UnifiedAgent REPL")
            print("=" * 60)
            print("Unified REPL: Auto-planning + User confirmation + Safe execution")
            print("Type /help for commands")
            print()

    async def execute_command(self, command: str) -> bool:
        """执行命令"""
        command = command.strip()

        if not command:
            return True

        # 快捷命令
        if command.startswith('/'):
            return await self._handle_quick_command(command)

        # 解析命令
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 执行命令
        if cmd in self.commands:
            handler = self.commands[cmd]
            result = await handler(args) if asyncio.iscoroutinefunction(handler) else handler(args)
            return result if isinstance(result, bool) else True
        else:
            # 当作查询执行
            return await self.cmd_run(command)

    async def _handle_quick_command(self, command: str) -> bool:
        """处理快捷命令"""
        cmd = command[1:].strip().lower()

        mode_map = {
            "react": "react",
            "graph": "graph_agent",
            "iel": "iel",
            "auto": "auto",
        }

        # Sprint 4: Task Chaining Commands
        if cmd.startswith("chain "):
            # /chain "Task A" -> "Task B" -> "Task C"
            return await self._cmd_chain(command[7:].strip())

        if cmd == "tasks":
            # /tasks - Show pending tasks
            return await self._cmd_tasks()

        if cmd == "tools":
            # /tools - List all available tools
            return await self.cmd_tools("")

        # Mode switching commands
        if cmd in mode_map:
            self.state.execution_mode = mode_map[cmd]
            self.print_success(f"Switched to {mode_map[cmd].upper()} mode")
        else:
            self.print_error(f"Unknown command: /{cmd}")
            return self.cmd_help("")

        return True

    # ========================================================================
    # 命令处理器
    # ========================================================================

    def cmd_help(self, args: str) -> bool:
        """显示帮助（使用 Rich 表格格式化）"""
        if self.console:
            self.console.print()

            # Basic Commands Table
            basic_table = Table(title="[bold yellow]Basic Commands[/bold yellow]", show_header=True)
            basic_table.add_column("[cyan]Command[/cyan]", style="cyan", width=25)
            basic_table.add_column("[green]Description[/green]", style="green")

            basic_commands = [
                ("run <query>", "Execute query (auto mode selection)"),
                ("mode <name>", "Switch mode (auto/react/graph/iel)"),
                ("stats", "Show session statistics"),
                ("save", "Save current session"),
                ("history [n]", "Show last n sessions (default: 10)"),
                ("help", "Show this help message"),
                ("exit/quit", "Exit and save session"),
            ]

            # Sprint 4: Task Chaining Commands
            chaining_commands = [
                ("/chain \"A\" -> \"B\"", "Create task chain (Sprint 4)"),
                ("/tasks", "Show pending tasks (Sprint 4)"),
            ]

            for cmd, desc in basic_commands:
                basic_table.add_row(cmd, desc)

            self.console.print(basic_table)
            self.console.print()

            # Sprint 4: Task Chaining Commands Table
            chaining_table = Table(title="[bold yellow]Task Chaining Commands (Sprint 4)[/bold yellow]", show_header=True)
            chaining_table.add_column("[cyan]Command[/cyan]", style="cyan", width=30)
            chaining_table.add_column("[green]Description[/green]", style="green")

            chaining_commands = [
                ("/chain \"A\" -> \"B\"", "Create task workflow"),
                ("/tasks", "Show pending tasks"),
            ]

            for cmd, desc in chaining_commands:
                chaining_table.add_row(cmd, desc)

            self.console.print(chaining_table)
            self.console.print()

            # Shortcut Commands Table
            shortcut_table = Table(title="[bold yellow]Mode Switching[/bold yellow]", show_header=True)
            shortcut_table.add_column("[cyan]Command[/cyan]", style="cyan", width=25)
            shortcut_table.add_column("[green]Description[/green]", style="green")

            shortcut_commands = [
                ("/react", "Switch to ReAct mode"),
                ("/graph", "Switch to GraphAgent mode"),
                ("/iel", "Switch to IEL mode"),
                ("/auto", "Switch to auto mode"),
            ]

            for cmd, desc in shortcut_commands:
                shortcut_table.add_row(cmd, desc)

            self.console.print(shortcut_table)
            self.console.print()

            # Execution Modes Info
            modes_table = Table(title="[bold yellow]Execution Modes[/bold yellow]", show_header=True)
            modes_table.add_column("[cyan]Mode[/cyan]", style="cyan", width=15)
            modes_table.add_column("[green]Description[/green]", style="green")

            modes_info = [
                ("auto", "Automatically select best mode"),
                ("react", "ReAct: Thought + Action loop"),
                ("graph", "GraphAgent: Plan then execute"),
                ("iel", "IEL: Safe execution with snapshots"),
            ]

            for mode, desc in modes_info:
                modes_table.add_row(mode, desc)

            self.console.print(modes_table)
            self.console.print()

            # Tips
            tips_panel = Panel(
                "[bold cyan]Tips:[/bold cyan]\n"
                "- Use [yellow]auto mode[/yellow] for intelligent mode selection\n"
                "- Type [yellow]run your query[/yellow] to start a task\n"
                "- Sessions are auto-saved on exit\n"
                "- Use [yellow]/react[/yellow], [yellow]/graph[/yellow] for quick mode switching",
                title="[bold magenta]Quick Tips[/bold magenta]",
                border_style="magenta"
            )
            self.console.print(tips_panel)
            self.console.print()

        else:
            print("\nAvailable Commands:")
            print("=" * 60)
            print("  run <query>    - Execute query")
            print("  mode <name>    - Switch mode")
            print("  stats          - Show statistics")
            print("  save           - Save session")
            print("  history [n]    - Show history")
            print("  help           - Show help")
            print("  exit/quit      - Exit")
            print()
            print("Shortcuts:")
            print("  /react, /graph, /iel, /auto")
            print()

        return True

    def cmd_exit(self, args: str) -> bool:
        """退出（保存会话）"""
        # 自动保存会话
        session_path = self.state.save_session()

        if self.console:
            if session_path:
                self.console.print(f"\n[bold cyan]Session saved: {session_path.name}[/bold cyan]")
            self.console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
        else:
            print("\nGoodbye!\n")
        return False

    async def cmd_mode(self, args: str) -> bool:
        """切换模式"""
        mode = args.strip().lower()

        valid_modes = ["auto", "react", "graph_agent", "iel"]

        if mode not in valid_modes:
            self.print_error(f"无效模式: {mode}")
            self.print_output(f"可用模式: {', '.join(valid_modes)}")
            return True

        self.state.execution_mode = mode
        self.print_success(f"切换到 {mode.upper()} 模式")

        return True

    async def cmd_stats(self, args: str) -> bool:
        """显示统计"""
        stats = self.state.get_stats()

        if self.console:
            table = Table(title="Session Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            for key, value in stats.items():
                table.add_row(key.replace("_", " ").title(), str(value))

            self.console.print(table)
        else:
            print("\nSession Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        return True

    async def cmd_save(self, args: str) -> bool:
        """保存会话"""
        session_path = self.state.save_session()

        if session_path:
            self.print_success(f"会话已保存: {session_path}")
        else:
            self.print_error("保存会话失败")

        return True

    # ========================================================================
    # Tool Listing Command
    # ========================================================================

    async def cmd_tools(self, args: str) -> bool:
        """列出所有可用工具（包括MCP工具）"""
        self.print_info("正在获取工具列表...")

        # 获取当前agent
        agent = self._get_current_agent()
        if not agent:
            self.print_error("无法获取当前agent")
            return True

        # 获取所有工具
        tools_dict = agent.tools if hasattr(agent, 'tools') else {}

        if not tools_dict:
            self.print_warning("未找到任何工具")
            return True

        # 分类工具
        builtin_tools = []
        mcp_tools = {}

        for tool_name, tool in tools_dict.items():
            tool_info = {
                "name": tool.name,
                "description": tool.description[:80] + "..." if len(tool.description) > 80 else tool.description,
                "group": getattr(tool, 'group', 'builtin')
            }

            if tool_info["group"] == "mcp":
                # 按MCP服务器分类
                server = getattr(tool, 'server', 'unknown')
                if server not in mcp_tools:
                    mcp_tools[server] = []
                mcp_tools[server].append(tool_info)
            else:
                builtin_tools.append(tool_info)

        # 显示统计
        total_builtin = len(builtin_tools)
        total_mcp = sum(len(tools) for tools in mcp_tools.values())
        total = total_builtin + total_mcp

        print()
        print(f"[统计] 总计 {total} 个工具")
        print(f"  - 内建工具: {total_builtin}")
        print(f"  - MCP工具: {total_mcp}")
        print()

        # 显示内建工具
        if builtin_tools:
            print(f"[内建工具] ({total_builtin}个)")
            for tool in builtin_tools[:10]:  # 只显示前10个
                print(f"  - {tool['name']}")
            if len(builtin_tools) > 10:
                print(f"  ... 还有 {len(builtin_tools) - 10} 个")
            print()

        # 显示MCP工具
        if mcp_tools:
            for server, tools in mcp_tools.items():
                print(f"[{server}] ({len(tools)}个)")
                for tool in tools[:10]:  # 只显示前10个
                    print(f"  - {tool['name']}")
                if len(tools) > 10:
                    print(f"  ... 还有 {len(tools) - 10} 个")
                print()

        return True

    # ========================================================================
    # Sprint 4: Task Chaining Commands
    # ========================================================================

    async def _cmd_chain(self, args: str) -> bool:
        """
        Handle /chain command - Create task chain

        Usage: /chain "Task A" -> "Task B" -> "Task C"

        Example:
            /chain "Write hello.py" -> "Run hello.py" -> "Delete hello.py"
        """
        # Parse tasks separated by ->
        tasks = [t.strip() for t in args.split("->") if t.strip()]

        if len(tasks) < 2:
            self.print_error("Usage: /chain \"Task A\" -> \"Task B\" -> \"Task C\"")
            self.print_info("Example: /chain \"Write hello.py\" -> \"Run hello.py\" -> \"Delete hello.py\"")
            return True

        # Get current agent based on execution mode
        agent = self._get_current_agent()
        if not agent:
            self.print_error("Agent not initialized")
            self.print_info("Try running a query first to initialize the agent")
            return True

        scheduler = agent.get_task_scheduler()
        if not scheduler:
            self.print_error("Task Scheduler not available")
            self.print_info("Enable reactive loop: config['reactive_loop']['enabled'] = True")
            return True

        # Schedule tasks
        self.print_info(f"[CHAIN] Creating workflow with {len(tasks)} tasks...")

        for i, task in enumerate(tasks):
            task_id = await agent.schedule_task(
                instruction=task,
                task_type="chain_step",
                priority=100 - i * 10  # Decreasing priority
            )

            if self.console:
                self.console.print(f"  [dim]Step {i+1}: {task}[/]")

        self.print_success(f"[CHAIN] {len(tasks)} tasks queued")

        # Start first task
        self.print_info(f"[CHAIN] Starting task 1/{len(tasks)}: {tasks[0]}")

        return await self.cmd_run(tasks[0])

    async def _cmd_tasks(self) -> bool:
        """
        Handle /tasks command - Show pending tasks

        Usage: /tasks

        Displays all pending tasks in the scheduler queue.
        """
        # Get current agent based on execution mode
        agent = self._get_current_agent()
        if not agent:
            self.print_error("Agent not initialized")
            self.print_info("Try running a query first to initialize the agent")
            return True

        scheduler = agent.get_task_scheduler()
        if not scheduler:
            self.print_error("Task Scheduler not available")
            return True

        # Get scheduler status
        status = scheduler.get_status()

        if self.console:
            self.console.print()

            if status['pending_count'] == 0:
                self.print_info("No pending tasks in queue")
            else:
                # Create table for pending tasks
                table = Table(title=f"[bold yellow]Pending Tasks ({status['pending_count']})[/bold yellow]")
                table.add_column("[cyan]Task ID[/cyan]", style="cyan", width=20)
                table.add_column("[green]Instruction[/green]", style="green")
                table.add_column("[yellow]Priority[/yellow]", style="yellow", width=10)

                # Get pending tasks
                temp_context = type('obj', (object,), {'messages': [], 'metadata': {}})()

                for i in range(min(status['pending_count'], 10)):  # Max 10 tasks shown
                    task = await scheduler.get_next_task(temp_context)
                    if task:
                        table.add_row(
                            task.task_id,
                            task.instruction[:50] + ("..." if len(task.instruction) > 50 else ""),
                            str(task.priority)
                        )

                self.console.print(table)

        # Show completed count
        if status['completed_count'] > 0:
            self.print_info(f"Completed: {status['completed_count']} tasks")

        return True

    def _get_current_agent(self):
        """
        Get current active agent based on execution mode
        Creates agent lazily if not yet initialized

        Returns:
            Current agent instance (react_agent, graph_agent, or iel_loop)
        """
        mode = self.state.execution_mode

        if mode == "react" or mode == "auto":
            return self._get_or_create_react_agent()
        elif mode == "graph_agent":
            # Note: graph_agent is created async in _get_or_create_graph_agent
            return self.state.graph_agent
        elif mode == "iel":
            return self.state.iel_loop
        else:
            return None

    # ========================================================================
    # End Sprint 4 Commands
    # ========================================================================

    async def cmd_history(self, args: str) -> bool:
        """显示历史"""
        limit = int(args) if args.isdigit() else 10

        # 列出会话文件
        session_files = sorted(
            self.state.session_dir.glob("unified_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]

        if not session_files:
            self.print_output("No history yet")
        else:
            if self.console:
                table = Table(title=f"Last {len(session_files)} Sessions")
                table.add_column("File")
                table.add_column("Time")
                table.add_column("Queries")

                for session_file in session_files:
                    import json

                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        table.add_row(
                            session_file.name,
                            data.get("timestamp", "")[:19],
                            str(data.get("stats", {}).get("total_queries", 0))
                        )
                    except:
                        pass

                self.console.print(table)
            else:
                print(f"\nLast {len(session_files)} sessions:")
                for session_file in session_files:
                    print(f"  {session_file.name}")

        return True

    def cmd_clear(self, args: str) -> bool:
        """清屏"""
        if self.console:
            self.console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
        return True

    # ========================================================================
    # Sprint 3: Non-blocking IEL (Dual-Track REPL)
    # ========================================================================

    async def _run_graph_agent_non_blocking(self, query: str) -> bool:
        """
        Phase 4: 非阻塞GraphAgent执行 - 真正的双轨并发架构

        Sprint 3.6: 添加ContextMonitor和完整结果显示，与阻塞模式UI对齐

        双轨架构：
        - Agent轨道：执行计划，每步yield控制权
        - 用户轨道：异步输入，随时可以干预
        - 使用 asyncio.gather 实现真正的并发
        """
        if not PROMPT_TOOLKIT_AVAILABLE:
            self.print_error("prompt_toolkit not available, falling back to blocking mode")
            return await self._run_graph_agent(query)

        import asyncio
        import time
        from fastreact.graph.runtime import ToolRuntime, ExecutionConfig, ExecutionStrategy
        from fastreact.graph.runtime import StepEvent

        self.state.stats["graph_agent_queries"] += 1

        if self.console:
            self.console.print(f"[cyan][GRAPHAGENT 模式 (Non-blocking IEL)][/cyan]")
            self.console.print()

        try:
            # 创建干预队列
            intervention_queue = asyncio.Queue()

            # Sprint 3.6: 显示初始 ContextMonitor（简化版，文本模式）
            from fastreact.context import get_context_monitor
            monitor_initial = get_context_monitor()
            # 使用print而不是console.print避免ANSI问题
            print(f"\n[Context Monitor] {monitor_initial.get_status_text()}")

            # 生成执行计划
            agent = await self._get_or_create_graph_agent()

            # Sprint 3.6: 添加计划生成提示（避免看起来"卡住"）
            if self.console:
                with self.console.status("[bold cyan]Planning execution...[/bold cyan]", spinner="dots2"):
                    plan = await agent._generate_plan(query)
            else:
                plan = await agent._generate_plan(query)

            # 显示执行计划
            self._display_plan(plan)

            # 用户确认
            if not self._confirm_plan():
                self.print_info("Execution cancelled by user")
                return True

            # Sprint 3.5: 加载工具策略配置
            from fastreact.tools.sprint35_policy_config import get_sprint35_policy
            from fastreact.core.tool_policy import ToolPolicy

            tool_policy_config = get_sprint35_policy()
            tool_policy = ToolPolicy(tool_policy_config)

            # Sprint 3.5: 创建审批队列
            approval_queue = asyncio.Queue()

            # 创建Runtime（注入策略和审批队列）
            runtime = ToolRuntime(
                config=ExecutionConfig(
                    strategy=ExecutionStrategy.LEVEL_BASED,
                    max_parallel=3,
                    timeout=300.0,
                    continue_on_error=False,
                    # Sprint 3.5: 注入策略系统
                    tool_policy=tool_policy,
                    approval_enabled=True,
                    approval_queue=approval_queue,
                ),
                state=None,  # Create new GraphState for this execution
            )

            # 转换计划为图
            graph = agent._plan_to_graph(plan)

            # Sprint 3.6: 显示执行开始消息
            if self.console:
                self.console.print()
                self.print_info("[bold green]执行中...[/bold green] (Type 'stop' to interrupt)")
                self.console.print("")

            # 运行状态标志
            is_running = True
            start_time = time.time()

            # ====================================================================
            # Track 2: Agent执行任务（消费者生成器）
            # ====================================================================
            async def agent_task():
                # 用于收集结果
                """Agent轨道：执行并yield事件"""
                nonlocal is_running
                final_result = None
                all_results = []
                completed_nodes = 0
                failed_nodes = 0
                total_nodes = len(graph.nodes)

                try:
                    async for event in runtime.execute_steppable(graph, initial_inputs=None, intervention_queue=intervention_queue):
                        if not is_running:
                            # User stopped execution
                            break

                        # Sprint 3.5: 处理审批请求事件
                        if event.type == "APPROVAL_REQUIRED":
                            # 显示风险提示
                            risk_color = {
                                "MEDIUM": "yellow",
                                "HIGH": "red",
                                "CRITICAL": "bold red"
                            }.get(event.risk_level, "yellow")

                            if self.console:
                                self.console.print(f"[{risk_color}][APPROVAL] {event.tool_name} ({event.risk_level} risk)[/{risk_color}]")
                                self.console.print(f"[dim]Node: {event.node_id}[/dim]")
                                if event.tool_params:
                                    self.console.print(f"[dim]Params: {event.tool_params}[/dim]")
                            else:
                                print(f"[APPROVAL] {event.tool_name} ({event.risk_level} risk)")
                                print(f"Node: {event.node_id}")

                            # 获取用户输入（使用同步input在线程池中运行）
                            import asyncio
                            try:
                                user_input = await asyncio.to_thread(
                                    input,
                                    f"Allow {event.tool_name}? [Y/n/stop]: "
                                )
                            except (EOFError, KeyboardInterrupt):
                                user_input = "n"  # 默认拒绝

                            # 处理用户决定
                            if user_input.lower() in ["y", "yes"]:
                                await approval_queue.put("allow")
                                if self.console:
                                    self.console.print("[green][OK] Approved[/green]")
                            elif user_input.lower() in ["n", "no"]:
                                await approval_queue.put("deny")
                                if self.console:
                                    self.console.print("[yellow][DENIED] Operation denied[/yellow]")
                            elif user_input.lower() in ["stop", "abort"]:
                                await approval_queue.put("stop")
                                if self.console:
                                    self.console.print("[red][STOPPED] Execution stopped[/red]")
                                break
                            else:
                                await approval_queue.put("deny")
                                if self.console:
                                    self.console.print("[yellow][DENIED] Invalid input, denied[/yellow]")

                            continue  # 处理完审批请求，继续下一个事件

                        # Sprint 3.6: 收集详细结果用于统一显示
                        if event.type == "STEP_COMPLETE":
                            completed_nodes += 1
                            if event.result:
                                all_results.append(event.result)
                                # 最后一个节点的结果作为最终结果
                                final_result = event.result.get('result') if isinstance(event.result, dict) else event.result

                        # 渲染事件到屏幕
                        self._render_step_event(event)

                    # Sprint 3.6: 执行完成 - 显示最终统计和结果（文本模式）
                    execution_time = time.time() - start_time

                    # 显示执行统计
                    print("")
                    print(f"[执行统计] 总节点: {total_nodes}, 完成: {completed_nodes}, 失败: {failed_nodes}, 耗时: {execution_time:.2f}s")

                    # 显示最终结果
                    if final_result or all_results:
                        print(f"\n[最终答案]\n{final_result or str(all_results[-1]) if all_results else '执行完成'}\n")

                except Exception as e:
                    # Agent execution error
                    self._render_step_event(StepEvent(
                        type="ERROR",
                        node_id="agent",
                        tool_name="agent",
                        message=f"Execution failed: {str(e)}"
                    ))
                finally:
                    is_running = False

            # ====================================================================
            # Track 1: 用户输入任务（生产者指令）
            # ====================================================================
            async def user_input_task():
                """用户轨道：异步输入，始终活跃"""
                prompt_session = PromptSession("FastReAct[interrupt] >> ")

                while is_running:
                    try:
                        # patch_stdout 确保日志不会打断输入行
                        with patch_stdout():
                            user_input = await prompt_session.prompt_async("")

                        if not user_input or not user_input.strip():
                            continue

                        # 将用户输入放入干预队列
                        await intervention_queue.put(user_input)

                        # 检查退出命令 - 不要立即break，等待agent处理
                        if user_input.strip().lower() in ["exit", "quit", "stop", "abort"]:
                            if self.console:
                                self.console.print("[yellow][INTERRUPT] Stop command sent. Waiting for agent to process...[/yellow]")
                            # Don't break - let agent process the stop command and set is_running=False
                            # Just continue checking is_running in the while loop condition

                    except (EOFError, KeyboardInterrupt):
                        # EOF in non-interactive mode - wait for agent to complete
                        # Don't exit, just sleep and check is_running again
                        await asyncio.sleep(0.1)
                        continue
                    except Exception:
                        # Input error - don't exit, just wait for agent
                        await asyncio.sleep(0.1)
                        continue

                # User input loop ended (agent completed)

            # ====================================================================
            # Phase 4 核心：并发启动双轨
            # ====================================================================

            # 创建任务列表
            tasks = [
                asyncio.create_task(agent_task(), name="agent"),
                asyncio.create_task(user_input_task(), name="input"),
            ]

            # 显示开始信息
            if self.console:
                self.console.print("[cyan][bold]Non-blocking IEL mode activated[/bold][/cyan]")
                self.console.print("[dim]Input bar is always active. Type 'stop' to interrupt.[/dim]")
                self.console.print("")

            # 并发执行，等待任意一个完成
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            # 取消未完成的任务
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 显示完成信息
            self.print_success("[bold green]执行完成[/bold green]")

            return True

        except Exception as e:
            self.print_error(f"GraphAgent non-blocking execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _render_step_event(self, event: StepEvent):
        """
        Phase 4: 漂亮的事件渲染

        Args:
            event: 步进执行事件
        """
        # 检查是否强制使用文本模式（环境变量或终端不支持）
        if self.force_text_mode or not self.console:
            # 简单文本模式
            if event.type == "STEP_START":
                print(f"[START] {event.message}")
            elif event.type == "STEP_COMPLETE":
                status_symbol = "[OK]" if event.status == "completed" else "[FAIL]"
                print(f"{status_symbol} {event.message}")
            elif event.type == "INTERVENTION":
                print(f"[INTERRUPT] {event.message}")
            elif event.type == "ERROR":
                print(f"[ERROR] {event.message}")
            return

        # Rich UI 模式 - 使用漂亮的格式（Sprint 3.6: 添加渲染失败回退）
        try:
            if event.type == "STEP_START":
                from rich.text import Text
                self.console.print(Text("➤ ", style="bold blue") + Text(event.message, style="dim"))

            elif event.type == "STEP_COMPLETE":
                if event.status == "completed":
                    from rich.text import Text
                    self.console.print(Text("✔ ", style="bold green") + Text(event.message, style="green"))
                else:
                    from rich.text import Text
                    self.console.print(Text("✖ ", style="bold red") + Text(event.message, style="red"))

            elif event.type == "INTERVENTION":
                from rich.text import Text
                self.console.print(Text("[INTERRUPT] ", style="bold yellow") + Text(f"{event.message}", style="yellow"))

            elif event.type == "ERROR":
                from rich.text import Text
                self.console.print(Text("[ERROR] ", style="bold red") + Text(event.message, style="red"))
        except Exception:
            # Sprint 3.6: Rich渲染失败（终端不支持ANSI），回退到文本模式
            if event.type == "STEP_START":
                print(f"[START] {event.message}")
            elif event.type == "STEP_COMPLETE":
                status_symbol = "[OK]" if event.status == "completed" else "[FAIL]"
                print(f"{status_symbol} {event.message}")
            elif event.type == "INTERVENTION":
                print(f"[INTERRUPT] {event.message}")
            elif event.type == "ERROR":
                print(f"[ERROR] {event.message}")

    # ========================================================================
    # 核心命令：RUN
    # ========================================================================

    async def cmd_run(self, query: str) -> bool:
        """执行查询（智能模式选择）"""
        try:
            # 保存查询到历史（使用事件系统）
            event = LifecycleEvent(
                phase="start",
                metadata={"query": query}
            )
            await self.state.event_manager.emit(event)

            self.state.stats["total_queries"] += 1

            # 用户友好度改进：早期回应机制
            # 检测是否为纯聊天查询（无需工具），直接回答
            chat_response = self._try_chat_only_response(query)
            if chat_response:
                # 直接回答，跳过复杂度评估和模式选择
                return await self._show_direct_answer(query, chat_response)

            # 自动模式选择
            if self.state.execution_mode == "auto":
                # 确保 evaluator 已初始化
                evaluator = self._get_or_create_evaluator()

                evaluation = await evaluator.evaluate(query)

                self._show_complexity_evaluation(evaluation)

                # 用户友好度改进：显示早期回应
                self._show_early_response(query, evaluation)

                # 选择模式
                mode = evaluation["suggested_mode"]
            else:
                mode = self.state.execution_mode

            # 执行
            if mode == "react":
                return await self._run_react(query)
            elif mode == "graph_agent":
                # Sprint 3: Check if we should use non-blocking IEL mode
                # For now, use non-blocking mode when prompt_toolkit is available
                # TODO: Add --step-mode flag to control this behavior
                if PROMPT_TOOLKIT_AVAILABLE and os.environ.get("FASTREACT_STEPPABLE", "").lower() in ["1", "true", "yes"]:
                    return await self._run_graph_agent_non_blocking(query)
                else:
                    return await self._run_graph_agent(query)
            elif mode == "iel":
                return await self._run_iel(query)
            else:
                self.print_error(f"未知模式: {mode}")
                return True

        except Exception as e:
            self.print_error(str(e))
            import traceback
            traceback.print_exc()
            return True

    def _try_chat_only_response(self, query: str) -> Optional[str]:
        """
        尝试直接回答纯聊天查询（无需工具）

        用户友好度改进：对于简单的问答，直接返回响应，跳过复杂流程

        Args:
            query: 用户查询

        Returns:
            直接回答内容，如果需要工具则返回None
        """
        query_lower = query.lower().strip()

        # 简单问候
        greetings = ["你好", "嗨", "hello", "hi", "早上好", "下午好", "晚上好"]
        if any(g in query_lower for g in greetings):
            return "你好！有什么可以帮您的吗？"

        # 简单的自我介绍
        intros = ["你是谁", "介绍一下自己", "what are you", "who are you"]
        if any(p in query_lower for p in intros):
            return "我是 FastReAct，一个智能代理助手，可以帮助您执行任务、编写代码、分析文件等。"

        # 询问能力
        capabilities = ["你能做什么", "你会什么", "help", "帮助"]
        if any(p in query_lower for p in capabilities):
            return "我可以帮您：\n- 编写和运行代码\n- 读取和分析文件\n- 执行系统命令\n- 搜索信息\n- 复杂的推理和规划任务\n\n直接告诉我您需要什么帮助！"

        # 需要工具的查询，返回None让系统处理
        return None

    async def _show_direct_answer(self, query: str, answer: str) -> bool:
        """
        显示直接回答（无需调用LLM）

        Args:
            query: 用户查询
            answer: 直接回答内容
        """
        # 显示回答
        if self.console:
            self.console.print()
            panel = Panel(
                answer,
                title="[bold cyan][FAST RESPONSE][/bold cyan]",
                border_style="cyan",
                padding=(0, 1)
            )
            self.console.print(panel)
        else:
            print(f"\n[FAST RESPONSE]\n{answer}\n")

        # 保存到历史
        self.state.history.append({"role": "user", "content": query})
        self.state.history.append({"role": "assistant", "content": answer})
        self.state.session_context["history"] = self.state.history.copy()

        return True

    def _show_early_response(self, query: str, evaluation: Dict[str, Any]):
        """
        显示早期回应（Claude Code风格）

        在执行前给用户一个简单的工作提示，提升用户体验

        Args:
            query: 用户查询
            evaluation: 复杂度评估结果
        """
        if not self.console:
            return

        import re
        query_lower = query.lower()

        # 根据查询内容生成早期回应
        response = None

        # 文件操作
        if any(word in query_lower for word in ["读取", "查看", "显示", "read", "show", "cat"]):
            response = "[dim]正在读取文件...[/dim]"
        elif any(word in query_lower for word in ["创建", "写入", "生成", "create", "write", "generate"]):
            response = "[dim]正在为您创建...[/dim]"
        elif any(word in query_lower for word in ["删除", "移除", "delete", "remove"]):
            response = "[dim]正在删除...[/dim]"

        # 代码执行
        elif any(word in query_lower for word in ["运行", "执行", "run", "execute"]):
            response = "[dim]正在执行...[/dim]"
        elif any(word in query_lower for word in ["计算", "算", "calculate", "compute"]):
            response = "[dim]正在计算...[/dim]"

        # 搜索/查找
        elif any(word in query_lower for word in ["搜索", "查找", "search", "find"]):
            response = "[dim]正在搜索...[/dim]"

        # 分析任务
        elif any(word in query_lower for word in ["分析", "analyze", "analysis"]):
            response = "[dim]正在分析...[/dim]"

        # 默认回应
        if not response:
            mode = evaluation.get("suggested_mode", "react")
            if mode == "graph_agent":
                response = "[dim]正在为您规划任务...[/dim]"
            else:
                response = "[dim]正在处理...[/dim]"

        # 显示早期回应（在同一行，不换行）
        self.console.print(response, end="")

    def _show_complexity_evaluation(self, evaluation: Dict[str, Any]):
        """
        显示复杂度评估（使用 Rich 格式化）

        Args:
            evaluation: 复杂度评估结果字典
        """
        if not self.console:
            return

        complexity = evaluation["complexity"].upper()
        score = evaluation["score"]
        reasons = evaluation.get("reasons", [])
        mode = evaluation["suggested_mode"].upper()
        method = evaluation.get("method", "unknown")

        # Color scheme based on complexity
        colors = {
            "SIMPLE": ("bright_green", "green"),
            "MEDIUM": ("bright_yellow", "yellow"),
            "COMPLEX": ("bright_red", "red"),
        }
        title_color, border_color = colors.get(complexity, ("white", "white"))

        # Method label color
        method_color = "cyan" if method == "llm" else "dim"

        # Build evaluation content
        content = []

        # Complexity with score
        content.append(f"[{title_color} bold]Complexity:[/] {complexity} (score: {score:.2f})")

        # Recommended mode
        content.append(f"[cyan bold]Recommended Mode:[/] {mode}")

        # Evaluation method
        content.append(f"[{method_color}]Evaluation Method:[/] {method.upper()}")

        # LLM-specific info
        if method == "llm":
            estimated_steps = evaluation.get("estimated_steps", 0)
            estimated_tools = evaluation.get("estimated_tools", 0)

            if estimated_steps > 0:
                content.append(f"[dim]Estimated Steps:[/] {estimated_steps}")

            if estimated_tools > 0:
                content.append(f"[dim]Estimated Tools:[/] {estimated_tools}")

        # Reasons (if available)
        if reasons:
            content.append(f"\n[dim]Reasons:[/]")
            for reason in reasons:
                content.append(f"  [dim]-[/] {reason}")

        # Create panel
        panel = Panel(
            "\n".join(content),
            title=f"[Task Evaluation] - {complexity}",
            title_align="left",
            border_style=border_color,
            padding=(0, 1)
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    # ========================================================================
    # ReAct 模式
    # ========================================================================

    async def _run_react(self, query: str) -> bool:
        """
        ReAct 模式执行（带实时进度显示）

        Sprint 2 Enhancement: Live status updates with spinner and ContextMonitor
        """
        self.state.stats["react_queries"] += 1

        if self.console:
            self.console.print(f"[yellow][REACT 模式][/yellow]")
            self.console.print()

        # ====================================================================
        # Step 1: Thinking - Analyze query and plan execution
        # ====================================================================

        if self.console:
            with self.console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
                # Brief pause to show the spinner
                await asyncio.sleep(0.5)

        # Show ContextMonitor before execution
        from fastreact.context import get_context_monitor
        monitor = get_context_monitor()
        if self.console:
            self.print_context_monitor(monitor)

        # ====================================================================
        # Step 2: Planning - Prepare agent
        # ====================================================================

        if self.console:
            with self.console.status("[bold cyan]Planning execution...[/bold cyan]", spinner="dots2"):
                # 创建 FastReAct agent（使用 bootstrap）
                agent = self._get_or_create_react_agent()
                await asyncio.sleep(0.3)

        # ====================================================================
        # Step 3: Execution - Run agent with tool tracking
        # ====================================================================

        # Execute agent with live status
        # Note: Event callbacks removed - Sprint 2 provides better feedback via spinners and ContextMonitor
        # 修复：传递 session_context 以支持多轮对话

        if self.console:
            # Wrap execution with live status spinner
            with self.console.status("[bold green][REACT] Executing tasks...[/bold green]", spinner="dots"):
                result = await agent.run_async(query, session_context=self.state.session_context)
        else:
            self.print_info("Executing tasks...")
            result = await agent.run_async(query, session_context=self.state.session_context)

        # 修复：更新对话历史
        if result:
            # 添加用户消息
            self.state.history.append({
                "role": "user",
                "content": query,
            })

            # 添加助手回复
            answer = result.get("answer", "")
            self.state.history.append({
                "role": "assistant",
                "content": answer,
            })

            # 更新 session_context
            self.state.session_context["history"] = self.state.history.copy()

        # ====================================================================
        # Step 4: Analysis - Show final ContextMonitor state
        # ====================================================================

        if self.console:
            with self.console.status("[bold cyan]Analyzing results...[/bold cyan]", spinner="bouncingBar"):
                await asyncio.sleep(0.3)

            # Show final ContextMonitor state
            self.print_context_monitor(monitor)

        # ====================================================================
        # Step 5: Display Result
        # ====================================================================

        # 显示结果
        if self.console:
            answer = result.get("answer", "")

            # Check if answer contains code, and if so, highlight it
            if "```" in answer and "python" in answer:
                # Extract code block and show with syntax highlighting
                lines = answer.split("```")
                for i, block in enumerate(lines):
                    if i % 2 == 1:  # Code block
                        # Extract language and code
                        first_line = block.split("\n")[0]
                        if "python" in first_line.lower():
                            code = "\n".join(block.split("\n")[1:])
                            self.print_code(code, language="python", title="[Python Code]")
                        else:
                            self.console.print(block)
                    else:
                        self.print_markdown(block)
            else:
                # Regular answer - show in panel
                self.console.print(Panel(
                    answer,
                    title="[REACT] Result",
                    border_style="green"
                ))
        else:
            print(f"\nAnswer: {result.get('answer', '')}")

        # 修复：自动保存会话（包含更新后的历史）
        self.state.save_session()

        return True

    def _get_or_create_evaluator(self) -> ComplexityEvaluator:
        """获取或创建复杂度评估器（延迟初始化，使用 LLMDriver）"""
        if self.complexity_evaluator is None:
            # 创建 LLMDriver（如果还没有）
            if not hasattr(self, 'llm_driver') or self.llm_driver is None:
                from fastreact.bootstrap.config_loader import load_config
                config = load_config()
                self.llm_driver = create_llm_driver_from_config(config)

            # 创建 evaluator（使用 LLMDriver）
            self.complexity_evaluator = ComplexityEvaluator(llm_driver=self.llm_driver)

        return self.complexity_evaluator

    def _get_or_create_react_agent(self):
        """获取或创建 ReAct Agent（使用 bootstrap + 内建工具）"""
        if self.state.react_agent is None:
            from fastreact import FastReAct
            from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model
            from fastreact.tools import create_builtin_tools  # 加载内建工具

            config = load_config()

            # Sprint 4/5: Enable reactive loop for auto-reflection
            if "reactive_loop" not in config:
                config["reactive_loop"] = {}
            config["reactive_loop"]["enabled"] = True

            api_key = get_api_key(config)
            base_url = get_base_url(config)
            model = get_model(config)

            # 确保 llm_driver 存在（延迟初始化）
            # 修复：手动 /graph 时跳过复杂度评估，需要手动创建 llm_driver
            if not hasattr(self, 'llm_driver') or self.llm_driver is None:
                from fastreact.llm import create_llm_driver_from_config
                self.llm_driver = create_llm_driver_from_config(config)

            # 创建内建工具（修复：确保 Agent 可以使用所有工具）
            builtin_tools = create_builtin_tools(config=config, model=model)

            if self.console:
                self.print_info(f"Loaded {len(builtin_tools)} builtin tools")

            self.state.react_agent = FastReAct(
                api_key=api_key,
                base_url=base_url,
                model=model,
                tools=builtin_tools,  # 传入内建工具
                enable_bootstrap=True,
                config=config,
                llm_driver=self.llm_driver,  # 传入 LLMDriver（包含 ContextMonitor）
            )

        return self.state.react_agent

    # ========================================================================
    # GraphAgent 模式
    # ========================================================================

    async def _run_graph_agent(self, query: str) -> bool:
        """
        GraphAgent 模式执行（带实时进度显示）

        Sprint 2 Enhancement: Enhanced status display with spinner
        """
        self.state.stats["graph_agent_queries"] += 1

        if self.console:
            self.console.print(f"[cyan][GRAPHAGENT 模式][/cyan]")
            self.console.print()

        # Show ContextMonitor before execution
        from fastreact.context import get_context_monitor
        monitor = get_context_monitor()
        if self.console:
            self.print_context_monitor(monitor)

        # 创建 GraphAgent
        agent = await self._get_or_create_graph_agent()

        # ====================================================================
        # Step 1: Plan Generation - Thinking phase
        # ====================================================================

        if self.console:
            with self.console.status("[bold cyan]Planning execution...[/bold cyan]", spinner="dots2"):
                await asyncio.sleep(0.3)
                plan = await agent._generate_plan(query)

            # 显示计划
            self._display_plan(plan)

            # 确认
            if self.state.config["auto_confirm_plan"]:
                if not self._confirm_plan():
                    self.state.stats["plan_rejections"] += 1
                    self.print_output("[yellow]计划已取消[/yellow]")
                    return True
        else:
            plan = await agent._generate_plan(query)
            self._display_plan(plan)

            if self.state.config["auto_confirm_plan"]:
                if not self._confirm_plan():
                    self.state.stats["plan_rejections"] += 1
                    self.print_output("[yellow]计划已取消[/yellow]")
                    return True

        # ====================================================================
        # Step 2: Plan Execution - Show progress
        # ====================================================================

        if self.console:
            self.console.print()
            self.print_info("[bold green]Executing plan...[/bold green]")

        with self._create_progress() as progress:
            task = progress.add_task("[cyan]执行中...", total=None)

            try:
                # Execute with spinner (only during agent.run)
                if self.console:
                    with self.console.status("[bold cyan]执行中...[/bold cyan]", spinner="dots"):
                        result = await agent.run(query)
                        # spinner 自动结束

                    progress.update(task, completed=True)

                    # 显示"执行完成"消息
                    self.print_success("[bold green]执行完成[/bold green]")

                    # Show ContextMonitor after execution
                    self.print_context_monitor(monitor)

                    # 显示结果
                    self._display_graph_agent_result(result)
                else:
                    result = await agent.run(query)
                    progress.update(task, completed=True)
                    self._display_graph_agent_result(result)

            except Exception as e:
                self.print_error(f"执行失败: {e}")
                raise

        return True

    async def _get_or_create_graph_agent(self):
        """获取或创建 GraphAgent（Sprint 3.5: 异步方法以支持MCP工具加载）"""
        if self.state.graph_agent is None:
            from fastreact.graph import GraphAgent, AgentConfig
            from fastreact.graph.runtime import ExecutionStrategy

            react_agent = self._get_or_create_react_agent()

            # Sprint 3.5 Hotfix: 强制加载MCP工具
            # 确保GraphAgent也能使用MCP工具（GitHub、Apollo等）
            if hasattr(react_agent, '_mcp_enabled') and react_agent._mcp_enabled:
                if not react_agent._mcp_loaded:
                    if self.console:
                        self.print_info("[GraphAgent] Loading MCP tools...")
                    try:
                        await react_agent._load_mcp_tools()
                        if self.console:
                            self.print_success(f"[GraphAgent] Loaded {len(react_agent.tools) - 13} MCP tools")
                    except Exception as e:
                        if self.console:
                            self.print_warning(f"[GraphAgent] MCP loading failed: {e}")
                        else:
                            print(f"[WARNING] MCP loading failed: {e}")

            self.state.graph_agent = GraphAgent(
                llm_driver=self.llm_driver,  # 使用 LLMDriver 而不是 llm_client
                tools=react_agent.tools,  # 现在包含 MCP 工具了！
                config=AgentConfig(
                    execution_strategy=ExecutionStrategy.LEVEL_BASED,  # ← 使用枚举，不是字符串！
                    max_parallel=3,
                    enable_visualization=True,
                ),
            )

        return self.state.graph_agent

    def _display_plan(self, plan):
        """显示执行计划（无 emoji）"""
        if not self.console:
            print(f"\nPlan: {plan.goal}")
            print(f"Steps: {len(plan.steps)}")
            for step in plan.steps:
                print(f"  - {step.step_id}: {step.tool_name} - {step.description}")
            return

        self.console.print()
        self.console.print(Panel(
            f"[bold]目标:[/] {plan.goal}\n"
            f"[bold]步骤数:[/] {len(plan.steps)}",
            title="[bold blue]执行计划[/bold blue]",
            border_style="blue"
        ))

        # 步骤表格
        table = Table(show_header=True, show_lines=True)
        table.add_column("ID", style="cyan")
        table.add_column("Tool", style="yellow")
        table.add_column("Description")
        table.add_column("Dependencies", style="dim")

        for step in plan.steps:
            deps = ", ".join(step.dependencies) if step.dependencies else "-"
            table.add_row(
                step.step_id,
                step.tool_name,
                step.description,
                deps
            )

        self.console.print(table)

    def _confirm_plan(self) -> bool:
        """确认计划"""
        try:
            response = input("\n是否执行该计划？ [Y/n]: ").strip().lower()

            if response in ['n', 'no', '否']:
                return False

            return True

        except (EOFError, KeyboardInterrupt):
            return False

    def _display_graph_agent_result(self, result: dict):
        """显示 GraphAgent 结果（无 emoji）"""
        if not self.console:
            print(f"\nResult: {result.get('response', '')}")
            return

        self.console.print()

        # 执行报告
        report = result.get("report", {})

        stats = f"""[bold]总节点:[/] {report.get('total_nodes', 0)}
[bold]完成:[/] {report.get('completed_nodes', 0)}
[bold]失败:[/] {report.get('failed_nodes', 0)}
[bold]耗时:[/] {report.get('execution_time', 0):.2f}s"""

        self.console.print(Panel(
            stats,
            title="[green]执行统计[/green]",
            border_style="green"
        ))

        # 最终响应
        self.console.print()
        self.console.print(Panel(
            result.get("response", ""),
            title="[bold green]最终答案[/bold green]",
            border_style="green"
        ))

        # 可视化（如果有）
        if result.get("visualization"):
            self.console.print()
            self.console.print(Panel(
                result["visualization"],
                title="[dim]Graph Visualization[/dim]",
                border_style="dim",
            ))

    def _create_progress(self):
        """创建进度条"""
        if self.console:
            from rich.progress import (
                Progress,
                SpinnerColumn,
                TextColumn,
                BarColumn,
                TimeRemainingColumn,
            )

            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=self.console,
            )
        else:
            # 简单的上下文管理器
            class DummyProgress:
                def __enter__(self): return self
                def __exit__(self, *args): pass

                def add_task(self, description, total=None):
                    return None

                def update(self, task, **kwargs):
                    pass

            return DummyProgress()

    # ========================================================================
    # IEL 模式
    # ========================================================================

    async def _run_iel(self, query: str) -> bool:
        """IEL 模式执行"""
        self.state.stats["iel_queries"] += 1

        if self.console:
            self.console.print(f"[magenta][IEL 模式][/magenta]")
            self.console.print()

        self.print_output("[yellow]IEL 模式正在开发中，暂时使用 GraphAgent 模式[/yellow]")

        # 回退到 GraphAgent
        return await self._run_graph_agent(query)

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def print_success(self, message: str):
        """打印成功信息（无 emoji）"""
        if self.console:
            self.console.print(f"[green bold][SUCCESS][/green bold] {message}")
        else:
            print(f"[SUCCESS] {message}")

    def print_error(self, message: str):
        """打印错误信息（无 emoji）"""
        if self.console:
            self.console.print(f"[red bold][ERROR][/red bold] {message}")
        else:
            print(f"[ERROR] {message}", file=sys.stderr)

    def print_output(self, message: str):
        """打印输出"""
        if self.console:
            self.console.print(message)
        else:
            print(message)

    def print_info(self, message: str):
        """打印信息提示"""
        if self.console:
            self.console.print(f"[cyan bold][INFO][/cyan bold] {message}")
        else:
            print(f"[INFO] {message}")

    def print_warning(self, message: str):
        """打印警告信息"""
        if self.console:
            self.console.print(f"[yellow bold][WARNING][/yellow bold] {message}")
        else:
            print(f"[WARNING] {message}")

    def print_code(self, code: str, language: str = "python", title: str = None):
        """
        Display code with syntax highlighting

        Args:
            code: Code content to display
            language: Programming language (default: python)
            title: Optional title for the code block
        """
        if not code:
            return

        if self.console:
            try:
                syntax = Syntax(
                    code,
                    language,
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True
                )

                panel_title = f"[{language}]" if title is None else title
                panel = Panel(
                    syntax,
                    title=panel_title,
                    title_align="left",
                    border_style="bright_blue"
                )
                self.console.print(panel)
            except Exception as e:
                # Fallback to plain text if syntax highlighting fails
                self.console.print(f"[{language}] Code:")
                self.console.print(code)
        else:
            print(f"\n[{language}] Code:")
            print("-" * 60)
            print(code)
            print("-" * 60)

    def print_markdown(self, text: str):
        """
        Render and display Markdown text

        Args:
            text: Markdown content to render
        """
        if not text:
            return

        if self.console:
            try:
                md = Markdown(text)
                self.console.print(md)
            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                # Windows GBK encoding fallback - render as plain text
                self.print_warning(f"Markdown rendering skipped due to encoding: {e}")
                self.console.print(text)
            except Exception as e:
                # Other exceptions - fallback to plain text
                self.console.print(text)
        else:
            print(text)

    def print_tool_call(self, tool_name: str, params: dict, result: str = None):
        """
        Show tool call with nice formatting

        Args:
            tool_name: Name of the tool being called
            params: Tool parameters
            result: Optional tool execution result
        """
        if self.console:
            try:
                # Create table for tool call
                table = Table(
                    title=f"[Tool Call] {tool_name}",
                    show_header=True,
                    header_style="bold cyan",
                    border_style="cyan"
                )
                table.add_column("Parameter", style="cyan", width=20)
                table.add_column("Value", style="green")

                # Add parameters
                for key, value in params.items():
                    # Truncate long values
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    table.add_row(key, value_str)

                self.console.print(table)

                # Show result if provided
                if result:
                    result_str = str(result)
                    if len(result_str) > 200:
                        result_str = result_str[:200] + "..."

                    self.print_info(f"Result: {result_str}")

            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                # Windows GBK encoding fallback
                self.print_warning(f"Table rendering skipped due to encoding: {e}")
                self._fallback_tool_display(tool_name, params, result)
            except Exception as e:
                # Other exceptions
                self._fallback_tool_display(tool_name, params, result)
        else:
            self._fallback_tool_display(tool_name, params, result)

    def _fallback_tool_display(self, tool_name: str, params: dict, result: str = None):
        """Fallback plain text display for tool calls"""
        print(f"\n[Tool Call] {tool_name}")
        print("-" * 60)
        for key, value in params.items():
            print(f"  {key}: {value}")
        if result:
            print(f"\n  Result: {result}")
        print("-" * 60)

    def print_context_monitor(self, monitor=None):
        """
        Display ContextMonitor progress bar and status

        Args:
            monitor: ContextMonitor instance (optional, will use global if None)
        """
        if monitor is None:
            from fastreact.context import get_context_monitor
            monitor = get_context_monitor()

        if self.console:
            progress_bar = monitor.get_progress_bar()
            status_text = monitor.get_status_text()

            panel = Panel(
                f"{status_text}\n{progress_bar}",
                title="[Context Monitor]",
                border_style="bright_yellow"
            )
            self.console.print(panel)
        else:
            print(f"\n{monitor.get_progress_bar()}")
            print(f"{monitor.get_status_text()}")


# ============================================================================
# 入口点
# ============================================================================

def run_unified_repl():
    """启动统一 REPL"""
    # 检查是否有历史会话
    session_dir = Path.cwd() / ".fastreact" / "sessions"

    session_to_load = None

    if session_dir.exists():
        # 找到最新的会话
        session_files = sorted(
            session_dir.glob("unified_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if session_files:
            latest_session = session_files[0]

            # 询问用户
            print(f"发现历史会话: {latest_session.name}")
            response = input("是否恢复？ [Y/n]: ").strip().lower()

            if response not in ['n', 'no', '否']:
                session_to_load = latest_session

    repl = UnifiedAgentREPL(session_to_load=session_to_load)

    try:
        asyncio.run(repl.run_async())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")


if __name__ == '__main__':
    run_unified_repl()
