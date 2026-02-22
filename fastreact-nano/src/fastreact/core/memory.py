"""
Memory Manager for FastReAct Nano

Implements dual-layer memory system:
1. SHORT-TERM: AgentSession._history (in-memory, max 50 messages)
2. LONG-TERM: MEMORY.md (persistent, key facts extracted by LLM)

When short-term history exceeds threshold, MemoryManager.consolidate() is triggered:
- Extracts key facts using LLM
- Appends to MEMORY.md
- Archives old history to HISTORY.md
- Clears short-term history

Architecture:
AgentSession → MemoryManager.consolidate() → MEMORY.md + HISTORY.md
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastreact import Agent


class MemoryManager:
    """
    Memory Manager - Dual-layer memory system

    Responsibilities:
    - Consolidate short-term history to long-term memory
    - Extract key facts using LLM
    - Maintain MEMORY.md (long-term facts)
    - Maintain HISTORY.md (searchable archive)

    File Structure:
    workspaces/{user}/
        MEMORY.md   - Long-term facts (user preferences, important conclusions)
        HISTORY.md  - Conversation archive (searchable history)
    """

    def __init__(
        self,
        workspace_path: Path,
        agent: "Agent",
        consolidation_threshold: int = 50,
    ):
        """
        Initialize memory manager

        Args:
            workspace_path: Path to user workspace
            agent: Agent instance for LLM calls
            consolidation_threshold: Trigger consolidation when history exceeds this
        """
        self._workspace_path = workspace_path
        self._agent = agent
        self._threshold = consolidation_threshold

        # Ensure workspace exists
        self._workspace_path.mkdir(parents=True, exist_ok=True)

        # Memory files
        self._memory_file = self._workspace_path / "MEMORY.md"
        self._history_file = self._workspace_path / "HISTORY.md"

        # Initialize files if not exist
        self._init_memory_files()

    def _init_memory_files(self):
        """Initialize MEMORY.md and HISTORY.md if they don't exist"""
        if not self._memory_file.exists():
            self._memory_file.write_text(
                "# Long-Term Memory\n\n"
                "_This file contains key facts extracted from conversations._\n\n"
                f"_Created: {datetime.utcnow().isoformat()}_\n\n"
                "---\n\n",
                encoding="utf-8"
            )

        if not self._history_file.exists():
            self._history_file.write_text(
                "# Conversation History\n\n"
                "_This file contains archived conversation history._\n\n"
                f"_Created: {datetime.utcnow().isoformat()}_\n\n"
                "---\n\n",
                encoding="utf-8"
            )

    async def consolidate(
        self,
        history: list[dict],
        session_id: str,
    ) -> list[dict]:
        """
        Consolidate short-term history to long-term memory

        Process:
        1. Extract key facts using LLM
        2. Append to MEMORY.md
        3. Archive to HISTORY.md
        4. Return empty history (cleared) on success, original history on failure

        Args:
            history: Current conversation history
            session_id: Session identifier for logging

        Returns:
            Empty list (history is cleared after consolidation) on success,
            or original history if consolidation fails
        """
        import sys

        print(
            f"[MEMORY] Consolidating {len(history)} messages for session {session_id}",
            file=sys.stderr
        )

        try:
            # Step 1: Extract key facts using LLM
            key_facts = await self._extract_key_facts(history)

            # Only continue if extraction succeeded
            if not key_facts:
                raise Exception("No key facts extracted")

            # Step 2: Append to MEMORY.md
            await self._append_to_memory(key_facts, history)
            print(
                f"[MEMORY] Extracted {len(key_facts)} key facts to MEMORY.md",
                file=sys.stderr
            )

            # Step 3: Archive to HISTORY.md
            await self._archive_to_history(history)

            # Step 4: Clear history on success
            print(
                f"[MEMORY] Archived history to HISTORY.md, cleared short-term memory",
                file=sys.stderr
            )

            return []  # Success: clear history

        except Exception as e:
            # Failure: return original history
            print(
                f"[ERROR] Memory consolidation failed: {e}, keeping original history",
                file=sys.stderr
            )
            return history  # Return original history (fallback)

    async def _extract_key_facts(self, history: list[dict]) -> list[str]:
        """
        Extract key facts from conversation history using LLM

        Args:
            history: Conversation history

        Returns:
            List of key facts (one per line)
        """
        # Build conversation summary
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in history
        ])

        # Prompt for LLM
        prompt = f"""Analyze this conversation and extract key facts worth remembering.

Focus on:
1. User identity (name, role, organization)
2. User preferences and requirements
3. Important decisions or conclusions
4. Technical details or configurations
5. Action items or next steps

Format: Return one fact per line as a bullet point.
- Fact 1
- Fact 2
- ...

Conversation:
{conversation_text}

Key facts:"""

        try:
            # Call LLM (reuse agent's LLM provider)
            if hasattr(self._agent, '_llm') or hasattr(self._agent, 'config'):
                # Try to get LLM from agent
                llm = getattr(self._agent, '_llm', None)
                if not llm and hasattr(self._agent, 'config'):
                    llm = getattr(self._agent.config, 'llm', None)

                if llm:
                    # Use chat() method instead of complete()
                    from fastreact.core.messages import Message
                    response = await llm.chat(
                        messages=[Message.user(prompt)],
                        tools=None
                    )
                    facts = self._parse_facts(response.content)
                    return facts

        except Exception as e:
            import sys
            print(
                f"[ERROR] Failed to extract key facts: {e}",
                file=sys.stderr
            )

        return []

    def _parse_facts(self, response: str) -> list[str]:
        """
        Parse LLM response into list of facts

        Args:
            response: LLM response text

        Returns:
            List of facts (bullet points without "- " prefix)
        """
        facts = []
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                facts.append(line[2:].strip())
            elif line and not line.startswith("#"):
                # Non-bullet lines that look like facts
                if len(line) > 10 and not line.startswith("Key facts"):
                    facts.append(line)

        return facts

    async def _append_to_memory(self, facts: list[str], history: list[dict]):
        """
        Append key facts to MEMORY.md

        Args:
            facts: List of key facts
            history: Original conversation (for context)
        """
        # Build entry
        timestamp = datetime.utcnow().isoformat()
        entry = f"\n## Memory Update - {timestamp}\n\n"

        if facts:
            entry += "### Key Facts\n\n"
            for fact in facts:
                entry += f"- {fact}\n"
            entry += "\n"

        # Append to file
        try:
            current_content = self._memory_file.read_text(encoding="utf-8")
            self._memory_file.write_text(
                current_content + entry,
                encoding="utf-8"
            )
        except Exception as e:
            import sys
            print(
                f"[ERROR] Failed to append to MEMORY.md: {e}",
                file=sys.stderr
            )

    async def _archive_to_history(self, history: list[dict]):
        """
        Archive conversation to HISTORY.md

        Args:
            history: Conversation history to archive
        """
        # Build entry
        timestamp = datetime.utcnow().isoformat()
        entry = f"\n## Conversation - {timestamp}\n\n"

        for msg in history:
            role = msg["role"].upper()
            content = msg["content"]
            entry += f"**{role}**: {content}\n\n"

        entry += "---\n"

        # Append to file
        try:
            current_content = self._history_file.read_text(encoding="utf-8")
            self._history_file.write_text(
                current_content + entry,
                encoding="utf-8"
            )
        except Exception as e:
            import sys
            print(
                f"[ERROR] Failed to archive to HISTORY.md: {e}",
                file=sys.stderr
            )

    async def recall(self, query: str, top_k: int = 5) -> list[str]:
        """
        Recall relevant facts from MEMORY.md

        Simple keyword-based search (can be upgraded to vector search later)

        Args:
            query: Search query
            top_k: Maximum number of facts to return

        Returns:
            List of relevant facts
        """
        try:
            # Read MEMORY.md
            content = self._memory_file.read_text(encoding="utf-8")

            # Simple keyword matching
            facts = []
            query_lower = query.lower()

            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("- ") and query_lower in line.lower():
                    facts.append(line[2:].strip())

                    if len(facts) >= top_k:
                        break

            return facts

        except Exception as e:
            import sys
            print(
                f"[ERROR] Failed to recall from memory: {e}",
                file=sys.stderr
            )
            return []

    def get_memory_stats(self) -> dict:
        """
        Get memory statistics

        Returns:
            Dict with stats (memory_size, history_size, last_update)
        """
        try:
            memory_content = self._memory_file.read_text(encoding="utf-8")
            history_content = self._history_file.read_text(encoding="utf-8")

            return {
                "memory_size_bytes": len(memory_content),
                "history_size_bytes": len(history_content),
                "memory_file": str(self._memory_file),
                "history_file": str(self._history_file),
            }
        except Exception:
            return {
                "memory_size_bytes": 0,
                "history_size_bytes": 0,
                "memory_file": str(self._memory_file),
                "history_file": str(self._history_file),
            }
