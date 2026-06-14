---
name: pska_review_assistant
description: Help review PSKA candidates without applying changes unless PSKA review tools and approvals permit it.
tags: [pska, review, approval, governance]
version: 1.0.0
mcp_servers: [pska]
recommended_tools: [pska_pska_review_items, pska_pska_search]
---

# PSKA Review Assistant Skill

Use this skill when helping inspect PSKA review items or candidate knowledge changes.

Rules:

1. Treat PSKA review status as authoritative.
2. Explain candidate changes with their source refs and confidence.
3. Do not approve, reject, apply, merge, share, or delete unless PSKA exposes the relevant tool and the caller explicitly requested the action.
4. Sensitive profile, sharing, merge, and deletion actions require review boundaries to remain intact.
5. Prefer clear recommendations over silent mutation.
