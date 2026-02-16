"""
Context management module

Provides token-aware context building and management.
Replaces hardcoded message limits with dynamic, configurable behavior.
"""

from .config import (
    ContextConfig,
    LLMProviderConfig,
    RetrievalConfig,
    HybridSearchConfig,
    CompactionConfig,
    get_default_context_window,
)
from .token_counter import TokenCounter, get_token_counter, init_token_counter
from .context_builder import ContextBuilder
from .context_pruning import (
    ContextPruner,
    PruningConfig,
    MessagePriority,
    prune_messages,
)
from .summarizer import Summarizer, SummarizerBuilder
from .memory_flush import MemoryFlush, MemoryFlushBuilder
from .monitor import ContextMonitor, get_context_monitor, reset_context_monitor, ContextMetrics
from .compaction import ProgressiveCompaction, ProgressiveCompactionBuilder, CompactionResult
from .repo_mapper import (
    RepoMapper,
    RepoMapConfig,
    RepoMapEntry,
    get_repo_mapper,
    remove_session,
)

__all__ = [
    "ContextConfig",
    "LLMProviderConfig",
    "RetrievalConfig",
    "HybridSearchConfig",
    "CompactionConfig",
    "TokenCounter",
    "ContextBuilder",
    # Context Pruning
    "ContextPruner",
    "PruningConfig",
    "MessagePriority",
    "prune_messages",
    "Summarizer",
    "SummarizerBuilder",
    "MemoryFlush",
    "MemoryFlushBuilder",
    "ProgressiveCompaction",
    "ProgressiveCompactionBuilder",
    "CompactionResult",
    "get_token_counter",
    "init_token_counter",
    "get_default_context_window",
    # Repository Mapper
    "RepoMapper",
    "RepoMapConfig",
    "RepoMapEntry",
    "get_repo_mapper",
    "remove_session",
    # Context Monitor
    "ContextMonitor",
    "get_context_monitor",
    "reset_context_monitor",
    "ContextMetrics",
]
