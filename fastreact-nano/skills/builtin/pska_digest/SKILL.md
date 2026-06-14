---
name: pska_digest
description: Execute PSKA digest jobs by summarizing allowed PSKA sources into reviewable summaries, memory candidates, and action candidates with citations.
tags: [pska, digest, memory, summary, review]
version: 1.0.0
mcp_servers: [pska]
recommended_tools: [pska_pska_search, pska_pska_index_status, pska_pska_review_items]
---

# PSKA Digest Skill

Use this skill when FastReAct is asked to run a PSKA digest pass.

Rules:

1. Retrieve context only through PSKA tools.
2. Preserve source refs for every summary, memory candidate, and review candidate.
3. Low-confidence, sensitive, or high-impact suggestions must become review candidates.
4. Do not write final user memory unless PSKA explicitly provides a write/apply tool and the action is approved.
5. Report gaps when evidence is insufficient.

Output shape:

```json
{
  "summaries": [],
  "memory_candidates": [],
  "review_candidates": [],
  "cited_source_ids": [],
  "gaps": []
}
```
