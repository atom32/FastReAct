"""
Conversation Summarizer

Generates concise summaries of conversation history using LLM.
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

from ..utils.logger import get_logger

logger = get_logger("fastreact.summarizer")


class Summarizer:
    """Conversation summarizer using LLM

    Compresses long conversation histories into concise summaries
    while preserving key information and decisions.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        prompt: str = "Please summarize the following conversation concisely, preserving key information and decisions.",
        temperature: float = 0.3,
        timeout: float = 60.0,
    ):
        """Initialize summarizer

        Args:
            api_key: LLM API key
            base_url: LLM API base URL
            model: Model name for summarization
            prompt: Custom prompt for summarization
            temperature: Temperature for generation (lower = more concise)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.prompt = prompt
        self.temperature = temperature
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def summarize(
        self,
        messages: List[Dict[str, Any]],
        custom_prompt: Optional[str] = None,
    ) -> str:
        """Summarize conversation messages

        Args:
            messages: List of messages to summarize
            custom_prompt: Optional custom prompt override

        Returns:
            Summary text

        Raises:
            httpx.HTTPError: If API call fails
        """
        if not messages:
            return ""

        # Build conversation text
        conversation_text = self._format_messages(messages)

        # Build request
        prompt = custom_prompt or self.prompt
        system_message = {
            "role": "system",
            "content": f"{prompt}\n\nSummarize the following conversation:\n\n{conversation_text}"
        }

        # Call LLM API
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [system_message],
                    "temperature": self.temperature,
                    "max_tokens": 2000,  # Summary should be concise
                },
            )

            response.raise_for_status()
            data = response.json()

            # Extract summary
            summary = data["choices"][0]["message"]["content"].strip()

            logger.info(f"Generated summary: {len(summary)} chars from {len(messages)} messages")

            return summary

        except httpx.HTTPError as e:
            logger.error(f"Summarization API call failed: {e}")
            raise

        except (KeyError, IndexError) as e:
            logger.error(f"Invalid API response format: {e}")
            raise

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into text for summarization

        Args:
            messages: List of messages

        Returns:
            Formatted conversation text
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."

            role_label = role.upper()
            lines.append(f"[{role_label}]: {content}")

        return "\n\n".join(lines)

    async def summarize_with_metadata(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Summarize with metadata for storage

        Args:
            messages: Messages to summarize
            session_id: Session ID
            custom_prompt: Optional custom prompt

        Returns:
            Dict with summary and metadata
        """
        import time

        start_time = time.time()
        summary = await self.summarize(messages, custom_prompt)
        elapsed = time.time() - start_time

        # Count tokens in original messages
        from .token_counter import TokenCounter
        counter = TokenCounter(model=self.model)
        original_tokens = counter.count_messages_tokens(messages)
        summary_tokens = counter.count_tokens(summary)

        compression_ratio = summary_tokens / original_tokens if original_tokens > 0 else 0

        metadata = {
            "session_id": session_id,
            "summary": summary,
            "message_count": len(messages),
            "original_tokens": original_tokens,
            "summary_tokens": summary_tokens,
            "compression_ratio": compression_ratio,
            "generation_time": elapsed,
            "model": self.model,
        }

        logger.info(
            f"Summary metadata: {len(messages)} msgs, "
            f"{original_tokens} -> {summary_tokens} tokens "
            f"({compression_ratio*100:.1f}% compression)"
        )

        return metadata


class SummarizerBuilder:
    """Builder for creating Summarizer from config"""

    @staticmethod
    def from_config(
        provider_config: Dict[str, Any],
        summarizer_config: Dict[str, Any],
    ) -> Summarizer:
        """Create Summarizer from configuration

        Args:
            provider_config: LLM provider configuration
            summarizer_config: Summarizer configuration (from context.memory_flush)

        Returns:
            Summarizer instance
        """
        return Summarizer(
            api_key=provider_config["api_key"],
            base_url=provider_config["base_url"],
            model=provider_config.get("model", provider_config.get("model", "gpt-4")),
            prompt=summarizer_config.get("summarize_prompt",
                "Please summarize the following conversation concisely, preserving key information and decisions."),
            temperature=summarizer_config.get("summarize_temperature", 0.3),
        )
