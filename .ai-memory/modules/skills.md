---
id: skills
type: module
title: Skills
summary: 16 AI skill definitions (SKILL.md + scripts/schemas) for SDLC, media routing, research, transforms, and lifecycle governance. Load when exploring skill behavior, writing new skills, or debugging skill dispatch.
parent_id: null
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: []
linked_sessions: ["20260529-000001"]
updated_at: 2026-05-29T00:00:00Z
confidence: high
tags: [skills, ai-skills, skill-system, sdlc, transforms, lifecycle]
owned_paths: ["skills/"]
path_hints: ["skills/"]
keywords: [skill, SKILL.md, skill-lifecycle, skill-creator]
test_paths: ["tests/test_repository_memory_skill_copies.py"]
spec_paths: []
---

# Skills

## Current Understanding

The `skills/` directory contains 16 AI skill packages, each following a canonical structure (SKILL.md + optional scripts/, schemas/, templates/, references/). Skills are categorized by domain: SDLC (OpenSpec, repository memory), media routing (OCR/VLM), research, transforms (SVG, math, XMind, algorithms), and lifecycle governance.

## Evidence

Initial discovery scan: 94 files across 16 subdirectories. File types: .md (47), .json (18), .py (16), .pyc (12), .yaml (1).

## Operational Guidance

- New skills follow the pattern in any existing skill directory (SKILL.md at root, scripts/ for tool scripts, schemas/ for validation).
- Skill lifecycle is governed by `meta-skill-lifecycle-governance`.
- When modifying a skill, check corresponding tests in `tests/`.

## Child Modules

16 individual skill packages, each self-contained:
- `integration-notion-sync/`, `media-ocr-router/`, `meta-skill-lifecycle-governance/`
- `ops-mackup-backup/`, `qa-ai-architecture/`, `research-general/`
- `sdlc-openspec-memory-sync/`, `sdlc-repository-memory-init/`, `sdlc-repository-memory-load/`, `sdlc-repository-memory-sync/`
- `study-zybook-notes/`, `transform-algo-render/`, `transform-markdown-svg/`, `transform-math-formula/`, `transform-xmind/`

## Key Files

- `skills/TAXONOMY.md` — skill categorization reference
- Each `skills/<name>/SKILL.md` — entry point for the skill

## Entry Points

All entry points follow `skills/<skill-name>/SKILL.md` convention.

## Tests

- `tests/test_repository_memory_skill_copies.py` — verifies skill copies consistency
- `tests/test_lifecycle_utils.py` — lifecycle governance utilities
- `tests/test_ocr_router_skill.py` — OCR router skill tests

## Update Notes

First sync after repository memory initialization.
