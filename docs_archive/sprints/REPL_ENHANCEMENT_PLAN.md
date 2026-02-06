# REPL Enhancement Plan - Immersive Experience

## Target: "Claude Code-like" Pair Programming Experience

### Current State Analysis

**Existing Features:**
- Rich library integrated (Panel, Table, Console)
- Basic slash commands (/help, /mode, /stats, /save, /history)
- Complexity evaluation and auto mode selection
- Event system and session management
- Statistics display

**Missing Features for "Immersive Experience":**

1. **Code Syntax Highlighting**
   - Current: Plain text code output
   - Target: Rich syntax highlighting with Pygments

2. **Markdown Rendering**
   - Current: Plain text agent responses
   - Target: Rendered Markdown with headers, lists, code blocks

3. **Real-time Progress Display**
   - Current: ContextMonitor progress bars not visible in REPL
   - Target: Live progress bar during agent execution

4. **Tool Call Visualization**
   - Current: No visibility into what tools agent is calling
   - Target: Show tool calls with parameters and results

5. **Thought Chain Display**
   - Current: Agent reasoning is hidden
   - Target: Show "Thinking..." state and reasoning steps

6. **Enhanced Commands**
   - /clear: Better context management
   - /resume: Restore from saved sessions
   - /export: Export conversation to Markdown

---

## Implementation Plan

### Phase 1: Core Visual Enhancements (Priority: HIGH)

#### 1.1 Code Syntax Highlighting
```python
from rich.syntax import Syntax
from rich.panel import Panel

def print_code(self, code: str, language: str = "python"):
    """Display code with syntax highlighting"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    panel = Panel(syntax, title=f"[{language}]", border_style="bright_blue")
    self.console.print(panel)
```

#### 1.2 Markdown Rendering
```python
from rich.markdown import Markdown

def print_markdown(self, text: str):
    """Render and display Markdown text"""
    md = Markdown(text)
    self.console.print(md)
```

#### 1.3 Tool Call Visualization
```python
def print_tool_call(self, tool_name: str, params: Dict[str, Any]):
    """Show tool call with nice formatting"""
    table = Table(title=f"[Tool] {tool_name}", show_header=False)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    for key, value in params.items():
        table.add_row(key, str(value))

    self.console.print(table)
```

### Phase 2: Progress Monitoring (Priority: HIGH)

#### 2.1 ContextMonitor Integration
```python
from fastreact.context import get_context_monitor
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

async def cmd_run_with_progress(self, query: str):
    """Execute query with real-time progress display"""
    monitor = get_context_monitor()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=self.console
    ) as progress:
        task = progress.add_task("[cyan]Executing...", total=100)

        # Show initial progress
        progress_bar = monitor.get_progress_bar()
        progress.update(task, completed=monitor.metrics.usage_percentage)

        # Execute and update
        result = await self._run_react(query)

        # Update progress
        progress.update(task, completed=monitor.metrics.usage_percentage)

    return result
```

### Phase 3: Enhanced Commands (Priority: MEDIUM)

#### 3.1 /clear Command
```python
async def cmd_clear(self, args: str) -> bool:
    """Clear context and reset session"""
    if self.console:
        self.console.clear()

    # Reset ContextMonitor
    from fastreact.context import reset_context_monitor
    reset_context_monitor()

    # Clear conversation history
    self.state.conversation_history = []

    self.print_success("Context cleared and session reset")
    return True
```

#### 3.2 /resume Command
```python
async def cmd_resume(self, args: str) -> bool:
    """Resume from a saved session"""
    if not args:
        # List available sessions
        return await self.cmd_history(args)

    session_file = Path(args)
    if not session_file.exists():
        self.print_error(f"Session not found: {args}")
        return True

    # Load session
    self.state.load_session(session_file)
    self.print_success(f"Resumed session: {session_file.name}")
    return True
```

#### 3.3 /export Command
```python
async def cmd_export(self, args: str) -> bool:
    """Export conversation to Markdown"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = self.state.workspace / f"conversation_{timestamp}.md"

    with open(export_path, 'w', encoding='utf-8') as f:
        f.write("# FastReAct Conversation\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for i, msg in enumerate(self.state.conversation_history, 1):
            f.write(f"## Turn {i}\n\n")
            f.write(f"**User**: {msg.get('query', '')}\n\n")
            f.write(f"**Agent**: {msg.get('response', '')}\n\n")
            f.write("---\n\n")

    self.print_success(f"Exported to: {export_path}")
    return True
```

### Phase 4: Enhanced Agent Execution Display (Priority: HIGH)

#### 4.1 Thinking State Display
```python
async def _run_react_with_display(self, query: str):
    """Run ReAct agent with enhanced display"""

    # Show "Thinking" state
    with self.console.status("[bold yellow]Thinking...", spinner="dots"):
        # Get complexity evaluation
        evaluation = await self.evaluator.evaluate(query)

    # Show evaluation result
    self._show_complexity_evaluation(evaluation)

    # Show planning phase
    with self.console.status("[bold cyan]Planning execution...", spinner="dots2"):
        # Agent plans execution
        ...

    # Show execution phase
    self.print_info("[bold green]Executing tasks...")

    # Execute and show tool calls
    result = await self._execute_with_tool_display(query)

    return result
```

#### 4.2 Tool Call Tracking
```python
async def _execute_with_tool_display(self, query: str):
    """Execute with real-time tool call display"""

    # Hook into agent's tool execution
    original_tool_call = self.state.react_agent.tool_executor.execute

    async def wrapped_tool_call(tool_name: str, **kwargs):
        # Show tool call
        self.print_tool_call(tool_name, kwargs)

        # Execute
        with self.console.status("[bold blue]Running tool...", spinner="arrow"):
            result = await original_tool_call(tool_name, **kwargs)

        # Show result (truncate if too long)
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."

        self.print_success(f"Result: {result_str}")
        return result

    # Replace tool executor
    self.state.react_agent.tool_executor.execute = wrapped_tool_call

    try:
        result = await self.state.react_agent.run_async(query=query)
    finally:
        # Restore original
        self.state.react_agent.tool_executor.execute = original_tool_call

    return result
```

---

## Implementation Order

### Sprint 1: Visual Foundation (This Sprint)
1. Add syntax highlighting for code blocks
2. Add Markdown rendering for responses
3. Enhance /help command with better formatting

### Sprint 2: Progress & Visibility (Next Sprint)
4. Integrate ContextMonitor progress bars
5. Add tool call visualization
6. Add "Thinking" state display

### Sprint 3: Enhanced Commands (Future Sprint)
7. Implement /resume command
8. Implement /export command
9. Enhance /clear command

### Sprint 4: Polish & Experience (Future Sprint)
10. Add color schemes/themes
11. Add sound effects (optional)
12. Add animations/transitions

---

## Testing Strategy

For each enhancement:
1. Create a test scenario in REPL
2. Verify visual appearance
3. Test cross-platform compatibility (Windows/Mac/Linux)
4. Ensure no emoji usage
5. Verify UTF-8 encoding

---

## Success Criteria

After Phase 1 & 2 completion, REPL should provide:
- [ ] Code displayed with syntax highlighting
- [ ] Markdown rendered properly
- [ ] Tool calls visible with parameters
- [ ] Real-time progress during execution
- [ ] ContextMonitor warnings shown
- [ ] Smooth, responsive user experience

This will make FastReAct feel like a "professional pair programming tool" rather than just a script runner.
