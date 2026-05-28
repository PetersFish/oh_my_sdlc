---
id: modules/skills
type: module
title: Skills Collection
summary: Core skill definitions organized by prefix taxonomy. 14 skills across qa-, research-, sdlc-, transform-, study-, media-, integration-, ops-, and meta-skill- categories. Each skill has SKILL.md, optional scripts/, schemas/, templates/, references/.
sync_status: synced
evidence_mode: discovery
linked_commits: ["72272fb8c448292dd985d7ee35f160de9e5c94bc"]
linked_specs: []
linked_sessions: ["20260529-01"]
updated_at: 2026-05-29T00:00:00Z
confidence: high
tags: [skills, taxonomy, collection]
---

# Skills Collection

## Current Understanding

This is the core skill repository containing 14 skill definitions organized by a formal prefix taxonomy (see `skills/TAXONOMY.md`). Skills are categorized by prefix:
- **qa-***: Conversational Q&A coaching (1 skill)
- **research-***: Durable research lifecycle (1 skill)
- **sdlc-***: Software development lifecycle, repository memory (4 skills)
- **transform-***: Atomic content transformation/render (4 skills)
- **study-***: Composite learning orchestration (1 skill)
- **media-***: Media/OCR routing (1 skill)
- **integration-***: External service integration (1 skill)
- **ops-***: Operational/backup tasks (1 skill)
- **meta-skill-***: Skill lifecycle governance (1 skill)

Skills follow a relationship model: composites delegate to atomics, adapters wrap core lifecycle skills.

## Evidence

- `skills/TAXONOMY.md` defines prefix semantics, trigger conflict priorities, and relationship map
- 14 SKILL.md files detected across subdirectories
- Module discovery scan at depth 2 confirmed skill subdirs with SKILL.md markers

## Operational Guidance

- When adding a new skill, follow the taxonomy prefix conventions
- Composite skills should delegate rendering to atomic transform-* skills
- Adapter skills should be thin wrappers, not duplicates of core logic
- Update TAXONOMY.md when adding new prefix categories

## Update Notes

Initial discovery during first repository memory sync (2026-05-29).
