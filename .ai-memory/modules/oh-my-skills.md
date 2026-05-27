---
id: oh-my-skills
type: module
title: Oh My Skills — Skill Collection Repository
summary: This repository is a curated collection of AI assistant skills distributed across multiple CLI environments (OpenCode, Claude, Cursor). Each skill lives in skills/ with installed copies in .opencode/skills/, .claude/skills/, and .cursor/skills/. Load when working on skill authoring, multi-CLI distribution, or understanding the repo's overall organization.
sync_status: synced
evidence_mode: commit
linked_commits: ['62085d3', '85218c6', '2f90be4', 'f409d1f', '4586e17', 'c5a231c', '598ffe1', 'c3fa28a', 'e1bd6da']
linked_specs: ['repository-memory-system-v2']
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [skills, multi-cli, openspec, repository-structure]
---

# Oh My Skills — Skill Collection Repository

## Current Understanding

This repository is a collection of AI assistant skills organized as a skill library. Skills are authored once as canonical copies in `skills/` and distributed to multiple CLI targets (OpenCode via `.opencode/skills/`, Claude via `.claude/skills/`, Cursor via `.cursor/skills/`). The skill lifecycle (author, test, install, backport, release) is governed by `skill-lifecycle-governance`.

### Key Directories

- `skills/` — Canonical skill definitions (27+ skills)
- `openspec/` — OpenSpec change artifacts, schemas, and workflow templates
- `tests/` — Python test suite verifying skill installs, lifecycle utilities, OCR routing, research, and repository memory system
- `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/` — Installed copies per CLI
- `.ai-memory/` — Repository memory system (modules, decisions, specs, evolution)

### Skill Categories

| Category | Skills |
|---|---|
| General workflow | brainstorming, planning-with-files, executing-plans, writing-plans, dispatching-parallel-agents, subagent-driven-development, finishing-a-development-branch, verification-before-completion |
| Code quality | test-driven-development, systematic-debugging, requesting-code-review, receiving-code-review |
| OpenSpec | openspec-new-change, openspec-apply-change, openspec-archive-change, openspec-continue-change, openspec-explore, openspec-onboard, openspec-propose, openspec-sync-specs, openspec-verify-change |
| Repository Memory | repository-memory-init, repository-memory-load, repository-memory-sync, openspec-memory-sync |
| Domain-specific | ai-architecture-coach, algo-render-core, stevens-cs556-review, zybook-assist |
| Media/Tools | clipboard-ocr, ocr-router, convert-xmind, markdown-svg-generator, math-formula-rendering, sync-notion, research, mackup-backup |
| Meta | skill-creator, skill-lifecycle-governance, writing-skills, customize-opencode |

## Evidence

- Full commit history from 62085d3 to e1bd6da (9 commits)
- Repo structure inspected via codegraph_codegraph_files
- Skill count: 27+ skills across categories

## Operational Guidance

- When adding a new skill, use `skill-lifecycle-governance` to install and distribute
- When making OpenSpec changes, follow the workflow via `openspec-new-change` → `openspec-apply-change` → `openspec-verify-change` → `openspec-archive-change`
- Run `repository-memory-sync` after significant changes to keep memory up to date

## Update Notes

- 2026-05-27: First memory sync — captured full repo structure and purpose
