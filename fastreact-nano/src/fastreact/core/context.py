"""
ContextManager - Smart context management with token monitoring

Based on FastReAct v1's ContextMonitor with Nanobot's file-based storage.
Provides token-aware context building and smart pruning.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import json


@dataclass
class Context:
    """Conversation context"""
    messages: list[dict[str, str]] = field(default_factory=list)
    user_id: str = ""
    session_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(
        self,
        role: str,
        content: str,
        **kwargs,
    ):
        """Add message to context"""
        msg = {"role": role, "content": content, **kwargs}
        self.messages.append(msg)

    def add_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
    ):
        """Add tool result message"""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        })

    def estimate_tokens(self) -> int:
        """Rough token estimation (4 chars ~ 1 token)"""
        total_chars = sum(
            len(m.get("content", "")) for m in self.messages
        )
        return total_chars // 4


class TokenMonitor:
    """Monitor token usage with warnings"""

    def __init__(
        self,
        max_tokens: int,
        reserve_tokens: int = 2000,
        warn_thresholds: list[int] = None,
    ):
        """
        Initialize token monitor

        Args:
            max_tokens: Maximum context window
            reserve_tokens: Reserve for response
            warn_thresholds: Warning percentages (default 80, 90, 95)
        """
        self._max = max_tokens
        self._reserve = reserve_tokens
        self._thresholds = warn_thresholds or [80, 90, 95]
        self._warned = set()

    @property
    def max_tokens(self) -> int:
        return self._max

    @property
    def reserve_tokens(self) -> int:
        return self._reserve

    @property
    def available_tokens(self) -> int:
        """Tokens available for input"""
        return self._max - self._reserve

    def calculate_budget(self, current_tokens: int) -> int:
        """Calculate budget for context building"""
        budget = self.available_tokens - current_tokens
        return max(0, budget)

    @property
    def usage_percent(self) -> float:
        """Get usage as percentage"""
        # This will be calculated based on actual usage
        return 0.0

    def should_warn(self, usage_percent: float) -> bool:
        """Check if should warn at this percentage"""
        for threshold in self._thresholds:
            if usage_percent >= threshold and threshold not in self._warned:
                self._warned.add(threshold)
                return True
        return False

    def reset_warnings(self):
        """Reset warning flags"""
        self._warned.clear()


class ContextStore(ABC):
    """Abstract context storage backend"""

    @abstractmethod
    async def load(self, session_id: str) -> Optional[Context]:
        """Load context for session"""
        pass

    @abstractmethod
    async def save(self, context: Context):
        """Save context for session"""
        pass

    @abstractmethod
    async def append(self, session_id: str, message: dict[str, Any]):
        """Append message to session"""
        pass


class FileContextStore(ContextStore):
    """File-based context storage using JSONL format"""

    def __init__(self, sessions_dir: Path):
        """
        Initialize file store

        Args:
            sessions_dir: Directory to store session files
        """
        self._sessions_dir = sessions_dir
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Get path for session file"""
        # Sanitize session_id for filename
        safe_id = session_id.replace(":", "_").replace("/", "_")
        return self._sessions_dir / f"{safe_id}.jsonl"

    async def load(self, session_id: str) -> Optional[Context]:
        """Load context from file"""
        path = self._get_session_path(session_id)

        if not path.exists():
            return None

        messages = []
        async with asyncio.to_thread.open(path, "r", encoding="utf-8") as f:
            async for line in f:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue

        return Context(
            messages=messages,
            session_id=session_id,
        )

    async def save(self, context: Context):
        """Save context to file (overwrite)"""
        path = self._get_session_path(context.session_id)

        async with asyncio.to_thread.open(path, "w", encoding="utf-8") as f:
            for msg in context.messages:
                line = json.dumps(msg, ensure_ascii=False)
                await f.write(line + "\n")

    async def append(self, session_id: str, message: dict[str, Any]):
        """Append message to session file"""
        path = self._get_session_path(session_id)

        async with asyncio.to_thread.open(path, "a", encoding="utf-8") as f:
            line = json.dumps(message, ensure_ascii=False)
            await f.write(line + "\n")


class ContextManager:
    """
    Context manager with token monitoring and smart pruning

    Features:
    - Token-aware context building
    - Smart message pruning by importance
    - File-based persistence
    - Memory cache for active sessions
    """

    def __init__(
        self,
        store: ContextStore,
        max_tokens: int = 8000,
        reserve_tokens: int = 2000,
        max_history: int = 50,
    ):
        """
        Initialize context manager

        Args:
            store: Context storage backend
            max_tokens: Maximum context window
            reserve_tokens: Reserve for response
            max_history: Maximum messages in history
        """
        self._store = store
        self._monitor = TokenMonitor(max_tokens, reserve_tokens)
        self._max_history = max_history

        # In-memory cache for active sessions
        self._cache: dict[str, Context] = {}

    async def get_context(
        self,
        session_id: str,
        user_id: str,
    ) -> Context:
        """
        Get or create context for session

        Args:
            session_id: Session identifier
            user_id: User identifier

        Returns:
            Context object
        """
        # Check cache first
        if session_id in self._cache:
            return self._cache[session_id]

        # Load from store
        context = await self._store.load(session_id)

        if not context:
            # Create new context
            context = Context(
                session_id=session_id,
                user_id=user_id,
            )

        # Cache it
        self._cache[session_id] = context

        return context

    async def save_context(self, context: Context):
        """Save context to store"""
        await self._store.save(context)

    async def append_message(
        self,
        session_id: str,
        message: dict[str, Any],
    ):
        """Append message to context"""
        if session_id in self._cache:
            self._cache[session_id].add_message(**message)

        await self._store.append(session_id, message)

    def prune_context(
        self,
        context: Context,
        max_tokens: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """
        Prune context to fit token budget

        Priority (keep in this order):
        1. System messages
        2. Tool results
        3. Recent user/assistant messages

        Args:
            context: Context to prune
            max_tokens: Maximum tokens (default from monitor)

        Returns:
            Pruned message list
        """
        if max_tokens is None:
            max_tokens = self._monitor.available_tokens

        messages = context.messages.copy()
        pruned = []
        current_tokens = 0

        # Process in reverse order (most recent first)
        for msg in reversed(messages):
            # Keep system messages
            if msg.get("role") == "system":
                pruned.insert(0, msg)
                tokens = self._estimate_tokens(msg)
                current_tokens += tokens
                continue

            # Keep tool results (important for context)
            if msg.get("role") == "tool":
                pruned.insert(0, msg)
                tokens = self._estimate_tokens(msg)
                current_tokens += tokens
                continue

            # Check budget
            tokens = self._estimate_tokens(msg)
            if current_tokens + tokens > max_tokens:
                # Truncate instead of dropping
                if msg.get("content"):
                    budget_left = max_tokens - current_tokens
                    if budget_left > 100:  # Minimum meaningful content
                        truncated = self._truncate_text(
                            msg["content"],
                            budget_left,
                        )
                        pruned.insert(0, {**msg, "content": truncated})
                        current_tokens += budget_left
                break

            # Keep message
            pruned.insert(0, msg)
            current_tokens += tokens

        return pruned

    def _estimate_tokens(self, msg: dict[str, Any]) -> int:
        """Estimate tokens for message"""
        content = msg.get("content", "")
        # Rough estimate: 4 chars = 1 token
        return len(content) // 4

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit token budget"""
        # Convert tokens to chars (rough estimate)
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text

        # Truncate with ellipsis
        return text[:max_chars - 3] + "..."

    def clear_cache(self, session_id: Optional[str] = None):
        """Clear cache for session or all sessions"""
        if session_id:
            self._cache.pop(session_id, None)
        else:
            self._cache.clear()
