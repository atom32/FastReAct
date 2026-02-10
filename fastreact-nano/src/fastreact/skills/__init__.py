"""
FastReAct Nano v2.0 - Skill System

Hybrid approach combining:
- Nanobot: Simplicity and minimal code
- Claude Code: Progressive disclosure and on-demand loading
- Moltbot: Extensibility through plugins

Skills are Markdown-first with optional Python scripts.
"""

from fastreact.skills.base import Skill, SkillMetadata
from fastreact.skills.loader import SkillLoader, SkillRegistry
from fastreact.skills.parser import SkillParser, ParsedSkill

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillLoader",
    "SkillRegistry",
    "SkillParser",
    "ParsedSkill",
]
