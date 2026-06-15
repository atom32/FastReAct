---
name: pska_digest
description: Execute PSKA digest jobs by summarizing allowed PSKA sources into reviewable summaries, memory candidates, and action candidates with citations.
tags: [pska, digest, memory, summary, review]
version: 1.0.0
mcp_servers: [pska]
recommended_tools: [pska_pska_job_context, pska_pska_write_candidates, pska_pska_search, pska_pska_index_status, pska_pska_review_items]
---

# PSKA Digest Skill

Use this skill when FastReAct is asked to run a PSKA digest pass.

Rules:

1. Retrieve context only through PSKA tools.
2. Use `pska_pska_job_context` when a `job_id` is provided, even if batch context was included in the prompt.
3. Write grounded candidates with `pska_pska_write_candidates` when useful candidates exist.
4. Every write must include `schema_version: "pska.candidates.v1"`, `job_id`, `source_refs`, `confidence`, and `producer: "fastreact"`.
5. Preserve source refs for every summary, memory candidate, and review candidate.
6. Low-confidence, sensitive, or high-impact suggestions must become review candidates.
7. Do not write final user memory unless PSKA explicitly provides a write/apply tool and the action is approved.
8. Report gaps when evidence is insufficient.

Output shape:

```json
{
  "schema_version": "pska.candidates.v1",
  "summaries": [],
  "memory_candidates": [],
  "review_items": [],
  "cited_source_ids": [],
  "gaps": []
}
```

When no candidate should be written, return an empty JSON object with `gaps` explaining why. Do not invent candidates to satisfy the shape.
