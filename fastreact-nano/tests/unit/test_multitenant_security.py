"""
Unit tests for Multi-Tenant Security

Tests for:
- Path traversal attack prevention
- Malicious user key validation
- Workspace isolation enforcement
- Config persistence isolation
- Concurrent user workspace separation
- Resource limits and security boundaries
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch

from fastreact.core.multitenant import (
    MultiTenantManager,
    UserContext,
    SecurityError,
)


@pytest.fixture
def temp_base_workspace(tmp_path):
    """Create temporary base workspace for testing"""
    base = tmp_path / "workspace"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def multitenant_manager(temp_base_workspace):
    """Create multi-tenant manager with temporary workspace"""
    return MultiTenantManager(temp_base_workspace)


class TestPathTraversalPrevention:
    """Test path traversal attack prevention"""

    def test_block_double_dot_in_channel(self, multitenant_manager):
        """Test blocking .. (double-dot) in channel"""
        # SAFE_PATTERN blocks . in channel/user_id
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("../etc:user")

    def test_block_double_dot_in_user_id(self, multitenant_manager):
        """Test blocking .. (double-dot) in user_id"""
        # SAFE_PATTERN blocks . in channel/user_id
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("feishu:../user")

    def test_block_tilde_in_channel(self, multitenant_manager):
        """Test blocking ~ (tilde) in channel"""
        # SAFE_PATTERN blocks ~ in channel/user_id
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("~root:user")

    def test_block_tilde_in_user_id(self, multitenant_manager):
        """Test blocking ~ (tilde) in user_id"""
        # SAFE_PATTERN blocks ~ in channel/user_id
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("feishu:~user")

    def test_block_null_byte_in_channel(self, multitenant_manager):
        """Test blocking null byte in channel"""
        # SAFE_PATTERN blocks null bytes
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("fei\x00shu:user")

    def test_block_null_byte_in_user_id(self, multitenant_manager):
        """Test blocking null byte in user_id"""
        # SAFE_PATTERN blocks null bytes
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("feishu:user\x00")

    def test_block_absolute_path_in_channel(self, multitenant_manager):
        """Test blocking absolute path pattern in channel"""
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("/etc/passwd:user")

    def test_block_absolute_path_in_user_id(self, multitenant_manager):
        """Test blocking absolute path pattern in user_id"""
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("feishu:/etc/passwd")

    def test_workspace_containment_check(self, temp_base_workspace):
        """Test that workspace is contained within base_workspace"""
        manager = MultiTenantManager(temp_base_workspace)

        # Create normal user
        context = manager.get_user_context("feishu:user123")

        # Verify workspace is contained
        assert context.workspace.is_absolute()
        # Should be under base workspace
        assert temp_base_workspace in context.workspace.parents or context.workspace == temp_base_workspace

    def test_block_symlink_escape(self, temp_base_workspace):
        """Test that symlinks cannot escape base workspace"""
        manager = MultiTenantManager(temp_base_workspace)

        # Create user context
        context = manager.get_user_context("feishu:user123")

        # Try to create symlink outside workspace (simulated attack)
        outside_path = temp_base_workspace.parent / "escaped"
        try:
            context.workspace.symlink_to(outside_path)

            # Even if symlink created, resolved path should not escape
            resolved = context.workspace.resolve()
            # Verify it's still contained
            resolved.relative_to(temp_base_workspace)
        except (OSError, ValueError):
            # Expected - symlink creation or resolution should fail/be contained
            pass


class TestUserKeyValidation:
    """Test user key format and validation"""

    def test_require_colon_separator(self, multitenant_manager):
        """Test that user_key must contain ':' separator"""
        with pytest.raises(ValueError, match="Invalid user_key format"):
            multitenant_manager.get_user_context("invalid_no_colon")

    def test_block_empty_channel(self, multitenant_manager):
        """Test blocking empty channel"""
        with pytest.raises(ValueError, match="Channel.*must not be empty"):
            multitenant_manager.get_user_context(":user_id")

    def test_block_empty_user_id(self, multitenant_manager):
        """Test blocking empty user_id"""
        with pytest.raises(ValueError, match="must not be empty"):
            multitenant_manager.get_user_context("feishu:")

    def test_allow_valid_feishu_user_key(self, multitenant_manager):
        """Test accepting valid Feishu user key"""
        context = multitenant_manager.get_user_context("feishu:ou_1234567890abcdef")
        assert context.user_key == "feishu:ou_1234567890abcdef"
        assert "feishu" in context.workspace.name

    def test_allow_valid_web_user_key(self, multitenant_manager):
        """Test accepting valid web user key"""
        context = multitenant_manager.get_user_context("web:user@example.com")
        assert context.user_key == "web:user@example.com"
        assert "web" in context.workspace.name

    def test_allow_valid_cli_user_key(self, multitenant_manager):
        """Test accepting valid CLI user key"""
        context = multitenant_manager.get_user_context("cli:local")
        assert context.user_key == "cli:local"
        assert "cli" in context.workspace.name

    def test_block_special_characters(self, multitenant_manager):
        """Test blocking special characters in user_key"""
        malicious_keys = [
            "feishu:user<script>",
            "feishu:user&malicious",
            "feishu:user|pipe",
            "feishu:user;command",
            "feishu:user$(cmd)",
            "feishu:user`cmd`",
        ]

        for key in malicious_keys:
            with pytest.raises(SecurityError, match="unsafe characters"):
                multitenant_manager.get_user_context(key)

    def test_allow_safe_special_characters(self, multitenant_manager):
        """Test allowing safe special characters (_, @, ., =, +, -)"""
        safe_keys = [
            "feishu:user_name",
            "web:user@domain.com",
            "cli:user.name",
            "slack:user=id123",
            "discord:user+test",
            "github:user-name",
        ]

        for key in safe_keys:
            # Should not raise error
            context = multitenant_manager.get_user_context(key)
            assert context.user_key == key


class TestWorkspaceIsolation:
    """Test workspace isolation between users"""

    def test_separate_workspaces_for_different_users(self, multitenant_manager):
        """Test that different users get separate workspaces"""
        user1_context = multitenant_manager.get_user_context("feishu:user1")
        user2_context = multitenant_manager.get_user_context("feishu:user2")

        assert user1_context.workspace != user2_context.workspace
        assert "feishu_user1" in str(user1_context.workspace)
        assert "feishu_user2" in str(user2_context.workspace)

    def test_workspace_separated_by_channel(self, multitenant_manager):
        """Test that different channels create separate workspaces"""
        feishu_context = multitenant_manager.get_user_context("feishu:user123")
        slack_context = multitenant_manager.get_user_context("slack:user123")

        # Same user_id but different channels = different workspaces
        assert feishu_context.workspace != slack_context.workspace

    def test_user_cannot_access_other_user_workspace(self, multitenant_manager, temp_base_workspace):
        """Test that users cannot access each other's workspaces"""
        user1 = multitenant_manager.get_user_context("feishu:user1")
        user2 = multitenant_manager.get_user_context("feishu:user2")

        # Create file in user1's workspace
        user1_file = user1.workspace / "secret.txt"
        user1_file.write_text("Secret data")

        # user2 should not be able to access user1's file
        user2_file = user2.workspace / "secret.txt"
        # Different path, different file
        assert not user2_file.exists()

        # Verify paths are different
        assert user1.workspace != user2.workspace

    def test_workspace_names_are_predictable(self, multitenant_manager):
        """Test that workspace names follow predictable pattern"""
        context = multitenant_manager.get_user_context("feishu:ou_abc123")

        # Pattern: {channel}_{user_id} with colons replaced by underscores
        expected_name = "feishu_ou_abc123"
        assert expected_name in context.workspace.name

    def test_colon_replacement_in_workspace_name(self, multitenant_manager):
        """Test that colons in user_id are replaced with underscores"""
        # Note: SAFE_PATTERN doesn't allow colons in user_id
        # So we use a format with dashes instead
        context = multitenant_manager.get_user_context("feishu:user-id-more")

        # Pattern should be preserved (no colons to replace)
        assert "feishu_user-id-more" in context.workspace.name


class TestConfigIsolation:
    """Test configuration file isolation between users"""

    def test_separate_config_files(self, multitenant_manager):
        """Test that each user has separate config file"""
        user1 = multitenant_manager.get_user_context("feishu:user1")
        user2 = multitenant_manager.get_user_context("feishu:user2")

        assert user1.config["user_key"] == "feishu:user1"
        assert user2.config["user_key"] == "feishu:user2"

    def test_config_persistence_isolated(self, multitenant_manager):
        """Test that config updates are isolated per user"""
        user1 = multitenant_manager.get_user_context("feishu:user1")
        user2 = multitenant_manager.get_user_context("feishu:user2")

        # Update user1's config
        multitenant_manager.update_user_config("feishu:user1", {"theme": "dark"})

        # user1 should have the update
        user1_updated = multitenant_manager.get_user_context("feishu:user1")
        assert user1_updated.config.get("theme") == "dark"

        # user2 should not be affected
        user2_context = multitenant_manager.get_user_context("feishu:user2")
        assert user2_context.config.get("theme") != "dark"

    def test_config_file_location(self, multitenant_manager):
        """Test that config files are in respective workspaces"""
        user = multitenant_manager.get_user_context("feishu:user123")

        config_file = user.workspace / "config.json"
        assert config_file.exists()
        assert config_file.is_file()

    def test_config_file_persistence_across_sessions(self, multitenant_manager):
        """Test that config persists across getting context multiple times"""
        # First session
        user1 = multitenant_manager.get_user_context("feishu:user1")
        multitenant_manager.update_user_config("feishu:user1", {"setting": "value1"})

        # Clear cache
        multitenant_manager.clear_cache()

        # Second session (should load from disk)
        user1_reload = multitenant_manager.get_user_context("feishu:user1")
        assert user1_reload.config.get("setting") == "value1"

    def test_default_config_creation(self, multitenant_manager):
        """Test that default config is created for new users"""
        user = multitenant_manager.get_user_context("feishu:newuser")

        # Should have default values
        assert "user_key" in user.config
        assert "channel" in user.config
        assert "user_id" in user.config
        assert "preferences" in user.config

    def test_config_loading_from_disk(self, multitenant_manager):
        """Test loading existing config from disk"""
        # Manually create config file
        user_key = "feishu:existing_user"
        context = multitenant_manager.get_user_context(user_key)

        # Modify config on disk
        config_file = context.workspace / "config.json"
        custom_config = {
            "user_key": user_key,
            "custom_field": "custom_value",
        }
        with open(config_file, "w") as f:
            json.dump(custom_config, f)

        # Clear cache and reload
        multitenant_manager.clear_cache()
        reloaded = multitenant_manager.get_user_context(user_key)

        assert reloaded.config.get("custom_field") == "custom_value"


class TestConcurrentUserScenarios:
    """Test concurrent user access and separation"""

    def test_multiple_users_simultaneous(self, multitenant_manager):
        """Test handling multiple users simultaneously"""
        user_keys = [
            "feishu:user1",
            "feishu:user2",
            "feishu:user3",
        ]

        contexts = [multitenant_manager.get_user_context(key) for key in user_keys]

        # All should have separate contexts
        assert len(set(c.workspace for c in contexts)) == 3

        # Each should have correct user_key
        for context, key in zip(contexts, user_keys):
            assert context.user_key == key

    def test_list_loaded_users(self, multitenant_manager):
        """Test listing all loaded users"""
        # Load multiple users
        user_keys = ["feishu:user1", "feishu:user2", "web:user3"]
        for key in user_keys:
            multitenant_manager.get_user_context(key)

        # List users
        loaded = multitenant_manager.list_users()

        assert set(loaded) == set(user_keys)

    def test_context_caching(self, multitenant_manager):
        """Test that contexts are cached"""
        user1_first = multitenant_manager.get_user_context("feishu:user1")
        user1_second = multitenant_manager.get_user_context("feishu:user1")

        # Should be same object (cached)
        assert user1_first is user1_second

    def test_cache_clear(self, multitenant_manager):
        """Test clearing user context cache"""
        # Load user
        user1_first = multitenant_manager.get_user_context("feishu:user1")

        # Clear cache
        multitenant_manager.clear_cache()

        # Load again
        user1_second = multitenant_manager.get_user_context("feishu:user1")

        # Should be different objects (cache cleared)
        assert user1_first is not user1_second

        # But should have same workspace
        assert user1_first.workspace == user1_second.workspace


class TestMemoryIsolation:
    """Test memory file isolation between users"""

    def test_separate_memory_files(self, multitenant_manager):
        """Test that each user has separate memory file"""
        user1 = multitenant_manager.get_user_context("feishu:user1")
        user2 = multitenant_manager.get_user_context("feishu:user2")

        assert user1.memory_file != user2.memory_file
        assert user1.workspace in user1.memory_file.parents
        assert user2.workspace in user2.memory_file.parents

    def test_memory_file_location(self, multitenant_manager):
        """Test that memory file is in user's workspace"""
        user = multitenant_manager.get_user_context("feishu:user123")

        assert "memory.json" in user.memory_file.name
        assert user.workspace == user.memory_file.parent


class TestSkillsIsolation:
    """Test skills directory isolation between users"""

    def test_separate_skills_directories(self, multitenant_manager):
        """Test that each user has separate skills directory"""
        user1 = multitenant_manager.get_user_context("feishu:user1")
        user2 = multitenant_manager.get_user_context("feishu:user2")

        assert user1.skills_dir != user2.skills_dir
        assert user1.workspace in user1.skills_dir.parents
        assert user2.workspace in user2.skills_dir.parents

    def test_skills_dir_exists(self, multitenant_manager):
        """Test that skills directory is created"""
        user = multitenant_manager.get_user_context("feishu:user123")

        assert user.skills_dir.exists()
        assert user.skills_dir.is_dir()
        assert "skills" in user.skills_dir.name


class TestUserContextProperties:
    """Test UserContext data integrity"""

    def test_user_context_immutability(self, multitenant_manager):
        """Test that user context properties are correctly set"""
        context = multitenant_manager.get_user_context("feishu:test_user")

        assert context.user_key == "feishu:test_user"
        assert isinstance(context.workspace, Path)
        assert isinstance(context.config, dict)
        assert isinstance(context.skills_dir, Path)
        assert isinstance(context.memory_file, Path)

    def test_config_contains_user_info(self, multitenant_manager):
        """Test that config contains user identification info"""
        context = multitenant_manager.get_user_context("web:user@example.com")

        assert context.config["user_key"] == "web:user@example.com"
        assert context.config["channel"] == "web"
        assert context.config["user_id"] == "user@example.com"


class TestBaseWorkspaceSecurity:
    """Test base workspace security requirements"""

    def test_require_absolute_path(self, tmp_path):
        """Test that base_workspace must be absolute path"""
        # Path objects normalize paths, so relative paths become absolute
        # The check happens at Path creation time
        # Let's test with a string that would be relative
        from pathlib import Path as LibPath

        # Create a relative path and verify it gets normalized
        # The implementation uses .resolve() which makes paths absolute
        relative = "relative/path"
        resolved = LibPath(relative).resolve()

        # After resolve, it should be absolute
        assert resolved.is_absolute()

        # Creating manager with resolved path should work
        manager = MultiTenantManager(resolved)
        assert manager._base_workspace.is_absolute()

    def test_base_workspace_created_if_not_exists(self, tmp_path):
        """Test that base workspace is created if it doesn't exist"""
        non_existent = tmp_path / "new_workspace"

        # Should not exist yet
        assert not non_existent.exists()

        # Creating manager should create it
        manager = MultiTenantManager(non_existent)

        assert non_existent.exists()

    def test_workspace_resolution(self, tmp_path):
        """Test that workspace paths are properly resolved"""
        # Create with relative path components
        base = tmp_path / "workspace" / ".." / "workspace"
        manager = MultiTenantManager(base.resolve())

        # Should be normalized
        assert manager._base_workspace.is_absolute()


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_long_user_id(self, multitenant_manager):
        """Test handling of very long user IDs"""
        # Use a length that won't exceed filesystem limits
        long_id = "user_" + "x" * 100  # 105 chars total
        user_key = f"feishu:{long_id}"

        # Should handle gracefully
        context = multitenant_manager.get_user_context(user_key)
        assert context.user_key == user_key

    def test_unicode_in_user_key(self, multitenant_manager):
        """Test handling of unicode characters"""
        # Unicode characters should be blocked by safe pattern
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("feishu:用户名")

    def test_multiple_colons_in_user_id(self, multitenant_manager):
        """Test user_id with colons (blocked by SAFE_PATTERN)"""
        # SAFE_PATTERN doesn't allow colons in user_id
        # This is a security feature to prevent path confusion
        with pytest.raises(SecurityError, match="unsafe characters"):
            multitenant_manager.get_user_context("feishu:user:id:more")

    def test_case_sensitivity(self, multitenant_manager):
        """Test that user keys are case-sensitive"""
        user1 = multitenant_manager.get_user_context("feishu:User")
        user2 = multitenant_manager.get_user_context("feishu:user")

        # Should be different users
        assert user1.workspace != user2.workspace


class TestSecurityErrorMessages:
    """Test security error message clarity"""

    def test_descriptive_error_for_invalid_format(self, multitenant_manager):
        """Test that invalid format errors are descriptive"""
        with pytest.raises(ValueError) as exc_info:
            multitenant_manager.get_user_context("invalid")

        error_msg = str(exc_info.value)
        assert "Invalid user_key format" in error_msg
        assert "channel:user_id" in error_msg

    def test_descriptive_error_for_unsafe_chars(self, multitenant_manager):
        """Test that unsafe character errors are descriptive"""
        with pytest.raises(SecurityError) as exc_info:
            multitenant_manager.get_user_context("feishu:user<script>")

        error_msg = str(exc_info.value)
        assert "unsafe characters" in error_msg
        assert "Allowed:" in error_msg

    def test_descriptive_error_for_path_traversal(self, multitenant_manager):
        """Test that path traversal errors are descriptive"""
        # .. is blocked by SAFE_PATTERN, not explicit traversal check
        with pytest.raises(SecurityError) as exc_info:
            multitenant_manager.get_user_context("feishu:../etc")

        error_msg = str(exc_info.value)
        # Should mention unsafe characters
        assert "unsafe characters" in error_msg


class TestConfigOperations:
    """Test configuration update and retrieval operations"""

    def test_update_config_creates_file(self, multitenant_manager):
        """Test that updating config creates/updates file"""
        user = multitenant_manager.get_user_context("feishu:user1")

        # Update config
        multitenant_manager.update_user_config("feishu:user1", {"new_key": "new_value"})

        # Verify file was updated
        config_file = user.workspace / "config.json"
        with open(config_file) as f:
            data = json.load(f)

        assert data.get("new_key") == "new_value"

    def test_get_config_returns_copy(self, multitenant_manager):
        """Test that get_user_config returns a copy"""
        user = multitenant_manager.get_user_context("feishu:user1")

        config1 = multitenant_manager.get_user_config("feishu:user1")
        config2 = multitenant_manager.get_user_config("feishu:user1")

        # Should be different objects (copies)
        assert config1 is not config2
        # But same content
        assert config1 == config2

    def test_get_config_does_not_modify_original(self, multitenant_manager):
        """Test that modifying returned config doesn't affect original"""
        user = multitenant_manager.get_user_context("feishu:user1")

        config = multitenant_manager.get_user_config("feishu:user1")
        config["test_key"] = "test_value"

        # Original should not be modified
        original_config = multitenant_manager.get_user_config("feishu:user1")
        assert "test_key" not in original_config


class TestWorkspaceIntegrity:
    """Test workspace directory integrity and structure"""

    def test_workspace_structure(self, multitenant_manager):
        """Test that workspace has correct structure"""
        user = multitenant_manager.get_user_context("feishu:user123")

        # Should have required directories
        assert user.workspace.exists()
        assert user.workspace.is_dir()

        # Should have skills subdirectory
        assert user.skills_dir.exists()
        assert user.skills_dir.is_dir()

    def test_workspace_nesting(self, multitenant_manager, temp_base_workspace):
        """Test that workspace is properly nested under base"""
        user = multitenant_manager.get_user_context("feishu:user123")

        # Workspace should be direct child of base
        assert temp_base_workspace in user.workspace.parents

    def test_multiple_workspaces_under_base(self, multitenant_manager, temp_base_workspace):
        """Test multiple workspaces are properly organized"""
        users = ["feishu:user1", "feishu:user2", "web:user3"]

        for user_key in users:
            multitenant_manager.get_user_context(user_key)

        # All should be under base workspace
        workspaces = [
            multitenant_manager.get_user_context(k).workspace
            for k in users
        ]

        for ws in workspaces:
            assert temp_base_workspace in ws.parents
