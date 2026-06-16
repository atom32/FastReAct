---
name: pska_digest
description: Execute PSKA digest jobs by summarizing allowed PSKA sources into reviewable summaries, memory candidates, and action candidates with citations.
tags: [pska, digest, memory, summary, review]
version: 1.0.1
mcp_servers: [pska]
recommended_tools: [pska_pska_job_context, pska_pska_write_candidates]
---

# PSKA Digest Skill

Use this skill when FastReAct is asked to run a PSKA digest pass.

Rules:

1. Retrieve context only through PSKA tools.
2. Use `pska_pska_job_context` at most once when a `job_id` is provided and context needs verification.
3. Write grounded candidates with `pska_pska_write_candidates` when useful candidates exist.
4. For a digest worker batch, call `pska_pska_write_candidates` at most once. If there are multiple candidate categories, merge all entities, memory candidates, review items, hyperedges, summaries, and action candidates into the same payload.
5. Do not split write calls by source, candidate type, confidence, or citation group.
6. Every write must include `schema_version: "pska.candidates.v1"`, `job_id`, `source_refs`, `confidence`, and `producer: "fastreact"`.
7. Preserve source refs for every summary, memory candidate, and review candidate.
8. Low-confidence, sensitive, or high-impact suggestions must become review candidates.
9. Do not write final user memory unless PSKA explicitly provides a write/apply tool and the action is approved.
10. Report gaps when evidence is insufficient.

Budget invariant: after one `pska_pska_write_candidates` call in a batch, do
not call it again. Add any additional grounded candidate to the first payload,
or omit it and report the gap in the final summary.

Valid `pska_pska_write_candidates` payload shape:

```json
{
  "schema_version": "pska.candidates.v1",
  "owner_user_id": "user_primary",
  "job_id": "job_id_from_context",
  "request_id": "stable_batch_request_id",
  "source_refs": [{"source_item_id": "src_id", "document_id": "optional", "chunk_id": "optional"}],
  "producer": "fastreact",
  "entities": [
    {"entity_type": "project|person|concept|source|service|event", "label": "Entity label", "confidence": 0.8}
  ],
  "memory_candidates": [
    {"kind": "agent_memory", "layer": "semantic", "text": "Grounded memory text.", "confidence": 0.8}
  ],
  "review_items": [
    {"review_type": "profile_update|conflict|quality", "title": "Review title", "proposal": {"note": "Grounded proposal"}}
  ],
  "hyperedges": [
    {
      "relation_type": "depends_on|mentions|related_to",
      "evidence_text": "Short source-grounded evidence.",
      "confidence": 0.75,
      "members": [
        {"entity_type": "project", "label": "PSKA", "role": "subject"},
        {"entity_type": "service", "label": "FastReAct", "role": "object"}
      ]
    }
  ]
}
```

For simple single-fact digests, prefer one `memory_candidates` item and omit
`entities`/`hyperedges` unless the source clearly names durable entities or a
relationship. Do not use `name`, `content`, `source`, or `memory_id` fields for
agent memories; use `text`.

When no candidate should be written, return an empty JSON object with `gaps` explaining why. Do not invent candidates to satisfy the shape.
