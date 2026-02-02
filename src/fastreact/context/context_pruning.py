"""
Context Pruning Module

Intelligently prunes context to reduce token usage by 40-60% while preserving important information.

Based on Moltbot's context-pruning.ts approach:
- Importance scoring for messages
- Smart content compression for tool results
- Priority-based message selection
"""

import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Dict, Any, Optional, Tuple
from .token_counter import TokenCounter

logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """Message priority levels (higher = more important)"""

    SYSTEM = 100
    USER = 90
    ASSISTANT_THOUGHT = 80
    ASSISTANT_ANSWER = 70
    TOOL_CALL = 50
    TOOL_RESULT = 30


@dataclass
class PruningConfig:
    """Configuration for context pruning"""

    # Enable/disable pruning
    enabled: bool = True

    # Target reduction ratio (0.4 = reduce to 40% of original)
    target_ratio: float = 0.5

    # Minimum messages to keep (regardless of token budget)
    min_messages: int = 10

    # Maximum messages to keep
    max_messages: int = 100

    # Tool result compression
    tool_result_max_lines: int = 50
    tool_result_head_lines: int = 30
    tool_result_tail_lines: int = 20
    tool_result_truncate_indicator: str = "\n... [{} lines omitted] ...\n"

    # Preserve recent messages (last N messages always kept)
    preserve_recent_count: int = 5

    # Importance weights for message types
    importance_weights: Dict[str, float] = field(default_factory=lambda: {
        "system": 1.0,
        "user": 0.9,
        "assistant": 0.7,
        "tool_result": 0.4,
    })

    @classmethod
    def from_dict(cls, config_dict: dict) -> "PruningConfig":
        """Create PruningConfig from config.json section"""
        pruning_cfg = config_dict.get("pruning", {})

        return cls(
            enabled=pruning_cfg.get("enabled", True),
            target_ratio=pruning_cfg.get("target_ratio", 0.5),
            min_messages=pruning_cfg.get("min_messages", 10),
            max_messages=pruning_cfg.get("max_messages", 100),
            tool_result_max_lines=pruning_cfg.get("tool_result_max_lines", 50),
            tool_result_head_lines=pruning_cfg.get("tool_result_head_lines", 30),
            tool_result_tail_lines=pruning_cfg.get("tool_result_tail_lines", 20),
            preserve_recent_count=pruning_cfg.get("preserve_recent_count", 5),
            importance_weights=pruning_cfg.get(
                "importance_weights",
                {
                    "system": 1.0,
                    "user": 0.9,
                    "assistant": 0.7,
                    "tool_result": 0.4,
                }
            ),
        )


@dataclass
class MessageScore:
    """Score and metadata for a message"""

    message: Dict[str, Any]
    score: float
    priority: MessagePriority
    token_count: int
    position: int  # Position in original conversation
    is_compressed: bool = False


class ContextPruner:
    """Intelligently prunes context to reduce token usage

    Strategy:
    1. Score each message based on importance
    2. Compress tool results (head/tail truncation)
    3. Select high-value messages within token budget
    4. Preserve recent messages and system messages
    """

    def __init__(
        self,
        config: PruningConfig,
        token_counter: TokenCounter
    ):
        """Initialize context pruner

        Args:
            config: Pruning configuration
            token_counter: Token counter instance
        """
        self.config = config
        self.token_counter = token_counter

        logger.debug(
            f"ContextPruner initialized: "
            f"enabled={config.enabled}, "
            f"target_ratio={config.target_ratio}, "
            f"min_messages={config.min_messages}"
        )

    def prune(
        self,
        messages: List[Dict[str, Any]],
        target_tokens: int
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Prune messages to fit within token budget

        Args:
            messages: List of messages to prune
            target_tokens: Target token count

        Returns:
            Tuple of (pruned_messages, metadata)
        """
        if not self.config.enabled:
            # Return original messages if pruning disabled
            total_tokens = self.token_counter.count_messages_tokens(messages)
            return messages, {
                "original_count": len(messages),
                "pruned_count": len(messages),
                "original_tokens": total_tokens,
                "pruned_tokens": total_tokens,
                "reduction_ratio": 0.0,
                "compression_applied": False,
            }

        # Count original tokens
        original_tokens = self.token_counter.count_messages_tokens(messages)

        if original_tokens <= target_tokens:
            # No pruning needed
            return messages, {
                "original_count": len(messages),
                "pruned_count": len(messages),
                "original_tokens": original_tokens,
                "pruned_tokens": original_tokens,
                "reduction_ratio": 0.0,
                "compression_applied": False,
            }

        logger.info(
            f"Pruning {len(messages)} messages ({original_tokens} tokens) "
            f"to fit {target_tokens} tokens"
        )

        # Step 1: Score all messages
        scored_messages = self._score_messages(messages)

        # Step 2: Compress tool results
        compressed_messages = self._compress_tool_results(scored_messages)

        # Step 3: Select messages within budget
        selected = self._select_messages(compressed_messages, target_tokens)

        # Calculate metrics
        pruned_tokens = self.token_counter.count_messages_tokens(selected)
        reduction_ratio = 1.0 - (pruned_tokens / original_tokens)

        metadata = {
            "original_count": len(messages),
            "pruned_count": len(selected),
            "original_tokens": original_tokens,
            "pruned_tokens": pruned_tokens,
            "reduction_ratio": reduction_ratio,
            "compression_applied": True,
            "messages_removed": len(messages) - len(selected),
        }

        logger.info(
            f"Pruning complete: {metadata['messages_removed']} messages removed, "
            f"{reduction_ratio:.1%} token reduction "
            f"({original_tokens} -> {pruned_tokens} tokens)"
        )

        return selected, metadata

    def _score_messages(self, messages: List[Dict[str, Any]]) -> List[MessageScore]:
        """Score messages based on importance

        Scoring factors:
        - Message type (system, user, assistant, tool)
        - Position (recent messages get bonus)
        - Content length (penalize very long messages)
        - Tool results (lower priority)
        """
        scored = []

        for idx, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Determine priority
            priority = self._get_priority(role, content)

            # Calculate base score from importance weight
            weight = self.config.importance_weights.get(
                role if role in self.config.importance_weights else "assistant",
                0.5
            )
            score = weight * 100

            # Position bonus: recent messages get higher score
            position_bonus = (idx / len(messages)) * 10
            score += position_bonus

            # Length penalty: very long messages get slight penalty
            token_count = self.token_counter.count_message_tokens(msg)
            if token_count > 1000:
                score -= (token_count - 1000) / 100

            # Bonus for user messages (they're critical)
            if role == "user":
                score += 20

            # Bonus for assistant thoughts (contains reasoning)
            if role == "assistant" and self._is_thought(content):
                score += 15

            scored.append(MessageScore(
                message=msg,
                score=max(0, score),
                priority=priority,
                token_count=token_count,
                position=idx,
            ))

        return scored

    def _get_priority(self, role: str, content: str) -> MessagePriority:
        """Get priority level for a message"""
        if role == "system":
            return MessagePriority.SYSTEM
        elif role == "user":
            return MessagePriority.USER
        elif role == "assistant":
            if self._is_thought(content):
                return MessagePriority.ASSISTANT_THOUGHT
            return MessagePriority.ASSISTANT_ANSWER
        elif role == "tool":
            return MessagePriority.TOOL_RESULT
        else:
            return MessagePriority.TOOL_CALL

    def _is_thought(self, content: str) -> bool:
        """Check if assistant content is a thought/reasoning"""
        thought_indicators = ["thinking", "thought", "reasoning", "plan", "分析", "思考"]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in thought_indicators)

    def _compress_tool_results(self, scored: List[MessageScore]) -> List[MessageScore]:
        """Compress tool result messages using head/tail truncation"""
        compressed = []

        for item in scored:
            if item.priority == MessagePriority.TOOL_RESULT:
                # Compress tool result
                compressed_msg = self._compress_tool_result(item.message)
                item.message = compressed_msg
                item.is_compressed = True
                # Recalculate tokens after compression
                item.token_count = self.token_counter.count_message_tokens(compressed_msg)

            compressed.append(item)

        return compressed

    def _compress_tool_result(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a single tool result message

        Strategy: Keep head + tail, omit middle
        """
        content = message.get("content", "")

        if not content or len(content) < 1000:
            # Skip compression for short content
            return message

        lines = content.split("\n")

        if len(lines) <= self.config.tool_result_max_lines:
            return message

        # Head + tail strategy
        head_lines = lines[:self.config.tool_result_head_lines]
        tail_lines = lines[-self.config.tool_result_tail_lines:]
        omitted_count = len(lines) - len(head_lines) - len(tail_lines)

        # Rebuild content
        compressed_content = (
            "\n".join(head_lines)
            + self.config.tool_result_truncate_indicator.format(omitted_count)
            + "\n".join(tail_lines)
        )

        return {
            **message,
            "content": compressed_content,
            "_compressed": True,
            "_original_lines": len(lines),
        }

    def _select_messages(
        self,
        scored: List[MessageScore],
        target_tokens: int
    ) -> List[Dict[str, Any]]:
        """Select messages within token budget

        Strategy:
        1. Always keep system messages
        2. Always keep recent N messages
        3. Sort remaining by score
        4. Add highest-scored messages until budget exhausted
        """
        selected = []
        current_tokens = 0

        # Separate system messages and recent messages
        system_messages = [m for m in scored if m.priority == MessagePriority.SYSTEM]
        recent_messages = scored[-self.config.preserve_recent_count:]
        remaining = [
            m for m in scored
            if m.priority != MessagePriority.SYSTEM
            and m not in recent_messages
        ]

        # Add system messages first
        for msg in system_messages:
            selected.append(msg.message)
            current_tokens += msg.token_count

        # Add recent messages
        for msg in recent_messages:
            if msg not in system_messages:  # Avoid duplicates
                selected.append(msg.message)
                current_tokens += msg.token_count

        # Sort remaining by score (descending)
        remaining.sort(key=lambda x: (x.score, x.priority), reverse=True)

        # Add remaining messages until budget exhausted
        for msg in remaining:
            # Check min_messages constraint
            if len(selected) < self.config.min_messages:
                selected.append(msg.message)
                current_tokens += msg.token_count
                continue

            # Check max_messages constraint
            if len(selected) >= self.config.max_messages:
                break

            # Check token budget
            if current_tokens + msg.token_count <= target_tokens:
                selected.append(msg.message)
                current_tokens += msg.token_count
            else:
                # Budget exhausted
                break

        # Sort by original position to maintain conversation flow
        selected_with_position = []
        for msg in selected:
            # Find original position
            original_pos = None
            for i, scored_msg in enumerate(scored):
                if scored_msg.message == msg:
                    original_pos = scored_msg.position
                    break
            selected_with_position.append((original_pos, msg))

        selected_with_position.sort(key=lambda x: x[0])
        result = [msg for _, msg in selected_with_position]

        return result


def prune_messages(
    messages: List[Dict[str, Any]],
    target_tokens: int,
    token_counter: TokenCounter,
    config: Optional[PruningConfig] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Convenience function to prune messages

    Args:
        messages: List of messages to prune
        target_tokens: Target token count
        token_counter: Token counter instance
        config: Optional pruning config (uses defaults if not provided)

    Returns:
        Tuple of (pruned_messages, metadata)
    """
    if config is None:
        config = PruningConfig()

    pruner = ContextPruner(config, token_counter)
    return pruner.prune(messages, target_tokens)
