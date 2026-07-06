"""
Unit tests for Configuration System

Tests for:
- v1 to v2 configuration migration (multi-provider format)
- Environment variable priority chain (config file → env vars → defaults)
- Multi-provider configuration (SiliconFlow, OpenAI, Anthropic, etc.)
- Path validation and security checks
- Config file discovery (multiple search paths)
- Default value fallbacks
- Invalid config handling
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, Mock

from fastreact.core.config import (
    Config,
    LLMConfig,
    ToolConfig,
    ReactConfig,
    ServiceConfig,
    ExtensionConfig,
    MCPConfig,
    MCPServerConfig,
    PathsConfig,
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file"""
    config_file = tmp_path / "config.json"
    yield config_file
    # Cleanup is automatic


@pytest.fixture
def clean_env():
    """Clean environment variables before tests"""
    original_env = os.environ.copy()
    os.environ.clear()
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestV1ToV2Migration:
    """Test v1 to v2 configuration migration"""

    def test_migration_v1_siliconflow_provider(self, temp_config_file, clean_env):
        """Test migration from v1 SiliconFlow provider format"""
        # v1 format with providers dict
        v1_config = {
            "llm": {
                "providers": {
                    "siliconflow": {
                        "enabled": True,
                        "model": "deepseek-chat",
                        "base_url": "https://api.siliconflow.cn/v1",
                        "api_key": "sk-test-key",
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    }
                },
                "default_provider": "siliconflow"
            },
            "tools": {
                "max_file_size": 1024 * 1024,
                "protected_paths": ["/etc/passwd"]
            },
            "react": {
                "max_iterations": 20
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        # Load config (should migrate from v1)
        config = Config.load(temp_config_file)

        # Verify migration
        assert config.llm.model == "deepseek-chat"  # SiliconFlow model preserved
        assert config.llm.api_base == "https://api.siliconflow.cn/v1"
        assert config.llm.api_key == "sk-test-key"
        assert config.llm.temperature == 0.7
        assert config.llm.max_tokens == 4096

    def test_migration_v1_openai_provider(self, temp_config_file, clean_env):
        """Test migration from v1 OpenAI provider format"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": True,
                        "model": "gpt-4",
                        "base_url": "https://api.openai.com/v1",
                        "api_key_env": "OPENAI_API_KEY",
                        "temperature": 0.5,
                    }
                },
                "default_provider": "openai"
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        # Set environment variable
        os.environ["OPENAI_API_KEY"] = "sk-env-key"

        config = Config.load(temp_config_file)

        # Verify migration with environment variable
        assert config.llm.model == "openai/gpt-4"  # Provider prefix added
        assert config.llm.api_key == "sk-env-key"  # Read from env
        assert config.llm.temperature == 0.5

    def test_migration_v1_anthropic_provider(self, temp_config_file, clean_env):
        """Test migration from v1 Anthropic provider format"""
        v1_config = {
            "llm": {
                "providers": {
                    "anthropic": {
                        "enabled": True,
                        "model": "claude-3-sonnet",
                        "api_key": "sk-ant-key",
                    }
                }
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Verify Anthropic migration
        assert config.llm.model == "anthropic/claude-3-sonnet"
        assert config.llm.api_key == "sk-ant-key"

    def test_migration_v1_deepseek_provider(self, temp_config_file, clean_env):
        """Test migration from v1 DeepSeek provider format"""
        v1_config = {
            "llm": {
                "providers": {
                    "deepseek": {
                        "enabled": True,
                        "model": "deepseek-coder",
                        "api_key": "sk-deepseek-key",
                    }
                }
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Verify DeepSeek migration
        assert config.llm.model == "deepseek/deepseek-coder"
        assert config.llm.api_key == "sk-deepseek-key"

    def test_migration_v1_ollama_provider(self, temp_config_file, clean_env):
        """Test migration from v1 Ollama provider format"""
        v1_config = {
            "llm": {
                "providers": {
                    "ollama": {
                        "enabled": True,
                        "model": "llama3",
                        "base_url": "http://localhost:11434",
                    }
                }
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Verify Ollama migration
        assert config.llm.model == "openai/llama3"  # OpenAI-compatible format
        assert config.llm.api_base == "http://localhost:11434"

    def test_migration_v2_simple_format(self, temp_config_file, clean_env):
        """Test v2 simple format (no providers dict)"""
        v2_config = {
            "llm": {
                "model": "gpt-4o-mini",
                "api_base": "https://api.openai.com/v1",
                "api_key": "sk-test",
                "temperature": 0.7,
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v2_config, f)

        config = Config.load(temp_config_file)

        # Verify direct format (no migration needed)
        assert config.llm.model == "gpt-4o-mini"
        assert config.llm.api_key == "sk-test"
        assert config.llm.temperature == 0.7

    def test_migration_preserves_tools_config(self, temp_config_file, clean_env):
        """Test that tools configuration is preserved during migration"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": True,
                        "model": "gpt-4",
                    }
                }
            },
            "tools": {
                "max_file_size": 2048 * 1024,
                "protected_paths": ["/etc/passwd", "/etc/shadow"],
                "shell_timeout": 60,
                "allowed_dir": "/workspace"
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Verify tools config migrated
        assert config.tools.max_file_size == 2048 * 1024
        assert "/etc/passwd" in config.tools.protected_paths
        assert config.tools.exec_timeout == 60
        assert config.tools.working_dir == Path("/workspace")

    def test_migration_preserves_react_config(self, temp_config_file, clean_env):
        """Test that react configuration is preserved during migration"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": True,
                        "model": "gpt-4",
                    }
                }
            },
            "react": {
                "max_iterations": 30,
                "enable_steering": False,
                "enable_followup": True,
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Verify react config migrated
        assert config.react.max_iterations == 30
        assert config.react.enable_steering is False
        assert config.react.enable_followup is True


class TestEnvironmentVariablePriority:
    """Test environment variable priority chain"""

    def test_env_override_config_file(self, temp_config_file, clean_env):
        """Test that environment variables override config file"""
        # Config file has one value
        config_data = {
            "llm": {
                "model": "gpt-4",
                "api_key": "file-key",
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        # Environment has different value
        os.environ["FASTRACT_MODEL"] = "gpt-4o-mini"
        os.environ["FASTRACT_API_KEY"] = "env-key"

        # Environment variables should NOT override file values
        # (Config.load() reads from file, from_env() reads from env)
        config = Config.load(temp_config_file)

        # File values take precedence (not env)
        assert config.llm.model == "gpt-4"
        assert config.llm.api_key == "file-key"

    def test_from_env_reads_environment(self, clean_env):
        """Test that from_env() reads environment variables"""
        os.environ["FASTRACT_MODEL"] = "claude-3-sonnet"
        os.environ["FASTRACT_API_KEY"] = "sk-env-test"
        os.environ["FASTRACT_TEMPERATURE"] = "0.5"
        os.environ["FASTRACT_MAX_TOKENS"] = "8192"

        config = Config.from_env()

        assert config.llm.model == "claude-3-sonnet"
        assert config.llm.api_key == "sk-env-test"
        assert config.llm.temperature == 0.5
        assert config.llm.max_tokens == 8192

    def test_fallback_to_defaults_when_no_config(self, tmp_path, clean_env):
        """Test fallback to defaults when no config file exists"""
        # Point to non-existent config
        non_existent = tmp_path / "non_existent.json"

        config = Config.load(non_existent)

        # Should use defaults (since from_env() is called)
        assert config.llm.model == "gpt-4o-mini"
        assert config.llm.temperature == 0.7
        assert config.llm.max_tokens == 8192

    def test_openai_api_key_fallback(self, clean_env):
        """Test OPENAI_API_KEY fallback for api_key"""
        # Set OPENAI_API_KEY but not FASTRACT_API_KEY
        os.environ["OPENAI_API_KEY"] = "sk-openai-key"

        config = Config.from_env()

        assert config.llm.api_key == "sk-openai-key"

    def test_fastreact_api_key_priority(self, clean_env):
        """Test FASTRACT_API_KEY takes priority over OPENAI_API_KEY"""
        os.environ["FASTRACT_API_KEY"] = "sk-fastreact-key"
        os.environ["OPENAI_API_KEY"] = "sk-openai-key"

        config = Config.from_env()

        # FASTRACT_API_KEY has priority
        assert config.llm.api_key == "sk-fastreact-key"

    def test_tools_env_variables(self, clean_env):
        """Test tools configuration from environment"""
        os.environ["FASTRACT_MAX_FILE_SIZE"] = "2048000"
        os.environ["FASTRACT_EXEC_TIMEOUT"] = "60"
        os.environ["FASTRACT_WORKING_DIR"] = "/workspace"

        config = Config.from_env()

        assert config.tools.max_file_size == 2048000
        assert config.tools.exec_timeout == 60
        assert config.tools.working_dir == Path("/workspace")

    def test_react_env_variables(self, clean_env):
        """Test react configuration from environment"""
        os.environ["FASTRACT_MAX_ITERATIONS"] = "30"
        os.environ["FASTRACT_ENABLE_STEERING"] = "false"
        os.environ["FASTRACT_ENABLE_FOLLOWUP"] = "true"

        config = Config.from_env()

        assert config.react.max_iterations == 30
        assert config.react.enable_steering is False
        assert config.react.enable_followup is True

    def test_boolean_env_parsing(self, clean_env):
        """Test boolean environment variable parsing"""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
        ]

        for env_val, expected in test_cases:
            os.environ["FASTRACT_ENABLE_STEERING"] = env_val
            config = Config.from_env()
            assert config.react.enable_steering == expected, f"Failed for {env_val}"

    def test_mcp_env_variable(self, clean_env):
        """Test MCP servers from environment variable"""
        mcp_servers = [
            {
                "name": "test-server",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-test"],
                "isolation": "shared"
            }
        ]

        os.environ["FASTRACT_MCP_SERVERS"] = json.dumps(mcp_servers)

        config = Config.from_env()

        assert len(config.mcp.servers) == 1
        assert config.mcp.servers[0].name == "test-server"
        assert config.mcp.servers[0].isolation == "shared"


class TestMultiProviderConfig:
    """Test multi-provider configuration"""

    def test_default_provider_selection(self, temp_config_file, clean_env):
        """Test that default_provider is respected when others are disabled"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": False,  # Disabled
                        "model": "gpt-4",
                    },
                    "anthropic": {
                        "enabled": True,  # Enabled default
                        "model": "claude-3-sonnet",
                    }
                },
                "default_provider": "anthropic"
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Should use Anthropic (only enabled provider that is default)
        assert config.llm.model == "anthropic/claude-3-sonnet"

    def test_first_enabled_provider_when_no_default(self, temp_config_file, clean_env):
        """Test that first enabled provider is used when no default specified"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": True,
                        "model": "gpt-4",
                    },
                    "anthropic": {
                        "enabled": True,
                        "model": "claude-3-sonnet",
                    }
                }
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Should use first enabled (openai)
        assert "openai" in config.llm.model

    def test_skip_disabled_provider(self, temp_config_file, clean_env):
        """Test that disabled providers are skipped"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": False,
                        "model": "gpt-4",
                    },
                    "anthropic": {
                        "enabled": True,
                        "model": "claude-3-sonnet",
                    }
                }
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Should skip disabled openai and use anthropic
        assert "anthropic" in config.llm.model

    def test_model_without_provider_prefix(self, temp_config_file, clean_env):
        """Test models that already have provider prefix"""
        v1_config = {
            "llm": {
                "providers": {
                    "openai": {
                        "enabled": True,
                        "model": "azure/gpt-4",  # Already has prefix
                    }
                }
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(v1_config, f)

        config = Config.load(temp_config_file)

        # Should not double-prefix
        assert config.llm.model == "azure/gpt-4"


class TestConfigFileDiscovery:
    """Test config file discovery in multiple search paths"""

    def test_discovery_home_directory(self, tmp_path, clean_env):
        """Test discovery in ~/.fastreact/config.json"""
        # Create mock home directory
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True)
        fastreact_dir = mock_home / ".fastreact"
        fastreact_dir.mkdir()
        config_file = fastreact_dir / "config.json"

        config_data = {"llm": {"model": "home-config-model"}}
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with patch("pathlib.Path.home", return_value=mock_home):
            config = Config.load()

        assert config.llm.model == "home-config-model"

    def test_discovery_cwd_fastreact_directory(self, tmp_path, clean_env):
        """Test discovery in ./.fastreact/config.json"""
        cwd = tmp_path
        fastreact_dir = cwd / ".fastreact"
        fastreact_dir.mkdir()
        config_file = fastreact_dir / "config.json"

        config_data = {"llm": {"model": "cwd-config-model"}}
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Also patch home to prevent picking up real config
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            with patch("pathlib.Path.cwd", return_value=cwd):
                config = Config.load()

        assert config.llm.model == "cwd-config-model"

    def test_discovery_cwd_root(self, tmp_path, clean_env):
        """Test discovery in ./config.json"""
        cwd = tmp_path
        config_file = cwd / "config.json"

        config_data = {"llm": {"model": "root-config-model"}}
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Also patch home to prevent picking up real config
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True)

        with patch("pathlib.Path.home", return_value=mock_home):
            with patch("pathlib.Path.cwd", return_value=cwd):
                config = Config.load()

        assert config.llm.model == "root-config-model"

    def test_discovery_priority_order(self, tmp_path, clean_env):
        """Test that discovery follows priority: home → ./.fastreact → ./"""
        cwd = tmp_path

        # Create all three config files
        # 1. ./config.json (lowest priority for cwd)
        root_config = cwd / "config.json"
        with open(root_config, "w") as f:
            json.dump({"llm": {"model": "root"}}, f)

        # 2. ./.fastreact/config.json (medium priority)
        fastreact_dir = cwd / ".fastreact"
        fastreact_dir.mkdir()
        local_config = fastreact_dir / "config.json"
        with open(local_config, "w") as f:
            json.dump({"llm": {"model": "local"}}, f)

        # 3. ~/.fastreact/config.json (highest priority)
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True)
        home_fastreact = mock_home / ".fastreact"
        home_fastreact.mkdir()
        home_config = home_fastreact / "config.json"
        with open(home_config, "w") as f:
            json.dump({"llm": {"model": "home"}}, f)

        # Should find home config first
        with patch("pathlib.Path.home", return_value=mock_home):
            with patch("pathlib.Path.cwd", return_value=cwd):
                config = Config.load()

        assert config.llm.model == "home"

    def test_discovery_uses_first_available(self, tmp_path, clean_env):
        """Test that discovery stops at first available config"""
        cwd = tmp_path

        # Only create home config (others don't exist)
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True)
        home_fastreact = mock_home / ".fastreact"
        home_fastreact.mkdir()
        home_config = home_fastreact / "config.json"
        with open(home_config, "w") as f:
            json.dump({"llm": {"model": "home-only"}}, f)

        with patch("pathlib.Path.home", return_value=mock_home):
            with patch("pathlib.Path.cwd", return_value=cwd):
                config = Config.load()

        # Should find and use home config
        assert config.llm.model == "home-only"


class TestPathValidationAndSecurity:
    """Test path validation and security checks"""

    def test_paths_config_from_env_reads_user_skills_dir(self, tmp_path, clean_env):
        """Test that user skills dir can be configured from environment."""
        user_skills = tmp_path / "user-skills"
        os.environ["FASTRACT_USER_SKILLS_DIR"] = str(user_skills)

        paths = PathsConfig.from_env()

        assert paths.user_skills_dir == user_skills

    def test_extension_config_defaults_disable_runtime_reload(self, clean_env):
        """Test that runtime reload features are opt-in."""
        extensions = ExtensionConfig.from_env()

        assert extensions.runtime_reload_enabled is False
        assert extensions.mcp_reload_enabled is False

    def test_extension_config_from_env(self, clean_env):
        """Test extension reload flags from environment."""
        os.environ["FASTRACT_EXTENSIONS_RUNTIME_RELOAD"] = "true"
        os.environ["FASTRACT_EXTENSIONS_MCP_RELOAD"] = "true"

        extensions = ExtensionConfig.from_env()

        assert extensions.runtime_reload_enabled is True
        assert extensions.mcp_reload_enabled is True

    def test_config_loads_extensions_block(self, temp_config_file, clean_env):
        """Test loading extension management settings from config."""
        config_data = {
            "extensions": {
                "runtime_reload_enabled": True,
                "mcp_reload_enabled": False,
            }
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        config = Config.load(temp_config_file)

        assert config.extensions.runtime_reload_enabled is True
        assert config.extensions.mcp_reload_enabled is False

    def test_path_conversion_in_save(self, tmp_path, clean_env):
        """Test that Path objects are converted to strings in save()"""
        config_file = tmp_path / "config.json"

        config = Config(
            tools=ToolConfig(working_dir=Path("/workspace")),
            react=ReactConfig(steering_file=Path("/.steering.jsonl"))
        )

        config.save(config_file)

        # Verify file was saved and can be loaded
        with open(config_file, "r") as f:
            data = json.load(f)

        # Paths should be strings
        assert isinstance(data["tools"]["working_dir"], str)
        assert isinstance(data["react"]["steering_file"], str)

    def test_path_conversion_in_load(self, temp_config_file, clean_env):
        """Test that string paths are converted to Path objects in load()"""
        config_data = {
            "tools": {
                "allowed_dir": "/workspace"
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        config = Config.load(temp_config_file)

        # Should be Path object
        assert isinstance(config.tools.working_dir, Path)
        assert config.tools.working_dir == Path("/workspace")

    def test_protected_paths_default(self, clean_env):
        """Test default protected paths"""
        config = Config()

        # Should have default protected paths
        assert len(config.tools.protected_paths) > 0
        assert "/etc/passwd" in config.tools.protected_paths
        assert "/etc/shadow" in config.tools.protected_paths

    def test_empty_working_dir_allowed(self, clean_env):
        """Test that empty working_dir is allowed"""
        config = Config(tools=ToolConfig(working_dir=None))

        assert config.tools.working_dir is None


class TestDefaultValueFallbacks:
    """Test default value fallbacks"""

    def test_llm_defaults(self, clean_env):
        """Test LLM configuration defaults"""
        config = Config()

        assert config.llm.model == "gpt-4o-mini"
        assert config.llm.temperature == 0.7
        assert config.llm.max_tokens == 8192
        assert config.llm.api_base is None
        assert config.llm.api_key is None

    def test_tools_defaults(self, clean_env):
        """Test tools configuration defaults"""
        config = Config()

        assert config.tools.max_file_size == 1024 * 1024  # 1MB
        assert config.tools.exec_timeout == 30
        assert config.tools.working_dir is None
        assert len(config.tools.protected_paths) > 0

    def test_react_defaults(self, clean_env):
        """Test react configuration defaults"""
        config = Config()

        assert config.react.max_iterations == 20
        assert config.react.enable_steering is True
        assert config.react.enable_followup is True
        assert config.react.max_context_tokens == 128000
        assert config.react.context_warning_threshold == 0.8
        assert config.react.max_tool_output_chars == 20000
        assert config.react.enable_filesystem_memory is True
        assert config.react.max_tree_depth == 3
        assert config.react.max_files_per_dir == 50
        assert config.react.enable_safety is True
        assert config.react.strict_mode is False
        assert config.react.auto_approve_safe is True

    def test_mcp_defaults(self, clean_env):
        """Test MCP configuration defaults"""
        config = Config()

        assert len(config.mcp.servers) == 0

    def test_mcp_server_defaults(self, clean_env):
        """Test MCP server configuration defaults"""
        server = MCPServerConfig(
            name="test-server",
            command="npx"
        )

        assert server.name == "test-server"
        assert server.command == "npx"
        assert server.args == []
        assert server.env is None
        assert server.isolation == "shared"
        assert server.idle_timeout == 300
        assert server.max_instances == 10


class TestInvalidConfigHandling:
    """Test invalid configuration handling"""

    def test_empty_config_file(self, temp_config_file, clean_env):
        """Test handling of empty config file"""
        with open(temp_config_file, "w") as f:
            json.dump({}, f)

        config = Config.load(temp_config_file)

        # Should use defaults
        assert config.llm.model == "gpt-4o-mini"

    def test_invalid_json_in_config_file(self, temp_config_file, clean_env):
        """Test handling of invalid JSON"""
        with open(temp_config_file, "w") as f:
            f.write("{ invalid json }")

        # Should raise JSONDecodeError or fallback to defaults
        with pytest.raises(json.JSONDecodeError):
            Config.load(temp_config_file)

    def test_missing_optional_fields(self, temp_config_file, clean_env):
        """Test that missing optional fields use defaults"""
        config_data = {
            "llm": {
                "model": "gpt-4"
                # Missing: api_base, api_key, temperature, max_tokens
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        config = Config.load(temp_config_file)

        # Should have specified value + defaults for missing
        assert config.llm.model == "gpt-4"
        assert config.llm.api_base is None
        assert config.llm.api_key is None
        assert config.llm.temperature == 0.7  # Default
        assert config.llm.max_tokens == 8192  # Default

    def test_invalid_mcp_servers_json(self, clean_env):
        """Test handling of invalid MCP servers JSON"""
        os.environ["FASTRACT_MCP_SERVERS"] = "{ invalid json }"

        config = Config.from_env()

        # Should gracefully handle invalid JSON
        assert len(config.mcp.servers) == 0

    def test_extra_unknown_fields(self, temp_config_file, clean_env):
        """Test that unknown fields are ignored"""
        config_data = {
            "llm": {
                "model": "gpt-4",
                "unknown_field": "should_be_ignored"
            },
            "unknown_section": {
                "data": "ignored"
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        # Should not raise error
        config = Config.load(temp_config_file)
        assert config.llm.model == "gpt-4"


class TestMCPConfiguration:
    """Test MCP server configuration"""

    def test_mcp_config_from_dict(self, clean_env):
        """Test creating MCP config from dictionary"""
        data = {
            "servers": [
                {
                    "name": "test-server",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-test"],
                    "isolation": "shared"
                }
            ]
        }

        config = MCPConfig.from_dict(data)

        assert len(config.servers) == 1
        assert config.servers[0].name == "test-server"
        assert config.servers[0].isolation == "shared"

    def test_mcp_server_all_fields(self, clean_env):
        """Test MCP server with all fields configured"""
        server = MCPServerConfig.from_dict({
            "name": "full-server",
            "command": "python",
            "args": ["-m", "server"],
            "env": {"DEBUG": "1"},
            "associated_skill": "test_skill",
            "description": "Test server",
            "isolation": "per_user",
            "per_user_args_template": ["--user", "{user_key}"],
            "idle_timeout": 600,
            "max_instances": 5
        })

        assert server.name == "full-server"
        assert server.command == "python"
        assert server.args == ["-m", "server"]
        assert server.env == {"DEBUG": "1"}
        assert server.associated_skill == "test_skill"
        assert server.description == "Test server"
        assert server.isolation == "per_user"
        assert server.per_user_args_template == ["--user", "{user_key}"]
        assert server.idle_timeout == 600
        assert server.max_instances == 5

    def test_mcp_server_defaults(self, clean_env):
        """Test MCP server default values"""
        server = MCPServerConfig.from_dict({
            "name": "minimal-server",
            "command": "npx"
        })

        assert server.args == []
        assert server.env is None
        assert server.associated_skill is None
        assert server.description is None
        assert server.isolation == "shared"
        assert server.per_user_args_template is None
        assert server.idle_timeout == 300
        assert server.max_instances == 10


class TestServiceConfiguration:
    """Test headless service configuration."""

    def test_service_config_loads_access_lists_from_dict(self, clean_env):
        config = ServiceConfig.from_dict(
            {
                "rate_limit_per_hour": 25,
                "blocked_user_keys": ["web:blocked"],
                "allowed_user_keys": ["web:alice", "pska:user_primary"],
            }
        )

        assert config.rate_limit_per_hour == 25
        assert config.blocked_user_keys == ["web:blocked"]
        assert config.allowed_user_keys == ["web:alice", "pska:user_primary"]

    def test_service_config_loads_access_lists_from_env(self, clean_env):
        os.environ["FASTREACT_BLOCKED_USER_KEYS"] = "web:blocked, pska:blocked"
        os.environ["FASTREACT_ALLOWED_USER_KEYS"] = "web:alice"

        config = ServiceConfig.from_env()

        assert config.blocked_user_keys == ["web:blocked", "pska:blocked"]
        assert config.allowed_user_keys == ["web:alice"]
