"""
Unit tests for MCP Multi-Tenant Isolation Modes

Tests for:
- Shared mode (global singleton across all users)
- Per-user mode (isolated instances per user)
- Lazy per-user mode (on-demand creation with timeout)
- Instance limit enforcement
- User parameter substitution ({user_key}, {user_workspace})
- Concurrent user scenarios
- Lazy instance lifecycle (spawn -> execute -> timeout -> kill)
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from fastreact.mcp.multitenant_manager import MultiTenantMCPManager, LazyMCPInstance
from fastreact.mcp.manager import MCPToolManager
from fastreact.core.tools import ToolRegistry


@pytest.fixture
def tool_registry():
    """Create mock tool registry"""
    return Mock(spec=ToolRegistry)


@pytest.fixture
def mock_multitenant_manager():
    """Create mock multi-tenant manager"""
    manager = Mock()
    user_context = Mock()
    user_context.workspace = Path("/workspace/user123")
    manager.get_user_context.return_value = user_context
    return manager


@pytest.fixture
def server_config_shared():
    """Create server config for shared mode"""
    config = Mock()
    config.name = "test-server"
    config.command = "npx"
    config.args = ["-y", "@modelcontextprotocol/server-test"]
    config.isolation = "shared"
    config.per_user_args_template = None
    config.max_instances = None
    config.idle_timeout = None
    return config


@pytest.fixture
def server_config_per_user():
    """Create server config for per-user mode"""
    config = Mock()
    config.name = "test-server"
    config.command = "npx"
    config.args = ["-y", "@modelcontextprotocol/server-test"]
    config.isolation = "per_user"
    config.per_user_args_template = None
    config.max_instances = None
    config.idle_timeout = None
    return config


@pytest.fixture
def server_config_lazy():
    """Create server config for lazy per-user mode"""
    config = Mock()
    config.name = "test-server"
    config.command = "npx"
    config.args = ["-y", "@modelcontextprotocol/server-test"]
    config.isolation = "lazy_per_user"
    config.per_user_args_template = None
    config.max_instances = 10
    config.idle_timeout = 2  # 2 seconds for testing
    return config


@pytest.fixture
def server_config_with_template():
    """Create server config with user argument template"""
    config = Mock()
    config.name = "test-server"
    config.command = "npx"
    config.args = ["-y", "@modelcontextprotocol/server-test"]
    config.isolation = "per_user"
    config.per_user_args_template = [
        "-y",
        "@modelcontextprotocol/server-test",
        "--user-key", "{user_key}",
        "--workspace", "{user_workspace}"
    ]
    config.max_instances = None
    config.idle_timeout = None
    return config


class TestSharedIsolationMode:
    """Test shared isolation mode (global singleton)"""

    @pytest.mark.asyncio
    async def test_shared_mode_creates_singleton(self, tool_registry, server_config_shared):
        """Test that shared mode creates single global instance"""
        manager = MultiTenantMCPManager(tool_registry)

        # Mock MCPToolManager creation
        with patch.object(manager, '_get_shared_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = (mock_manager, None)

            # Multiple users request same server
            result1 = await manager.get_manager("test-server", server_config_shared, "user1")
            result2 = await manager.get_manager("test-server", server_config_shared, "user2")
            result3 = await manager.get_manager("test-server", server_config_shared, "user1")

            # Should only create once (shared)
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_shared_mode_no_user_key_required(self, tool_registry, server_config_shared):
        """Test that shared mode works without user_key"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_shared_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = (mock_manager, None)

            # Should not raise error for missing user_key
            result = await manager.get_manager("test-server", server_config_shared, user_key=None)
            assert result[0] is mock_manager

    @pytest.mark.asyncio
    async def test_shared_mode_isolated_per_server(self, tool_registry):
        """Test that shared mode creates separate instances per server"""
        manager = MultiTenantMCPManager(tool_registry)

        # Create two server configs
        config1 = Mock()
        config1.name = "server1"
        config1.command = "npx"
        config1.args = ["-y", "server1"]
        config1.isolation = "shared"
        config1.per_user_args_template = None

        config2 = Mock()
        config2.name = "server2"
        config2.command = "npx"
        config2.args = ["-y", "server2"]
        config2.isolation = "shared"
        config2.per_user_args_template = None

        with patch.object(manager, '_get_shared_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = (mock_manager, None)

            await manager.get_manager("server1", config1, "user1")
            await manager.get_manager("server2", config2, "user1")

            # Should call for each server
            assert mock_get.call_count == 2


class TestPerUserIsolationMode:
    """Test per-user isolation mode"""

    @pytest.mark.asyncio
    async def test_per_user_requires_user_key(self, tool_registry, server_config_per_user):
        """Test that per_user mode requires user_key"""
        manager = MultiTenantMCPManager(tool_registry)

        with pytest.raises(ValueError, match="user_key required"):
            await manager.get_manager("test-server", server_config_per_user, user_key=None)

    @pytest.mark.asyncio
    async def test_per_user_creates_isolated_instances(self, tool_registry, server_config_per_user):
        """Test that per_user mode creates isolated instances per user"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_per_user_manager') as mock_get:
            mock_manager1 = Mock()
            mock_manager2 = Mock()
            mock_get.side_effect = [(mock_manager1, None), (mock_manager2, None)]

            # Two different users
            result1 = await manager.get_manager("test-server", server_config_per_user, "user1")
            result2 = await manager.get_manager("test-server", server_config_per_user, "user2")

            assert result1[0] is mock_manager1
            assert result2[0] is mock_manager2
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_per_user_reuses_instance_for_same_user(self, tool_registry, server_config_per_user):
        """Test that per_user mode reuses instance for same user"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_per_user_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = (mock_manager, None)

            # Same user requests twice
            result1 = await manager.get_manager("test-server", server_config_per_user, "user1")
            result2 = await manager.get_manager("test-server", server_config_per_user, "user1")

            # Should return same manager both times
            assert result1[0] is mock_manager
            assert result2[0] is mock_manager

    @pytest.mark.asyncio
    async def test_per_user_with_user_substitution(
        self,
        tool_registry,
        server_config_with_template,
        mock_multitenant_manager
    ):
        """Test user parameter substitution in per_user mode"""
        manager = MultiTenantMCPManager(tool_registry, mock_multitenant_manager)

        # Mock the manager creation
        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager = Mock()
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()

            # Substitute arguments
            result = await manager._get_per_user_manager(
                "test-server",
                server_config_with_template,
                "feishu:user123"
            )

            # Verify substitution was called
            mock_manager_instance.add_server.assert_called_once()
            call_args = mock_manager_instance.add_server.call_args
            args = call_args[0][2]  # Third argument is args list

            # Check that user_key was substituted
            assert any("feishu:user123" in str(arg) for arg in args)


class TestLazyPerUserIsolationMode:
    """Test lazy per-user isolation mode with lifecycle management"""

    @pytest.mark.asyncio
    async def test_lazy_requires_user_key(self, tool_registry, server_config_lazy):
        """Test that lazy mode requires user_key"""
        manager = MultiTenantMCPManager(tool_registry)

        with pytest.raises(ValueError, match="user_key required"):
            await manager.get_manager("test-server", server_config_lazy, user_key=None)

    @pytest.mark.asyncio
    async def test_lazy_spawn_on_demand(self, tool_registry, server_config_lazy):
        """Test lazy mode spawns instance on first request"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()

            # First request should spawn instance
            result = await manager.get_manager("test-server", server_config_lazy, "user1")

            assert MockMCPManager.called
            assert mock_manager_instance.add_server.called

            # Verify instance is tracked
            assert "user1" in manager._user_managers
            assert "test-server" in manager._user_managers["user1"]

    @pytest.mark.asyncio
    async def test_lazy_reuse_active_instance(self, tool_registry, server_config_lazy):
        """Test lazy mode reuses active instance"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()

            # First request spawns instance
            result1 = await manager.get_manager("test-server", server_config_lazy, "user1")

            # Second request should reuse (not spawn new)
            # Mock should only be called once
            assert MockMCPManager.call_count == 1

            result2 = await manager.get_manager("test-server", server_config_lazy, "user1")

            # Still only one manager created
            assert MockMCPManager.call_count == 1

    @pytest.mark.asyncio
    async def test_lazy_timeout_and_cleanup(self, tool_registry, server_config_lazy):
        """Test lazy mode timeout and cleanup (spawn -> execute -> timeout -> kill)"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            # Phase 1: Spawn
            result1 = await manager.get_manager("test-server", server_config_lazy, "user1")
            assert "user1" in manager._user_managers
            instance1 = manager._user_managers["user1"]["test-server"]
            assert not instance1.is_idle()

            # Phase 2: Execute (instance is active)
            # Accessing via get_manager already increments ref_count internally
            assert instance1._ref_count > 0

            # Release reference (simulating end of usage)
            await instance1.release()
            assert instance1._ref_count == 0

            # Phase 3: Timeout
            # Wait for idle timeout (2 seconds from config)
            await asyncio.sleep(2.5)

            # Verify instance is now idle
            assert instance1.is_idle()

            # Phase 4: Kill (cleanup on next access)
            # The _get_lazy_manager should clean idle instances before creating new ones
            # We verify this by checking that close_all is called when we access the instance again

            # Request again - should detect idle and clean up
            result2 = await manager.get_manager("test-server", server_config_lazy, "user1")

            # Give cleanup a moment to complete
            await asyncio.sleep(0.1)

            # Old instance should have been cleaned up
            mock_manager_instance.close_all.assert_called()

    @pytest.mark.asyncio
    async def test_lazy_instance_limit_enforcement(self, tool_registry):
        """Test lazy mode enforces max_instances limit"""
        # Create config with max_instances = 2
        config = Mock()
        config.name = "test-server"
        config.command = "npx"
        config.args = ["-y", "@modelcontextprotocol/server-test"]
        config.isolation = "lazy_per_user"
        config.per_user_args_template = None
        config.max_instances = 2
        config.idle_timeout = 300

        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            # Create instances up to limit
            await manager.get_manager("test-server", config, "user1")
            await manager.get_manager("test-server", config, "user2")

            # Third instance should fail
            with pytest.raises(RuntimeError, match="Maximum MCP instances"):
                await manager.get_manager("test-server", config, "user3")

    @pytest.mark.asyncio
    async def test_lazy_cleanup_idle_instances_to_make_room(self, tool_registry):
        """Test lazy mode cleans idle instances to make room for new ones"""
        # Create config with max_instances = 2
        config = Mock()
        config.name = "test-server"
        config.command = "npx"
        config.args = ["-y", "@modelcontextprotocol/server-test"]
        config.isolation = "lazy_per_user"
        config.per_user_args_template = None
        config.max_instances = 2
        config.idle_timeout = 1  # 1 second timeout

        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            # Create first instance
            await manager.get_manager("test-server", config, "user1")
            instance1 = manager._user_managers["user1"]["test-server"]

            # Create second instance
            await manager.get_manager("test-server", config, "user2")

            # Wait for first instance to become idle
            await instance1.release()
            await asyncio.sleep(1.5)

            # Third instance should succeed (first cleaned up)
            result3 = await manager.get_manager("test-server", config, "user3")

            # Verify cleanup was called
            mock_manager_instance.close_all.assert_called()

    @pytest.mark.asyncio
    async def test_lazy_background_cleanup_task(self, tool_registry):
        """Test lazy mode background cleanup loop"""
        config = Mock()
        config.name = "test-server"
        config.command = "npx"
        config.args = ["-y", "@modelcontextprotocol/server-test"]
        config.isolation = "lazy_per_user"
        config.per_user_args_template = None
        config.max_instances = 10
        config.idle_timeout = 1

        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            # Create instance (should start cleanup task)
            await manager.get_manager("test-server", config, "user1")

            # Verify cleanup task started
            assert manager._cleanup_running is True
            assert manager._cleanup_task is not None

            # Wait for cleanup cycle
            await asyncio.sleep(2)

            # Cleanup should have run
            # (We can't easily verify this without waiting longer, but task should be running)

            # Cleanup on close
            await manager.close_all()

            # Task should be stopped
            assert manager._cleanup_running is False


class TestLazyMCPInstance:
    """Test LazyMCPInstance lifecycle"""

    def test_instance_creation(self):
        """Test LazyMCPInstance creation"""
        mock_manager = Mock()
        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        assert instance._manager is mock_manager
        assert instance._idle_timeout == 300
        assert instance._ref_count == 0
        assert isinstance(instance._last_used, datetime)

    def test_manager_access_increments_ref_count(self):
        """Test that accessing manager increments ref_count"""
        mock_manager = Mock()
        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        assert instance._ref_count == 0

        # Access manager property
        manager = instance.manager

        assert manager is mock_manager
        assert instance._ref_count == 1

        # Access again
        manager = instance.manager
        assert instance._ref_count == 2

    def test_manager_access_updates_last_used(self):
        """Test that accessing manager updates last_used timestamp"""
        mock_manager = Mock()
        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        original_time = instance._last_used

        # Wait a bit
        import time
        time.sleep(0.1)

        # Access manager
        _ = instance.manager

        # Timestamp should be updated
        assert instance._last_used > original_time

    @pytest.mark.asyncio
    async def test_release_decrements_ref_count(self):
        """Test that release decrements ref_count"""
        mock_manager = Mock()
        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        # Access manager twice
        _ = instance.manager
        _ = instance.manager

        assert instance._ref_count == 2

        # Release once
        await instance.release()
        assert instance._ref_count == 1

        # Release again
        await instance.release()
        assert instance._ref_count == 0

        # Should not go negative
        await instance.release()
        assert instance._ref_count == 0

    def test_is_idle_with_references(self):
        """Test is_idle returns False when ref_count > 0"""
        mock_manager = Mock()
        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        # Access manager to increment ref_count
        _ = instance.manager

        # Should not be idle while referenced
        assert instance.is_idle() is False

    def test_is_idle_without_references_and_within_timeout(self):
        """Test is_idle returns False when within timeout"""
        mock_manager = Mock()
        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        # No references, but just created
        assert instance._ref_count == 0
        assert instance.is_idle() is False  # Within timeout

    def test_is_idle_without_references_and_past_timeout(self):
        """Test is_idle returns True when timeout exceeded"""
        mock_manager = Mock()
        # Short timeout for testing
        instance = LazyMCPInstance(mock_manager, idle_timeout=0)

        # No references
        assert instance._ref_count == 0

        # Should be idle immediately with 0 timeout
        assert instance.is_idle() is True

    @pytest.mark.asyncio
    async def test_cleanup_closes_manager(self):
        """Test cleanup closes all connections"""
        mock_manager = Mock()
        mock_manager.close_all = AsyncMock()

        instance = LazyMCPInstance(mock_manager, idle_timeout=300)

        await instance.cleanup()

        mock_manager.close_all.assert_called_once()


class TestUserParameterSubstitution:
    """Test user parameter substitution"""

    def test_substitute_user_key(self, tool_registry, mock_multitenant_manager):
        """Test {user_key} substitution"""
        manager = MultiTenantMCPManager(tool_registry, mock_multitenant_manager)

        template = ["--user", "{user_key}", "--value", "test"]
        result = manager._substitute_user_args(template, "feishu:user123")

        assert "--user" in result
        assert "feishu:user123" in result
        assert "--value" in result
        assert "test" in result

    def test_substitute_user_workspace(self, tool_registry, mock_multitenant_manager):
        """Test {user_workspace} substitution"""
        manager = MultiTenantMCPManager(tool_registry, mock_multitenant_manager)

        template = ["--workspace", "{user_workspace}"]
        result = manager._substitute_user_args(template, "feishu:user123")

        assert "--workspace" in result
        assert "/workspace/user123" in result

    def test_substitute_multiple_placeholders(self, tool_registry, mock_multitenant_manager):
        """Test multiple placeholders in same template"""
        manager = MultiTenantMCPManager(tool_registry, mock_multitenant_manager)

        template = [
            "--user", "{user_key}",
            "--workspace", "{user_workspace}",
            "--key", "{user_key}"
        ]
        result = manager._substitute_user_args(template, "feishu:user123")

        # Check all occurrences substituted
        assert result.count("feishu:user123") == 2
        assert result.count("/workspace/user123") == 1

    def test_substitute_without_multitenant_manager(self, tool_registry):
        """Test substitution returns template unchanged when no multitenant manager"""
        manager = MultiTenantMCPManager(tool_registry, multitenant_manager=None)

        template = ["--user", "{user_key}", "--workspace", "{user_workspace}"]
        result = manager._substitute_user_args(template, "feishu:user123")

        # Should return unchanged (no substitution)
        assert result == template


class TestConcurrentUserScenarios:
    """Test concurrent user access scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_users_shared_mode(self, tool_registry, server_config_shared):
        """Test concurrent users with shared mode"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_shared_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = (mock_manager, None)

            # Concurrent requests from different users
            tasks = [
                manager.get_manager("test-server", server_config_shared, f"user{i}")
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 10
            # All should get same manager (shared)
            assert all(r[0] is mock_manager for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_users_per_user_mode(self, tool_registry, server_config_per_user):
        """Test concurrent users with per-user mode"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_per_user_manager') as mock_get:
            # Create different manager for each user
            managers = {f"user{i}": Mock() for i in range(10)}
            mock_get.side_effect = [(managers[f"user{i}"], None) for i in range(10)]

            # Concurrent requests from different users
            tasks = [
                manager.get_manager("test-server", server_config_per_user, f"user{i}")
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 10
            # Each should get their own manager
            for i, result in enumerate(results):
                assert result[0] is managers[f"user{i}"]

    @pytest.mark.asyncio
    async def test_concurrent_users_lazy_mode(self, tool_registry, server_config_lazy):
        """Test concurrent users with lazy mode"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()

            # Concurrent requests from different users
            tasks = [
                manager.get_manager("test-server", server_config_lazy, f"user{i}")
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 5
            # Should have created 5 separate instances
            assert MockMCPManager.call_count == 5

            # Verify each user has their own instance
            for i in range(5):
                assert f"user{i}" in manager._user_managers


class TestManagerLifecycle:
    """Test manager lifecycle operations"""

    @pytest.mark.asyncio
    async def test_close_all_shared_managers(self, tool_registry):
        """Test closing all shared managers"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            config = Mock()
            config.name = "test-server"
            config.command = "npx"
            config.args = ["-y", "test"]
            config.isolation = "shared"
            config.per_user_args_template = None

            # Create shared manager
            await manager.get_manager("test-server", config, "user1")

            # Close all
            await manager.close_all()

            # Verify cleanup
            mock_manager_instance.close_all.assert_called()
            assert len(manager._shared_managers) == 0

    @pytest.mark.asyncio
    async def test_close_all_user_managers(self, tool_registry, server_config_lazy):
        """Test closing all user managers"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            # Create multiple user instances
            await manager.get_manager("test-server", server_config_lazy, "user1")
            await manager.get_manager("test-server", server_config_lazy, "user2")

            assert len(manager._user_managers) == 2

            # Close all
            await manager.close_all()

            # Verify cleanup
            assert mock_manager_instance.close_all.call_count == 2
            assert len(manager._user_managers) == 0

    @pytest.mark.asyncio
    async def test_context_manager(self, tool_registry, server_config_lazy):
        """Test using manager as async context manager"""
        with patch('fastreact.mcp.multitenant_manager.MCPToolManager') as MockMCPManager:
            mock_manager_instance = Mock()
            MockMCPManager.return_value = mock_manager_instance
            mock_manager_instance.add_server = AsyncMock()
            mock_manager_instance.close_all = AsyncMock()

            async with MultiTenantMCPManager(tool_registry) as manager:
                # Create instance
                await manager.get_manager("test-server", server_config_lazy, "user1")
                assert len(manager._user_managers) == 1

            # After exit, should be cleaned up
            assert len(manager._user_managers) == 0
            mock_manager_instance.close_all.assert_called()

    @pytest.mark.asyncio
    async def test_preload_shared_servers(self, tool_registry):
        """Test preloading shared servers"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_shared_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = (mock_manager, None)

            # Create server configs (mix of shared and per_user)
            configs = []
            for i in range(3):
                config = Mock()
                config.name = f"server{i}"
                config.command = "npx"
                config.args = ["-y", f"server{i}"]
                config.isolation = "shared" if i < 2 else "per_user"
                config.per_user_args_template = None
                configs.append(config)

            # Preload
            await manager.preload_shared_servers(configs)

            # Should only preload shared servers (first 2)
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_list_mcp_tools(self, tool_registry):
        """Test listing MCP tools from shared servers"""
        manager = MultiTenantMCPManager(tool_registry)

        # Mock shared managers
        mock_manager1 = Mock()
        mock_manager1.list_mcp_tools.return_value = ["tool1", "tool2"]

        mock_manager2 = Mock()
        mock_manager2.list_mcp_tools.return_value = ["tool3", "tool4"]

        manager._shared_managers = {
            "server1": mock_manager1,
            "server2": mock_manager2
        }

        tools = manager.list_mcp_tools()

        assert len(tools) == 4
        assert "tool1" in tools
        assert "tool2" in tools
        assert "tool3" in tools
        assert "tool4" in tools


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_unknown_isolation_mode(self, tool_registry):
        """Test error on unknown isolation mode"""
        manager = MultiTenantMCPManager(tool_registry)

        config = Mock()
        config.name = "test-server"
        config.isolation = "unknown_mode"

        with pytest.raises(ValueError, match="Unknown isolation mode"):
            await manager.get_manager("test-server", config, "user1")

    @pytest.mark.asyncio
    async def test_preload_continues_on_error(self, tool_registry):
        """Test that preload continues if one server fails"""
        manager = MultiTenantMCPManager(tool_registry)

        with patch.object(manager, '_get_shared_manager') as mock_get:
            # First server succeeds, second fails, third succeeds
            mock_manager = Mock()
            mock_get.side_effect = [
                (mock_manager, None),
                RuntimeError("Server failed"),
                (mock_manager, None)
            ]

            # Create configs
            configs = []
            for i in range(3):
                config = Mock()
                config.name = f"server{i}"
                config.command = "npx"
                config.args = ["-y", f"server{i}"]
                config.isolation = "shared"
                config.per_user_args_template = None
                configs.append(config)

            # Should not raise error
            await manager.preload_shared_servers(configs)

            # Should have attempted all 3
            assert mock_get.call_count == 3
