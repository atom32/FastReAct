---
name: pska_digest
description: Execute PSKA digest jobs with claim-first knowledge extraction, grounded digest notes, and reviewable memory/action/relationship candidates.
tags: [pska, digest, knowledge-claims, memory, summary, review]
version: 1.1.0
mcp_servers: [pska]
recommended_tools: [pska_pska_job_context, pska_pska_write_candidates]
---

# PSKA Digest Skill

Use this skill when FastReAct is asked to run a PSKA digest pass.

Rules:

1. Retrieve context only through PSKA tools.
2. Use `pska_pska_job_context` at most once when a `job_id` is provided and context needs verification.
3. First extract readable `knowledge_claims` that state what the source says. Then write digest notes and other candidates only when useful.
4. Write grounded candidates with `pska_pska_write_candidates` when useful candidates exist.
5. For a digest worker batch, call `pska_pska_write_candidates` at most once. If there are multiple candidate categories, merge all knowledge claims, digest notes, entities, memory candidates, review items, hyperedges, summaries, and action candidates into the same payload.
6. Do not split write calls by source, candidate type, confidence, or citation group.
7. Every write must include `schema_version: "pska.candidates.v1"`, `job_id`, `source_refs`, `confidence`, and `producer: "fastreact"`.
8. Every claim, digest note, hyperedge, memory candidate, and review candidate must preserve source refs. Prefer the narrowest available refs: `passage_window_id`, then `chunk_id`, then `document_id`, then `source_item_id`.
9. Do not write `digest_notes`, `hyperedges`, or relationship suggestions unless the same payload also includes at least one `knowledge_claim`.
10. Low-confidence, sensitive, or high-impact suggestions must become review candidates.
11. Do not write final user memory unless PSKA explicitly provides a write/apply tool and the action is approved.
12. Report gaps when evidence is insufficient.

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
  "source_refs": [{"source_item_id": "src_id", "document_id": "optional", "passage_window_id": "optional", "chunk_id": "optional"}],
  "producer": "fastreact",
  "knowledge_claims": [
    {
      "claim_type": "fact|definition|decision|constraint|action|risk|conflict|preference|relationship",
      "statement": "中文优先的自然语言 claim，说明文档说了什么。",
      "subject": "optional subject",
      "predicate": "optional predicate",
      "object": "optional object",
      "qualifiers": {"scope": "optional"},
      "evidence_text": "Minimal exact evidence snippet from the source.",
      "confidence": 0.85,
      "source_refs": [{"source_item_id": "src_id", "document_id": "doc_id", "passage_window_id": "pw_id"}]
    }
  ],
  "digest_notes": [
    {
      "title": "Readable digest title",
      "synopsis": "Human-readable summary of what matters.",
      "key_points": [{"summary": "Important point.", "source_refs": [{"source_item_id": "src_id"}]}],
      "actions": [],
      "open_questions": [],
      "risks": [],
      "memory_suggestions": [],
      "relationship_suggestions": [],
      "confidence": 0.8,
      "source_refs": [{"source_item_id": "src_id", "document_id": "doc_id", "passage_window_id": "pw_id"}]
    }
  ],
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

For simple single-fact digests, prefer one readable `knowledge_claim` and one
small `digest_note`. Only add `memory_candidates`, `entities`, or `hyperedges`
when the source clearly contains durable information, durable entities, or a
relationship worth review/retrieval. Do not use `name`, `content`, `source`, or
`memory_id` fields for agent memories; use `text`.

When no candidate should be written, return an empty JSON object with `gaps` explaining why. Do not invent candidates to satisfy the shape.
