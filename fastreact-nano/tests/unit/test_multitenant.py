"""
Unit tests for multi-tenant isolation

Tests that users have properly isolated workspaces, configs, and skills.
"""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastreact.core.multitenant import MultiTenantManager, SecurityError, UserContext


class TestUserContext:
    """Test UserContext dataclass"""

    def test_user_context_creation(self):
        """UserContext should be created with correct fields"""
        context = UserContext(
            user_key="feishu:ou_123",
            workspace=Path("/tmp/workspace"),
            config={"test": "value"},
            skills_dir=Path("/tmp/skills"),
            memory_file=Path("/tmp/memory.json"),
        )

        assert context.user_key == "feishu:ou_123"
        assert context.workspace == Path("/tmp/workspace")
        assert context.config == {"test": "value"}
        assert context.skills_dir == Path("/tmp/skills")
        assert context.memory_file == Path("/tmp/memory.json")
        assert context.tenant_key == ""


class TestMultiTenantManager:
    """Test MultiTenantManager functionality"""

    def test_manager_initialization(self):
        """MultiTenantManager should initialize correctly"""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir).resolve()
            manager = MultiTenantManager(workspace)

            assert manager._base_workspace == workspace
            assert len(manager.list_users()) == 0

    def test_parse_user_key(self):
        """Manager should parse user_key correctly"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Create user contexts
            context1 = manager.get_user_context("feishu:ou_123")
            context2 = manager.get_user_context("web:user@example.com")
            context3 = manager.get_user_context("cli:local")

            assert context1.user_key == "feishu:ou_123"
            assert context2.user_key == "web:user@example.com"
            assert context3.user_key == "cli:local"

    def test_invalid_user_key_format(self):
        """Manager should reject invalid user_key format"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            with pytest.raises(ValueError, match="Invalid user_key format"):
                manager.get_user_context("invalid_format")

    def test_invalid_user_key_empty_parts(self):
        """Manager should reject user_key with empty parts"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Empty channel
            with pytest.raises(ValueError, match="Channel and user_id must not be empty"):
                manager.get_user_context(":user_id")

            # Empty user_id
            with pytest.raises(ValueError, match="Channel and user_id must not be empty"):
                manager.get_user_context("channel:")

    def test_workspace_creation(self):
        """Manager should create user workspace directories"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context
            context = manager.get_user_context("feishu:ou_abc123")

            # Check workspace exists
            assert context.workspace.exists()
            assert context.workspace.is_dir()

            # Check workspace name
            assert context.workspace.name == "feishu_ou_abc123"

    def test_workspace_isolation(self):
        """Different users should have isolated workspaces"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get two user contexts
            context_a = manager.get_user_context("feishu:ou_aaa")
            context_b = manager.get_user_context("feishu:ou_bbb")

            # Check workspaces are different
            assert context_a.workspace != context_b.workspace

            # Check both exist
            assert context_a.workspace.exists()
            assert context_b.workspace.exists()

            # Create file in user A's workspace
            (context_a.workspace / "test.txt").write_text("User A data")

            # Check file doesn't exist in user B's workspace
            assert not (context_b.workspace / "test.txt").exists()

    def test_user_config_creation(self):
        """Manager should create user config files"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context
            context = manager.get_user_context("feishu:ou_xyz")

            # Check config file exists
            config_file = context.workspace / "config.json"
            assert config_file.exists()

            # Load and check config
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert config["user_key"] == "feishu:ou_xyz"
            assert config["tenant_key"] == "feishu"
            assert config["channel"] == "feishu"
            assert config["user_id"] == "ou_xyz"
            assert "preferences" in config

    def test_user_config_persistence(self):
        """User config should persist across context retrievals"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context first time
            context1 = manager.get_user_context("feishu:ou_persist")

            # Update config
            context1.config["custom_field"] = "custom_value"
            manager.update_user_config("feishu:ou_persist", {"custom_field": "custom_value"})

            # Clear cache
            manager.clear_cache()

            # Get user context second time
            context2 = manager.get_user_context("feishu:ou_persist")

            # Check config persisted
            assert context2.config.get("custom_field") == "custom_value"

    def test_user_skills_directory(self):
        """Manager should create user skills directory"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context
            context = manager.get_user_context("feishu:ou_skills")

            # Check skills directory exists
            assert context.skills_dir.exists()
            assert context.skills_dir.is_dir()
            assert context.skills_dir.name == "skills"

    def test_user_memory_file(self):
        """Manager should create user memory file path"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context
            context = manager.get_user_context("feishu:ou_memory")

            # Check memory file path
            assert context.memory_file.name == "memory.json"
            assert context.memory_file.parent == context.workspace

    def test_get_user_workspace(self):
        """Manager should return correct workspace path"""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir).resolve()
            manager = MultiTenantManager(workspace)

            # Get workspace for user
            user_workspace = manager.get_user_workspace("feishu:ou_workspace")

            # Check path (use resolve() for cross-platform compatibility)
            expected = workspace / "tenants" / "feishu" / "users" / "feishu_ou_workspace"
            assert user_workspace == expected

    def test_explicit_tenant_key_controls_workspace_layout(self):
        """Explicit tenant_key should separate users from identity-provider prefixes."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            manager = MultiTenantManager(root)

            context = manager.get_user_context("sso:alice", tenant_key="acme")

            assert context.tenant_key == "acme"
            assert context.workspace == root / "tenants" / "acme" / "users" / "sso_alice"
            assert context.workspace.exists()

    def test_same_user_key_can_exist_in_different_tenants(self):
        """Context cache keys include tenant_key so tenants cannot share workspaces."""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir).resolve())

            acme = manager.get_user_context("sso:alice", tenant_key="acme")
            beta = manager.get_user_context("sso:alice", tenant_key="beta")

            assert acme.workspace != beta.workspace
            assert acme.tenant_key == "acme"
            assert beta.tenant_key == "beta"

    def test_invalid_tenant_key_is_rejected(self):
        """Tenant keys must not be able to escape the workspace root."""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir).resolve())

            with pytest.raises(SecurityError, match="Tenant key"):
                manager.get_user_context("sso:alice", tenant_key="../acme")

    def test_update_user_config(self):
        """Manager should update user config"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context
            context = manager.get_user_context("feishu:ou_update")

            # Update config
            manager.update_user_config(
                "feishu:ou_update",
                {
                    "test_key": "test_value",
                    "nested": {"key": "value"}
                }
            )

            # Reload config from file
            config_file = context.workspace / "config.json"
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Check updates
            assert config.get("test_key") == "test_value"
            assert config.get("nested", {}).get("key") == "value"

    def test_get_user_config(self):
        """Manager should return user config copy"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get user context
            context = manager.get_user_context("feishu:ou_getconfig")

            # Get config
            config = manager.get_user_config("feishu:ou_getconfig")

            # Check it's a copy (not the same object)
            assert config is not context.config

            # Check content
            assert config["user_key"] == "feishu:ou_getconfig"

    def test_list_users(self):
        """Manager should list all loaded users"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Initially empty
            assert manager.list_users() == []

            # Add users
            manager.get_user_context("feishu:ou_user1")
            manager.get_user_context("feishu:ou_user2")
            manager.get_user_context("web:user@example.com")

            # List users
            users = manager.list_users()
            assert len(users) == 3
            assert "feishu:ou_user1" in users
            assert "feishu:ou_user2" in users
            assert "web:user@example.com" in users

    def test_clear_cache(self):
        """Manager should clear user context cache"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Add users
            manager.get_user_context("feishu:ou_cache1")
            manager.get_user_context("feishu:ou_cache2")

            assert len(manager.list_users()) == 2

            # Clear cache
            manager.clear_cache()

            # Check cache cleared
            assert len(manager.list_users()) == 0

    def test_special_characters_in_user_id(self):
        """Manager should reject special characters that pose security risks"""
        from fastreact.core.multitenant import SecurityError

        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir).resolve())

            # User ID with slashes - rejected by security policy
            with pytest.raises(SecurityError, match="unsafe characters"):
                manager.get_user_context("feishu:ou/abc:123")

            # User ID with allowed special characters (underscores, hyphens)
            context = manager.get_user_context("feishu:ou_abc-123")
            assert context.workspace.name == "feishu_ou_abc-123"

    def test_repeated_user_context_retrieval(self):
        """Manager should return same context for repeated calls"""
        with TemporaryDirectory() as tmpdir:
            manager = MultiTenantManager(Path(tmpdir))

            # Get context twice
            context1 = manager.get_user_context("feishu:ou_repeat")
            context2 = manager.get_user_context("feishu:ou_repeat")

            # Should be same object (cached)
            assert context1 is context2
