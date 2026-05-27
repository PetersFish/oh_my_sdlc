---
id: repository-memory-system
type: module
title: Repository Memory System (V2)
summary: A general-purpose repository memory system split across three lifecycle phases: init (one-time setup), load (selective hydration), and sync (evidence-backed update). Uses YAML frontmatter per memory file, seven memory types, dirty-worktree support, review queue, and sync-history audit trail. Load when working on memory infrastructure, troubleshooting sync issues, or extending the memory system.
sync_status: synced
evidence_mode: commit
linked_commits: ['c5a231c', '598ffe1', 'c3fa28a', 'e1bd6da']
linked_specs: ['repository-memory-system-v2']
linked_sessions: ['2026-05-27-001']
updated_at: 2026-05-27T13:43:32Z
confidence: high
tags: [memory, sync, init, load, openspec-memory-sync]
---

# Repository Memory System (V2)

## Current Understanding

Three core skills plus one OpenSpec adapter form the repository memory system:

1. **repository-memory-init** — One-time infrastructure setup: `.ai-memory/` directory, manifest, index, review queue, schemas, gitignore
2. **repository-memory-load** — Read-only context hydration: selects up to 5 relevant memory files from index, outputs a context pack; never modifies memory
3. **repository-memory-sync** — Evidence-backed synchronization: detects git state, classifies changes into memory types, applies per-type policies, manages review queue
4. **openspec-memory-sync** — Thin OpenSpec adapter that wraps load + sync, preserving the `verify → memory-sync → archive` gate

### Key Scripts (in `.opencode/skills/repository-memory-sync/scripts/`)

| Script | Purpose |
|---|---|
| `detect_state.py` | Detect git state, changed paths, OpenSpec candidates |
| `reconcile_pending.py` | Upgrade pending memory when commits match |
| `validate_memory.py` | Check schema conformance, reference integrity |
| `rebuild_index.py` | Scan memory files and rebuild `index.json` |
| `update_manifest.py` | Update `manifest.json` with sync metadata |
| `select_memory.py` (in load) | Select relevant memory files for context hydration |

### Memory Types and Policies

| Type | Auto-Update | User Confirm | Notes |
|---|---|---|---|
| sessions | Yes | No | Cumulative session log |
| pitfalls | Yes (with evidence) | No | Needs stack trace or test failure |
| specs | Yes (with change ID) | No | Requires OpenSpec change ID |
| modules | Yes | No | Dirty marks pending_commit |
| evolution | Yes | No | Only with stable commit range |
| decisions | No | Yes | Candidate only |
| architecture | No | Yes | Candidate only |

## Evidence

- OpenSpec change `repository-memory-system-v2` (commits c5a231c through e1bd6da)
- Spec file: `openspec/changes/repository-memory-system-v2/specs/repository-memory-sync/spec.md`
- Test files: `tests/test_repository_memory_init.py`, `test_repository_memory_load.py`, `test_repository_memory_sync.py`

## Operational Guidance

- Never load `.ai-memory/sync-history/`, `sessions/`, `snapshots/`, `tmp/`, `cache/` by default
- Dirty worktrees are OK — memory gets `pending_commit`, reconciled next sync
- `needs_user_review` items go to `review-queue.json`, NOT formal memory files

## Update Notes

- 2026-05-27: First memory sync — documented the complete V2 memory system architecture
