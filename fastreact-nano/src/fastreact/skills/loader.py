"""
Skill loader and registry for FastReAct Nano v2.0
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastreact.skills.base import Skill, SkillMetadata
from fastreact.skills.parser import SkillParser, ParsedSkill


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
        return self._loader.list_skills()

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
