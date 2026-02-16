"""
Unit tests for FastReAct Nano v2.0 streaming

NOTE: streaming.py module has been deprecated in v2.0.
Event streaming is now handled through AgentEvent system in core/events.py
This test file is kept for reference but should not be run.
"""

import pytest
import asyncio

# Skip these tests as streaming module has been removed
pytest.skip("streaming module deprecated in v2.0, use AgentEvent instead", allow_module_level=True)


class TestStreamChunk:
    """Test StreamChunk"""

    def test_create_chunk(self):
        """Test creating a stream chunk"""
        chunk = StreamChunk(content="Hello", done=False)
        assert chunk.content == "Hello"
        assert chunk.done is False
        assert chunk.metadata == {}

    def test_create_chunk_with_metadata(self):
        """Test creating chunk with metadata"""
        chunk = StreamChunk(content="World", done=True, metadata={"key": "value"})
        assert chunk.content == "World"
        assert chunk.done is True
        assert chunk.metadata["key"] == "value"


class TestStreamCallback:
    """Test StreamCallback"""

    @pytest.mark.asyncio
    async def test_base_callback(self):
        """Test base callback (no-op)"""
        callback = StreamCallback()
        chunk = StreamChunk(content="test", done=False)

        # Should not raise
        await callback.on_start()
        await callback.on_chunk(chunk)
        await callback.on_complete()

    @pytest.mark.asyncio
    async def test_error_callback(self):
        """Test error callback"""
        callback = StreamCallback()
        error = Exception("Test error")

        # Should not raise
        await callback.on_error(error)


class TestCollectStreamCallback:
    """Test CollectStreamCallback"""

    @pytest.mark.asyncio
    async def test_collect_chunks(self):
        """Test collecting stream chunks"""
        callback = CollectStreamCallback()

        chunk1 = StreamChunk(content="Hello, ")
        chunk2 = StreamChunk(content="World!")

        await callback.on_chunk(chunk1)
        await callback.on_chunk(chunk2)

        assert callback.get_content() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting collected content"""
        callback = CollectStreamCallback()

        await callback.on_chunk(StreamChunk(content="content"))
        assert callback.get_content() == "content"

        callback.reset()
        assert callback.get_content() == ""

    @pytest.mark.asyncio
    async def test_empty_chunks(self):
        """Test handling empty chunks"""
        callback = CollectStreamCallback()

        await callback.on_chunk(StreamChunk(content=""))
        assert callback.get_content() == ""


class TestStreamToIterator:
    """Test stream_to_iterator"""

    @pytest.mark.asyncio
    async def test_string_iterator(self):
        """Test converting string iterator to chunks"""
        async def string_gen():
            yield "Hello"
            yield " "
            yield "World"

        chunks = []
        async for chunk in stream_to_iterator(None, string_gen()):
            chunks.append(chunk)

        assert len(chunks) == 4  # 3 content + 1 done
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " "
        assert chunks[2].content == "World"
        assert chunks[3].done is True

    @pytest.mark.asyncio
    async def test_with_callback(self):
        """Test stream_to_iterator with callback"""
        collected = []

        async def callback(chunk):
            collected.append(chunk.content)

        async def string_gen():
            yield "test"

        async for chunk in stream_to_iterator(callback, string_gen()):
            pass

        assert "test" in collected


class TestStreamWithCallback:
    """Test stream_with_callback"""

    @pytest.mark.asyncio
    async def test_collecting_stream(self):
        """Test collecting stream through callback"""
        callback = CollectStreamCallback()

        async def string_gen():
            yield "Part 1"
            yield "Part 2"
            yield "Part 3"

        result = await stream_with_callback(string_gen(), callback)

        assert result == "Part 1Part 2Part 3"
        assert callback.get_content() == result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in stream"""
        class ErrorCallback(StreamCallback):
            def __init__(self):
                self.errors = []

            async def on_error(self, error):
                self.errors.append(error)

        callback = ErrorCallback()

        async def string_gen():
            yield "before"
            raise Exception("Test error")

        with pytest.raises(Exception):
            await stream_with_callback(string_gen(), callback)

        # Error is called twice: once from stream_to_iterator, once from stream_with_callback
        assert len(callback.errors) == 2
        assert all(isinstance(e, Exception) for e in callback.errors)

    @pytest.mark.asyncio
    async def test_lifecycle_methods(self):
        """Test callback lifecycle methods"""
        class LifecycleCallback(StreamCallback):
            def __init__(self):
                self.started = False
                self.completed = False

            async def on_start(self):
                self.started = True

            async def on_complete(self):
                self.completed = True

        callback = LifecycleCallback()

        async def string_gen():
            yield "content"

        await stream_with_callback(string_gen(), callback)

        assert callback.started is True
        assert callback.completed is True


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        print("[INFO] Running streaming tests...\n")

        # Test StreamChunk
        test = TestStreamChunk()
        test.test_create_chunk()
        print("[OK] StreamChunk: create_chunk")
        test.test_create_chunk_with_metadata()
        print("[OK] StreamChunk: create_chunk_with_metadata")

        # Test StreamCallback
        test = TestStreamCallback()
        await test.test_base_callback()
        print("[OK] StreamCallback: base_callback")
        await test.test_error_callback()
        print("[OK] StreamCallback: error_callback")

        # Test CollectStreamCallback
        test = TestCollectStreamCallback()
        await test.test_collect_chunks()
        print("[OK] CollectStreamCallback: collect_chunks")
        await test.test_reset()
        print("[OK] CollectStreamCallback: reset")
        await test.test_empty_chunks()
        print("[OK] CollectStreamCallback: empty_chunks")

        # Test stream_to_iterator
        test = TestStreamToIterator()
        await test.test_string_iterator()
        print("[OK] stream_to_iterator: string_iterator")
        await test.test_with_callback()
        print("[OK] stream_to_iterator: with_callback")

        # Test stream_with_callback
        test = TestStreamWithCallback()
        await test.test_collecting_stream()
        print("[OK] stream_with_callback: collecting_stream")
        await test.test_error_handling()
        print("[OK] stream_with_callback: error_handling")
        await test.test_lifecycle_methods()
        print("[OK] stream_with_callback: lifecycle_methods")

        print("\n[SUCCESS] All streaming tests passed!")

    asyncio.run(run_tests())
