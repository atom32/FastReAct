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
from .summarizer import Summarizer, SummarizerBuilder
from .memory_flush import MemoryFlush, MemoryFlushBuilder
from .compaction import ProgressiveCompaction, ProgressiveCompactionBuilder, CompactionResult

__all__ = [
    "ContextConfig",
    "LLMProviderConfig",
    "RetrievalConfig",
    "HybridSearchConfig",
    "CompactionConfig",
    "TokenCounter",
    "ContextBuilder",
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
]
