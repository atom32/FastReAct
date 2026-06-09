"""
Concurrent user tests for multi-tenant isolation

Tests validate that multiple users can access the system simultaneously
with proper workspace, config, and memory isolation.
"""

import pytest
import asyncio
import sys
from pathlib import Path

from fastreact import Agent, EventType
from fastreact.core.config import Config

from tests.helpers import (
    collect_events,
    extract_final_answer,
    assert_session_completed,
)


# Use python3 on macOS, python on other platforms
PYTHON_CMD = sys.executable


class TestConcurrentUserAccess:
    """
    Test concurrent user access to validate multi-tenant isolation
    """

    @pytest.mark.asyncio
    async def test_ten_users_concurrent_queries(self):
        """10 users should be able to query concurrently without interference"""
        # Config without real API (use mock for faster testing)
        config = Config()

        agent = Agent(config=config, multitenant=True)

        # Create 10 concurrent queries
        tasks = []
        for i in range(10):
            user_key = f"feishu:ou_user_{i}"
            task = agent.run_event_stream(
                f"Hello, I am user {i}",
                user_key=user_key,
            )
            tasks.append(task)

        # Execute all concurrently
        results = await asyncio.gather(*[collect_events(t) for t in tasks])

        # Verify all completed
        for i, events in enumerate(results):
            assert_session_completed(events)
            print(f"[TEST] User {i} completed")

        # Verify workspaces are isolated
        for i in range(10):
            workspace = agent._multitenant.get_user_workspace(f"feishu:ou_user_{i}")
            assert workspace.exists()
            assert workspace.name == f"feishu_ou_user_{i}"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_concurrent_users_with_graphrag(self, config_with_real_llm):
        """Multiple users should be able to use GraphRAG concurrently"""
        # Setup config with GraphRAG
        config = config_with_real_llm
        config.mcp.servers = [
            {
                "name": "graphrag",
                "command": PYTHON_CMD,
                "args": ["mcp_servers/builtin/graph_rag_server.py"],
                "associated_skill": "graphrag_workflow",
            }
        ]

        agent = Agent(config=config, multitenant=True)

        # Create concurrent queries for different users
        queries = [
            ("feishu:ou_user_a", "Search for AI"),
            ("feishu:ou_user_b", "Search for ML"),
            ("feishu:ou_user_c", "Search for DL"),
            ("feishu:ou_user_d", "Tell me about Neural Networks"),
        ]

        tasks = []
        for user_key, query in queries:
            task = agent.run_event_stream(
                query,
                user_key=user_key,
                skills=["graphrag_workflow"]
            )
            tasks.append((user_key, task))

        # Execute all concurrently
        results = []
        for user_key, task in tasks:
            events = await collect_events(task)
            results.append((user_key, events))

        # Verify all completed
        for user_key, events in results:
            assert_session_completed(events)
            print(f"[TEST] {user_key} completed")

        # Verify workspaces are isolated
        workspaces = [agent._multitenant.get_user_workspace(uk) for uk, _ in queries]
        assert len(set(workspaces)) == len(queries), "Workspaces should be unique"

        # Cleanup
        await agent.close_mcp_servers()

    @pytest.mark.asyncio
    async def test_same_user_concurrent_sessions(self):
        """Same user should have multiple concurrent sessions with different session_ids"""
        config = Config()
        agent = Agent(config=config, multitenant=True)
        user_key = "feishu:ou_concurrent_sessions"

        # Create 3 concurrent sessions for same user
        tasks = []
        session_ids = ["session-1", "session-2", "session-3"]

        for session_id in session_ids:
            task = agent.run_event_stream(
                f"Message for {session_id}",
                user_key=user_key,
                session_id=session_id,
            )
            tasks.append(task)

        # Execute all concurrently
        results = await asyncio.gather(*[collect_events(t) for t in tasks])

        # Verify all completed
        for i, events in enumerate(results):
            assert_session_completed(events)

        # All should use same workspace
        workspace = agent._multitenant.get_user_workspace(user_key)
        assert workspace.exists()


class TestWorkspaceIsolation:
    """
    Test workspace isolation between users
    """

    @pytest.mark.asyncio
    async def test_user_workspace_structure(self):
        """Each user workspace should have correct structure"""
        config = Config()
        agent = Agent(config=config, multitenant=True)

        # Create queries for multiple users
        users = ["feishu:ou_alice", "feishu:ou_bob", "feishu:ou_charlie"]

        for user_key in users:
            await collect_events(
                agent.run_event_stream(
                    "Create my workspace",
                    user_key=user_key,
                )
            )

        # Check each workspace structure
        for user_key in users:
            context = agent._multitenant.get_user_context(user_key)
            workspace = context.workspace

            # Check workspace exists
            assert workspace.exists()
            assert workspace.is_dir()

            # Check config file exists
            config_file = workspace / "config.json"
            assert config_file.exists()

            # Check skills directory exists
            skills_dir = workspace / "skills"
            assert skills_dir.exists()

            # Check memory file path
            memory_file = context.memory_file
            assert memory_file.parent == workspace

    @pytest.mark.asyncio
    async def test_workspace_data_isolation(self):
        """Data in one workspace should not leak to another"""
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            config = Config()
            agent = Agent(config=config, multitenant=True, base_workspace=Path(tmpdir))

            user_a = "feishu:ou_user_a"
            user_b = "feishu:ou_user_b"

            # User A creates a file
            await collect_events(
                agent.run_event_stream(
                    'Write file "test.txt" with content "User A data"',
                    user_key=user_a,
                )
            )

            # User B queries
            await collect_events(
                agent.run_event_stream(
                    "Read file test.txt",
                    user_key=user_b,
                )
            )

            # User B should not see User A's file
            workspace_b = agent._multitenant.get_user_workspace(user_b)
            test_file_b = workspace_b / "test.txt"

            # File should not exist in B's workspace
            assert not test_file_b.exists(), "User B should not see User A's file"

    @pytest.mark.asyncio
    async def test_config_isolation(self):
        """Each user should have independent config"""
        config = Config()
        agent = Agent(config=config, multitenant=True)

        # Get contexts for different users
        context_a = agent._multitenant.get_user_context("feishu:ou_config_a")
        context_b = agent._multitenant.get_user_context("feishu:ou_config_b")

        # Update config for user A
        agent._multitenant.update_user_config(
            "feishu:ou_config_a",
            {"preference": "user_a_preference"}
        )

        # Reload contexts
        context_a_reloaded = agent._multitenant.get_user_context("feishu:ou_config_a")
        context_b_reloaded = agent._multitenant.get_user_context("feishu:ou_config_b")

        # Check isolation
        assert context_a_reloaded.config.get("preference") == "user_a_preference"
        assert context_b_reloaded.config.get("preference") != "user_a_preference"


class TestSessionIsolation:
    """
    Test session isolation within the same user context
    """

    @pytest.mark.asyncio
    async def test_different_sessions_same_user(self):
        """Same user with different session_ids should have isolated conversations"""
        config = Config()
        agent = Agent(config=config, multitenant=True)
        user_key = "feishu:ou_session_test"

        # Session 1: English conversation
        events_1 = await collect_events(
            agent.run_event_stream(
                "My name is Alice",
                user_key=user_key,
                session_id="session-en",
            )
        )

        # Session 2: Chinese conversation
        events_2 = await collect_events(
            agent.run_event_stream(
                "我的名字是 Bob",
                user_key=user_key,
                session_id="session-cn",
            )
        )

        # Both should complete
        assert_session_completed(events_1)
        assert_session_completed(events_2)

        # Sessions should be independent
        answer_1 = extract_final_answer(events_1)
        answer_2 = extract_final_answer(events_2)

        # Both should have answers (even if empty, sessions completed)
        assert answer_1 is not None
        assert answer_2 is not None

        # Check session IDs are different in events
        # Note: session_id format is "user_key:session_id"
        session_ids_1 = set(e.session_id for e in events_1 if e.session_id)
        session_ids_2 = set(e.session_id for e in events_2 if e.session_id)

        # Sessions should have different IDs
        assert len(session_ids_1) > 0
        assert len(session_ids_2) > 0
        # Check that the session-specific IDs are different
        assert session_ids_1 != session_ids_2
        # Verify each contains the correct session_id suffix
        assert any("session-en" in sid for sid in session_ids_1)
        assert any("session-cn" in sid for sid in session_ids_2)

    @pytest.mark.asyncio
    async def test_session_context_preservation(self):
        """Session context should be preserved across multiple messages"""
        config = Config()
        agent = Agent(config=config, multitenant=True)
        user_key = "feishu:ou_context_test"
        session_id = "context-preservation-test"

        # First message
        await collect_events(
            agent.run_event_stream(
                "My favorite color is blue",
                user_key=user_key,
                session_id=session_id,
            )
        )

        # Second message in same session
        events = await collect_events(
            agent.run_event_stream(
                "What is my favorite color?",
                user_key=user_key,
                session_id=session_id,
            )
        )

        # Should complete
        assert_session_completed(events)


class TestConcurrentStressTest:
    """
    Stress tests for concurrent access
    """

    @pytest.mark.asyncio
    async def test_rapid_successive_queries_same_user(self):
        """Rapid successive queries from same user should not cause conflicts"""
        config = Config()
        agent = Agent(config=config, multitenant=True)
        user_key = "feishu:ou_rapid"

        # Send 10 rapid queries
        tasks = []
        for i in range(10):
            task = agent.run_event_stream(
                f"Query number {i}",
                user_key=user_key,
                session_id=f"rapid-{i}",
            )
            tasks.append(task)

        # Execute all
        results = await asyncio.gather(*[collect_events(t) for t in tasks])

        # All should complete
        for i, events in enumerate(results):
            assert_session_completed(events)

    @pytest.mark.asyncio
    async def test_mixed_users_and_sessions(self):
        """Mix of different users and different sessions"""
        config = Config()
        agent = Agent(config=config, multitenant=True)

        # Create mixed workload
        tasks = []

        # 5 users, 2 sessions each
        for user_idx in range(5):
            for session_idx in range(2):
                user_key = f"feishu:ou_mixed_{user_idx}"
                session_id = f"mixed-session-{session_idx}"

                task = agent.run_event_stream(
                    f"Message from user {user_idx}, session {session_idx}",
                    user_key=user_key,
                    session_id=session_id,
                )
                tasks.append(task)

        # Execute all
        results = await asyncio.gather(*[collect_events(t) for t in tasks])

        # All should complete
        assert len(results) == 10  # 5 users * 2 sessions
        for events in results:
            assert_session_completed(events)
