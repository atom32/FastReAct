---
name: pska_extract
description: Execute PSKA extraction jobs by using PSKA MCP tools, preserving ACLs, source refs, review boundaries, and JSON-compatible candidate outputs.
tags: [pska, extraction, knowledge, entities, hyperedges, review]
version: 1.0.0
mcp_servers: [pska]
recommended_tools: [pska_pska_search, pska_pska_index_status, pska_pska_review_items]
---

# PSKA Extract Skill

Use this skill when FastReAct is asked to execute a PSKA extraction job.

Rules:

1. Treat PSKA as the knowledge authority. Do not infer or bypass PSKA ACLs.
2. Use PSKA MCP tools for context and citations.
3. Return JSON-compatible candidates for entities, hyperedges, review items, gaps, and cited source ids.
4. Do not apply high-impact changes directly. Put uncertain, sensitive, merge, or sharing decisions into review candidates.
5. Every candidate must include source refs or cited source ids.

Output shape:

```json
{
  "entities": [],
  "hyperedges": [],
  "review_items": [],
  "cited_source_ids": [],
  "gaps": []
}
```
