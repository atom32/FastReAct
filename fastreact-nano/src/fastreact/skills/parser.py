"""
Skill parser for FastReAct Nano v2.0

Parses SKILL.md files and extracts structured information.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


@dataclass
class ParsedSkill:
    """Parsed skill content"""

    name: str
    description: str
    sections: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    referenced_files: list[str] = field(default_factory=list)

    # Extracted tool references
    tool_references: list[str] = field(default_factory=list)

    def get_section(self, section_name: str) -> Optional[str]:
        """Get a section by name"""
        return self.sections.get(section_name)

    def get_prompt(self) -> str:
        """Get the main prompt for this skill"""
        # Combine description with main sections
        parts = [f"# {self.name}\n", self.description]

        # Add key sections
        for section in ["When to Use", "How it Works", "Instructions"]:
            content = self.get_section(section)
            if content:
                parts.append(f"\n## {section}\n{content}")

        return "\n".join(parts)


class SkillParser:
    """
    Parser for SKILL.md files

    Extracts structured information from Markdown skill definitions.
    """

    # YAML frontmatter pattern
    FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

    # Section pattern (## Header)
    SECTION_RE = re.compile(r"^##\s+(.+?)\s*\n(.*?)(?=^##|\Z)", re.MULTILINE | re.DOTALL)

    # File reference pattern ([filename.md] or (see filename.md))
    FILE_REF_RE = re.compile(r"\[([^\]]+\.(?:md|txt|py|js))\]|\(see\s+([^\)]+\.(?:md|txt|py|js))\)")

    # Tool reference pattern (tool_name or `tool_name`)
    TOOL_REF_RE = re.compile(r"(?:^|\s)([a-zA-Z_][a-zA-Z0-9_]*_mcp_[a-zA-Z0-9_]+|[a-zA-Z_][a-zA-Z0-9_]*)(?=$|\s|[.,:])")

    def __init__(self):
        pass

    def parse(self, content: str, skill_name: str = "unknown") -> ParsedSkill:
        """
        Parse skill markdown content

        Args:
            content: Markdown content
            skill_name: Name of the skill

        Returns:
            ParsedSkill object
        """
        # Extract frontmatter
        frontmatter = self._extract_frontmatter(content)
        content_without_frontmatter = self.FRONTMATTER_RE.sub("", content)

        # Extract sections
        sections = self._extract_sections(content_without_frontmatter)

        # Extract name and description
        # Priority: frontmatter > sections > skill_name
        name = frontmatter.get("name", sections.get("Name", skill_name))
        description = frontmatter.get("description", sections.get("Description", ""))

        # If still no description, use the first paragraph
        if not description:
            first_paragraph = self._extract_first_paragraph(content_without_frontmatter)
            description = first_paragraph

        # Extract file references
        referenced_files = self._extract_file_references(content)

        # Extract tool references
        tool_references = self._extract_tool_references(frontmatter, content)

        return ParsedSkill(
            name=name,
            description=description.strip(),
            sections=sections,
            metadata=frontmatter,
            referenced_files=referenced_files,
            tool_references=tool_references,
        )

    def parse_file(self, skill_file: Path) -> ParsedSkill:
        """
        Parse a SKILL.md file

        Args:
            skill_file: Path to SKILL.md

        Returns:
            ParsedSkill object
        """
        if not skill_file.exists():
            raise FileNotFoundError(f"Skill file not found: {skill_file}")

        content = skill_file.read_text(encoding="utf-8")
        skill_name = skill_file.parent.name

        return self.parse(content, skill_name)

    def _extract_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter"""
        match = self.FRONTMATTER_RE.match(content)
        if not match:
            return {}

        try:
            import yaml
            data = yaml.safe_load(match.group(1)) or {}

            # Normalize MCP server dependencies
            if "mcp_servers" not in data:
                data["mcp_servers"] = []

            # Normalize recommended tools
            if "recommended_tools" not in data:
                data["recommended_tools"] = []

            return data
        except Exception:
            return {}

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Extract markdown sections"""
        sections = {}

        for match in self.SECTION_RE.finditer(content):
            header = match.group(1).strip()
            body = match.group(2).strip()
            sections[header] = body

        return sections

    def _extract_first_paragraph(self, content: str) -> str:
        """Extract the first non-empty paragraph"""
        lines = content.split("\n")
        paragraph = []

        for line in lines:
            line = line.strip()
            # Skip headers and empty lines
            if line.startswith("#") or not line:
                if paragraph:  # Stop if we already have content
                    break
                continue
            paragraph.append(line)
            if len(paragraph) >= 3:  # Limit to 3 lines
                break

        return " ".join(paragraph)

    def _extract_file_references(self, content: str) -> list[str]:
        """Extract referenced filenames"""
        files = []

        for match in self.FILE_REF_RE.finditer(content):
            # Try both capture groups
            filename = match.group(1) or match.group(2)
            if filename:
                files.append(filename)

        return list(set(files))  # Deduplicate

    def _extract_tool_references(self, frontmatter: dict[str, Any], content: str) -> list[str]:
        """Extract tool references from frontmatter and content"""
        tools = []

        # Extract from frontmatter
        if "recommended_tools" in frontmatter:
            tools.extend(frontmatter["recommended_tools"])

        # Extract from content (look for tool patterns)
        # Look for mentions of specific tools in the content
        for match in self.TOOL_REF_RE.finditer(content):
            tool = match.group(1)
            if tool and len(tool) > 3:  # Filter out short words
                tools.append(tool)

        return list(set(tools))  # Deduplicate
