## Why

The current `openspec-memory-sync` skill is tightly coupled to the OpenSpec workflow and limited to three memory types (ADRs, pitfalls, module docs). It cannot serve repositories without OpenSpec, cannot associate memory with git commits or sessions, and has no read/hydration mechanism. This change replaces the MVP with a general-purpose repository memory system split across three lifecycle phases: init, load, and sync.

## What Changes

- **New `repository-memory-init` skill**: One-time initialization of `.ai-memory/` directory, manifest, index, review queue, schemas, and gitignore; optional `AGENTS.md` memory-load reminder.
- **New `repository-memory-load` skill**: Read-only selective context hydration from `.ai-memory/index.json`; outputs a context pack with up to 5 relevant memory files; never reads `sync-history`, `sessions`, `snapshots`, `tmp`, `cache`, or `review-queue.json` by default.
- **New `repository-memory-sync` skill**: General-purpose memory synchronization with support for dirty worktrees, uncommitted snapshots, per-memory evidence linkage, pending reconciliation, review queue, and sync-history audit trail.
- **Modified `openspec-memory-sync` skill**: **BREAKING** — downgraded from the core memory system to a thin OpenSpec adapter that wraps `repository-memory-load` and `repository-memory-sync`, preserving the `verify -> memory-sync -> archive` gate while delegating memory operations to the new core skills.
- **New `.ai-memory/` data contract**: Directory layout, manifest.json, index.json, review-queue.json, per-memory YAML frontmatter, git tracking strategy, and eight formal memory types (modules, architecture, decisions, pitfalls, specs, evolution, sessions-local, schemas).
- **New deterministic Python scripts**: `init_memory.py`, `detect_state.py`, `reconcile_pending.py`, `validate_memory.py`, `rebuild_index.py`, `update_manifest.py`, `select_memory.py`.
- **New JSON schemas**: manifest, index, review-queue, memory-frontmatter.
- **Modified OpenSpec workflow skills**: Add `repository-memory-load` reminder to `openspec-new-change`, `openspec-apply-change`, `openspec-verify-change`, and `openspec-archive-change`.

## Capabilities

### New Capabilities
- `repository-memory-init`: Initialize `.ai-memory/` in a repository, create manifest, index, review queue, gitignore, and directory structure; optionally add an `AGENTS.md` memory-load reminder.
- `repository-memory-load`: Read-only selective context hydration from repository memory; select up to 5 relevant memory files via index matching; output structured context pack; never modify memory.
- `repository-memory-sync`: Synchronize repository memory after changes; classify evidence into eight memory types with per-type policies; support dirty worktrees, uncommitted snapshots, pending reconciliation, and review queue; write sync-history audit trail.

### Modified Capabilities
- `openspec-memory-sync`: Changed from core memory system to thin OpenSpec adapter that delegates to `repository-memory-load` and `repository-memory-sync` while preserving the archive gate and per-change `memory-sync.md` report.

## Impact

- New skill directories: `skills/repository-memory-init/`, `skills/repository-memory-load/`, `skills/repository-memory-sync/` with scripts, schemas, and templates.
- Installed copies: `.opencode/skills/`, `.claude/skills/`, `.cursor/skills/` for all three new skills.
- Modified skill files: `skills/openspec-memory-sync/SKILL.md` and installed copies.
- Modified OpenSpec workflow skills: `openspec-new-change`, `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change` — each gains a `repository-memory-load` reminder block.
- New test files: `tests/test_repository_memory_init.py`, `tests/test_repository_memory_load.py`, `tests/test_repository_memory_sync.py`, `tests/test_repository_memory_skill_copies.py`.
- New OpenSpec change artifacts under `openspec/changes/repository-memory-system-v2/`.
- Repositories using this system will gain `.ai-memory/` directories (git-tracked subset).