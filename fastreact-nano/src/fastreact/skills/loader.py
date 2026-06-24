"""
Skill loader and registry for FastReAct Nano v2.0
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastreact.skills.base import Skill, SkillMetadata
from fastreact.skills.parser import SkillParser, ParsedSkill


@dataclass(frozen=True)
class SkillLocation:
    """Filesystem location where a skill name was discovered."""

    name: str
    skill_dir: Path
    root_dir: Path
    priority: int
    active: bool = False


class SkillLoader:
    """
    Loads skills from the filesystem

    Skills are directories containing SKILL.md and optional files.
    """

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        parser: Optional[SkillParser] = None,
    ):
        """
        Initialize skill loader

        Args:
            skills_dir: Directory containing skills (default: ./skills/)
            parser: Skill parser instance
        """
        self._skills_dir = skills_dir or Path.cwd() / "skills"
        self._parser = parser or SkillParser()

    @property
    def skills_dir(self) -> Path:
        """Get skills directory"""
        return self._skills_dir

    @property
    def skills_dirs(self) -> list[Path]:
        """Get skill search roots, ordered by precedence."""
        return [self._skills_dir]

    def list_skills(self) -> list[str]:
        """
        List available skill names

        Returns:
            List of skill names (directory names)
        """
        if not self._skills_dir.exists():
            return []

        return [
            d.name for d in self._skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]

    def locations_for(self, name: str) -> list[SkillLocation]:
        """Return all filesystem locations for a skill name."""
        skill_dir = self._skills_dir / name
        if not skill_dir.is_dir():
            return []
        return [
            SkillLocation(
                name=name,
                skill_dir=skill_dir,
                root_dir=self._skills_dir,
                priority=0,
                active=True,
            )
        ]

    def load_skill(self, name: str) -> Optional[Skill]:
        """
        Load a skill by name

        Args:
            name: Skill name (directory name)

        Returns:
            Skill object or None if not found
        """
        skill_dir = self._skills_dir / name

        if not skill_dir.exists():
            return None

        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            return None

        # Parse the skill file
        try:
            parsed = self._parser.parse_file(skill_file)
        except Exception:
            return None

        # Create metadata from parsed content
        metadata = SkillMetadata(
            name=parsed.name,
            description=parsed.description,
            version=str(parsed.metadata.get("version", "1.0.0")),
            author=parsed.metadata.get("author"),
            tags=parsed.metadata.get("tags", []),
            dependencies=parsed.metadata.get("dependencies", []),
            mcp_servers=parsed.metadata.get("mcp_servers", []),
            recommended_tools=parsed.metadata.get("recommended_tools", []),
        )

        return Skill(metadata=metadata, skill_dir=skill_dir)

    def load_all(self) -> dict[str, Skill]:
        """
        Load all available skills

        Returns:
            Dict mapping skill names to Skill objects
        """
        skills = {}

        for name in self.list_skills():
            skill = self.load_skill(name)
            if skill:
                skills[name] = skill

        return skills

    async def load_skill_async(self, name: str) -> Optional[Skill]:
        """
        Load a skill asynchronously

        Args:
            name: Skill name

        Returns:
            Skill object or None if not found
        """
        # Run in thread to avoid blocking
        return await asyncio.to_thread(self.load_skill, name)


class MultiPathSkillLoader:
    """
    Loads skills from multiple directories with deterministic precedence.

    Earlier search paths win. This lets user/workspace skills override global
    built-ins without mutating the global registry or hiding diagnostics about
    duplicate skill names.
    """

    def __init__(
        self,
        skills_dirs: list[Path],
        parser: Optional[SkillParser] = None,
    ):
        self._skills_dirs: list[Path] = []
        for skills_dir in skills_dirs:
            path = Path(skills_dir).expanduser()
            if path not in self._skills_dirs:
                self._skills_dirs.append(path)
        self._parser = parser or SkillParser()

    @property
    def skills_dir(self) -> Path:
        """Compatibility alias for the highest-priority search root."""
        return self._skills_dirs[0] if self._skills_dirs else Path.cwd() / "skills"

    @property
    def skills_dirs(self) -> list[Path]:
        """Get skill search roots, ordered by precedence."""
        return list(self._skills_dirs)

    def _loader_for(self, skills_dir: Path) -> SkillLoader:
        return SkillLoader(skills_dir=skills_dir, parser=self._parser)

    def list_skills(self) -> list[str]:
        """List unique skill names in precedence order."""
        names: list[str] = []
        seen = set()
        for skills_dir in self._skills_dirs:
            if not skills_dir.exists():
                continue
            for name in self._loader_for(skills_dir).list_skills():
                if name not in seen:
                    names.append(name)
                    seen.add(name)
        return names

    def locations_for(self, name: str) -> list[SkillLocation]:
        """Return every discovered location for a skill name."""
        locations: list[SkillLocation] = []
        for priority, skills_dir in enumerate(self._skills_dirs):
            skill_dir = skills_dir / name
            if skill_dir.is_dir():
                locations.append(
                    SkillLocation(
                        name=name,
                        skill_dir=skill_dir,
                        root_dir=skills_dir,
                        priority=priority,
                        active=False,
                    )
                )
        if locations:
            locations[0] = SkillLocation(
                name=locations[0].name,
                skill_dir=locations[0].skill_dir,
                root_dir=locations[0].root_dir,
                priority=locations[0].priority,
                active=True,
            )
        return locations

    def load_skill(self, name: str) -> Optional[Skill]:
        """Load the highest-priority skill matching name."""
        for skills_dir in self._skills_dirs:
            skill = self._loader_for(skills_dir).load_skill(name)
            if skill:
                return skill
        return None

    def load_all(self) -> dict[str, Skill]:
        """Load all unique skills in precedence order."""
        skills = {}
        for name in self.list_skills():
            skill = self.load_skill(name)
            if skill:
                skills[name] = skill
        return skills

    async def load_skill_async(self, name: str) -> Optional[Skill]:
        """Load a skill asynchronously."""
        return await asyncio.to_thread(self.load_skill, name)


class SkillRegistry:
    """
    Registry for managing loaded skills

    Provides on-demand loading with progressive disclosure.
    """

    def __init__(
        self,
        loader: Optional[SkillLoader] = None,
    ):
        """
        Initialize skill registry

        Args:
            loader: Skill loader instance
        """
        self._loader = loader or SkillLoader()
        self._skills: dict[str, Skill] = {}
        self._loaded_prompts: dict[str, str] = {}

    @property
    def loader(self) -> SkillLoader:
        """Get the skill loader"""
        return self._loader

    def list_skills(self) -> list[str]:
        """List all available skill names (alias for list_available)"""
        return self.list_available()

    def list_available(self) -> list[str]:
        """List all available skill names"""
        names: list[str] = []
        seen = set()
        for name in self._loader.list_skills():
            if name not in seen:
                names.append(name)
                seen.add(name)
        for name in self._skills.keys():
            if name not in seen:
                names.append(name)
                seen.add(name)
        return names

    def list_loaded(self) -> list[str]:
        """List currently loaded skill names"""
        return list(self._skills.keys())

    def get(self, name: str, load_if_missing: bool = True) -> Optional[Skill]:
        """
        Get a skill by name

        Args:
            name: Skill name
            load_if_missing: If True, load skill if not already loaded

        Returns:
            Skill object or None
        """
        if name in self._skills:
            return self._skills[name]

        if not load_if_missing:
            return None

        skill = self._loader.load_skill(name)
        if skill:
            self._skills[name] = skill

        return skill

    def add_skill(self, name: str, skill: Skill) -> None:
        """
        Add a skill to the registry

        Args:
            name: Skill name
            skill: Skill object
        """
        self._skills[name] = skill

    def locations_for(self, name: str) -> list[SkillLocation]:
        """Return discovered filesystem locations for a skill."""
        if hasattr(self._loader, "locations_for"):
            locations = self._loader.locations_for(name)
            if locations:
                return locations
        skill = self._skills.get(name)
        if skill:
            return [
                SkillLocation(
                    name=name,
                    skill_dir=skill.skill_dir,
                    root_dir=skill.skill_dir.parent,
                    priority=0,
                    active=True,
                )
            ]
        return []

    def source_path(self, name: str) -> Optional[Path]:
        """Return the active source path for a skill, if known."""
        locations = self.locations_for(name)
        for location in locations:
            if location.active:
                return location.skill_dir
        return locations[0].skill_dir if locations else None

    def get_prompt(self, name: str) -> Optional[str]:
        """
        Get the prompt for a skill

        This implements progressive disclosure:
        1. Load skill if not loaded
        2. Read SKILL.md
        3. Return parsed prompt

        Args:
            name: Skill name

        Returns:
            Skill prompt or None
        """
        skill = self.get(name)
        if not skill:
            return None

        # Check if we already have the prompt cached
        if name in self._loaded_prompts:
            return self._loaded_prompts[name]

        # Read and parse SKILL.md
        skill_file = skill.skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None

        try:
            parsed = self._loader._parser.parse_file(skill_file)
            prompt = parsed.get_prompt()
            self._loaded_prompts[name] = prompt
            return prompt
        except Exception:
            return None

    def get_skill_summary(self, name: str) -> Optional[str]:
        """
        Get a brief summary of a skill for discovery

        Args:
            name: Skill name

        Returns:
            Skill summary or None
        """
        skill = self.get(name, load_if_missing=False)
        if not skill:
            return None

        return f"{skill.name}: {skill.description}"

    def list_summaries(self) -> list[str]:
        """List summaries of all available skills"""
        summaries = []

        for name in self.list_available():
            summary = self.get_skill_summary(name)
            if summary:
                summaries.append(summary)

        return summaries

    async def get_async(self, name: str) -> Optional[Skill]:
        """Get a skill asynchronously"""
        if name in self._skills:
            return self._skills[name]

        skill = await self._loader.load_skill_async(name)
        if skill:
            self._skills[name] = skill

        return skill

    def clear_cache(self):
        """Clear all cached prompts"""
        self._loaded_prompts.clear()

    def reload(self, name: str) -> Optional[Skill]:
        """
        Reload a skill from disk

        Args:
            name: Skill name

        Returns:
            Reloaded skill or None
        """
        # Remove from cache
        if name in self._skills:
            del self._skills[name]
        if name in self._loaded_prompts:
            del self._loaded_prompts[name]

        return self.get(name)
