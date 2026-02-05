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

    console = Console()
except ImportError:
    console = None

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
        if self.llm_client is not None:
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

        # 事件管理器（复用）
        self.event_manager = EventManager()

    def get_session_path(self) -> Path:
        """获取当前会话文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.session_dir / f"unified_{timestamp}.json"

    def save_session(self) -> Optional[Path]:
        """保存会话到文件"""
        import json

        session_path = self.get_session_path()

        session_data = {
            "timestamp": datetime.now().isoformat(),
            "execution_mode": self.execution_mode,
            "stats": self.stats.copy(),
            "config": self.config.copy(),
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

                # 执行命令
                await self.execute_command(command)

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
        """打印欢迎信息（无 emoji）"""
        if self.console:
            self.console.print()
            self.console.print(Panel(
                """FastReAct UnifiedAgent REPL

统一入口 REPL：
• 自动评估任务复杂度
• GraphAgent 自动生成执行计划
• 用户确认后再执行
• IEL 快照和自动回滚

输入 /help 查看命令""",
                title="Welcome",
                border_style="cyan"
            ))
            self.console.print()
        else:
            print()
            print("=" * 60)
            print("FastReAct UnifiedAgent REPL")
            print("=" * 60)
            print("统一入口 REPL：自动规划 + 用户确认 + 安全执行")
            print("输入 /help 查看命令")
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

        if cmd in mode_map:
            self.state.execution_mode = mode_map[cmd]
            self.print_success(f"切换到 {mode_map[cmd].upper()} 模式")
        else:
            self.print_error(f"未知命令: /{cmd}")
            return await self.cmd_help("")

        return True

    # ========================================================================
    # 命令处理器
    # ========================================================================

    def cmd_help(self, args: str) -> bool:
        """显示帮助（无 emoji）"""
        if self.console:
            self.console.print()
            self.console.print("[bold cyan]可用命令：[/bold cyan]")
            self.console.print()

            self.console.print("[bold yellow]基础命令：[/bold yellow]")
            basics = [
                ("run <query>", "执行查询（自动模式选择）"),
                ("mode <name>", "切换模式 (auto/react/graph/iel)"),
                ("stats", "显示统计信息"),
                ("save", "保存当前会话"),
                ("history", "显示查询历史"),
                ("help", "显示帮助"),
                ("exit/quit", "退出"),
            ]
            for cmd, desc in basics:
                self.console.print(f"  {cmd:<30} {desc}")

            self.console.print()
            self.console.print("[bold yellow]快捷命令：[/bold yellow]")
            shortcuts = [
                ("/react", "切换到 ReAct 模式"),
                ("/graph", "切换到 GraphAgent 模式"),
                ("/iel", "切换到 IEL 模式"),
                ("/auto", "切换到自动模式"),
            ]
            for cmd, desc in shortcuts:
                self.console.print(f"  {cmd:<30} {desc}")

            self.console.print()
        else:
            print("\n可用命令：")
            print("  run <query> - 执行查询")
            print("  mode <name> - 切换模式")
            print("  stats - 统计信息")
            print("  save - 保存会话")
            print("  history - 历史记录")
            print("  help - 帮助")
            print("  exit/quit - 退出")

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
            self.state.event_manager.emit(event)

            self.state.stats["total_queries"] += 1

            # 自动模式选择
            if self.state.execution_mode == "auto":
                # 确保 evaluator 已初始化
                evaluator = self._get_or_create_evaluator()

                evaluation = await evaluator.evaluate(query)

                self._show_complexity_evaluation(evaluation)

                # 选择模式
                mode = evaluation["suggested_mode"]
            else:
                mode = self.state.execution_mode

            # 执行
            if mode == "react":
                return await self._run_react(query)
            elif mode == "graph_agent":
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

    def _show_complexity_evaluation(self, evaluation: Dict[str, Any]):
        """显示复杂度评估（无 emoji）"""
        if not self.console:
            return

        complexity = evaluation["complexity"].upper()
        score = evaluation["score"]
        reasons = evaluation["reasons"]
        mode = evaluation["suggested_mode"].upper()
        method = evaluation.get("method", "unknown")

        # 颜色
        colors = {
            "SIMPLE": "green",
            "MEDIUM": "yellow",
            "COMPLEX": "red",
        }

        color = colors.get(complexity, "white")

        # 方法标签颜色
        method_color = "cyan" if method == "llm" else "dim"

        self.console.print()
        self.console.print(f"[{color}]任务复杂度: {complexity}[/] (score: {score:.2f})")
        self.console.print(f"[cyan]推荐模式: {mode}[/]")
        self.console.print(f"[{method_color}]评估方法: {method.upper()}[/]")

        # 如果是 LLM 评估，显示额外信息
        if method == "llm":
            estimated_steps = evaluation.get("estimated_steps", 0)
            estimated_tools = evaluation.get("estimated_tools", 0)

            if estimated_steps > 0:
                self.console.print(f"[dim]预估步骤: {estimated_steps}[/]")

            if estimated_tools > 0:
                self.console.print(f"[dim]预估工具: {estimated_tools}[/]")

        if reasons:
            self.console.print(f"[dim]原因: {', '.join(reasons)}[/]")

        self.console.print()

    # ========================================================================
    # ReAct 模式
    # ========================================================================

    async def _run_react(self, query: str) -> bool:
        """ReAct 模式执行"""
        self.state.stats["react_queries"] += 1

        if self.console:
            self.console.print(f"[yellow][REACT 模式][/yellow]")
            self.console.print()

        # 创建 FastReAct agent（使用 bootstrap）
        agent = self._get_or_create_react_agent()

        # 执行（使用事件回调）
        def event_callback(event):
            """事件回调（统一流式输出）"""
            if self.console:
                if event.type == "lifecycle":
                    self.console.print(f"[dim][{event.phase.upper()}][/dim]")
                elif event.type == "tool":
                    if event.phase == "start":
                        self.console.print(f"[cyan][TOOL] {event.tool_name}[/cyan]")
                    elif event.phase == "result":
                        self.console.print(f"[green][RESULT] {event.tool_name}[/green]")

        # 注册事件回调
        self.state.event_manager.register(event_callback)

        # 执行
        result = await agent.run_async(query)

        # 注销事件回调
        self.state.event_manager.unregister(event_callback)

        # 显示结果
        if self.console:
            self.console.print(Panel(
                result.get("answer", ""),
                title="[REACT] Result",
                border_style="green"
            ))
        else:
            print(f"\nAnswer: {result.get('answer', '')}")

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
        """获取或创建 ReAct Agent（使用 bootstrap）"""
        if self.state.react_agent is None:
            from fastreact import FastReAct
            from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

            config = load_config()
            api_key = get_api_key(config)
            base_url = get_base_url(config)
            model = get_model(config)

            self.state.react_agent = FastReAct(
                api_key=api_key,
                base_url=base_url,
                model=model,
                enable_bootstrap=True,
                config=config,
            )

        return self.state.react_agent

    # ========================================================================
    # GraphAgent 模式
    # ========================================================================

    async def _run_graph_agent(self, query: str) -> bool:
        """GraphAgent 模式执行"""
        self.state.stats["graph_agent_queries"] += 1

        if self.console:
            self.console.print(f"[cyan][GRAPHAGENT 模式][/cyan]")
            self.console.print()

        # 创建 GraphAgent
        agent = self._get_or_create_graph_agent()

        # 步骤 1：生成计划
        if self.console:
            self.console.print("[bold blue]Step 1: 生成执行计划...[/bold blue]")

        plan = await agent._generate_plan(query)

        # 显示计划
        self._display_plan(plan)

        # 确认
        if self.state.config["auto_confirm_plan"]:
            if not self._confirm_plan():
                self.state.stats["plan_rejections"] += 1
                self.print_output("[yellow]计划已取消[/yellow]")
                return True

        # 步骤 2：执行计划
        if self.console:
            self.console.print()
            self.console.print("[bold blue]Step 2: 执行计划...[/bold blue]")

        with self._create_progress() as progress:
            task = progress.add_task("[cyan]执行中...", total=None)

            try:
                result = await agent.run(query)

                progress.update(task, completed=True)

                # 显示结果
                self._display_graph_agent_result(result)

            except Exception as e:
                self.print_error(f"执行失败: {e}")
                raise

        return True

    def _get_or_create_graph_agent(self):
        """获取或创建 GraphAgent"""
        if self.state.graph_agent is None:
            from fastreact.graph import GraphAgent, AgentConfig

            react_agent = self._get_or_create_react_agent()

            self.state.graph_agent = GraphAgent(
                llm_client=react_agent._get_client(),
                tools=react_agent.tools,
                config=AgentConfig(
                    execution_strategy="level_based",
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
