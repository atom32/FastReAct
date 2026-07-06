"""MCP lazy bootstrap boundary."""

from typing import Optional, TYPE_CHECKING

from fastreact.runtime.timing import TimingSpan

if TYPE_CHECKING:
    from fastreact.agent import Agent


class MCPBootstrapper:
    """Load MCP tools once and refresh Core schemas when needed."""

    def __init__(self, agent: "Agent"):
        self._agent = agent
        self._last_required_skills: tuple[str, ...] | None = None

    async def ensure_loaded(
        self,
        required_skills: Optional[list[str]] = None,
        user_key: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> dict:
        span = TimingSpan("mcp.ensure_loaded")
        identity_key = f"{tenant_key}:{user_key}" if tenant_key and user_key else (user_key or "global")
        skill_key = (identity_key, *tuple(sorted(required_skills or [])))

        already_loaded = self._agent._mcp_manager is not None
        if already_loaded and self._last_required_skills == skill_key and self._required_mcp_ready(required_skills):
            return span.finish(cache_hit=True).to_dict()

        await self._agent._load_mcp_servers(
            required_skills=required_skills,
            user_key=user_key,
            tenant_key=tenant_key,
        )
        self._agent._core._tools = self._agent._tools
        mcp_ready = self._required_mcp_ready(required_skills)
        if mcp_ready:
            self._last_required_skills = skill_key
        return span.finish(cache_hit=False, mcp_ready=mcp_ready).to_dict()

    def _required_mcp_ready(self, required_skills: Optional[list[str]] = None) -> bool:
        required_servers = self._required_mcp_servers(required_skills)
        if not required_servers:
            return True
        try:
            statuses = self._agent.list_mcp_server_status()
        except Exception:
            statuses = []
        status_by_name = {str(status.get("name")): status for status in statuses if status.get("name")}
        for server_name in required_servers:
            status = status_by_name.get(server_name)
            if not status or not status.get("alive") or not status.get("loaded") or not status.get("tool_count"):
                return False
        return True

    def _required_mcp_servers(self, required_skills: Optional[list[str]] = None) -> set[str]:
        required_servers: set[str] = set()
        skills = getattr(self._agent, "_skills", {}) or {}
        for skill_name in required_skills or []:
            skill = skills.get(skill_name)
            metadata = getattr(skill, "metadata", None)
            for server_name in getattr(metadata, "mcp_servers", []) or []:
                if str(server_name).strip():
                    required_servers.add(str(server_name).strip())
        return required_servers
