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

    async def ensure_loaded(self, required_skills: Optional[list[str]] = None) -> dict:
        span = TimingSpan("mcp.ensure_loaded")
        skill_key = tuple(sorted(required_skills or []))

        already_loaded = self._agent._mcp_manager is not None
        if already_loaded and self._last_required_skills == skill_key:
            return span.finish(cache_hit=True).to_dict()

        await self._agent._load_mcp_servers(required_skills=required_skills)
        self._agent._core._tools = self._agent._tools
        self._last_required_skills = skill_key
        return span.finish(cache_hit=False).to_dict()
