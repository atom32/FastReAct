"""
Configuration management for FastReAct Nano v2.0

Centralized configuration with environment variable support.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


@dataclass
class LLMConfig:
    """LLM provider configuration"""

    model: str = "gpt-4o-mini"
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create from environment variables"""
        return cls(
            model=os.getenv("FASTRACT_MODEL", "gpt-4o-mini"),
            api_base=os.getenv("FASTRACT_API_BASE"),
            api_key=os.getenv("FASTRACT_API_KEY") or os.getenv("OPENAI_API_KEY"),
            temperature=float(os.getenv("FASTRACT_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("FASTRACT_MAX_TOKENS", "4096")),
        )


@dataclass
class ToolConfig:
    """Tool configuration"""

    # File operations
    max_file_size: int = 1024 * 1024  # 1MB
    protected_paths: list[str] = field(default_factory=lambda: [
        "/etc/passwd",
        "/etc/shadow",
        "C:\\Windows\\System32\\*",
    ])

    # Exec
    exec_timeout: int = 30
    working_dir: Optional[Path] = None

    @classmethod
    def from_env(cls) -> "ToolConfig":
        """Create from environment variables"""
        return cls(
            max_file_size=int(os.getenv("FASTRACT_MAX_FILE_SIZE", str(1024 * 1024))),
            exec_timeout=int(os.getenv("FASTRACT_EXEC_TIMEOUT", "30")),
            working_dir=Path(os.getenv("FASTRACT_WORKING_DIR")) if os.getenv("FASTRACT_WORKING_DIR") else None,
        )


@dataclass
class ReactConfig:
    """ReAct loop configuration"""

    max_iterations: int = 20
    enable_steering: bool = True
    enable_followup: bool = True
    steering_file: Path = field(default_factory=lambda: Path.cwd() / ".steering.jsonl")

    # Context monitoring
    max_context_tokens: int = 128000
    context_warning_threshold: float = 0.8
    max_tool_output_chars: int = 5000

    # Filesystem memory (Ghost Map)
    enable_filesystem_memory: bool = True
    max_tree_depth: int = 3
    max_files_per_dir: int = 50

    # Safety policy (Guardrails)
    enable_safety: bool = True
    strict_mode: bool = False
    auto_approve_safe: bool = True

    @classmethod
    def from_env(cls) -> "ReactConfig":
        """Create from environment variables"""
        steering_path = os.getenv("FASTRACT_STEERING_FILE")
        return cls(
            max_iterations=int(os.getenv("FASTRACT_MAX_ITERATIONS", "20")),
            enable_steering=os.getenv("FASTRACT_ENABLE_STEERING", "true").lower() == "true",
            enable_followup=os.getenv("FASTRACT_ENABLE_FOLLOWUP", "true").lower() == "true",
            steering_file=Path(steering_path) if steering_path else Path.cwd() / ".steering.jsonl",
            max_context_tokens=int(os.getenv("FASTRACT_MAX_CONTEXT_TOKENS", "128000")),
            context_warning_threshold=float(os.getenv("FASTRACT_CONTEXT_WARNING_THRESHOLD", "0.8")),
            max_tool_output_chars=int(os.getenv("FASTRACT_MAX_TOOL_OUTPUT_CHARS", "5000")),
            enable_filesystem_memory=os.getenv("FASTRACT_ENABLE_FILESYSTEM_MEMORY", "true").lower() == "true",
            max_tree_depth=int(os.getenv("FASTRACT_MAX_TREE_DEPTH", "3")),
            max_files_per_dir=int(os.getenv("FASTRACT_MAX_FILES_PER_DIR", "50")),
            enable_safety=os.getenv("FASTRACT_ENABLE_SAFETY", "true").lower() == "true",
            strict_mode=os.getenv("FASTRICT_MODE", "false").lower() == "true",
            auto_approve_safe=os.getenv("FASTRACT_AUTO_APPROVE_SAFE", "true").lower() == "true",
        )


@dataclass
class Config:
    """
    Main configuration for FastReAct Nano

    Environment variables:
        FASTRACT_MODEL: Model name (default: gpt-4o-mini)
        FASTRACT_API_BASE: API base URL
        FASTRACT_API_KEY: API key (also checks OPENAI_API_KEY)
        FASTRACT_TEMPERATURE: Temperature (default: 0.7)
        FASTRACT_MAX_TOKENS: Max tokens (default: 4096)
        FASTRACT_MAX_FILE_SIZE: Max file size in bytes (default: 1048576)
        FASTRACT_EXEC_TIMEOUT: Exec timeout in seconds (default: 30)
        FASTRACT_WORKING_DIR: Working directory for exec
        FASTRACT_MAX_ITERATIONS: Max ReAct iterations (default: 20)
        FASTRACT_ENABLE_STEERING: Enable steering (default: true)
        FASTRACT_ENABLE_FOLLOWUP: Enable follow-up (default: true)
        FASTRACT_STEERING_FILE: Steering file path
        FASTRACT_MAX_CONTEXT_TOKENS: Max context window size (default: 128000)
        FASTRACT_CONTEXT_WARNING_THRESHOLD: Context warning threshold (default: 0.8)
        FASTRACT_MAX_TOOL_OUTPUT_CHARS: Max tool output chars (default: 5000)
        FASTRACT_ENABLE_FILESYSTEM_MEMORY: Enable filesystem memory (default: true)
        FASTRACT_MAX_TREE_DEPTH: Max tree depth for filesystem memory (default: 3)
        FASTRACT_MAX_FILES_PER_DIR: Max files per dir in tree (default: 50)
        FASTRACT_ENABLE_SAFETY: Enable safety guardrails (default: true)
        FASTRICT_MODE: Require confirmation for all modifications (default: false)
        FASTRACT_AUTO_APPROVE_SAFE: Auto-approve safe operations (default: true)
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    react: ReactConfig = field(default_factory=ReactConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables"""
        return cls(
            llm=LLMConfig.from_env(),
            tools=ToolConfig.from_env(),
            react=ReactConfig.from_env(),
        )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from file or environment

        Args:
            config_path: Path to config file (JSON). If None, tries default locations.

        Returns:
            Config instance with loaded settings
        """
        import json
        from pathlib import Path as LibPath

        # Default config locations to try
        if config_path is None:
            default_paths = [
                LibPath.home() / ".fastreact" / "config.json",
                LibPath.cwd() / ".fastreact" / "config.json",
                LibPath.cwd() / "config.json",
            ]
            for path in default_paths:
                if path.exists():
                    config_path = path
                    break

        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse v1 config format (multi-provider)
            llm_config = LLMConfig()
            tools_config = ToolConfig()
            react_config = ReactConfig()

            # Extract LLM configuration
            if "llm" in data:
                llm_data = data["llm"]

                # v1 format: has providers dict
                if "providers" in llm_data:
                    providers = llm_data["providers"]
                    default_provider = llm_data.get("default_provider", "")

                    # Find enabled provider
                    for provider_name, provider_data in providers.items():
                        is_enabled = provider_data.get("enabled", True)

                        # Check if this is the default or first enabled provider
                        if provider_name == default_provider or is_enabled:
                            # Extract API key
                            api_key = provider_data.get("api_key")
                            if not api_key and "api_key_env" in provider_data:
                                # Read from environment variable
                                api_key = os.getenv(provider_data["api_key_env"])

                            # Convert model name to LiteLLM format
                            model = provider_data.get("model", "gpt-4o-mini")

                            # Map provider names to LiteLLM format
                            provider_map = {
                                "siliconflow": "openai",  # SiliconFlow uses OpenAI-compatible API
                                "openai": "openai",
                                "anthropic": "anthropic",
                                "deepseek": "deepseek",
                                "ollama": "openai",  # Ollama uses OpenAI-compatible
                            }

                            # For SiliconFlow, use the model as-is (it's a DeepSeek model hosted there)
                            # For others, add provider prefix
                            if provider_name == "siliconflow":
                                # SiliconFlow hosts DeepSeek, use model directly
                                litellm_model = model
                            elif provider_name in provider_map and "/" not in model:
                                litellm_model = f"{provider_map[provider_name]}/{model}"
                            else:
                                litellm_model = model

                            llm_config = LLMConfig(
                                model=litellm_model,
                                api_base=provider_data.get("base_url"),
                                api_key=api_key,
                                temperature=provider_data.get("temperature", 0.7),
                                max_tokens=provider_data.get("max_tokens", 4096),
                            )
                            break
                else:
                    # Simple format (direct config)
                    llm_config = LLMConfig(
                        model=llm_data.get("model", "gpt-4o-mini"),
                        api_base=llm_data.get("api_base"),
                        api_key=llm_data.get("api_key"),
                        temperature=llm_data.get("temperature", 0.7),
                        max_tokens=llm_data.get("max_tokens", 4096),
                    )

            # Extract tools configuration
            if "tools" in data:
                tools_data = data["tools"]
                tools_config = ToolConfig(
                    max_file_size=tools_data.get("max_file_size", 1024*1024),
                    protected_paths=tools_data.get("protected_paths", []),
                    exec_timeout=tools_data.get("shell_timeout", 30),
                    working_dir=Path(tools_data.get("allowed_dir")) if tools_data.get("allowed_dir") else None,
                )

            # Extract react configuration
            if "react" in data:
                react_data = data["react"]
                react_config = ReactConfig(
                    max_iterations=react_data.get("max_iterations", 20),
                    enable_steering=react_data.get("enable_steering", True),
                    enable_followup=react_data.get("enable_followup", True),
                )

            return cls(
                llm=llm_config,
                tools=tools_config,
                react=react_config,
            )

        # Fallback to environment variables
        return cls.from_env()

    def save(self, config_path: Path) -> None:
        """Save configuration to file"""
        import json
        from dataclasses import asdict

        data = asdict(self)
        # Convert Path objects to strings
        def convert_paths(obj: Any) -> Any:
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            return obj

        data = convert_paths(data)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# Default configuration
default_config = Config()
