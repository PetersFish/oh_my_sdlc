---
id: repository-memory-system-v2-decision
type: decisions
title: Choose Repository Memory System V2 over MVP openspec-memory-sync
summary: Decision to replace the MVP openspec-memory-sync (tightly coupled to OpenSpec, limited to 3 memory types) with a general-purpose V2 repository memory system split into init, load, and sync phases. The V2 system supports 8 memory types, dirty worktrees, review queues, and works in repositories without OpenSpec.
sync_status: synced
evidence_mode: commit
linked_commits: ['c5a231c', '598ffe1', 'c3fa28a', 'e1bd6da']
linked_specs: ['repository-memory-system-v2']
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [decision, memory, openspec, architecture]
---

# Choose Repository Memory System V2 over MVP openspec-memory-sync

## Context

The initial MVP (`openspec-memory-sync`) was tightly coupled to the OpenSpec workflow and limited to three memory types (ADRs, pitfalls, module docs). It could not serve repositories without OpenSpec, had no read/hydration mechanism, and could not associate memory with git commits or sessions.

## Decision

Replace the MVP with a general-purpose V2 repository memory system that:
1. Works in any repository (OpenSpec optional)
2. Splits into three lifecycle phases: init, load, sync
3. Supports 8 memory types with per-type policies
4. Handles dirty worktrees and uncommitted snapshots
5. Provides review queue for decisions/architecture
6. Maintains sync-history audit trail
7. Downgrades `openspec-memory-sync` to a thin adapter

## Alternatives Considered

1. **Keep MVP and extend it** — Would increase coupling to OpenSpec and make it harder to generalize
2. **Use external memory system** (e.g., Notion, wiki) — Loses git-based evidence linkage and local-first approach
3. **Skip repository memory entirely** — Loses context preservation across sessions

## Consequences

### Positive
- Memory works in any repo, not just OpenSpec-enabled ones
- Selective loading via index avoids context bloat
- Dirty worktree support means no need to commit before syncing
- Review queue prevents premature formalization of architectural decisions

### Negative
- More complex than MVP (3 skills instead of 1, 7 scripts)
- Requires initialization step before first use
- Pending commit reconciliation adds a future sync dependency

## Evidence

- OpenSpec change: `openspec/changes/repository-memory-system-v2/proposal.md`
- Commits: c5a231c → 598ffe1 → c3fa28a → e1bd6da
- Spec: `repository-memory-sync/spec.md` with 15 requirements

## Update Notes

- 2026-05-27: Created from first memory sync — decision documented from user confirmation
