"""Skill loading and prompt resolution boundary."""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastreact.agent import Agent
    from fastreact.core.multitenant import UserContext


class SkillResolver:
    """Resolve selected skills and build cache-friendly prompt pieces."""

    def __init__(self, agent: "Agent"):
        self._agent = agent

    def auto_select(
        self,
        query: str,
        max_skills: Optional[int] = None,
        user_context: Optional["UserContext"] = None,
    ) -> list[str]:
        return self._agent._select_skills_auto(
            query,
            max_skills or self._agent._max_auto_skills,
            user_context=user_context,
        )

    def build_prompt(self, skills: Optional[list[str]]) -> tuple[str, str]:
        base_prompt, variable_content = self._agent._build_system_prompt_with_skills(skills)
        if hasattr(self._agent, "tasks"):
            task_context = self._agent.tasks.prompt_context()
            if task_context:
                variable_content = f"{variable_content}\n\n{task_context}"
        return base_prompt, variable_content

    def list_available(self) -> list[str]:
        return self._agent._skills.list_available()
