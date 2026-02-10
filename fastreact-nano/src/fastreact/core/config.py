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

    @classmethod
    def from_env(cls) -> "ReactConfig":
        """Create from environment variables"""
        steering_path = os.getenv("FASTRACT_STEERING_FILE")
        return cls(
            max_iterations=int(os.getenv("FASTRACT_MAX_ITERATIONS", "20")),
            enable_steering=os.getenv("FASTRACT_ENABLE_STEERING", "true").lower() == "true",
            enable_followup=os.getenv("FASTRACT_ENABLE_FOLLOWUP", "true").lower() == "true",
            steering_file=Path(steering_path) if steering_path else Path.cwd() / ".steering.jsonl",
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
            config_path: Path to config file (JSON/YAML). If None, uses environment.
        """
        if config_path and config_path.exists():
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # TODO: Implement proper deserialization
            return cls()

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
