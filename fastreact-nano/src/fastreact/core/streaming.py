"""
Streaming support for FastReAct Nano v2.0

Real-time streaming of LLM responses and tool execution.
"""

import asyncio
from typing import AsyncIterator, Callable, Optional, Any
from dataclasses import dataclass


@dataclass
class StreamChunk:
    """A chunk of streamed content"""
    content: str
    done: bool = False
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamCallback:
    """
    Callback for handling streamed content

    Can be subclassed for custom streaming behavior.
    """

    async def on_chunk(self, chunk: StreamChunk) -> None:
        """
        Handle a chunk of streamed content

        Args:
            chunk: The streamed chunk
        """
        pass

    async def on_start(self) -> None:
        """Called when streaming starts"""
        pass

    async def on_complete(self) -> None:
        """Called when streaming completes"""
        pass

    async def on_error(self, error: Exception) -> None:
        """
        Called when an error occurs

        Args:
            error: The exception
        """
        pass


class PrintStreamCallback(StreamCallback):
    """Print streamed content to stdout"""

    def __init__(self, prefix: str = ""):
        self._prefix = prefix

    async def on_chunk(self, chunk: StreamChunk) -> None:
        if chunk.content:
            print(f"{self._prefix}{chunk.content}", end="", flush=True)

    async def on_complete(self) -> None:
        print()  # New line after completion


class CollectStreamCallback(StreamCallback):
    """Collect all streamed chunks"""

    def __init__(self):
        self._chunks: list[str] = []

    async def on_chunk(self, chunk: StreamChunk) -> None:
        if chunk.content:
            self._chunks.append(chunk.content)

    def get_content(self) -> str:
        """Get collected content"""
        return "".join(self._chunks)

    def reset(self) -> None:
        """Reset collected content"""
        self._chunks.clear()


async def stream_to_iterator(
    callback: Callable[[StreamChunk], Any],
    iterator: AsyncIterator[str],
) -> AsyncIterator[StreamChunk]:
    """
    Convert a string iterator to StreamChunk iterator

    Args:
        callback: Optional callback for each chunk
        iterator: String iterator

    Yields:
        StreamChunk objects
    """
    try:
        async for content in iterator:
            chunk = StreamChunk(content=content, done=False)
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(chunk)
                else:
                    callback(chunk)
            yield chunk
        yield StreamChunk(content="", done=True)
    except Exception as e:
        yield StreamChunk(content="", done=True, metadata={"error": str(e)})


async def stream_with_callback(
    iterator: AsyncIterator[str],
    callback: StreamCallback,
) -> str:
    """
    Stream content through a callback

    Args:
        iterator: String iterator
        callback: Stream callback

    Returns:
        Complete content
    """
    await callback.on_start()

    try:
        content_parts = []
        async for chunk in stream_to_iterator(None, iterator):
            if chunk.metadata and chunk.metadata.get("error"):
                error = Exception(chunk.metadata["error"])
                await callback.on_error(error)
                raise error

            if chunk.content:
                content_parts.append(chunk.content)
                await callback.on_chunk(chunk)

        await callback.on_complete()
        return "".join(content_parts)

    except Exception as e:
        await callback.on_error(e)
        raise
