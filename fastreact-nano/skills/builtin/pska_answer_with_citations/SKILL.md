---
name: pska_answer_with_citations
description: Answer questions using PSKA MCP retrieval tools with citations, gaps, and no unsupported claims.
tags: [pska, qa, citations, retrieval]
version: 1.1.0
mcp_servers: [pska]
recommended_tools: [pska_pska_search, pska_pska_index_status]
---

# PSKA Answer With Citations Skill

Use this skill when answering a user question from Ask PSKA.

Rules:

1. Search PSKA before answering.
2. Use only evidence returned by PSKA tools.
3. Include citations or cited source ids in the response.
4. State gaps directly when PSKA has insufficient evidence.
5. Do not expose private source details unless PSKA returned them for the represented user.
6. Use only read-only PSKA tools for QA: `pska_pska_search` and `pska_pska_index_status`.
7. Do not call `pska_pska_agentic_search`, write, review mutation, job mutation, filesystem, shell, or host tools.
8. During the event stream, short progress `think` messages are allowed so PSKA can show an agentic search timeline: understand the question, search PSKA, inspect results, decide whether another search is needed, then synthesize.
9. For deep research questions, use a generic research loop: start with a broad search, inspect whether the returned evidence names follow-up evidence keys, dossier ids, source ids, unresolved checks, contradictions, or missing dimensions, then run targeted follow-up searches for those items before synthesizing. Stop when the evidence is sufficient, no new evidence appears, or the iteration budget is reached.
10. Start the final user-facing answer with the substantive answer. Do not describe GraphRAG, FastReAct, MCP, tool calls, routing, or retrieval status in the final answer body.
11. If a tool fails or evidence is insufficient, put that limitation in the answer as a knowledge gap, not as an implementation trace.
12. Return source ids/citations in a form PSKA can validate and copy into report text.
