"""
Context configuration module

Defines all configuration schemas and defaults for context management.
No hardcoded values - all parameters come from configuration files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .context_pruning import PruningConfig


@dataclass
class ContextConfig:
    """Context management configuration

    All values are loaded from config.json, with sensible defaults.
    Defaults are optimized for models with 64k+ context windows.

    Strategy: Aggressive utilization of context window
    - History: 60-75% of context window
    - Reserve: 15-20% for response
    - System: 2-5% for system prompt
    """

    # Maximum number of messages to keep in context (soft limit)
    max_history_messages: int = 1000

    # Maximum tokens for history messages (hard budget)
    # For 64k context window: ~48k history (75%) + ~12k reserve (19%) + ~2k system + ~2k query
    # This allows much longer conversations before needing memory flush
    max_history_tokens: int = 48000

    # Reserve tokens for response generation
    reserve_tokens: int = 12000

    # Estimated tokens for system prompt
    system_prompt_tokens: int = 2000

    # Model name for token counting (affects tokenizer selection)
    token_model: str = "gpt-4"

    # Enable smart truncation (token-aware vs message-count-based)
    smart_truncate: bool = True

    # Memory flush configuration
    memory_flush_enabled: bool = False
    memory_flush_soft_threshold: int = 50000
    memory_flush_hard_threshold: int = 55000
    memory_flush_prompt: str = "Please summarize the following conversation concisely, preserving key information and decisions."
    memory_flush_temperature: float = 0.3

    # Memory retrieval configuration (optional, created from dict)
    retrieval: Optional[RetrievalConfig] = None
    compaction: Optional[CompactionConfig] = None

    # Context pruning configuration (optional, created from dict)
    pruning: Optional["PruningConfig"] = None
    

    @classmethod
    def from_dict(cls, config_dict: dict) -> "ContextConfig":
        """Create ContextConfig from config.json section

        Args:
            config_dict: The 'context' section from config.json

        Returns:
            ContextConfig instance
        """
        # Extract top-level context config
        context_cfg = config_dict.get("context", {})

        # Extract memory flush config
        memory_flush_cfg = context_cfg.get("memory_flush", {})

        # Extract retrieval config
        retrieval_config = RetrievalConfig.from_dict(context_cfg) if context_cfg.get("retrieval", {}).get("enabled", False) else None

        # Extract compaction config
        compaction_config = CompactionConfig.from_dict(context_cfg) if context_cfg.get('compaction', {}).get('enabled', False) else None

        # Extract pruning config
        pruning_config = None
        if context_cfg.get("pruning", {}).get("enabled", False):
            # Import here to avoid circular dependency
            from .context_pruning import PruningConfig
            pruning_config = PruningConfig.from_dict(context_cfg)

        return cls(
            max_history_messages=context_cfg.get("max_history_messages", 50),
            max_history_tokens=context_cfg.get("max_history_tokens", 4000),
            reserve_tokens=context_cfg.get("reserve_tokens", 2048),
            system_prompt_tokens=context_cfg.get("system_prompt_tokens", 1000),
            token_model=context_cfg.get("token_model", "gpt-4"),
            smart_truncate=context_cfg.get("smart_truncate", True),
            memory_flush_enabled=memory_flush_cfg.get("enabled", False),
            memory_flush_soft_threshold=memory_flush_cfg.get("soft_threshold_tokens", 4000),
            memory_flush_hard_threshold=memory_flush_cfg.get("hard_threshold_tokens", 6000),
            memory_flush_prompt=memory_flush_cfg.get("summarize_prompt",
                "请用简洁的语言总结以下对话，保留关键信息和决策。"),
            memory_flush_temperature=memory_flush_cfg.get("summarize_temperature", 0.3),
            retrieval=retrieval_config,
            compaction=compaction_config,
            pruning=pruning_config,
        )

    def calculate_budget(self, context_window: int) -> int:
        """Calculate available token budget for history

        Args:
            context_window: Model's context window size

        Returns:
            Available tokens for history messages
        """
        return min(
            self.max_history_tokens,
            context_window - self.reserve_tokens - self.system_prompt_tokens
        )


@dataclass
class HybridSearchConfig:
    """Hybrid search configuration (BM25 + Semantic)"""

    # Enable hybrid search
    enabled: bool = False

    # Fusion method: "rrf" (Reciprocal Rank Fusion) or "weighted"
    fusion_method: str = "rrf"

    # Alpha weight for BM25 (0-1), semantic gets (1-alpha)
    # 0.5 = equal weight, 0.7 = 70% BM25, 0.3 = 70% semantic
    alpha: float = 0.5

    # RRF constant (higher = ranks have less impact)
    rrf_k: int = 60

    # BM25 parameters
    bm25_k1: float = 1.2  # Term saturation parameter
    bm25_b: float = 0.75  # Length normalization parameter
    bm25_language: str = "chinese"  # "chinese", "english", "mixed"

    # Minimum score threshold
    min_score: float = 0.3

    @classmethod
    def from_dict(cls, config_dict: dict) -> "HybridSearchConfig":
        """Create HybridSearchConfig from config.json section

        Args:
            config_dict: The 'hybrid_search' section from retrieval config

        Returns:
            HybridSearchConfig instance
        """
        hybrid_cfg = config_dict.get("hybrid_search", {})

        return cls(
            enabled=hybrid_cfg.get("enabled", False),
            fusion_method=hybrid_cfg.get("fusion_method", "rrf"),
            alpha=hybrid_cfg.get("alpha", 0.5),
            rrf_k=hybrid_cfg.get("rrf_k", 60),
            bm25_k1=hybrid_cfg.get("bm25_k1", 1.2),
            bm25_b=hybrid_cfg.get("bm25_b", 0.75),
            bm25_language=hybrid_cfg.get("bm25_language", "chinese"),
            min_score=hybrid_cfg.get("min_score", 0.3),
        )




@dataclass
class CompactionConfig:
    """Progressive compaction configuration"""

    # Enable/disable progressive compaction
    enabled: bool = False

    # Compression ratios
    base_chunk_ratio: float = 0.4  # Base compression ratio
    min_chunk_ratio: float = 0.15   # Minimum compression ratio
    safety_margin: float = 1.2        # Safety margin for token budget

    # Compression levels
    summary_levels: int = 3           # Number of compression levels (1-3)

    # Trigger thresholds
    trigger_threshold_tokens: int = 50000  # Trigger compaction at this token level
    auto_compact: bool = True              # Automatically compact when threshold reached

    @classmethod
    def from_dict(cls, config_dict: dict) -> "CompactionConfig":
        """Create CompactionConfig from config.json section

        Args:
            config_dict: The 'compaction' section from context config

        Returns:
            CompactionConfig instance
        """
        compaction_cfg = config_dict.get("compaction", {})

        return cls(
            enabled=compaction_cfg.get("enabled", False),
            base_chunk_ratio=compaction_cfg.get("base_chunk_ratio", 0.4),
            min_chunk_ratio=compaction_cfg.get("min_chunk_ratio", 0.15),
            safety_margin=compaction_cfg.get("safety_margin", 1.2),
            summary_levels=compaction_cfg.get("summary_levels", 3),
            trigger_threshold_tokens=compaction_cfg.get("trigger_threshold_tokens", 50000),
            auto_compact=compaction_cfg.get("auto_compact", True),
        )

@dataclass
class RetrievalConfig:
    """Memory retrieval configuration for semantic search"""

    # Enable/disable retrieval
    enabled: bool = False

    # Embedding provider configuration
    provider: str = "modelscope"
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dim: int = 1536  # Auto-detected from model, fallback only
    device: str = "cuda"  # "cuda" or "cpu"

    # Vector store configuration
    vector_store: str = "sqlite_vec"  # or "apsw" for Windows
    db_path: str = "./data/memory.db"

    # Chunking parameters
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval parameters
    top_k: int = 3  # Number of results to retrieve
    min_similarity: float = 0.65  # Minimum similarity threshold
    max_context_chunks: int = 5  # Max chunks to inject into context

    # Injection configuration
    inject_position: str = "system"  # "system" or "user"
    template: str = (
        "以下是相关的历史对话上下文，请参考这些信息来回答问题：\n\n"
        "{context}\n\n"
        "---\n\n"
    )

    # Auto-indexing
    auto_index: bool = True  # Automatically index conversations
    index_delay: int = 1  # Delay before indexing (iterations)

    # Hybrid search configuration (optional)
    hybrid_search: Optional[HybridSearchConfig] = None

    @classmethod
    def from_dict(cls, config_dict: dict) -> "RetrievalConfig":
        """Create RetrievalConfig from config.json section

        Args:
            config_dict: The 'retrieval' section from context config

        Returns:
            RetrievalConfig instance
        """
        # Get retrieval config, default to disabled
        retrieval_cfg = config_dict.get("retrieval", {})

        # Parse hybrid search config if enabled
        hybrid_config = None
        if retrieval_cfg.get("hybrid_search", {}).get("enabled", False):
            hybrid_config = HybridSearchConfig.from_dict(retrieval_cfg)

        return cls(
            enabled=retrieval_cfg.get("enabled", False),
            provider=retrieval_cfg.get("provider", "modelscope"),
            embedding_model=retrieval_cfg.get("embedding_model", "Qwen/Qwen3-Embedding-0.6B"),
            embedding_dim=retrieval_cfg.get("embedding_dim", 1536),  # Auto-detected, fallback only
            device=retrieval_cfg.get("device", "cuda"),
            vector_store=retrieval_cfg.get("vector_store", "sqlite_vec"),
            db_path=retrieval_cfg.get("db_path", "./data/memory.db"),
            chunk_size=retrieval_cfg.get("chunk_size", 500),
            chunk_overlap=retrieval_cfg.get("chunk_overlap", 50),
            top_k=retrieval_cfg.get("top_k", 3),
            min_similarity=retrieval_cfg.get("min_similarity", 0.65),
            max_context_chunks=retrieval_cfg.get("max_context_chunks", 5),
            inject_position=retrieval_cfg.get("inject_position", "system"),
            template=retrieval_cfg.get(
                "template",
                "以下是相关的历史对话上下文，请参考这些信息来回答问题：\n\n{context}\n\n---\n\n"
            ),
            auto_index=retrieval_cfg.get("auto_index", True),
            index_delay=retrieval_cfg.get("index_delay", 1),
            hybrid_search=hybrid_config,
        )


@dataclass
class LLMProviderConfig:
    """LLM provider configuration with context window info"""

    name: str
    model: str
    max_tokens: int
    context_window: int = 64000  # Default, should be overridden
    temperature: float = 0.7
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    @classmethod
    def from_dict(cls, provider_dict: dict) -> "LLMProviderConfig":
        """Create LLMProviderConfig from provider config section

        Args:
            provider_dict: Provider configuration dict

        Returns:
            LLMProviderConfig instance
        """
        return cls(
            name=provider_dict.get("name", "Unknown"),
            model=provider_dict.get("model", ""),
            max_tokens=provider_dict.get("max_tokens", 8192),
            context_window=provider_dict.get("context_window", 64000),
            temperature=provider_dict.get("temperature", 0.7),
            base_url=provider_dict.get("base_url"),
            api_key=provider_dict.get("api_key"),
        )


# Default context window sizes for common models
# Values as of 2025, may vary by provider
DEFAULT_CONTEXT_WINDOWS = {
    # OpenAI models
    "gpt-4": 8192,  # Legacy GPT-4
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-3.5-turbo": 16385,
    "o1": 200000,
    "o1-mini": 128000,

    # DeepSeek models
    "deepseek-ai/DeepSeek-V3": 64000,
    "deepseek-ai/DeepSeek-R1": 64000,

    # Anthropic models (Claude)
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,

    # Meta models (Llama)
    "llama3.1": 128000,
    "llama-3.1-70b": 128000,
    "llama-3.1-8b": 128000,

    # Moonshot (Kimi)
    "moonshot-v1": 256000,

    # MiniMax
    "minimax": 200000,

    # Qwen (Alibaba)
    "qwen": 128000,
    "qwen-max": 128000,
}


def get_default_context_window(model: str) -> int:
    """Get default context window for a model

    Args:
        model: Model name

    Returns:
        Context window size in tokens
    """
    # Try exact match
    if model in DEFAULT_CONTEXT_WINDOWS:
        return DEFAULT_CONTEXT_WINDOWS[model]

    # Try prefix match
    for key, value in DEFAULT_CONTEXT_WINDOWS.items():
        if model.startswith(key):
            return value

    # Default fallback
    return 64000
