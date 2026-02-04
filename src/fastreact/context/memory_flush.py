"""
Memory Flush Mechanism

Automatically summarizes long conversations when context approaches limits.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .summarizer import Summarizer
from .config import ContextConfig

logger = logging.getLogger(__name__)


class MemoryFlush:
    """Memory flush trigger and executor

    Monitors context usage and triggers summarization when thresholds are reached.
    """

    def __init__(
        self,
        summarizer: Summarizer,
        context_config: ContextConfig,
    ):
        """Initialize memory flush

        Args:
            summarizer: Summarizer instance
            context_config: Context configuration
        """
        self.summarizer = summarizer
        self.config = context_config

        # Track flush state
        self._last_flush_iteration: Optional[int] = None
        self._flush_count = 0

    def should_trigger(
        self,
        current_tokens: int,
        context_window: int,
        iteration: Optional[int] = None,
    ) -> bool:
        """Check if memory flush should be triggered

        Args:
            current_tokens: Current token count
            context_window: Model context window size
            iteration: Optional iteration number (to prevent duplicate flushes)

        Returns:
            True if flush should be triggered
        """
        if not self.config.memory_flush_enabled:
            return False

        # Prevent duplicate flushes in same iteration
        if iteration is not None and self._last_flush_iteration == iteration:
            logger.debug(f"Skipping flush, already flushed in iteration {iteration}")
            return False

        # Get threshold values (these represent USED token counts)
        reserve = self.config.reserve_tokens
        soft_threshold = self.config.memory_flush_soft_threshold
        hard_threshold = self.config.memory_flush_hard_threshold

        # Validate thresholds
        available = context_window - reserve

        # Check hard threshold first (more aggressive)
        if current_tokens >= hard_threshold:
            logger.warning(
                f"Hard threshold exceeded: {current_tokens} >= {hard_threshold} tokens, "
                f"forcing memory flush (available: {available}, reserve: {reserve})"
            )
            return True

        # Check soft threshold
        if current_tokens >= soft_threshold:
            logger.info(
                f"Soft threshold reached: {current_tokens} >= {soft_threshold} tokens, "
                f"triggering memory flush (available: {available}, reserve: {reserve})"
            )
            return True

        return False

    async def flush(
        self,
        history: List[Dict[str, Any]],
        session_id: str,
        iteration: Optional[int] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute memory flush: summarize and return result

        Args:
            history: History messages to summarize
            session_id: Session ID
            iteration: Optional iteration number
            custom_prompt: Optional custom prompt

        Returns:
            Flush result metadata
        """
        if not history:
            logger.warning("No history to flush")
            return {}

        logger.info(f"Starting memory flush for {len(history)} messages")

        try:
            # Generate summary
            metadata = await self.summarizer.summarize_with_metadata(
                messages=history,
                session_id=session_id,
                custom_prompt=custom_prompt,
            )

            # Add flush metadata
            metadata.update({
                "flush_timestamp": datetime.now().isoformat(),
                "flush_iteration": iteration,
                "flush_count": self._flush_count,
            })

            # Update state
            if iteration is not None:
                self._last_flush_iteration = iteration
            self._flush_count += 1

            logger.info(
                f"Memory flush complete: {metadata['message_count']} msgs -> "
                f"{metadata['summary_tokens']} tokens "
                f"({metadata['compression_ratio']*100:.1f}% compression)"
            )

            return metadata

        except Exception as e:
            logger.error(f"Memory flush failed: {e}")
            raise

    def create_summary_message(self, summary_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a message from summary for context injection

        Args:
            summary_metadata: Metadata from flush()

        Returns:
            Message dict with summary
        """
        summary = summary_metadata.get("summary", "")
        message_count = summary_metadata.get("message_count", 0)
        original_tokens = summary_metadata.get("original_tokens", 0)

        # Create a summary message that can be injected into context
        content = (
            f"[Previous conversation summary ({message_count} messages, "
            f"{original_tokens} tokens compressed)]:\n\n{summary}"
        )

        return {
            "role": "system",
            "content": content,
            "metadata": {
                "type": "memory_flush_summary",
                "flush_timestamp": summary_metadata.get("flush_timestamp"),
                "message_count": message_count,
                "compression_ratio": summary_metadata.get("compression_ratio"),
            },
        }

    async def flush_and_update_context(
        self,
        history: List[Dict[str, Any]],
        session_id: str,
        iteration: Optional[int] = None,
        custom_prompt: Optional[str] = None,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Flush and return updated history

        Args:
            history: Current history
            session_id: Session ID
            iteration: Optional iteration
            custom_prompt: Optional custom prompt

        Returns:
            Tuple of (flush_metadata, updated_history)
        """
        # Execute flush
        flush_metadata = await self.flush(
            history=history,
            session_id=session_id,
            iteration=iteration,
            custom_prompt=custom_prompt,
        )

        # Create summary message
        summary_message = self.create_summary_message(flush_metadata)

        # Replace history with summary (or prepend if keeping some)
        # Strategy: Keep last 20% of messages + summary
        keep_count = max(1, len(history) // 5)  # Keep last 20%
        kept_messages = history[-keep_count:] if keep_count > 0 else []

        updated_history = [summary_message] + kept_messages

        logger.info(
            f"Updated history: {len(history)} -> {len(updated_history)} messages "
            f"(1 summary + {keep_count} recent)"
        )

        return flush_metadata, updated_history


class MemoryFlushBuilder:
    """Builder for creating MemoryFlush from config"""

    @staticmethod
    def from_config(
        summarizer: Summarizer,
        context_config: ContextConfig,
    ) -> MemoryFlush:
        """Create MemoryFlush from configuration

        Args:
            summarizer: Summarizer instance
            context_config: Context configuration

        Returns:
            MemoryFlush instance
        """
        return MemoryFlush(
            summarizer=summarizer,
            context_config=context_config,
        )
