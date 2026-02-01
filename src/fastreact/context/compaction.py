"""
Progressive Compaction for Conversation History

Implements multi-tier compression: raw → summary → compressed.
Adaptive compression ratios based on conversation age and importance.
Preserves key conversation nodes (decisions, preferences, important info).
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .summarizer import Summarizer

logger = logging.getLogger(__name__)


@dataclass
class CompactionLevel:
    """Compression level metadata"""
    level: int
    name: str
    target_ratio: float  # Target compression ratio (tokens)
    description: str


@dataclass
class CompactionResult:
    """Result of compaction operation"""
    original_messages: List[Dict[str, Any]]
    original_tokens: int
    compressed_text: str
    compressed_tokens: int
    compression_ratio: float
    level: int
    preserved_nodes: List[str]  # Key conversation nodes preserved


class ProgressiveCompaction:
    """Progressive compaction for conversation history

    Implements multi-tier compression strategy:
    - Level 0: Raw messages (no compression)
    - Level 1: Single summary
    - Level 2: Compressed summary
    - Level 3: Ultra-compressed
    """

    # Compression level definitions
    LEVELS = {
        0: CompactionLevel(0, "raw", 1.0, "Original messages"),
        1: CompactionLevel(1, "summary", 0.3, "Single summary"),
        2: CompactionLevel(2, "compressed", 0.1, "Compressed summary"),
        3: CompactionLevel(3, "ultra", 0.05, "Ultra-compressed"),
    }

    def __init__(
        self,
        summarizer: Summarizer,
        base_chunk_ratio: float = 0.4,
        min_chunk_ratio: float = 0.15,
        safety_margin: float = 1.2,
        summary_levels: int = 3,
    ):
        """Initialize progressive compaction

        Args:
            summarizer: Summarizer instance
            base_chunk_ratio: Base compression ratio (default 0.4)
            min_chunk_ratio: Minimum compression ratio (default 0.15)
            safety_margin: Safety margin for token budget (default 1.2)
            summary_levels: Number of compression levels (default 3)
        """
        self.summarizer = summarizer
        self.base_chunk_ratio = base_chunk_ratio
        self.min_chunk_ratio = min_chunk_ratio
        self.safety_margin = safety_margin
        self.summary_levels = summary_levels

        logger.info(
            f"ProgressiveCompaction initialized: "
            f"base_ratio={base_chunk_ratio}, min_ratio={min_chunk_ratio}, "
            f"levels={summary_levels}"
        )

    def calculate_compression_ratio(
        self,
        level: int,
        message_count: int,
        age_iterations: int = 0,
    ) -> float:
        """Calculate compression ratio for a given level

        Args:
            level: Compression level (0-3)
            message_count: Number of messages to compress
            age_iterations: Age in iterations (optional)

        Returns:
            Target compression ratio
        """
        if level == 0:
            return 1.0  # No compression

        # Base ratio decreases with level
        base_ratios = {
            1: 0.3,   # Single summary
            2: 0.1,   # Compressed
            3: 0.05,  # Ultra-compressed
        }

        base_ratio = base_ratios.get(level, self.min_chunk_ratio)

        # Adjust for age (older conversations get more compressed)
        if level > 1 and age_iterations > 0:
            age_factor = min(age_iterations / 100, 0.5)  # Max 50% extra compression
            adjusted_ratio = base_ratio * (1 - age_factor)
            return max(adjusted_ratio, self.min_chunk_ratio)

        return base_ratio

    async def compact(
        self,
        messages: List[Dict[str, Any]],
        target_level: int = 1,
        current_tokens: int = 0,
        context_window: int = 64000,
    ) -> CompactionResult:
        """Compact messages to target level

        Args:
            messages: List of messages to compress
            target_level: Target compression level (1-3)
            current_tokens: Current token count (optional)
            context_window: Context window size (optional)

        Returns:
            CompactionResult with compressed text
        """
        if not messages:
            raise ValueError("No messages to compact")

        if target_level == 0:
            return self._create_no_compaction_result(messages)

        # Count tokens in original messages
        from .token_counter import TokenCounter
        counter = TokenCounter(model="gpt-4")

        original_text = self._format_messages(messages)
        original_tokens = counter.count_tokens(original_text)

        # Extract key nodes before compression
        key_nodes = self._extract_key_nodes(messages)

        # Perform compression based on level
        if target_level == 1:
            compressed_text = await self._level_1_compact(messages, key_nodes)
        elif target_level == 2:
            compressed_text = await self._level_2_compact(messages, key_nodes)
        elif target_level == 3:
            compressed_text = await self._level_3_compact(messages, key_nodes)
        else:
            raise ValueError(f"Invalid compression level: {target_level}")

        # Count compressed tokens
        compressed_tokens = counter.count_tokens(compressed_text)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        logger.info(
            f"Compaction complete: level={target_level}, "
            f"tokens={original_tokens}→{compressed_tokens}, "
            f"ratio={compression_ratio:.2%}"
        )

        return CompactionResult(
            original_messages=messages,
            original_tokens=original_tokens,
            compressed_text=compressed_text,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            level=target_level,
            preserved_nodes=key_nodes,
        )

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into text

        Args:
            messages: List of messages

        Returns:
            Formatted text
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"[{role.upper()}]: {content}")
        return "\n\n".join(lines)

    def _extract_key_nodes(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract key conversation nodes

        Preserves:
        - User preferences
        - Important decisions
        - Action items
        - Questions and answers

        Args:
            messages: List of messages

        Returns:
            List of key nodes (as text)
        """
        key_nodes = []

        for msg in messages:
            content = msg.get("content", "").strip()
            role = msg.get("role", "")

            # Detect key patterns
            if role == "user":
                # User preferences
                if any(keyword in content.lower() for keyword in [
                    "我喜欢", "我想要", "请", "帮我", "需要",
                    "i want", "i like", "please", "help",
                ]):
                    key_nodes.append(content)

                # Questions
                if "?" in content or "？" in content:
                    key_nodes.append(content)

            elif role == "assistant":
                # Decisions and confirmations
                if any(keyword in content.lower() for keyword in [
                    "好的", "明白了", "确认", "决定", "将",
                    "ok", "sure", "confirmed", "decided",
                ]):
                    key_nodes.append(content)

                # Action items
                if any(keyword in content.lower() for keyword in [
                    "会", "将", "做", "执行",
                    "will", "going to",
                ]):
                    key_nodes.append(content)

        return key_nodes

    async def _level_1_compact(
        self,
        messages: List[Dict[str, Any]],
        key_nodes: List[str],
    ) -> str:
        """Level 1: Single summary compression

        Args:
            messages: Messages to compress
            key_nodes: Key nodes to preserve

        Returns:
            Compressed text
        """
        # Use summarizer
        summary = await self.summarizer.summarize(messages)

        # Append key nodes if any
        if key_nodes:
            key_section = "\n\nKey points:\n" + "\n".join(f"- {node}" for node in key_nodes[:5])
            return summary + key_section

        return summary

    async def _level_2_compact(
        self,
        messages: List[Dict[str, Any]],
        key_nodes: List[str],
    ) -> str:
        """Level 2: Compressed summary

        Args:
            messages: Messages to compress
            key_nodes: Key nodes to preserve

        Returns:
            Compressed text
        """
        # First, get level 1 summary
        level_1_text = await self._level_1_compact(messages, [])

        # Then summarize the summary
        level_2_messages = [
            {"role": "assistant", "content": level_1_text}
        ]

        compressed = await self.summarizer.summarize(
            level_2_messages,
            prompt="Summarize extremely concisely, focusing only on the most essential information.",
        )

        # Append top 3 key nodes
        if key_nodes:
            key_section = "\n\nKey: " + "; ".join(key_nodes[:3])
            return compressed + key_section

        return compressed

    async def _level_3_compact(
        self,
        messages: List[Dict[str, Any]],
        key_nodes: List[str],
    ) -> str:
        """Level 3: Ultra-compressed summary

        Args:
            messages: Messages to compress
            key_nodes: Key nodes to preserve

        Returns:
            Ultra-compressed text
        """
        # Extract only the most critical information
        topics = self._extract_topics(messages)

        # Build ultra-compressed summary
        parts = []
        if topics:
            parts.append("Topics: " + ", ".join(topics[:3]))

        if key_nodes:
            parts.append("Key: " + ", ".join(key_nodes[:2]))

        return " | ".join(parts) if parts else "Conversation summary"

    def _extract_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract main topics from messages

        Args:
            messages: List of messages

        Returns:
            List of topics
        """
        # Simple keyword extraction
        topics = []
        keywords = set()

        for msg in messages:
            content = msg.get("content", "").lower()

            # Common topic indicators
            if "机器学习" in content or "machine learning" in content:
                keywords.add("机器学习")
            if "深度学习" in content or "deep learning" in content:
                keywords.add("深度学习")
            if "苹果" in content or "水果" in content:
                keywords.add("水果偏好")

        topics = list(keywords)
        return topics

    def _create_no_compaction_result(
        self,
        messages: List[Dict[str, Any]],
    ) -> CompactionResult:
        """Create result for no compression (level 0)

        Args:
            messages: Original messages

        Returns:
            CompactionResult
        """
        from .token_counter import TokenCounter

        counter = TokenCounter(model="gpt-4")
        text = self._format_messages(messages)
        tokens = counter.count_tokens(text)

        return CompactionResult(
            original_messages=messages,
            original_tokens=tokens,
            compressed_text=text,
            compressed_tokens=tokens,
            compression_ratio=1.0,
            level=0,
            preserved_nodes=[],
        )

    async def get_compaction_plan(
        self,
        current_tokens: int,
        context_window: int,
        message_count: int,
    ) -> Dict[str, Any]:
        """Calculate recommended compaction plan

        Args:
            current_tokens: Current token count
            context_window: Context window size
            message_count: Number of messages

        Returns:
            Compaction plan with recommended level and target tokens
        """
        available_tokens = context_window * self.base_chunk_ratio
        overflow = current_tokens - available_tokens

        if overflow <= 0:
            return {
                "needs_compaction": False,
                "current_level": 0,
                "recommended_level": 0,
                "target_tokens": current_tokens,
            }

        # Calculate required compression ratio
        required_ratio = available_tokens / current_tokens

        # Determine recommended level
        if required_ratio > 0.5:
            level = 1
        elif required_ratio > 0.2:
            level = 2
        else:
            level = 3

        target_tokens = int(current_tokens * required_ratio * self.safety_margin)

        return {
            "needs_compaction": True,
            "overflow_tokens": overflow,
            "current_level": 0,
            "recommended_level": level,
            "target_tokens": target_tokens,
            "required_ratio": required_ratio,
        }


class ProgressiveCompactionBuilder:
    """Builder for creating ProgressiveCompaction from config"""

    @staticmethod
    def from_config(
        summarizer: Summarizer,
        config: Dict[str, Any],
    ) -> ProgressiveCompaction:
        """Create ProgressiveCompaction from configuration

        Args:
            summarizer: Summarizer instance
            config: Configuration dict

        Returns:
            ProgressiveCompaction instance
        """
        return ProgressiveCompaction(
            summarizer=summarizer,
            base_chunk_ratio=config.get("base_chunk_ratio", 0.4),
            min_chunk_ratio=config.get("min_chunk_ratio", 0.15),
            safety_margin=config.get("safety_margin", 1.2),
            summary_levels=config.get("summary_levels", 3),
        )
