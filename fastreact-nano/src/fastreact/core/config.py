"""
Configuration management for FastReAct Nano v2.0

Centralized configuration with environment variable support.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


AUTHNODE_TENANT_CLAIMS = ["tenant_key", "tenant_id", "tenant", "org_id"]
DEFAULT_SERVICE_PORT = 18741
DEFAULT_LLM_MAX_TOKENS = 8192
DEFAULT_MAX_TOOL_OUTPUT_CHARS = 20000
DEFAULT_MCP_TOOL_OUTPUT_BUDGET_CHARS = 20000
DEFAULT_MCP_TOOL_OUTPUT_PREVIEW_CHARS = 1200


def _env_value(*names: str, default: str | None = None) -> str | None:
    """Return the first non-empty environment variable value from names."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


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
    max_tokens: int = DEFAULT_LLM_MAX_TOKENS

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create from environment variables"""
        config = cls(
            model=os.getenv("FASTRACT_MODEL", "gpt-4o-mini"),
            api_base=os.getenv("FASTRACT_API_BASE"),
            api_key=os.getenv("FASTRACT_API_KEY") or os.getenv("OPENAI_API_KEY"),
            api_key_file=_expand_path(os.getenv("FASTRACT_API_KEY_FILE")) if os.getenv("FASTRACT_API_KEY_FILE") else None,
            temperature=float(os.getenv("FASTRACT_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("FASTRACT_MAX_TOKENS", str(DEFAULT_LLM_MAX_TOKENS))),
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


def _csv_env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


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
    max_tool_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS
    mcp_tool_output_budget_chars: int = DEFAULT_MCP_TOOL_OUTPUT_BUDGET_CHARS
    mcp_tool_output_preview_chars: int = DEFAULT_MCP_TOOL_OUTPUT_PREVIEW_CHARS
    mcp_tool_output_retry_attempts: int = 1
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
            max_tool_output_chars=int(os.getenv("FASTRACT_MAX_TOOL_OUTPUT_CHARS", str(DEFAULT_MAX_TOOL_OUTPUT_CHARS))),
            mcp_tool_output_budget_chars=int(_env_value(
                "FASTREACT_MCP_TOOL_OUTPUT_BUDGET_CHARS",
                "FASTRACT_MCP_TOOL_OUTPUT_BUDGET_CHARS",
                default=str(DEFAULT_MCP_TOOL_OUTPUT_BUDGET_CHARS),
            )),
            mcp_tool_output_preview_chars=int(_env_value(
                "FASTREACT_MCP_TOOL_OUTPUT_PREVIEW_CHARS",
                "FASTRACT_MCP_TOOL_OUTPUT_PREVIEW_CHARS",
                default=str(DEFAULT_MCP_TOOL_OUTPUT_PREVIEW_CHARS),
            )),
            mcp_tool_output_retry_attempts=int(_env_value(
                "FASTREACT_MCP_TOOL_OUTPUT_RETRY_ATTEMPTS",
                "FASTRACT_MCP_TOOL_OUTPUT_RETRY_ATTEMPTS",
                default="1",
            )),
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
    identity_forwarding: Optional[dict[str, Any]] = None
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
            identity_forwarding=data.get("identity_forwarding"),
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

    # Runtime workspaces. gateway_workspace is retained for legacy single-workspace deployments.
    workspaces_root: Path = field(default_factory=lambda: Path.home() / "FastReAct_workspaces")
    gateway_workspace: Path = field(default_factory=lambda: Path.home() / "FastReAct_workspaces" / "single" / "default")

    @classmethod
    def from_env(cls) -> "PathsConfig":
        """Create paths config from environment variables"""
        user_skills_dir = os.getenv("FASTRACT_USER_SKILLS_DIR")
        workspaces_root = _expand_path(
            _env_value("FASTREACT_WORKSPACES_ROOT", "FASTRACT_WORKSPACES_ROOT", default=str(Path.home() / "FastReAct_workspaces"))
        )
        gateway_workspace = _env_value("FASTREACT_GATEWAY_WORKSPACE", "FASTRACT_GATEWAY_WORKSPACE")
        return cls(
            global_skills_dir=_expand_path(os.getenv("FASTRACT_SKILLS_DIR", str(Path.cwd() / "skills" / "builtin"))),
            user_skills_template=os.getenv("FASTRACT_USER_SKILLS_TEMPLATE", "{user_workspace}/skills"),
            user_skills_dir=_expand_path(user_skills_dir) if user_skills_dir else None,
            workspaces_root=workspaces_root,
            gateway_workspace=_expand_path(gateway_workspace) if gateway_workspace else workspaces_root / "single" / "default",
        )


@dataclass
class AuthConfig:
    """Inbound identity verification boundary for HTTP/SSE deployments."""

    mode: str = "service_token"
    trusted_header_user_key: str = "X-FastReAct-User-Key"
    trusted_header_tenant_key: str = "X-FastReAct-Tenant-Key"
    trusted_header_subject: str = "X-FastReAct-Subject"
    trusted_header_display_name: str = "X-FastReAct-Display-Name"
    trusted_header_email: str = "X-FastReAct-Email"
    trusted_header_groups: str = "X-FastReAct-Groups"
    trusted_header_roles: str = "X-FastReAct-Roles"
    trusted_header_provider: str = "X-FastReAct-Auth-Provider"
    jwt_secret: Optional[str] = None
    jwt_secret_env: Optional[str] = None
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_tenant_claims: list[str] = field(default_factory=lambda: list(AUTHNODE_TENANT_CLAIMS))
    jwt_user_claim: str = "sub"
    jwt_display_name_claim: str = "name"
    jwt_email_claim: str = "email"
    jwt_groups_claim: str = "groups"
    jwt_roles_claim: str = "roles"
    jwt_provider_claim: str = "iss"

    @classmethod
    def from_env(cls) -> "AuthConfig":
        jwt_secret_env = os.getenv("FASTREACT_AUTH_JWT_SECRET_ENV")
        jwt_secret = os.getenv("FASTREACT_AUTH_JWT_SECRET")
        if not jwt_secret and jwt_secret_env:
            jwt_secret = os.getenv(jwt_secret_env)
        return cls(
            mode=os.getenv("FASTREACT_AUTH_MODE", "service_token"),
            trusted_header_user_key=os.getenv("FASTREACT_AUTH_HEADER_USER_KEY", cls.trusted_header_user_key),
            trusted_header_tenant_key=os.getenv("FASTREACT_AUTH_HEADER_TENANT_KEY", cls.trusted_header_tenant_key),
            trusted_header_subject=os.getenv("FASTREACT_AUTH_HEADER_SUBJECT", cls.trusted_header_subject),
            trusted_header_display_name=os.getenv("FASTREACT_AUTH_HEADER_DISPLAY_NAME", cls.trusted_header_display_name),
            trusted_header_email=os.getenv("FASTREACT_AUTH_HEADER_EMAIL", cls.trusted_header_email),
            trusted_header_groups=os.getenv("FASTREACT_AUTH_HEADER_GROUPS", cls.trusted_header_groups),
            trusted_header_roles=os.getenv("FASTREACT_AUTH_HEADER_ROLES", cls.trusted_header_roles),
            trusted_header_provider=os.getenv("FASTREACT_AUTH_HEADER_PROVIDER", cls.trusted_header_provider),
            jwt_secret=jwt_secret,
            jwt_secret_env=jwt_secret_env,
            jwt_issuer=os.getenv("FASTREACT_AUTH_JWT_ISSUER"),
            jwt_audience=os.getenv("FASTREACT_AUTH_JWT_AUDIENCE"),
            jwt_algorithm=os.getenv("FASTREACT_AUTH_JWT_ALGORITHM", "HS256"),
            jwt_tenant_claims=_csv_env_list("FASTREACT_AUTH_JWT_TENANT_CLAIMS") or list(AUTHNODE_TENANT_CLAIMS),
            jwt_user_claim=os.getenv("FASTREACT_AUTH_JWT_USER_CLAIM", "sub"),
            jwt_display_name_claim=os.getenv("FASTREACT_AUTH_JWT_DISPLAY_NAME_CLAIM", "name"),
            jwt_email_claim=os.getenv("FASTREACT_AUTH_JWT_EMAIL_CLAIM", "email"),
            jwt_groups_claim=os.getenv("FASTREACT_AUTH_JWT_GROUPS_CLAIM", "groups"),
            jwt_roles_claim=os.getenv("FASTREACT_AUTH_JWT_ROLES_CLAIM", "roles"),
            jwt_provider_claim=os.getenv("FASTREACT_AUTH_JWT_PROVIDER_CLAIM", "iss"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthConfig":
        tenant_claims = data.get("jwt_tenant_claims", AUTHNODE_TENANT_CLAIMS)
        if isinstance(tenant_claims, str):
            tenant_claims = [item.strip() for item in tenant_claims.split(",") if item.strip()]
        jwt_secret_env = data.get("jwt_secret_env")
        jwt_secret = data.get("jwt_secret")
        if not jwt_secret and jwt_secret_env:
            jwt_secret = os.getenv(str(jwt_secret_env))
        return cls(
            mode=data.get("mode", "service_token"),
            trusted_header_user_key=data.get("trusted_header_user_key", cls.trusted_header_user_key),
            trusted_header_tenant_key=data.get("trusted_header_tenant_key", cls.trusted_header_tenant_key),
            trusted_header_subject=data.get("trusted_header_subject", cls.trusted_header_subject),
            trusted_header_display_name=data.get("trusted_header_display_name", cls.trusted_header_display_name),
            trusted_header_email=data.get("trusted_header_email", cls.trusted_header_email),
            trusted_header_groups=data.get("trusted_header_groups", cls.trusted_header_groups),
            trusted_header_roles=data.get("trusted_header_roles", cls.trusted_header_roles),
            trusted_header_provider=data.get("trusted_header_provider", cls.trusted_header_provider),
            jwt_secret=jwt_secret,
            jwt_secret_env=jwt_secret_env,
            jwt_issuer=data.get("jwt_issuer"),
            jwt_audience=data.get("jwt_audience"),
            jwt_algorithm=data.get("jwt_algorithm", "HS256"),
            jwt_tenant_claims=list(tenant_claims or AUTHNODE_TENANT_CLAIMS),
            jwt_user_claim=data.get("jwt_user_claim", "sub"),
            jwt_display_name_claim=data.get("jwt_display_name_claim", "name"),
            jwt_email_claim=data.get("jwt_email_claim", "email"),
            jwt_groups_claim=data.get("jwt_groups_claim", "groups"),
            jwt_roles_claim=data.get("jwt_roles_claim", "roles"),
            jwt_provider_claim=data.get("jwt_provider_claim", "iss"),
        )


@dataclass
class ServiceConfig:
    """Headless HTTP service configuration."""

    host: str = "0.0.0.0"
    port: int = DEFAULT_SERVICE_PORT
    log_level: str = "info"
    service_token: Optional[str] = None
    approval_timeout_seconds: float = 300.0
    run_lease_seconds: float = 300.0
    run_max_attempts: int = 3
    run_retry_base_seconds: float = 5.0
    run_retry_max_seconds: float = 300.0
    run_concurrency: int = 4
    recover_queued_runs: bool = True
    rate_limit_per_hour: int = 0
    blocked_user_keys: list[str] = field(default_factory=list)
    allowed_user_keys: list[str] = field(default_factory=list)
    cors_origins: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, api_key_file: Optional[Path] = None) -> "ServiceConfig":
        token = _service_token_from_api_key_file(api_key_file)
        return cls(
            host=os.getenv("FASTREACT_HOST", "0.0.0.0"),
            port=int(os.getenv("FASTREACT_PORT", str(DEFAULT_SERVICE_PORT))),
            log_level=os.getenv("FASTREACT_LOG_LEVEL", "info"),
            service_token=token,
            approval_timeout_seconds=float(os.getenv("FASTREACT_APPROVAL_TIMEOUT_SECONDS", "300")),
            run_lease_seconds=float(os.getenv("FASTREACT_RUN_LEASE_SECONDS", "300")),
            run_max_attempts=int(os.getenv("FASTREACT_RUN_MAX_ATTEMPTS", "3")),
            run_retry_base_seconds=float(os.getenv("FASTREACT_RUN_RETRY_BASE_SECONDS", "5")),
            run_retry_max_seconds=float(os.getenv("FASTREACT_RUN_RETRY_MAX_SECONDS", "300")),
            run_concurrency=int(os.getenv("FASTREACT_RUN_CONCURRENCY", "4")),
            recover_queued_runs=os.getenv("FASTREACT_RECOVER_QUEUED_RUNS", "true").lower() == "true",
            rate_limit_per_hour=int(os.getenv("FASTREACT_RATE_LIMIT_PER_HOUR", "0")),
            blocked_user_keys=_csv_env_list("FASTREACT_BLOCKED_USER_KEYS"),
            allowed_user_keys=_csv_env_list("FASTREACT_ALLOWED_USER_KEYS"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any], api_key_file: Optional[Path] = None) -> "ServiceConfig":
        token = data.get("service_token") or data.get("token") or _service_token_from_api_key_file(api_key_file)
        cors_origins = data.get("cors_origins", []) or []
        if isinstance(cors_origins, str):
            cors_origins = [cors_origins]
        return cls(
            host=data.get("host", "0.0.0.0"),
            port=int(data.get("port", DEFAULT_SERVICE_PORT)),
            log_level=data.get("log_level", "info"),
            service_token=token,
            approval_timeout_seconds=float(data.get("approval_timeout_seconds", 300.0)),
            run_lease_seconds=float(data.get("run_lease_seconds", 300.0)),
            run_max_attempts=int(data.get("run_max_attempts", 3)),
            run_retry_base_seconds=float(data.get("run_retry_base_seconds", 5.0)),
            run_retry_max_seconds=float(data.get("run_retry_max_seconds", 300.0)),
            run_concurrency=int(data.get("run_concurrency", 4)),
            recover_queued_runs=bool(data.get("recover_queued_runs", True)),
            rate_limit_per_hour=int(data.get("rate_limit_per_hour", 0)),
            blocked_user_keys=list(data.get("blocked_user_keys", []) or []),
            allowed_user_keys=list(data.get("allowed_user_keys", []) or []),
            cors_origins=list(cors_origins),
        )


@dataclass
class ExtensionConfig:
    """Runtime extension management settings."""

    runtime_reload_enabled: bool = False
    mcp_reload_enabled: bool = False

    @classmethod
    def from_env(cls) -> "ExtensionConfig":
        """Create extension config from environment variables."""
        return cls(
            runtime_reload_enabled=os.getenv("FASTRACT_EXTENSIONS_RUNTIME_RELOAD", "false").lower() == "true",
            mcp_reload_enabled=os.getenv("FASTRACT_EXTENSIONS_MCP_RELOAD", "false").lower() == "true",
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtensionConfig":
        """Create extension config from dictionary."""
        if not isinstance(data, dict):
            raise ValueError("extensions must be an object")
        return cls(
            runtime_reload_enabled=bool(data.get("runtime_reload_enabled", False)),
            mcp_reload_enabled=bool(data.get("mcp_reload_enabled", False)),
        )


@dataclass
class PolicyConfig:
    """Tool execution policy for headless service deployments."""

    ALLOWED_ACTIONS = {"allow", "caution", "require_approval", "deny"}

    default_action: Optional[str] = None
    tool_rules: dict[str, Any] = field(default_factory=dict)
    user_rules: dict[str, Any] = field(default_factory=dict)
    tenant_rules: dict[str, Any] = field(default_factory=dict)
    tool_profiles: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "PolicyConfig":
        policy_json = os.getenv("FASTRACT_POLICY")
        if policy_json:
            import json

            return cls.from_dict(json.loads(policy_json))
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyConfig":
        if not isinstance(data, dict):
            raise ValueError("policy must be an object")
        cls._validate_action(data.get("default_action"), "policy.default_action", allow_none=True)
        tool_rules = cls._validate_rules_map(data.get("tool_rules", {}), "policy.tool_rules")
        user_rules = cls._validate_rules_map(data.get("user_rules", {}), "policy.user_rules")
        tenant_rules = cls._validate_rules_map(data.get("tenant_rules", {}), "policy.tenant_rules")
        tool_profiles = cls._validate_tool_profiles(data.get("tool_profiles", {}), "policy.tool_profiles")
        return cls(
            default_action=data.get("default_action"),
            tool_rules=tool_rules,
            user_rules=user_rules,
            tenant_rules=tenant_rules,
            tool_profiles=tool_profiles,
        )

    def to_safety_policy(self) -> dict[str, Any]:
        return {
            "default_action": self.default_action,
            "tool_rules": self.tool_rules,
            "user_rules": self.user_rules,
            "tenant_rules": self.tenant_rules,
            "tool_profiles": self.tool_profiles,
        }

    @classmethod
    def _validate_tool_profiles(cls, profiles: Any, path: str) -> dict[str, Any]:
        if profiles is None:
            return {}
        if not isinstance(profiles, dict):
            raise ValueError(f"{path} must be an object")
        for profile_name, profile in profiles.items():
            if not isinstance(profile_name, str) or not profile_name:
                raise ValueError(f"{path} keys must be non-empty strings")
            if isinstance(profile, list):
                for tool_name in profile:
                    if not isinstance(tool_name, str) or not tool_name:
                        raise ValueError(f"{path}.{profile_name} must contain non-empty tool names")
                continue
            if not isinstance(profile, dict):
                raise ValueError(f"{path}.{profile_name} must be a list or object")
            tools = profile.get("tools", [])
            if not isinstance(tools, list):
                raise ValueError(f"{path}.{profile_name}.tools must be a list")
            for tool_name in tools:
                if not isinstance(tool_name, str) or not tool_name:
                    raise ValueError(f"{path}.{profile_name}.tools must contain non-empty tool names")
        return profiles

    @classmethod
    def _validate_rules_map(cls, rules: Any, path: str) -> dict[str, Any]:
        if rules is None:
            return {}
        if not isinstance(rules, dict):
            raise ValueError(f"{path} must be an object")
        for key, rule in rules.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{path} keys must be non-empty strings")
            cls._validate_rule(rule, f"{path}.{key}")
        return rules

    @classmethod
    def _validate_rule(cls, rule: Any, path: str) -> None:
        if isinstance(rule, str):
            cls._validate_action(rule, path)
            return
        if not isinstance(rule, dict):
            raise ValueError(f"{path} must be an action string or object")

        has_action = False
        for action_key in ("action", "default_action"):
            if action_key in rule:
                has_action = True
                cls._validate_action(rule[action_key], f"{path}.{action_key}")

        tools = rule.get("tools", rule.get("tool_rules"))
        if tools is not None:
            if not isinstance(tools, dict):
                raise ValueError(f"{path}.tools must be an object")
            for tool_name, tool_rule in tools.items():
                if not isinstance(tool_name, str) or not tool_name:
                    raise ValueError(f"{path}.tools keys must be non-empty strings")
                cls._validate_rule(tool_rule, f"{path}.tools.{tool_name}")
            has_action = True

        if not has_action:
            raise ValueError(f"{path} must define action, default_action, tools, or tool_rules")

    @classmethod
    def _validate_action(cls, action: Any, path: str, allow_none: bool = False) -> None:
        if action is None and allow_none:
            return
        if not isinstance(action, str) or not action.strip():
            raise ValueError(f"{path} must be one of {sorted(cls.ALLOWED_ACTIONS)}")
        normalized = action.strip()
        if normalized not in cls.ALLOWED_ACTIONS:
            raise ValueError(f"{path} has invalid action {action!r}; expected one of {sorted(cls.ALLOWED_ACTIONS)}")


@dataclass
class Config:
    """
    Main configuration for FastReAct Nano

    Environment variables:
        FASTRACT_MODEL: Model name (default: gpt-4o-mini)
        FASTRACT_API_BASE: API base URL
        FASTRACT_API_KEY: API key (also checks OPENAI_API_KEY)
        FASTRACT_TEMPERATURE: Temperature (default: 0.7)
        FASTRACT_MAX_TOKENS: Max tokens (default: 8192)
        FASTRACT_MAX_FILE_SIZE: Max file size in bytes (default: 1048576)
        FASTRACT_EXEC_TIMEOUT: Exec timeout in seconds (default: 30)
        FASTRACT_WORKING_DIR: Working directory for exec
        FASTRACT_MAX_ITERATIONS: Max ReAct iterations (default: 20)
        FASTRACT_ENABLE_STEERING: Enable steering (default: true)
        FASTRACT_ENABLE_FOLLOWUP: Enable follow-up (default: true)
        FASTRACT_STEERING_FILE: Steering file path
        FASTRACT_MAX_CONTEXT_TOKENS: Max context window size (default: 128000)
        FASTRACT_CONTEXT_WARNING_THRESHOLD: Context warning threshold (default: 0.8)
        FASTRACT_MAX_TOOL_OUTPUT_CHARS: Max tool output chars for explicit preview/truncation helpers (default: 20000)
        FASTREACT_MCP_TOOL_OUTPUT_BUDGET_CHARS: MCP result budget before artifact/context governance (default: 20000)
        FASTREACT_MCP_TOOL_OUTPUT_PREVIEW_CHARS: MCP issue preview metadata budget (default: 1200)
        FASTREACT_MCP_TOOL_OUTPUT_RETRY_ATTEMPTS: Automatic MCP max_* shrink retries (default: 1)
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
        FASTRACT_USER_SKILLS_DIR: User skills directory (default: none)
        FASTRACT_USER_SKILLS_TEMPLATE: User skills path template (default: {user_workspace}/skills)
        FASTREACT_WORKSPACES_ROOT: Runtime workspace root (default: ~/FastReAct_workspaces)
        FASTREACT_GATEWAY_WORKSPACE: Legacy single-workspace override (default: {workspaces_root}/single/default)
        FASTREACT_AUTH_MODE: service_token, trusted_headers, or jwt (default: service_token)
        FASTREACT_AUTH_JWT_SECRET: JWT shared secret for env-based config
        FASTREACT_AUTH_JWT_SECRET_ENV: Name of the env var holding the JWT shared secret
        FASTRACT_EXTENSIONS_RUNTIME_RELOAD: Enable authenticated runtime extension reload (default: false)
        FASTRACT_EXTENSIONS_MCP_RELOAD: Enable runtime MCP reconnect/reload (default: false)
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    react: ReactConfig = field(default_factory=ReactConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    extensions: ExtensionConfig = field(default_factory=ExtensionConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)

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
            auth=AuthConfig.from_env(),
            extensions=ExtensionConfig.from_env(),
            policy=PolicyConfig.from_env(),
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
                                max_tokens=provider_data.get("max_tokens", DEFAULT_LLM_MAX_TOKENS),
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
                        max_tokens=llm_data.get("max_tokens", DEFAULT_LLM_MAX_TOKENS),
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
                default_react = ReactConfig()
                steering_file = react_data.get("steering_file")
                react_config = ReactConfig(
                    max_iterations=react_data.get("max_iterations", default_react.max_iterations),
                    enable_steering=react_data.get("enable_steering", default_react.enable_steering),
                    enable_followup=react_data.get("enable_followup", default_react.enable_followup),
                    steering_file=_expand_path(steering_file) if steering_file else default_react.steering_file,
                    max_context_tokens=react_data.get("max_context_tokens", default_react.max_context_tokens),
                    context_warning_threshold=react_data.get("context_warning_threshold", default_react.context_warning_threshold),
                    max_tool_output_chars=react_data.get("max_tool_output_chars", default_react.max_tool_output_chars),
                    mcp_tool_output_budget_chars=react_data.get("mcp_tool_output_budget_chars", default_react.mcp_tool_output_budget_chars),
                    mcp_tool_output_preview_chars=react_data.get("mcp_tool_output_preview_chars", default_react.mcp_tool_output_preview_chars),
                    mcp_tool_output_retry_attempts=react_data.get("mcp_tool_output_retry_attempts", default_react.mcp_tool_output_retry_attempts),
                    use_tiktoken=react_data.get("use_tiktoken", default_react.use_tiktoken),
                    tiktoken_model=react_data.get("tiktoken_model", default_react.tiktoken_model),
                    sliding_window_size=react_data.get("sliding_window_size", default_react.sliding_window_size),
                    enable_filesystem_memory=react_data.get("enable_filesystem_memory", default_react.enable_filesystem_memory),
                    max_tree_depth=react_data.get("max_tree_depth", default_react.max_tree_depth),
                    max_files_per_dir=react_data.get("max_files_per_dir", default_react.max_files_per_dir),
                    enable_safety=react_data.get("enable_safety", default_react.enable_safety),
                    strict_mode=react_data.get("strict_mode", default_react.strict_mode),
                    auto_approve_safe=react_data.get("auto_approve_safe", default_react.auto_approve_safe),
                )

            # Extract MCP configuration
            mcp_config = MCPConfig()
            if "mcp" in data:
                mcp_config = MCPConfig.from_dict(data["mcp"])

            # Extract paths configuration
            paths_config = PathsConfig()
            if "paths" in data:
                paths_data = data["paths"]
                workspaces_root = _expand_path(
                    paths_data.get("workspaces_root", str(Path.home() / "FastReAct_workspaces"))
                )
                gateway_workspace = paths_data.get("gateway_workspace")
                paths_config = PathsConfig(
                    global_skills_dir=_expand_path(paths_data.get("global_skills_dir", str(Path.cwd() / "skills" / "builtin"))),
                    user_skills_template=paths_data.get("user_skills_template", "{user_workspace}/skills"),
                    user_skills_dir=_expand_path(paths_data.get("user_skills_dir")) if paths_data.get("user_skills_dir") else None,
                    workspaces_root=workspaces_root,
                    gateway_workspace=_expand_path(gateway_workspace) if gateway_workspace else workspaces_root / "single" / "default",
                )

            # Extract headless HTTP service configuration
            service_config = ServiceConfig()
            if "service" in data:
                service_config = ServiceConfig.from_dict(data["service"], llm_config.api_key_file)

            auth_config = AuthConfig()
            if "auth" in data:
                auth_config = AuthConfig.from_dict(data["auth"])

            extensions_config = ExtensionConfig()
            if "extensions" in data:
                extensions_config = ExtensionConfig.from_dict(data["extensions"])

            policy_config = PolicyConfig()
            if "policy" in data:
                policy_config = PolicyConfig.from_dict(data["policy"])

            return cls(
                llm=llm_config,
                tools=tools_config,
                react=react_config,
                mcp=mcp_config,
                paths=paths_config,
                service=service_config,
                auth=auth_config,
                extensions=extensions_config,
                policy=policy_config,
            )

        # No config file found: use explicit defaults. Runtime startup should be
        # driven by a JSON config path rather than ambient environment variables.
        return cls()

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
