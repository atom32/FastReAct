"""
REPL Adapter for FastReAct Nano

Provides interactive Read-Eval-Print Loop with:
- Conversation history (context retention)
- Session state
- Event streaming visualization
Install with: pip install fastreact-nano[cli]
"""

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.syntax import Syntax

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from fastreact import Agent, Config, EventType
from fastreact.core.messages import Message
from fastreact.core.react import ReActCore


class REPLSession:
    """
    REPL Session with context retention

    Maintains conversation history and state across multiple turns.
    """

    def __init__(
        self,
        agent: Agent,
        session_id: Optional[str] = None,
    ):
        self.agent = agent
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc)

        # Conversation history
        self.messages: List[dict] = []

        # Event statistics
        self.event_counts = {event_type: 0 for event_type in EventType}
        self.total_tokens = 0

    async def run(self, query: str):
        """
        Run a query with session context

        Args:
            query: User query

        Yields:
            AgentEvent objects
        """
        # Prepare history (all previous messages)
        history = list(self.messages)

        # Add current user message to history
        self.messages.append({
            "role": "user",
            "content": query,
        })

        # Run agent with event stream and history
        async for event in self.agent.run_event_stream(
            query,
            session_id=self.session_id,
            history=history,  # Pass conversation history
        ):
            # Count events
            self.event_counts[event.type] += 1

            # Emit event to display
            yield event

            # Track assistant response
            if event.type == EventType.SESSION_END:
                # Add assistant response to history
                self.messages.append({
                    "role": "assistant",
                    "content": event.content,
                })

    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.messages),
            "event_counts": {k.value: v for k, v in self.event_counts.items()},
        }


class REPLAdapter:
    """
    REPL Adapter with Rich UI

    Provides interactive terminal interface with:
    - Conversation history
    - Context retention
    - Event streaming
    - Session management
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        max_history: int = 50,
    ):
        """
        Initialize REPL adapter

        Args:
            config: Agent configuration
            max_history: Maximum messages to keep in history
        """
        if not RICH_AVAILABLE:
            raise ImportError(
                "Rich is required for REPL adapter. "
                "Install with: pip install rich"
            )

        self.config = config or Config.load()  # Load from config file
        self.max_history = max_history
        self.console = Console()

        # Create agent
        self.agent = Agent(config=self.config)

        # Current session
        self.session: Optional[REPLSession] = None

    def _print_banner(self):
        """Print welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        FastReAct Nano v2.0 - Interactive REPL                ║
║                                                               ║
║   Type your queries below. Commands:                         ║
║     exit, quit, q  - Exit REPL                               ║
║     /clear         - Clear conversation history             ║
║     /stats         - Show session statistics                ║
║     /reset         - Reset session                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold blue")

    def _print_event(self, event):
        """Print event to console"""
        if event.type == EventType.SESSION_START:
            pass  # Skip session start

        elif event.type == EventType.THINK:
            # Stream thinking (cyan, with newline to avoid buffering issues)
            self.console.print(f"[cyan]{event.content}[/cyan]")

        elif event.type == EventType.TOOL_CALL:
            # Show tool call (yellow, with newline)
            self.console.print(f"\n[yellow]→ {event.tool_name}[/yellow]")
            if event.tool_args:
                args_preview = str(event.tool_args)[:80]
                self.console.print(f"[dim]   {args_preview}...[/dim]")

        elif event.type == EventType.TOOL_RESULT:
            # Show result preview (dim, folded)
            lines = event.content.split("\n")
            if len(lines) > 3:
                preview = "\n".join(lines[:3]) + f"\n... ({len(lines)} lines total)"
            else:
                preview = event.content[:200]
            self.console.print(f"[dim]{preview}[/dim]")

        elif event.type == EventType.ERROR:
            # Show error (red)
            self.console.print(f"\n[bold red]ERROR: {event.content}[/bold red]")

        elif event.type == EventType.SESSION_END:
            # Show completion (green, with newline)
            self.console.print(f"\n[bold green][DONE] Complete[/bold green]")

    async def _handle_command(self, cmd: str) -> bool:
        """
        Handle REPL command

        Args:
            cmd: Command string

        Returns:
            True if should continue, False if should quit
        """
        cmd = cmd.strip()

        if cmd == "/quit":
            self.console.print("[yellow]Goodbye![/yellow]")
            return False

        elif cmd == "/clear":
            if self.session:
                self.session.messages = []
                self.console.print("[dim]Conversation history cleared.[/dim]")
            return True

        elif cmd == "/reset":
            self.session = REPLSession(self.agent)
            self.console.print("[dim]Session reset.[/dim]")
            return True

        elif cmd == "/stats":
            if self.session:
                stats = self.session.get_stats()
                self.console.print("\n[bold]Session Statistics:[/bold]")
                self.console.print(f"  Session ID: {stats['session_id']}")
                self.console.print(f"  Messages: {stats['message_count']}")
                self.console.print(f"  Events: {stats['event_counts']}")
            else:
                self.console.print("[dim]No active session.[/dim]")
            return True

        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("[dim]Commands: /clear, /stats, /reset, /quit[/dim]")
            return True

    async def run(self):
        """
        Run REPL loop

        Usage:
            adapter = REPLAdapter()
            await adapter.run()
        """
        self._print_banner()

        # Create session
        self.session = REPLSession(self.agent)

        self.console.print(f"[dim]Session: {self.session.session_id}[/dim]\n")

        try:
            while True:
                # Get user input
                try:
                    query = self.console.input("[bold blue]>>> [/bold blue]")
                except (EOFError, KeyboardInterrupt):
                    self.console.print("\n[yellow]Goodbye![/yellow]")
                    break

                # Skip empty input
                if not query.strip():
                    continue

                # Handle exit commands (without sending to LLM)
                if query.lower() in ["exit", "quit", "q"]:
                    self.console.print("[yellow]Goodbye![/yellow]")
                    break

                # Handle slash commands
                if query.startswith("/"):
                    should_continue = await self._handle_command(query)
                    if not should_continue:
                        break
                    continue

                # Print query
                self.console.print(f"\n[bold cyan]Query:[/bold cyan] {query}\n")

                # Run query with session
                try:
                    async for event in self.session.run(query):
                        self._print_event(event)

                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Query interrupted[/yellow]")
                    continue
                except Exception as e:
                    self.console.print(f"\n[bold red]ERROR: {e}[/bold red]")
                    import traceback
                    traceback.print_exc()
                    continue

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Goodbye![/yellow]")


async def repl_main():
    """Main entry point for REPL"""
    adapter = REPLAdapter()
    await adapter.run()


if __name__ == "__main__":
    try:
        asyncio.run(repl_main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] REPL stopped by user")
