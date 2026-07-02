"""
Unit tests for FastReAct Nano v2.0 configuration
"""

import os
import pytest
import tempfile
from pathlib import Path

from fastreact.core.config import (
    AuthConfig,
    Config,
    LLMConfig,
    PathsConfig,
    ServiceConfig,
    ToolConfig,
    ReactConfig,
    default_config,
)


class TestLLMConfig:
    """Test LLMConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = LLMConfig()
        assert config.model == "gpt-4o-mini"
        assert config.api_base is None
        assert config.api_key is None
        assert config.api_key_file is None
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_from_env(self):
        """Test creating configuration from environment"""
        # Set environment variables
        os.environ["FASTRACT_MODEL"] = "gpt-4"
        os.environ["FASTRACT_API_BASE"] = "https://api.example.com"
        os.environ["FASTRACT_API_KEY"] = "test-key-123"
        os.environ["FASTRACT_TEMPERATURE"] = "0.5"
        os.environ["FASTRACT_MAX_TOKENS"] = "2048"

        try:
            config = LLMConfig.from_env()
            assert config.model == "gpt-4"
            assert config.api_base == "https://api.example.com"
            assert config.api_key == "test-key-123"
            assert config.temperature == 0.5
            assert config.max_tokens == 2048
        finally:
            # Clean up
            del os.environ["FASTRACT_MODEL"]
            del os.environ["FASTRACT_API_BASE"]
            del os.environ["FASTRACT_API_KEY"]
            del os.environ["FASTRACT_TEMPERATURE"]
            del os.environ["FASTRACT_MAX_TOKENS"]

    def test_from_env_defaults(self):
        """Test that from_env uses defaults when env vars not set"""
        # Ensure env vars are not set
        for key in ["FASTRACT_MODEL", "FASTRACT_TEMPERATURE", "FASTRACT_MAX_TOKENS"]:
            os.environ.pop(key, None)

        config = LLMConfig.from_env()
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096


class TestServiceConfig:
    """Test ServiceConfig"""

    def test_default_values(self):
        config = ServiceConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 18741
        assert config.log_level == "info"
        assert config.service_token is None


class TestPathsConfig:
    """Test runtime workspace path configuration."""

    def test_default_workspaces_root_is_home_fastreact_workspaces(self):
        config = PathsConfig()

        assert config.workspaces_root == Path.home() / "FastReAct_workspaces"
        assert config.gateway_workspace == Path.home() / "FastReAct_workspaces" / "single" / "default"

    def test_from_env_overrides_workspaces_root(self, monkeypatch, tmp_path):
        root = tmp_path / "FastReAct_workspaces"
        monkeypatch.setenv("FASTREACT_WORKSPACES_ROOT", str(root))
        monkeypatch.delenv("FASTREACT_GATEWAY_WORKSPACE", raising=False)
        monkeypatch.delenv("FASTRACT_GATEWAY_WORKSPACE", raising=False)

        config = PathsConfig.from_env()

        assert config.workspaces_root == root
        assert config.gateway_workspace == root / "single" / "default"

    def test_load_paths_config_can_override_root_and_legacy_gateway_workspace(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text(
            """
{
  "paths": {
    "workspaces_root": "%s",
    "gateway_workspace": "%s"
  }
}
"""
            % (tmp_path / "root", tmp_path / "legacy"),
            encoding="utf-8",
        )

        config = Config.load(config_path)

        assert config.paths.workspaces_root == tmp_path / "root"
        assert config.paths.gateway_workspace == tmp_path / "legacy"


class TestAuthConfig:
    """Test inbound identity configuration."""

    def test_default_auth_mode_is_service_token(self):
        config = AuthConfig()

        assert config.mode == "service_token"
        assert config.trusted_header_user_key == "X-FastReAct-User-Key"
        assert config.jwt_tenant_claims == ["tenant_key", "tenant_id", "tenant", "org_id"]

    def test_from_env_resolves_named_jwt_secret(self, monkeypatch):
        monkeypatch.setenv("AUTHNODE_JWT_SECRET", "shared-authnode-secret")
        monkeypatch.setenv("FASTREACT_AUTH_MODE", "jwt")
        monkeypatch.setenv("FASTREACT_AUTH_JWT_SECRET_ENV", "AUTHNODE_JWT_SECRET")

        config = AuthConfig.from_env()

        assert config.mode == "jwt"
        assert config.jwt_secret == "shared-authnode-secret"
        assert config.jwt_secret_env == "AUTHNODE_JWT_SECRET"
        assert config.jwt_tenant_claims == ["tenant_key", "tenant_id", "tenant", "org_id"]

    def test_from_dict_supports_jwt_claim_mapping(self):
        config = AuthConfig.from_dict(
            {
                "mode": "jwt",
                "jwt_secret": "secret",
                "jwt_tenant_claims": "tenant,org_id",
                "jwt_user_claim": "user_id",
            }
        )

        assert config.mode == "jwt"
        assert config.jwt_secret == "secret"
        assert config.jwt_tenant_claims == ["tenant", "org_id"]
        assert config.jwt_user_claim == "user_id"


class TestToolConfig:
    """Test ToolConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = ToolConfig()
        assert config.max_file_size == 1024 * 1024
        assert len(config.protected_paths) > 0
        assert config.exec_timeout == 30
        assert config.working_dir is None

    def test_from_env(self):
        """Test creating configuration from environment"""
        os.environ["FASTRACT_MAX_FILE_SIZE"] = "2048000"
        os.environ["FASTRACT_EXEC_TIMEOUT"] = "60"
        os.environ["FASTRACT_WORKING_DIR"] = "/tmp/work"

        try:
            config = ToolConfig.from_env()
            assert config.max_file_size == 2048000
            assert config.exec_timeout == 60
            assert config.working_dir == Path("/tmp/work")
        finally:
            del os.environ["FASTRACT_MAX_FILE_SIZE"]
            del os.environ["FASTRACT_EXEC_TIMEOUT"]
            del os.environ["FASTRACT_WORKING_DIR"]


class TestReactConfig:
    """Test ReactConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = ReactConfig()
        assert config.max_iterations == 20
        assert config.enable_steering is True
        assert config.enable_followup is True
        assert config.steering_file == Path.cwd() / ".steering.jsonl"

    def test_from_env(self):
        """Test creating configuration from environment"""
        os.environ["FASTRACT_MAX_ITERATIONS"] = "30"
        os.environ["FASTRACT_ENABLE_STEERING"] = "false"
        os.environ["FASTRACT_ENABLE_FOLLOWUP"] = "false"
        os.environ["FASTRACT_STEERING_FILE"] = "/tmp/steering.jsonl"

        try:
            config = ReactConfig.from_env()
            assert config.max_iterations == 30
            assert config.enable_steering is False
            assert config.enable_followup is False
            assert config.steering_file == Path("/tmp/steering.jsonl")
        finally:
            del os.environ["FASTRACT_MAX_ITERATIONS"]
            del os.environ["FASTRACT_ENABLE_STEERING"]
            del os.environ["FASTRACT_ENABLE_FOLLOWUP"]
            del os.environ["FASTRACT_STEERING_FILE"]


class TestConfig:
    """Test main Config"""

    def test_default_config(self):
        """Test default configuration"""
        config = Config()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.tools, ToolConfig)
        assert isinstance(config.react, ReactConfig)
        assert isinstance(config.service, ServiceConfig)

    def test_load_json_api_key_file_and_service_token(self, tmp_path):
        key_file = tmp_path / "api_key.json"
        key_file.write_text(
            '{"api_key":"sk-test","model":"deepseek-v4-flash","base_url":"https://api.deepseek.com","service_token":"local-token"}',
            encoding="utf-8",
        )
        config_file = tmp_path / "fastreact.json"
        config_file.write_text(
            '{"llm":{"api_key_file":"%s"},"service":{"host":"127.0.0.1","port":8010},"mcp":{"servers":[{"name":"pska","command":"pska","args":["mcp-server"],"env":{"PSKA_DATABASE_URL":"postgresql:///pska"}}]}}'
            % str(key_file),
            encoding="utf-8",
        )

        config = Config.load(config_file)

        assert config.llm.api_key == "sk-test"
        assert config.llm.model == "deepseek-v4-flash"
        assert config.llm.api_base == "https://api.deepseek.com"
        assert config.service.host == "127.0.0.1"
        assert config.service.port == 8010
        assert config.service.service_token == "local-token"
        assert config.mcp.servers[0].env == {"PSKA_DATABASE_URL": "postgresql:///pska"}

    def test_load_json_react_context_settings(self, tmp_path):
        config_file = tmp_path / "fastreact.json"
        config_file.write_text(
            """
            {
              "react": {
                "max_iterations": 9,
                "max_context_tokens": 64000,
                "context_warning_threshold": 0.7,
                "max_tool_output_chars": 20000,
                "use_tiktoken": false,
                "tiktoken_model": "deepseek-chat",
                "sliding_window_size": 30,
                "enable_filesystem_memory": false,
                "max_tree_depth": 2,
                "max_files_per_dir": 25,
                "enable_safety": false,
                "strict_mode": true,
                "auto_approve_safe": false
              }
            }
            """,
            encoding="utf-8",
        )

        config = Config.load(config_file)

        assert config.react.max_iterations == 9
        assert config.react.max_context_tokens == 64000
        assert config.react.context_warning_threshold == 0.7
        assert config.react.max_tool_output_chars == 20000
        assert config.react.use_tiktoken is False
        assert config.react.tiktoken_model == "deepseek-chat"
        assert config.react.sliding_window_size == 30
        assert config.react.enable_filesystem_memory is False
        assert config.react.max_tree_depth == 2
        assert config.react.max_files_per_dir == 25
        assert config.react.enable_safety is False
        assert config.react.strict_mode is True
        assert config.react.auto_approve_safe is False

    def test_from_env(self):
        """Test creating full config from environment"""
        os.environ["FASTRACT_MODEL"] = "gpt-4"
        os.environ["FASTRACT_MAX_ITERATIONS"] = "50"

        try:
            config = Config.from_env()
            assert config.llm.model == "gpt-4"
            assert config.react.max_iterations == 50
        finally:
            del os.environ["FASTRACT_MODEL"]
            del os.environ["FASTRACT_MAX_ITERATIONS"]

    def test_save_and_load(self):
        """Test saving and loading configuration"""
        config = Config()
        config.llm.model = "gpt-4"
        config.react.max_iterations = 100

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            config_path = Path(f.name)

        try:
            # Save
            config.save(config_path)
            assert config_path.exists()

            # Load (note: load currently just creates from_env)
            # TODO: Implement proper deserialization
            loaded_config = Config.load(config_path)
            assert isinstance(loaded_config, Config)

        finally:
            config_path.unlink()


if __name__ == "__main__":
    test = TestLLMConfig()
    test.test_default_values()
    print("[OK] LLMConfig: default_values")
    test.test_from_env()
    print("[OK] LLMConfig: from_env")
    test.test_from_env_defaults()
    print("[OK] LLMConfig: from_env_defaults")

    test = TestToolConfig()
    test.test_default_values()
    print("[OK] ToolConfig: default_values")
    test.test_from_env()
    print("[OK] ToolConfig: from_env")

    test = TestReactConfig()
    test.test_default_values()
    print("[OK] ReactConfig: default_values")
    test.test_from_env()
    print("[OK] ReactConfig: from_env")

    test = TestConfig()
    test.test_default_config()
    print("[OK] Config: default_config")
    test.test_from_env()
    print("[OK] Config: from_env")
    test.test_save_and_load()
    print("[OK] Config: save_and_load")

    print("\n[SUCCESS] All config tests passed!")
