---
id: skills/sdlc
type: module
title: SDLC Workflow Skills
summary: SDLC lifecycle management skills covering project bootstrap, OpenSpec init, workflow orchestration and routing, roadmap planning, repository memory init/load/sync/reset, and OpenSpec memory sync after the removal of the sdd-plus-superpowers custom schema.
parent_id: skills
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: [add-project-bootstrap-skill, sdlc-repository-memory-sync, sdlc-repository-memory-load, sdlc-repository-memory-init, sdlc-repository-memory-reset, sdlc-openspec-memory-sync, add-sdlc-roadmap-skill, simplify-sdlc-routing-schemas]
linked_sessions: []
updated_at: 2026-06-10T04:00:00Z
confidence: high
tags: [sdlc, openspec, bootstrap, memory, workflow, orchestration, roadmap]
owned_paths:
  - skills/sdlc-repository-memory-init
  - skills/sdlc-openspec-init
  - skills/sdlc-project-bootstrap
  - skills/sdlc-repository-memory-load
  - skills/sdlc-repository-memory-reset
  - skills/sdlc-repository-memory-sync
  - skills/sdlc-openspec-memory-sync
  - skills/sdlc-roadmap
  - skills/sdlc-orchestrator
path_hints:
  - skills/sdlc-repository-memory-init
  - skills/sdlc-openspec-init
  - skills/sdlc-project-bootstrap
  - skills/sdlc-repository-memory-load
  - skills/sdlc-repository-memory-reset
  - skills/sdlc-repository-memory-sync
  - skills/sdlc-openspec-memory-sync
  - skills/sdlc-roadmap
  - skills/sdlc-orchestrator
keywords: [sdlc, bootstrap, openspec, schema, tools, memory, init, load, sync, reset, orchestration, roadmap]
test_paths: []
spec_paths: []
---

# SDLC Workflow Skills

## Current Understanding

Grouped child module for SDLC-related skills sharing the `sdlc-*` prefix. These skills cover project foundation bootstrap, OpenSpec initialization with schema/tool selection, and the full lifecycle of repository memory management.

- **sdlc-repository-memory-init** — One-time `.ai-memory/` infrastructure creation
- **sdlc-openspec-init** — OpenSpec initialization, AI tool selection, schema installation/default persistence, and partial init recovery
- **sdlc-project-bootstrap** — Ordered bootstrap orchestration: AGENTS.md -> OpenSpec/init schema -> repository memory
- **sdlc-repository-memory-load** — Loading repository memory context for sessions
- **sdlc-repository-memory-reset** — Safe deletion and re-initialization of `.ai-memory/`
- **sdlc-repository-memory-sync** — Synchronizing memory after code changes
- **sdlc-openspec-memory-sync** — Post-verify memory sync gate for OpenSpec
- **sdlc-roadmap** — Thin orchestration between long-term product roadmap and single OpenSpec changes
- **sdlc-orchestrator** — Pre-OpenSpec decision layer classifying task complexity and coordinating SDLC gates

## Evidence

Prefix-based semantic grouping of sibling skill directories under `skills/`, plus change-driven updates from `add-project-bootstrap-skill`, `add-sdlc-roadmap-skill`, and `simplify-sdlc-routing-schemas`.

## Operational Guidance

Use `sdlc-project-bootstrap` for new-project foundation setup, `sdlc-openspec-init` for standalone OpenSpec/schema setup, `sdlc-repository-memory-load` when starting work, and `sdlc-repository-memory-sync` after changes. Use `sdlc-orchestrator` for initial task routing and workflow selection. Use `sdlc-roadmap` for long-term product planning.

## Key Files

- skills/sdlc-repository-memory-init/scripts/init_memory.py
- skills/sdlc-repository-memory-sync/scripts/detect_state.py
- skills/sdlc-repository-memory-sync/scripts/discover_modules.py
- skills/sdlc-repository-memory-sync/scripts/validate_memory.py
- skills/sdlc-repository-memory-sync/scripts/rebuild_index.py
- skills/sdlc-repository-memory-load/scripts/load_memory.py

## Entry Points

## Tests

## Related Specs

## Known Pitfalls

- Stale global skill copies (for example under `~/.config/opencode/skills`) can silently bypass updated bootstrap/init guardrails even when repo-local copies are current.
- Symptom: bootstrap summary reports `config.yaml skipped in non-interactive mode` and lacks `AI tools`/`Default schema` fields.
- Mitigation: redistribute canonical `skills/sdlc-openspec-init/SKILL.md` and `skills/sdlc-project-bootstrap/SKILL.md` to all active CLI targets (`~/.config/opencode/skills`, `~/.claude/skills`, `~/.cursor/skills`, and repo-local copies).

## Update Notes

First sync after memory reset. Created from prefix-based child module discovery.
Updated after `add-project-bootstrap-skill`: added bootstrap/init ownership and stale-global-copy pitfall.
Updated after `simplify-sdlc-routing-schemas`: added sdlc-orchestrator and sdlc-roadmap ownership; removed sdd-plus-superpowers custom schema; OpenSpec defaults to package-provided spec-driven; schema installation step removed from sdlc-openspec-init.
