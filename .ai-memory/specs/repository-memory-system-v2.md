---
id: repository-memory-system-v2
type: specs
title: Repository Memory System V2 — Active Spec
summary: Active OpenSpec change replacing the MVP openspec-memory-sync with a general-purpose repository memory system across init, load, and sync phases. Defines eight memory types, dirty-worktree support, review queue, sync-history audit trail, and deterministic Python scripts. Load when implementing or extending memory features, or when the current task touches .ai-memory/ infrastructure.
sync_status: synced
evidence_mode: spec_reference
linked_commits: ['c5a231c', '598ffe1', 'c3fa28a', 'e1bd6da']
linked_specs: ['repository-memory-system-v2']
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [openspec, memory, sync, init, load, spec]
---

# Repository Memory System V2 — Active Spec

## Current Understanding

This OpenSpec change (`openspec/changes/repository-memory-system-v2/`) defines the complete V2 memory system. It is currently in active implementation (not yet archived).

### Key Requirements

From `specs/repository-memory-sync/spec.md` (210 lines, 15 requirements):

1. **Detect repository state** — Git availability, commits, HEAD, worktree state, OpenSpec candidates
2. **Reconcile pending snapshots** — Upgrade `pending_commit` memory when matching commits appear
3. **Per-type memory policy** — Different update policies for each of 8 memory types
4. **Dirty worktree support** — Allow sync on dirty trees, mark as `pending_commit`
5. **Three public sync statuses** — `synced`, `pending_commit`, `needs_user_review`
6. **Review queue management** — Decision/architecture candidates go to review queue, not formal memory
7. **Sync history audit trail** — Write `.ai-memory/sync-history/<id>.md` per sync run
8. **YAML frontmatter** — Required fields per memory file
9. **OpenSpec change ID detection** — 7-priority detection order
10. **Spec lineage** — Link related changes to single spec memory
11. **Index rebuild** — Selective inclusion of synced/pending memory
12. **Index entry summaries** — 2-3 sentence routing summaries
13. **Manifest update** — Update manifest after each sync
14. **Init check before sync** — Require `.ai-memory/manifest.json` to exist
15. **Script CLIs** — `--root`, `--json`, `--write` arguments

### Change Artifacts

- `proposal.md` — Why and what changes
- `design.md` — Architecture decisions
- `tasks.md` — Implementation tasks
- `specs/repository-memory-init/spec.md` — Init skill spec
- `specs/repository-memory-load/spec.md` — Load skill spec
- `specs/repository-memory-sync/spec.md` — Sync skill spec

## Evidence

- OpenSpec change directory: `openspec/changes/repository-memory-system-v2/`
- Four commits (c5a231c through e1bd6da) implementing the system
- Skills installed in three CLI targets

## Operational Guidance

- This change is NOT yet archived — use `openspec-verify-change` before archiving
- When the change is archived, specs memory should be updated to reflect archived status
- All memory system behavior should conform to the specs defined here

## Update Notes

- 2026-05-27: First memory sync — captured active spec state
