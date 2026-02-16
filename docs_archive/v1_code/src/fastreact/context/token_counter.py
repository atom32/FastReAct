"""
Token counting module

Provides token estimation for messages and context.
Supports tiktoken if available, falls back to estimation.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using estimation (less accurate)")


class TokenCounter:
    """Token counter for messages and context

    Uses tiktoken if available for accurate counting,
    otherwise falls back to character-based estimation.
    """

    # Character-to-token ratios for estimation
    CHARS_PER_TOKEN_ZH = 1.5  # Chinese: ~1.5 chars per token
    CHARS_PER_TOKEN_EN = 4.0  # English: ~4 chars per token

    def __init__(self, model: str = "gpt-4"):
        """Initialize token counter

        Args:
            model: Model name for tokenizer selection
        """
        self.model = model
        self._tokenizer = None

        if TIKTOKEN_AVAILABLE:
            try:
                # Try to get encoding for model
                self._tokenizer = tiktoken.encoding_for_model(model)
                logger.debug(f"Using tiktoken for model: {model}")
            except KeyError:
                # Model not found, use cl100k_base (GPT-4 default)
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.debug(f"Using cl100k_base encoding for model: {model}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self._tokenizer:
            # Use tiktoken for accurate counting
            return len(self._tokenizer.encode(text))
        else:
            # Fall back to estimation
            return self._estimate_tokens(text)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens based on character count

        Uses different ratios for Chinese and English text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Count Chinese characters
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # Count other characters
        other_chars = len(text) - chinese_chars

        # Estimate tokens
        tokens = int(chinese_chars / self.CHARS_PER_TOKEN_ZH +
                     other_chars / self.CHARS_PER_TOKEN_EN)

        return max(1, tokens)  # At least 1 token

    def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """Count tokens in a message

        Includes role, content, and overhead for message formatting.

        Args:
            message: Message dict with 'role' and 'content'

        Returns:
            Number of tokens
        """
        role = message.get("role", "")
        content = message.get("content", "")

        # Count content tokens
        content_tokens = self.count_tokens(content)

        # Add overhead for role and formatting (~4 tokens per message)
        overhead_tokens = self.count_tokens(role) + 4

        return content_tokens + overhead_tokens

    def count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Count total tokens in message list

        Args:
            messages: List of message dicts

        Returns:
            Total token count
        """
        return sum(self.count_message_tokens(msg) for msg in messages)

    def count_system_prompt_tokens(self, system_prompt: str) -> int:
        """Count tokens in system prompt

        Args:
            system_prompt: System prompt text

        Returns:
            Number of tokens
        """
        # Add overhead for system message
        return self.count_tokens(system_prompt) + 4

    def estimate_response_tokens(self, max_tokens: int) -> int:
        """Estimate tokens needed for response

        Args:
            max_tokens: Configured max_tokens for response

        Returns:
            Estimated token budget for response
        """
        # Use configured max_tokens as estimate
        # Could be refined based on actual response patterns
        return max_tokens


# Global token counter instance (will be initialized with config)
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get global token counter instance

    Returns:
        TokenCounter instance
    """
    global _token_counter
    if _token_counter is None:
        # Default to gpt-4 if not initialized
        _token_counter = TokenCounter(model="gpt-4")
    return _token_counter


def init_token_counter(model: str) -> TokenCounter:
    """Initialize global token counter with specific model

    Args:
        model: Model name for tokenizer selection

    Returns:
        TokenCounter instance
    """
    global _token_counter
    _token_counter = TokenCounter(model=model)
    return _token_counter
