from pathlib import Path

import pytest

from fastreact.agent import Agent
from fastreact.core.config import Config, PathsConfig
from fastreact.core.multitenant import SecurityError, UserContext


def _agent(tmp_path: Path) -> Agent:
    return Agent(
        config=Config(
            paths=PathsConfig(
                global_skills_dir=tmp_path / "missing-skills",
                gateway_workspace=tmp_path / "workspace",
            )
        )
    )


def test_user_skills_dir_must_stay_inside_workspace(tmp_path):
    agent = _agent(tmp_path)
    workspace = tmp_path / "workspace" / "web_alice"
    skills_dir = tmp_path / "outside-skills"
    context = UserContext(
        user_key="web:alice",
        workspace=workspace,
        config={},
        skills_dir=skills_dir,
        memory_file=workspace / "memory.json",
    )

    with pytest.raises(SecurityError, match="not contained within workspace"):
        agent._select_skills_auto("use my private skill", user_context=context)


def test_user_skills_dir_inside_workspace_is_allowed(tmp_path):
    agent = _agent(tmp_path)
    workspace = tmp_path / "workspace" / "web_alice"
    skills_dir = workspace / "skills"
    skills_dir.mkdir(parents=True)
    context = UserContext(
        user_key="web:alice",
        workspace=workspace,
        config={},
        skills_dir=skills_dir,
        memory_file=workspace / "memory.json",
    )

    assert agent._select_skills_auto("no matching skill", user_context=context) == []
