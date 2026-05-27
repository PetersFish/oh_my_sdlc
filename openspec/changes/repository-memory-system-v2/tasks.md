## 1. Shared Schemas and Templates

- [x] 1.1 Create `skills/repository-memory-init/schemas/manifest.schema.json` with required fields: `schema_version`, `repository_id`, `memory_version`, `git` (with `available`, `has_commits`, `head`, `last_synced_commit`, `worktree_state`), `pending_snapshots`, `last_sync`
- [x] 1.2 Create `skills/repository-memory-init/schemas/index.schema.json` with required fields: `schema_version`, `generated_at`, `entries` (array with `id`, `type`, `path`, `title`, `summary`, `tags`, `updated_at`, `confidence`, `status`)
- [x] 1.3 Create `skills/repository-memory-init/schemas/review-queue.schema.json` with required fields: `items` array (each with `id`, `type`, `source_sync_id`, `reason`, `title`, `source_refs`, `status`, `created_at`)
- [x] 1.4 Create `skills/repository-memory-init/schemas/memory-frontmatter.schema.json` with required fields: `id`, `type`, `title`, `summary`, `sync_status`, `evidence_mode`, `linked_commits`, `linked_specs`, `linked_sessions`, `updated_at`, `confidence`, `tags` and allowed `sync_status` values: `synced`, `pending_commit`, `needs_user_review`
- [x] 1.5 Create `skills/repository-memory-sync/templates/memory-file.md` with YAML frontmatter template and body sections: Current Understanding, Evidence, Operational Guidance, Update Notes
- [x] 1.6 Create `skills/repository-memory-sync/templates/sync-history.md` template with sections: Changed Files, Evidence Used, Memory Deltas, Skipped Types, Confidence Notes

## 2. `repository-memory-init` Skill

- [x] 2.1 Write `skills/repository-memory-init/SKILL.md` with trigger-heavy description and init workflow: create `.ai-memory/` directory structure, create manifest/index/review-queue, create `.gitignore`, ask about AGENTS.md, output summary
- [x] 2.2 Implement `skills/repository-memory-init/scripts/init_memory.py` accepting `--root` and `--json` arguments; create `.ai-memory/` subdirectories, write template `manifest.json`, `index.json`, `review-queue.json`, `.gitignore`; report AGENTS.md status; output JSON summary
- [x] 2.3 Create `skills/repository-memory-init/templates/manifest.json` with default values (null git head, empty pending snapshots, null last_sync)
- [x] 2.4 Create `skills/repository-memory-init/templates/index.json` with default values (empty entries)
- [x] 2.5 Create `skills/repository-memory-init/templates/review-queue.json` with default values (empty items)
- [x] 2.6 Create `skills/repository-memory-init/templates/AGENTS-memory-block.md` with the minimal repository memory reminder block
- [x] 2.7 Write `tests/test_repository_memory_init.py` covering: full directory creation, idempotent init, preserving existing manifest, reporting missing AGENTS.md, writing expected .gitignore

## 3. `repository-memory-load` Skill

- [x] 3.1 Write `skills/repository-memory-load/SKILL.md` with trigger-heavy description, read-only behavior, selective loading (max 5 files), excluded paths (sync-history, sessions, snapshots, tmp, cache, review-queue), context pack output format
- [x] 3.2 Implement `skills/repository-memory-load/scripts/select_memory.py` accepting `--root`, `--query`, `--max` (default 5), `--json`; read index.json, score entries by query/tags/path, return top matches, exclude restricted paths
- [x] 3.3 Copy `skills/repository-memory-init/schemas/` schemas into `skills/repository-memory-load/schemas/` for self-contained distribution
- [x] 3.4 Implement `skills/repository-memory-load/scripts/validate_memory.py` accepting `--root` and `--json`; validate manifest, index, review queue, and memory frontmatter against schemas
- [x] 3.5 Create `skills/repository-memory-load/templates/context-pack.md` with sections: Loaded Memory, Relevant Facts, Constraints, Skipped
- [x] 3.6 Write `tests/test_repository_memory_load.py` covering: missing index returns no memory, query selects matching entries, excluded paths are filtered, max result limit enforced, context pack format

## 4. `repository-memory-sync` Skill

- [x] 4.1 Write `skills/repository-memory-sync/SKILL.md` with trigger-heavy description, sync workflow (detect state, reconcile pending, compute ranges, classify memory, apply policies, validate, rebuild index, update manifest, write sync-history), per-type policy table, dirty worktree policy, review queue policy, specs ID detection, spec lineage
- [x] 4.2 Implement `skills/repository-memory-sync/scripts/detect_state.py` accepting `--root` and `--json`; detect git availability, commits, HEAD, worktree state, staged/unstaged files, last synced commit, OpenSpec candidates from diff paths
- [x] 4.3 Implement `skills/repository-memory-sync/scripts/reconcile_pending.py` accepting `--root`, `--write`, `--json`; read manifest pending snapshots, compare against new committed range, upgrade matched to synced, create review queue items for ambiguous cases, only use public statuses (synced, pending_commit, needs_user_review)
- [x] 4.4 Implement `skills/repository-memory-sync/scripts/validate_memory.py` (shared with load); validate manifest, index, review queue, and frontmatter against schemas; reject unsupported memory types and statuses
- [x] 4.5 Implement `skills/repository-memory-sync/scripts/rebuild_index.py` accepting `--root`, `--write`, `--json`; scan formal memory directories, include only synced and pending_commit entries, exclude needs_user_review and restricted paths, require 2-3 sentence summaries, write index.json
- [x] 4.6 Implement `skills/repository-memory-sync/scripts/update_manifest.py` accepting `--root`, `--sync-id`, `--json`; update git.head, last_synced_commit, worktree_state, pending_snapshots, last_sync
- [x] 4.7 Write `tests/test_repository_memory_sync.py` covering: non-git directory, git without commits, dirty worktree produces pending_commit, reconciliation of matched pending, partial reconciliation creates review queue item, validation accepts valid samples, validation rejects unsupported statuses, index excludes needs_user_review and restricted paths, manifest update on clean and dirty worktrees

## 5. `openspec-memory-sync` Wrapper Update

- [x] 5.1 Rewrite `skills/openspec-memory-sync/SKILL.md` as a thin OpenSpec adapter: use `repository-memory-load` first, collect OpenSpec artifacts, delegate to `repository-memory-sync` workflow, preserve archive gate, write per-change `memory-sync.md`
- [x] 5.2 Copy updated `skills/openspec-memory-sync/SKILL.md` to `.opencode/skills/openspec-memory-sync/SKILL.md`
- [x] 5.3 Copy updated `skills/openspec-memory-sync/SKILL.md` to `.claude/skills/openspec-memory-sync/SKILL.md`
- [x] 5.4 Copy updated `skills/openspec-memory-sync/SKILL.md` to `.cursor/skills/openspec-memory-sync/SKILL.md`

## 6. Workflow Skill Memory-Load Reminders

- [x] 6.1 Add repository-memory-load reminder block to `.opencode/skills/openspec-new-change/SKILL.md`
- [x] 6.2 Add repository-memory-load reminder block to `.opencode/skills/openspec-apply-change/SKILL.md`
- [x] 6.3 Add repository-memory-load reminder block to `.opencode/skills/openspec-verify-change/SKILL.md`
- [x] 6.4 Add repository-memory-load reminder block to `.opencode/skills/openspec-archive-change/SKILL.md`

## 7. Multi-Client Skill Distribution

- [x] 7.1 Copy `skills/repository-memory-init/` to `.opencode/skills/repository-memory-init/` (full self-contained: SKILL.md, scripts, schemas, templates)
- [x] 7.2 Copy `skills/repository-memory-init/` to `.claude/skills/repository-memory-init/`
- [x] 7.3 Copy `skills/repository-memory-init/` to `.cursor/skills/repository-memory-init/`
- [x] 7.4 Copy `skills/repository-memory-load/` to `.opencode/skills/repository-memory-load/` (full self-contained)
- [x] 7.5 Copy `skills/repository-memory-load/` to `.claude/skills/repository-memory-load/`
- [x] 7.6 Copy `skills/repository-memory-load/` to `.cursor/skills/repository-memory-load/`
- [x] 7.7 Copy `skills/repository-memory-sync/` to `.opencode/skills/repository-memory-sync/` (full self-contained)
- [x] 7.8 Copy `skills/repository-memory-sync/` to `.claude/skills/repository-memory-sync/`
- [x] 7.9 Copy `skills/repository-sync/` to `.cursor/skills/repository-memory-sync/`
- [x] 7.10 Generate `.skill-install.json` for each client copy with payload_hash, source_ref, and file list

## 8. Consistency and End-to-End Tests

- [x] 8.1 Write `tests/test_repository_memory_skill_copies.py` verifying all three skills exist in all three client directories, SKILL.md matches canonical, scripts/schemas/templates match canonical, missing copy fails test
- [x] 8.2 Add end-to-end test: no `.ai-memory/` triggers init suggestion
- [x] 8.3 Add end-to-end test: init creates `.ai-memory/` idempotently
- [x] 8.4 Add end-to-end test: load selects max 5 memory files
- [x] 8.5 Add end-to-end test: dirty worktree produces `pending_commit`
- [x] 8.6 Add end-to-end test: later commit reconciles pending memory
- [x] 8.7 Add end-to-end test: no-commit repo uses working-tree snapshot
- [x] 8.8 Add end-to-end test: multiple active changes with one diff-touched change auto-selects
- [x] 8.9 Add end-to-end test: `sync-history/` is committed but not indexed
- [x] 8.10 Add end-to-end test: `review-queue.json` is committed but only sync reads it