"""
Configuration management for FastReAct Nano v2.0

Centralized configuration with environment variable support.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


def _expand_path(path_str: str | Path) -> Path:
    """
    Expand user home directory (~) and environment variables in path.

    Args:
        path_str: Path string that may contain ~ or $VAR

    Returns:
        Expanded Path object

    Examples:
        _expand_path("~/skills") -> /home/user/skills
        _expand_path("$HOME/skills") -> /home/user/skills
        _expand_path("/absolute/path") -> /absolute/path
    """
    if isinstance(path_str, Path):
        return path_str

    # First expand environment variables, then expand ~
    expanded = os.path.expandvars(path_str)
    return Path(expanded).expanduser()


@dataclass
class LLMConfig:
    """LLM provider configuration"""

    model: str = "gpt-4o-mini"
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    api_key_file: Optional[Path] = None
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create from environment variables"""
        config = cls(
            model=os.getenv("FASTRACT_MODEL", "gpt-4o-mini"),
            api_base=os.getenv("FASTRACT_API_BASE"),
            api_key=os.getenv("FASTRACT_API_KEY") or os.getenv("OPENAI_API_KEY"),
            api_key_file=_expand_path(os.getenv("FASTRACT_API_KEY_FILE")) if os.getenv("FASTRACT_API_KEY_FILE") else None,
            temperature=float(os.getenv("FASTRACT_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("FASTRACT_MAX_TOKENS", "4096")),
        )
        return _apply_api_key_file(config)


def _read_api_key_file(path: Path) -> dict[str, str]:
    """Read JSON or legacy line-based OpenAI-compatible API key files."""
    import json

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    if text.startswith("{"):
        data = json.loads(text)
        return {str(key): str(value) for key, value in data.items() if value is not None}

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    data: dict[str, str] = {}
    if len(lines) > 0:
        data["api_key"] = lines[0]
    if len(lines) > 1:
        data["model"] = lines[1]
    if len(lines) > 2:
        data["base_url"] = lines[2]
    if len(lines) > 3:
        data["service_token"] = lines[3]
    return data


def _apply_api_key_file(config: LLMConfig) -> LLMConfig:
    if not config.api_key_file:
        return config
    data = _read_api_key_file(config.api_key_file)
    config.api_key = config.api_key or data.get("api_key") or data.get("key")
    config.model = config.model if config.model != "gpt-4o-mini" else data.get("model", config.model)
    config.api_base = config.api_base or data.get("base_url") or data.get("api_base")
    return config


def _service_token_from_api_key_file(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    data = _read_api_key_file(path)
    return data.get("service_token") or data.get("fastreact_service_token")


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
        working_dir = os.getenv("FASTRACT_WORKING_DIR")
        return cls(
            max_file_size=int(os.getenv("FASTRACT_MAX_FILE_SIZE", str(1024 * 1024))),
            exec_timeout=int(os.getenv("FASTRACT_EXEC_TIMEOUT", "30")),
            working_dir=_expand_path(working_dir) if working_dir else None,
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
    use_tiktoken: bool = True  # Use tiktoken for accurate token counting
    tiktoken_model: str = "gpt-4o"  # Model name for tiktoken encoding
    sliding_window_size: int = 15  # Number of recent messages to preserve in compression

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
            use_tiktoken=os.getenv("FASTRACT_USE_TIKTOKEN", "true").lower() == "true",
            tiktoken_model=os.getenv("FASTRACT_TIKTOKEN_MODEL", "gpt-4o"),
            sliding_window_size=int(os.getenv("FASTRACT_SLIDING_WINDOW_SIZE", "15")),
            enable_filesystem_memory=os.getenv("FASTRACT_ENABLE_FILESYSTEM_MEMORY", "true").lower() == "true",
            max_tree_depth=int(os.getenv("FASTRACT_MAX_TREE_DEPTH", "3")),
            max_files_per_dir=int(os.getenv("FASTRACT_MAX_FILES_PER_DIR", "50")),
            enable_safety=os.getenv("FASTRACT_ENABLE_SAFETY", "true").lower() == "true",
            strict_mode=os.getenv("FASTRICT_MODE", "false").lower() == "true",
            auto_approve_safe=os.getenv("FASTRACT_AUTO_APPROVE_SAFE", "true").lower() == "true",
        )


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server"""

    name: str
    command: str = ""  # Required for stdio transport
    args: list[str] = field(default_factory=list)
    env: Optional[dict[str, str]] = None

    # Transport configuration
    transport: str = "stdio"  # "stdio" | "http"
    url: Optional[str] = None  # HTTP server URL (required for http transport)
    auth_token_ref: Optional[str] = None  # Reference to credentials.json (e.g., "mcp.server_name")

    # Optional skill association
    associated_skill: Optional[str] = None

    # Description for tool discovery
    description: Optional[str] = None

    # Multi-tenant isolation settings
    isolation: str = "shared"  # "shared" | "per_user" | "lazy_per_user"
    per_user_args_template: Optional[list[str]] = None  # e.g., ["--user-dir", "{user_workspace}"]
    idle_timeout: int = 300  # seconds, only for lazy_per_user mode
    max_instances: int = 10  # max instances, only for lazy_per_user mode

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPServerConfig":
        """Create from dictionary"""
        return cls(
            name=data.get("name", "unknown"),
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env"),
            transport=data.get("transport", "stdio"),
            url=data.get("url"),
            auth_token_ref=data.get("auth_token_ref"),
            associated_skill=data.get("associated_skill"),
            description=data.get("description"),
            isolation=data.get("isolation", "shared"),
            per_user_args_template=data.get("per_user_args_template"),
            idle_timeout=data.get("idle_timeout", 300),
            max_instances=data.get("max_instances", 10),
        )


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) server configuration"""

    servers: list[MCPServerConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "MCPConfig":
        """Create MCP config from dictionary"""
        servers_data = data.get("servers", [])
        servers = [MCPServerConfig.from_dict(s) for s in servers_data]
        return cls(servers=servers)

    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Create MCP config from environment variables"""
        import json

        servers_json = os.getenv("FASTRACT_MCP_SERVERS", "[]")
        try:
            servers_data = json.loads(servers_json)
            servers = [MCPServerConfig.from_dict(s) for s in servers_data]
        except json.JSONDecodeError:
            servers = []

        return cls(servers=servers)


@dataclass
class PathsConfig:
    """Path configuration for different deployment modes"""

    # Skills directories
    global_skills_dir: Path = field(default_factory=lambda: Path.cwd() / "skills" / "builtin")
    user_skills_template: str = "{user_workspace}/skills"
    user_skills_dir: Optional[Path] = None  # User-defined skills directory

    # Workspace
    gateway_workspace: Path = field(default_factory=lambda: Path.cwd() / "workspaces" / "default")
    feishu_workspace_base: Path = field(default_factory=lambda: Path("/var/fastreact/tenants/feishu"))

    @classmethod
    def from_env(cls) -> "PathsConfig":
        """Create paths config from environment variables"""
        return cls(
            global_skills_dir=_expand_path(os.getenv("FASTRACT_SKILLS_DIR", str(Path.cwd() / "skills" / "builtin"))),
            user_skills_template=os.getenv("FASTRACT_USER_SKILLS_TEMPLATE", "{user_workspace}/skills"),
            gateway_workspace=_expand_path(os.getenv("FASTRACT_GATEWAY_WORKSPACE", str(Path.cwd() / "workspaces" / "default"))),
            feishu_workspace_base=_expand_path(os.getenv("FEISHU_BASE_WORKSPACE", "/var/fastreact/tenants/feishu")),
        )


@dataclass
class GatewayConfig:
    """Gateway (WebSocket) configuration"""

    # Multi-tenant mode
    enable_multitenant: bool = True  # Default: multi-tenant mode enabled
    admin_only: bool = False  # Restrict to admin only (for single-tenant mode)

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 9000
    log_level: str = "info"

    # Admin API
    admin_api_key: str = "admin-secret-key-change-in-production"

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Create Gateway config from environment variables"""
        return cls(
            enable_multitenant=os.getenv("GATEWAY_MULTITENANT", "true").lower() == "true",
            admin_only=os.getenv("GATEWAY_ADMIN_ONLY", "false").lower() == "true",
            host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
            port=int(os.getenv("GATEWAY_PORT", "9000")),
            log_level=os.getenv("GATEWAY_LOG_LEVEL", "info"),
            admin_api_key=os.getenv("GATEWAY_ADMIN_KEY", "admin-secret-key-change-in-production"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GatewayConfig":
        """Create Gateway config from dictionary"""
        return cls(
            enable_multitenant=data.get("enable_multitenant", True),
            admin_only=data.get("admin_only", False),
            host=data.get("host", "0.0.0.0"),
            port=data.get("port", 9000),
            log_level=data.get("log_level", "info"),
            admin_api_key=data.get("admin_api_key", "admin-secret-key-change-in-production"),
        )


@dataclass
class ServiceConfig:
    """Headless HTTP service configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    service_token: Optional[str] = None

    @classmethod
    def from_env(cls, api_key_file: Optional[Path] = None) -> "ServiceConfig":
        token = os.getenv("FASTREACT_SERVICE_TOKEN") or _service_token_from_api_key_file(api_key_file)
        return cls(
            host=os.getenv("FASTREACT_HOST", "0.0.0.0"),
            port=int(os.getenv("FASTREACT_PORT", "8000")),
            log_level=os.getenv("FASTREACT_LOG_LEVEL", "info"),
            service_token=token,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any], api_key_file: Optional[Path] = None) -> "ServiceConfig":
        token = data.get("service_token") or data.get("token") or _service_token_from_api_key_file(api_key_file)
        return cls(
            host=data.get("host", "0.0.0.0"),
            port=int(data.get("port", 8000)),
            log_level=data.get("log_level", "info"),
            service_token=token,
        )


@dataclass
class FeishuConfig:
    """Feishu (Lark) channel configuration"""

    # Connection mode: "webhook" (HTTP) or "sdk" (WebSocket long connection)
    connection_mode: str = "sdk"

    # App credentials
    app_id: str = ""
    app_secret: str = ""

    # Webhook security (only for webhook mode)
    encrypt_key: str = ""
    verification_token: str = ""

    # Server configuration (only for webhook mode)
    host: str = "0.0.0.0"
    port: int = 8001
    webhook_path: str = "/webhook/feishu"

    # SDK configuration (only for SDK mode)
    auto_reconnect: bool = True
    log_level: str = "info"

    # Multi-tenant settings
    enable_multitenant: bool = True
    base_workspace: Optional[Path] = None

    @classmethod
    def from_env(cls) -> "FeishuConfig":
        """Create Feishu config from environment variables"""
        workspace_str = os.getenv("FEISHU_WORKSPACE")
        return cls(
            connection_mode=os.getenv("FEISHU_CONNECTION_MODE", "sdk"),
            app_id=os.getenv("FEISHU_APP_ID", ""),
            app_secret=os.getenv("FEISHU_APP_SECRET", ""),
            encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", ""),
            verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", ""),
            host=os.getenv("FEISHU_HOST", "0.0.0.0"),
            port=int(os.getenv("FEISHU_PORT", "8001")),
            webhook_path=os.getenv("FEISHU_WEBHOOK_PATH", "/webhook/feishu"),
            auto_reconnect=os.getenv("FEISHU_AUTO_RECONNECT", "true").lower() == "true",
            log_level=os.getenv("FEISHU_LOG_LEVEL", "info"),
            enable_multitenant=os.getenv("FEISHU_MULTITENANT", "true").lower() == "true",
            base_workspace=_expand_path(workspace_str) if workspace_str else None,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeishuConfig":
        """Create Feishu config from dictionary"""
        workspace_str = data.get("base_workspace")
        return cls(
            connection_mode=data.get("connection_mode", "sdk"),
            app_id=data.get("app_id", ""),
            app_secret=data.get("app_secret", ""),
            encrypt_key=data.get("encrypt_key", ""),
            verification_token=data.get("verification_token", ""),
            host=data.get("host", "0.0.0.0"),
            port=data.get("port", 8001),
            webhook_path=data.get("webhook_path", "/webhook/feishu"),
            auto_reconnect=data.get("auto_reconnect", True),
            log_level=data.get("log_level", "info"),
            enable_multitenant=data.get("enable_multitenant", True),
            base_workspace=_expand_path(workspace_str) if workspace_str else None,
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
        FASTRACT_USE_TIKTOKEN: Use tiktoken for accurate token counting (default: true)
        FASTRACT_TIKTOKEN_MODEL: Model name for tiktoken encoding (default: gpt-4o)
        FASTRACT_SLIDING_WINDOW_SIZE: Number of recent messages to preserve (default: 15)
        FASTRACT_ENABLE_FILESYSTEM_MEMORY: Enable filesystem memory (default: true)
        FASTRACT_MAX_TREE_DEPTH: Max tree depth for filesystem memory (default: 3)
        FASTRACT_MAX_FILES_PER_DIR: Max files per dir in tree (default: 50)
        FASTRACT_ENABLE_SAFETY: Enable safety guardrails (default: true)
        FASTRICT_MODE: Require confirmation for all modifications (default: false)
        FASTRACT_AUTO_APPROVE_SAFE: Auto-approve safe operations (default: true)
        FASTRACT_MCP_SERVERS: JSON array of MCP server configs (default: [])
        FASTRACT_SKILLS_DIR: Global skills directory (default: ./skills/builtin)
        FASTRACT_USER_SKILLS_TEMPLATE: User skills path template (default: {user_workspace}/skills)
        FASTRACT_GATEWAY_WORKSPACE: Gateway workspace path (default: ./workspaces/default)
        FEISHU_BASE_WORKSPACE: Feishu multi-tenant base workspace (default: /var/fastreact/tenants/feishu)
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    react: ReactConfig = field(default_factory=ReactConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables"""
        llm_config = LLMConfig.from_env()
        return cls(
            llm=llm_config,
            tools=ToolConfig.from_env(),
            react=ReactConfig.from_env(),
            mcp=MCPConfig.from_env(),
            paths=PathsConfig.from_env(),
            service=ServiceConfig.from_env(llm_config.api_key_file),
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
                    api_key_file = llm_data.get("api_key_file") or llm_data.get("key_file")
                    llm_config = LLMConfig(
                        model=llm_data.get("model", "gpt-4o-mini"),
                        api_base=llm_data.get("api_base") or llm_data.get("base_url"),
                        api_key=llm_data.get("api_key"),
                        api_key_file=_expand_path(api_key_file) if api_key_file else None,
                        temperature=llm_data.get("temperature", 0.7),
                        max_tokens=llm_data.get("max_tokens", 4096),
                    )
                    llm_config = _apply_api_key_file(llm_config)

            # Extract tools configuration
            if "tools" in data:
                tools_data = data["tools"]
                allowed_dir = tools_data.get("allowed_dir")
                tools_config = ToolConfig(
                    max_file_size=tools_data.get("max_file_size", 1024*1024),
                    protected_paths=tools_data.get("protected_paths", []),
                    exec_timeout=tools_data.get("shell_timeout", 30),
                    working_dir=_expand_path(allowed_dir) if allowed_dir else None,
                )

            # Extract react configuration
            if "react" in data:
                react_data = data["react"]
                react_config = ReactConfig(
                    max_iterations=react_data.get("max_iterations", 20),
                    enable_steering=react_data.get("enable_steering", True),
                    enable_followup=react_data.get("enable_followup", True),
                )

            # Extract MCP configuration
            mcp_config = MCPConfig()
            if "mcp" in data:
                mcp_config = MCPConfig.from_dict(data["mcp"])

            # Extract paths configuration
            paths_config = PathsConfig()
            if "paths" in data:
                paths_data = data["paths"]
                paths_config = PathsConfig(
                    global_skills_dir=_expand_path(paths_data.get("global_skills_dir", str(Path.cwd() / "skills" / "builtin"))),
                    user_skills_template=paths_data.get("user_skills_template", "{user_workspace}/skills"),
                    user_skills_dir=_expand_path(paths_data.get("user_skills_dir")) if paths_data.get("user_skills_dir") else None,
                    gateway_workspace=_expand_path(paths_data.get("gateway_workspace", str(Path.cwd() / "workspaces" / "default"))),
                    feishu_workspace_base=_expand_path(paths_data.get("feishu_workspace_base", "/var/fastreact/tenants/feishu")),
                )

            # Extract Feishu configuration
            feishu_config = FeishuConfig()
            if "feishu" in data:
                feishu_data = data["feishu"]
                feishu_config = FeishuConfig.from_dict(feishu_data)

            # Extract Gateway configuration
            gateway_config = GatewayConfig()
            if "gateway" in data:
                gateway_data = data["gateway"]
                gateway_config = GatewayConfig.from_dict(gateway_data)

            # Extract headless HTTP service configuration
            service_config = ServiceConfig()
            if "service" in data:
                service_config = ServiceConfig.from_dict(data["service"], llm_config.api_key_file)
            else:
                service_config = ServiceConfig.from_env(llm_config.api_key_file)

            return cls(
                llm=llm_config,
                tools=tools_config,
                react=react_config,
                mcp=mcp_config,
                paths=paths_config,
                gateway=gateway_config,
                service=service_config,
                feishu=feishu_config,
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
