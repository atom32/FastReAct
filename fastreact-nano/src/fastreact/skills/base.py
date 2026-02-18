"""
Skill base classes for FastReAct Nano v2.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Any


@dataclass
class SkillMetadata:
    """Metadata about a skill"""

    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    # MCP server dependencies
    mcp_servers: list[str] = field(default_factory=list)

    # Tool recommendations
    recommended_tools: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillMetadata":
        """Create from dictionary"""
        return cls(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            mcp_servers=data.get("mcp_servers", []),
            recommended_tools=data.get("recommended_tools", []),
        )


class Skill:
    """
    Base class for all skills

    A skill is a reusable capability that can be loaded on-demand.
    Skills use progressive disclosure to minimize token usage.
    """

    def __init__(
        self,
        metadata: SkillMetadata,
        skill_dir: Path,
    ):
        """
        Initialize a skill

        Args:
            metadata: Skill metadata
            skill_dir: Directory containing skill files
        """
        self._metadata = metadata
        self._skill_dir = skill_dir

    @property
    def metadata(self) -> SkillMetadata:
        """Get skill metadata"""
        return self._metadata

    @property
    def name(self) -> str:
        """Get skill name"""
        return self._metadata.name

    @property
    def description(self) -> str:
        """Get skill description"""
        return self._metadata.description

    @property
    def skill_dir(self) -> Path:
        """Get skill directory"""
        return self._skill_dir

    def get_file_path(self, filename: str) -> Optional[Path]:
        """
        Get path to a file in the skill directory

        Args:
            filename: Name of the file

        Returns:
            Path if file exists, None otherwise
        """
        path = self._skill_dir / filename
        return path if path.exists() else None

    def read_file(self, filename: str) -> Optional[str]:
        """
        Read a file from the skill directory

        Args:
            filename: Name of the file

        Returns:
            File content or None if not found
        """
        path = self.get_file_path(filename)
        if path:
            return path.read_text(encoding="utf-8")
        return None

    def list_files(self) -> list[str]:
        """List all files in the skill directory"""
        if not self._skill_dir.exists():
            return []

        return [
            f.name for f in self._skill_dir.iterdir()
            if f.is_file() and not f.name.startswith("_")
        ]

    def __repr__(self) -> str:
        return f"Skill(name={self.name}, version={self.metadata.version})"
