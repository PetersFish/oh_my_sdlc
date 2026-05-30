---
id: skills/sdlc
type: module
title: SDLC Workflow Skills
summary: SDLC lifecycle management skills covering repository memory init, load, sync, reset, and OpenSpec memory sync.
parent_id: skills
sync_status: synced
evidence_mode: discovery
linked_commits: []
linked_specs: [sdlc-repository-memory-sync, sdlc-repository-memory-load, sdlc-repository-memory-init, sdlc-repository-memory-reset, sdlc-openspec-memory-sync]
linked_sessions: []
updated_at: 2026-05-30T11:47:00Z
confidence: high
tags: [sdlc, memory, workflow]
owned_paths:
  - skills/sdlc-repository-memory-init
  - skills/sdlc-repository-memory-load
  - skills/sdlc-repository-memory-reset
  - skills/sdlc-repository-memory-sync
  - skills/sdlc-openspec-memory-sync
path_hints:
  - skills/sdlc-repository-memory-init
  - skills/sdlc-repository-memory-load
  - skills/sdlc-repository-memory-reset
  - skills/sdlc-repository-memory-sync
  - skills/sdlc-openspec-memory-sync
keywords: [sdlc, memory, init, load, sync, reset, openspec]
test_paths: []
spec_paths: []
---

# SDLC Workflow Skills

## Current Understanding

Grouped child module for 5 SDLC-related skills sharing the `sdlc-*` prefix. These skills cover the full lifecycle of repository memory management: initialization, loading, synchronization, reset, and OpenSpec-specific memory sync.

- **sdlc-repository-memory-init** — One-time `.ai-memory/` infrastructure creation
- **sdlc-repository-memory-load** — Loading repository memory context for sessions
- **sdlc-repository-memory-reset** — Safe deletion and re-initialization of `.ai-memory/`
- **sdlc-repository-memory-sync** — Synchronizing memory after code changes
- **sdlc-openspec-memory-sync** — Post-verify memory sync gate for OpenSpec

## Evidence

Prefix-based semantic grouping of 5 sibling skill directories under `skills/`.

## Operational Guidance

Use `sdlc-repository-memory-load` when starting work; `sdlc-repository-memory-sync` after changes; `sdlc-repository-memory-reset` only for test/clean-slate scenarios.

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

## Update Notes

First sync after memory reset. Created from prefix-based child module discovery.
