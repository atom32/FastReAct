#!/usr/bin/env python
"""
Basic tests for FastReAct Nano (no API key required)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact.core.bus import MessageBus, InboundMessage, OutboundMessage
from fastreact.core.tools import ToolRegistry, EchoTool, AddTool
from fastreact.core.context import ContextManager, FileContextStore, Context
from fastreact.channels.base import Channel, ChannelMeta, CLIChannel
from fastreact.channels.registry import ChannelRegistry


def test_message_bus():
    """Test MessageBus"""
    print("\n[TEST] MessageBus")
    print("-" * 40)

    bus = MessageBus()

    # Test message creation
    msg = InboundMessage(
        channel="test",
        user_id="user1",
        content="Hello",
    )
    print(f"[OK] Created inbound message: {msg.to_dict()}")

    # Test queue
    async def test_queue():
        await bus.publish_inbound(msg)
        assert bus.inbound_size() == 1
        consumed = await bus.consume_inbound()
        assert consumed.content == "Hello"
        print("[OK] Queue operations work")

    asyncio.run(test_queue())
    print("[OK] MessageBus tests passed\n")


def test_tools():
    """Test Tool system"""
    print("\n[TEST] Tool System")
    print("-" * 40)

    registry = ToolRegistry()

    # Register tools
    registry.register(EchoTool())
    registry.register(AddTool())

    print(f"[OK] Registered tools: {registry.list_all()}")

    # Test schemas
    schemas = registry.schemas()
    print(f"[OK] Generated {len(schemas)} tool schemas")

    # Test tool execution
    async def test_execution():
        # Echo tool
        result = await registry.execute("echo", {"text": "test"})
        assert "[ECHO]" in result
        print(f"[OK] Echo tool: {result}")

        # Add tool
        result = await registry.execute("add", {"a": 5, "b": 3})
        assert "8" in result
        print(f"[OK] Add tool: {result}")

        # Invalid tool
        result = await registry.execute("invalid", {"param": "value"})
        assert "not found" in result
        print(f"[OK] Invalid tool handled: {result}")

    asyncio.run(test_execution())
    print("[OK] Tool tests passed\n")


def test_context():
    """Test Context system"""
    print("\n[TEST] Context System")
    print("-" * 40)

    # Create temp directory
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())

    store = FileContextStore(temp_dir)
    ctx_mgr = ContextManager(store=store, max_tokens=1000)

    # Test context creation
    context = Context(
        session_id="test:123",
        user_id="123",
    )

    context.add_message("system", "You are helpful")
    context.add_message("user", "Hello")
    context.add_message("assistant", "Hi there")

    print(f"[OK] Context has {len(context.messages)} messages")
    print(f"[OK] Estimated tokens: {context.estimate_tokens()}")

    # Test pruning
    pruned = ctx_mgr.prune_context(context, max_tokens=100)
    print(f"[OK] Pruned to {len(pruned)} messages")

    # Test file storage
    async def test_storage():
        await store.save(context)
        loaded = await store.load("test:123")
        assert loaded is not None
        assert len(loaded.messages) == 3
        print(f"[OK] Saved and loaded context from file")

    asyncio.run(test_storage())

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print("[OK] Context tests passed\n")


def test_channels():
    """Test Channel system"""
    print("\n[TEST] Channel System")
    print("-" * 40)

    # Test registry
    registry = ChannelRegistry()
    print(f"[OK] Created channel registry")

    # Test CLI channel
    cli = CLIChannel()
    print(f"[OK] Created CLI channel: {cli.name}")
    print(f"[OK] Channel meta: {cli.meta.label}")

    # Test stats
    stats = cli.get_stats()
    print(f"[OK] Channel stats: {stats}")

    # Test registry operations
    # Note: We can't register CLIChannel directly as it's an instance not a class
    print(f"[OK] Channel system tests passed\n")


def test_config():
    """Test configuration system"""
    print("\n[TEST] Configuration")
    print("-" * 40)

    from fastreact.utils.config import Config, Paths

    config = Config()
    paths = Paths(config)

    print(f"[OK] Base dir: {paths.base_dir}")
    print(f"[OK] Data dir: {paths.data_dir}")
    print(f"[OK] Sessions dir: {paths.sessions_dir}")

    # Test directory creation
    paths.ensure_directories()
    assert paths.base_dir.exists()
    print(f"[OK] Directories created")

    print("[OK] Configuration tests passed\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("FastReAct Nano - Basic Tests (No API Key Required)")
    print("=" * 60)

    try:
        test_message_bus()
        test_tools()
        test_context()
        test_channels()
        test_config()

        print("=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
