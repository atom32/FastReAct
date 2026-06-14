---
name: pska_answer_with_citations
description: Answer questions using PSKA MCP retrieval tools with citations, gaps, and no unsupported claims.
tags: [pska, qa, citations, retrieval]
version: 1.0.0
mcp_servers: [pska]
recommended_tools: [pska_pska_search, pska_pska_agentic_search, pska_pska_index_status]
---

# PSKA Answer With Citations Skill

Use this skill when answering a user question from PSKA.

Rules:

1. Search PSKA before answering.
2. Use only evidence returned by PSKA tools.
3. Include citations or cited source ids in the response.
4. State gaps directly when PSKA has insufficient evidence.
5. Do not expose private source details unless PSKA returned them for the represented user.
