"""
FastReAct Nano - MCP Tool Discovery Service

Provides tool discovery and matching between skills and MCP tools.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import time


@dataclass
class ToolInfo:
    """Information about an available tool"""

    name: str
    description: str
    server_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    associated_skill: Optional[str] = None

    def __str__(self) -> str:
        """String representation for prompt injection"""
        lines = [
            f"- `{self.name}`: {self.description}",
        ]
        if self.associated_skill:
            lines.append(f"  (Part of {self.associated_skill} skill)")
        return "\n".join(lines)


class MCPToolDiscovery:
    """
    Discovers and indexes MCP tools for skill integration.

    This service:
    1. Indexes all registered MCP tools
    2. Provides tool summaries for skills
    3. Matches skills to their required tools
    4. Generates tool availability context
    """

    def __init__(self):
        """Initialize tool discovery service"""
        self._tools: Dict[str, ToolInfo] = {}
        self._servers: Dict[str, List[str]] = {}  # server_name -> tool_names
        self._skill_tools: Dict[str, List[str]] = {}  # skill_name -> tool_names
        self._server_descriptions: Dict[str, str] = {}  # server_name -> description

    def index_tool(
        self,
        tool_name: str,
        server_name: str,
        description: str,
        parameters: Dict[str, Any] = None,
        associated_skill: Optional[str] = None,
    ) -> None:
        """
        Index a tool for discovery

        Args:
            tool_name: Full tool name (with namespace)
            server_name: MCP server name
            description: Tool description
            parameters: Tool parameter schema
            associated_skill: Optional skill this tool belongs to
        """
        tool_info = ToolInfo(
            name=tool_name,
            description=description,
            server_name=server_name,
            parameters=parameters or {},
            associated_skill=associated_skill,
        )

        self._tools[tool_name] = tool_info

        # Track by server
        if server_name not in self._servers:
            self._servers[server_name] = []
        self._servers[server_name].append(tool_name)

        # Track by skill
        if associated_skill:
            if associated_skill not in self._skill_tools:
                self._skill_tools[associated_skill] = []
            self._skill_tools[associated_skill].append(tool_name)

    def index_server(self, server_name: str, description: str) -> None:
        """
        Index a server description

        Args:
            server_name: MCP server name
            description: Server description
        """
        self._server_descriptions[server_name] = description

    def get_tools_for_skill(self, skill_name: str) -> List[ToolInfo]:
        """
        Get tools associated with a specific skill

        Args:
            skill_name: Name of the skill

        Returns:
            List of ToolInfo objects
        """
        tool_names = self._skill_tools.get(skill_name, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tools_for_server(self, server_name: str) -> List[ToolInfo]:
        """
        Get tools from a specific server

        Args:
            server_name: Name of the MCP server

        Returns:
            List of ToolInfo objects
        """
        tool_names = self._servers.get(server_name, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def search_tools(self, query: str, limit: int = 10) -> List[ToolInfo]:
        """
        Search for tools by keyword

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching ToolInfo objects
        """
        query_lower = query.lower()
        results = []

        for tool_info in self._tools.values():
            # Search in name and description
            if (
                query_lower in tool_info.name.lower()
                or query_lower in tool_info.description.lower()
            ):
                results.append(tool_info)

        return results[:limit]

    def generate_skill_tools_section(
        self,
        skill_name: str,
        mcp_servers: List[str] = None,
    ) -> str:
        """
        Generate tool section for a skill's prompt

        Args:
            skill_name: Name of the skill
            mcp_servers: Optional list of MCP server names to include

        Returns:
            Markdown formatted section with available tools
        """
        tools = self.get_tools_for_skill(skill_name)

        # Also include tools from specified servers
        if mcp_servers:
            for server_name in mcp_servers:
                server_tools = self.get_tools_for_server(server_name)
                for tool in server_tools:
                    if tool not in tools:
                        tools.append(tool)

        if not tools:
            return ""

        lines = [
            "## Available MCP Tools",
            "",
            "The following MCP tools are available for this skill:",
            "",
        ]

        for tool in tools:
            lines.append(str(tool))

        return "\n".join(lines)

    def generate_tools_summary(self, tool_names: List[str]) -> str:
        """
        Generate a summary of specific tools

        Args:
            tool_names: List of tool names to summarize

        Returns:
            Markdown formatted summary
        """
        lines = []
        for tool_name in tool_names:
            if tool_name in self._tools:
                tool_info = self._tools[tool_name]
                lines.append(f"- `{tool_info.name}`: {tool_info.description}")

        return "\n".join(lines)

    def list_all_tools(self) -> List[str]:
        """List all indexed tool names"""
        return list(self._tools.keys())

    def list_all_servers(self) -> List[str]:
        """List all indexed server names"""
        return list(self._servers.keys())

    def get_server_description(self, server_name: str) -> Optional[str]:
        """Get description of a server"""
        return self._server_descriptions.get(server_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is indexed"""
        return tool_name in self._tools

    def has_server(self, server_name: str) -> bool:
        """Check if a server is indexed"""
        return server_name in self._servers

    def clear(self) -> None:
        """Clear all indexed data"""
        self._tools.clear()
        self._servers.clear()
        self._skill_tools.clear()
        self._server_descriptions.clear()

    def get_index_time(self) -> float:
        """
        Get approximate time to index tools (for performance monitoring)

        Returns:
            Time in seconds (placeholder for now)
        """
        return 0.0  # Placeholder for future timing implementation
