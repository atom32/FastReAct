"""
Context builder module

Intelligently builds context from session history with token-aware management.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

from .config import ContextConfig, LLMProviderConfig
from .token_counter import TokenCounter
from .context_pruning import ContextPruner, PruningConfig

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context with token-aware message selection

    Replaces hardcoded message limits with dynamic, budget-aware selection.
    """

    def __init__(
        self,
        context_config: ContextConfig,
        llm_config: LLMProviderConfig,
        token_counter: Optional[TokenCounter] = None,
        pruning_config: Optional[PruningConfig] = None
    ):
        """Initialize context builder

        Args:
            context_config: Context management configuration
            llm_config: LLM provider configuration
            token_counter: Token counter instance (optional)
            pruning_config: Pruning configuration (optional)
        """
        self.config = context_config
        self.llm_config = llm_config
        self.token_counter = token_counter or TokenCounter(
            model=context_config.token_model
        )

        # Initialize pruning config
        self.pruning_config = pruning_config or PruningConfig()
        if self.pruning_config.enabled:
            self.pruner = ContextPruner(self.pruning_config, self.token_counter)
        else:
            self.pruner = None

        # Calculate available token budget
        self.context_window = llm_config.context_window
        self.budget = context_config.calculate_budget(self.context_window)

        logger.debug(
            f"ContextBuilder initialized: "
            f"context_window={self.context_window}, "
            f"budget={self.budget}, "
            f"max_messages={context_config.max_history_messages}, "
            f"pruning_enabled={self.pruning_config.enabled}"
        )

    def build_context(
        self,
        system_prompt: str,
        user_query: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Build context messages with token-aware history selection

        Args:
            system_prompt: System prompt text
            user_query: Current user query
            history: Optional message history from session

        Returns:
            Tuple of (messages, metadata)
            - messages: List of message dicts for API
            - metadata: Debug info about token usage
        """
        messages = []
        metadata = {
            "system_prompt_tokens": 0,
            "user_query_tokens": 0,
            "history_tokens": 0,
            "history_messages_used": 0,
            "history_messages_total": 0,
            "total_tokens": 0,
            "budget_remaining": 0,
        }

        # Count system prompt
        system_tokens = self.token_counter.count_system_prompt_tokens(system_prompt)
        metadata["system_prompt_tokens"] = system_tokens

        # Count user query
        query_tokens = self.token_counter.count_tokens(user_query)
        metadata["user_query_tokens"] = query_tokens

        # Calculate remaining budget for history
        history_budget = self.budget - system_tokens - query_tokens

        if history_budget < 0:
            logger.warning(
                f"System prompt and query exceed budget: "
                f"{system_tokens + query_tokens} > {self.budget}"
            )
            history_budget = 0

        # Select history messages within budget
        selected_history = self._select_history(
            history or [],
            history_budget
        )

        # Count history tokens
        history_tokens = self.token_counter.count_messages_tokens(selected_history)
        metadata["history_tokens"] = history_tokens
        metadata["history_messages_used"] = len(selected_history)
        metadata["history_messages_total"] = len(history) if history else 0

        # Build message list
        messages.append({"role": "system", "content": system_prompt})

        # Insert history before user query
        for msg in selected_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        messages.append({"role": "user", "content": user_query})

        # Calculate totals
        metadata["total_tokens"] = (
            metadata["system_prompt_tokens"] +
            metadata["user_query_tokens"] +
            metadata["history_tokens"]
        )
        metadata["budget_remaining"] = self.budget - metadata["total_tokens"]

        logger.debug(
            f"Context built: {metadata['history_messages_used']}/{metadata['history_messages_total']} "
            f"messages, {metadata['total_tokens']}/{self.budget} tokens"
        )

        return messages, metadata

    def _select_history(
        self,
        history: List[Dict[str, Any]],
        budget: int
    ) -> List[Dict[str, Any]]:
        """Select history messages within token budget

        Prioritizes recent messages, but respects token limits.
        Uses intelligent pruning if enabled.

        Args:
            history: Full message history
            budget: Available token budget for history

        Returns:
            Selected messages (most recent within budget)
        """
        if not history:
            return []

        # Use Context Pruning if enabled
        if self.pruner is not None and self.pruning_config.enabled:
            # Check if pruning is needed (count tokens first)
            history_tokens = self.token_counter.count_messages_tokens(history)

            if history_tokens > budget:
                logger.info(f"Using Context Pruning: {history_tokens} > {budget} tokens")
                pruned_history, pruning_metadata = self.pruner.prune(history, budget)

                logger.debug(
                    f"Pruning complete: {pruning_metadata['reduction_ratio']:.1%} reduction, "
                    f"{pruning_metadata['messages_removed']} messages removed"
                )

                return pruned_history

        # Fallback to smart truncation
        if not self.config.smart_truncate:
            # Simple mode: use max_history_messages limit
            max_msg = self.config.max_history_messages
            return history[-max_msg:] if len(history) > max_msg else history

        # Smart mode: token-aware selection
        selected = []
        current_tokens = 0

        # Iterate from most recent to oldest
        for msg in reversed(history):
            msg_tokens = self.token_counter.count_message_tokens(msg)

            if current_tokens + msg_tokens <= budget:
                # Add to front of list (to maintain order)
                selected.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Budget exhausted
                break

            # Safety limit
            if len(selected) >= self.config.max_history_messages:
                break

        logger.debug(
            f"History selection: {len(selected)} messages, "
            f"{current_tokens}/{budget} tokens"
        )

        return selected

    def should_trigger_memory_flush(
        self,
        history: List[Dict[str, Any]],
        system_prompt: str
    ) -> bool:
        """Check if memory flush should be triggered

        Args:
            history: Current message history
            system_prompt: System prompt text

        Returns:
            True if memory flush should be triggered
        """
        if not self.config.memory_flush_enabled:
            return False

        # Count current tokens
        history_tokens = self.token_counter.count_messages_tokens(history)
        system_tokens = self.token_counter.count_system_prompt_tokens(system_prompt)
        query_estimate = 500  # Estimate for typical query
        response_estimate = self.llm_config.max_tokens

        total_tokens = system_tokens + history_tokens + query_estimate + response_estimate

        # Check against thresholds
        soft_threshold = self.context_window - self.config.reserve_tokens - self.config.memory_flush_soft_threshold
        hard_threshold = self.context_window - self.config.reserve_tokens - self.config.memory_flush_hard_threshold

        if total_tokens >= hard_threshold:
            logger.warning(f"Hard threshold exceeded: {total_tokens} >= {hard_threshold}")
            return True

        if total_tokens >= soft_threshold:
            logger.info(f"Soft threshold reached: {total_tokens} >= {soft_threshold}")
            return True

        return False

    def calculate_safe_context_size(self) -> int:
        """Calculate safe context size considering all factors

        Returns:
            Maximum safe tokens for context
        """
        return min(
            self.context_window - self.config.reserve_tokens,
            self.budget
        )
