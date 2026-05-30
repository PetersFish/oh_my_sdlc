---
id: skills
type: module
title: Skills
summary: Personal AI skill collection across SDLC workflow, content transformation, research, study, and system integration domains.
parent_id: root
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: []
linked_sessions: []
updated_at: 2026-05-30T11:47:00Z
confidence: high
tags: [skills, sdlc, transform, research]
owned_paths: [skills/]
path_hints: [skills/]
keywords: [skill, agent, opencode]
test_paths: []
spec_paths: []
---

# Skills

## Current Understanding

Root module for all AI skills. Contains grouped SDLC workflow skills (`sdlc-*`), content transformation skills (`transform-*`), and standalone skills for integration, research, study, and system operations.

## Evidence

Directory discovery at repository root. Contains 95 files across 17 sub-directories.

## Operational Guidance

- SDLC skills handle repository memory lifecycle (init, load, sync, reset)
- Transform skills handle content rendering (markdown SVG, math formulas, algorithm blocks)
- Standalone skills handle specific domains (research, notion sync, zybooks, mackup backup, architecture coaching)

## Child Modules

- `skills/sdlc` — SDLC workflow skills (memory init/load/sync/reset, OpenSpec memory sync)
- `skills/transform` — Content transformation skills (algo render, markdown SVG, math formula, xmind)
- `skills/integration-notion-sync` — Notion knowledge base sync
- `skills/media-ocr-router` — OCR/VLM image routing
- `skills/meta-skill-lifecycle-governance` — Skill lifecycle governance
- `skills/ops-mackup-backup` — Mackup directory backup
- `skills/qa-ai-architecture` — AI architecture coaching
- `skills/research-general` — Durable local research topics
- `skills/study-zybook-notes` — zyBooks study notes

## Key Files

## Entry Points

## Tests

## Related Specs

## Known Pitfalls

## Update Notes

First sync after memory reset. Created from discovery.
