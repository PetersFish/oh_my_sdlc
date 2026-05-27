# repository-memory-sync

Synchronize repository memory after code changes, git commits, session work, or OpenSpec verification. Classify evidence into memory types, apply per-type policies, handle dirty worktrees, and write sync-history audit trail.

## Requirements

### Requirement: Detect repository state
`repository-memory-sync` SHALL detect git availability, commit existence, current HEAD, worktree state (clean/dirty/unknown), staged and unstaged files, last synced commit from manifest, and OpenSpec change candidates from diff paths.

#### Scenario: Clean worktree with commits
- **WHEN** `repository-memory-sync` runs in a git repository with a clean worktree and at least one commit
- **THEN** it SHALL detect `git.available = true`, `git.has_commits = true`, `git.head` set to current HEAD, `git.worktree_state = clean`, and compute the stable committed range from `last_synced_commit` to HEAD

#### Scenario: Dirty worktree with commits
- **WHEN** `repository-memory-sync` runs in a git repository with uncommitted changes
- **THEN** it SHALL detect `git.worktree_state = dirty` and compute both the stable committed range and the working-tree snapshot

#### Scenario: Git repository with no commits
- **WHEN** `repository-memory-sync` runs in a git repository with no commits
- **THEN** it SHALL detect `git.has_commits = false`, `git.head = null`, and use only the working-tree snapshot

#### Scenario: Non-git directory
- **WHEN** `repository-memory-sync` runs in a directory that is not a git repository
- **THEN** it SHALL detect `git.available = false`

### Requirement: Reconcile pending snapshots
`repository-memory-sync` SHALL reconcile pending uncommitted snapshots on every sync run. It SHALL compare pending snapshot metadata against new committed ranges and upgrade matched memory from `pending_commit` to `synced`, or create review queue items for ambiguous or unresolvable cases.

#### Scenario: Pending snapshot matches a new commit
- **WHEN** a memory file has `sync_status: pending_commit` and the subsequent commit range includes the changes described by the snapshot
- **THEN** `repository-memory-sync` SHALL update the memory frontmatter to `sync_status: synced` and record the linked commit(s)

#### Scenario: Pending snapshot partially matches
- **WHEN** a memory file has `sync_status: pending_commit` and only some of the snapshot changes appear in subsequent commits
- **THEN** `repository-memory-sync` SHALL create a review queue item with `reason: partial_reconcile` and NOT change the memory status to `synced`

#### Scenario: Pending snapshot has no matching commit
- **WHEN** a memory file has `sync_status: pending_commit` and no subsequent commit matches the snapshot evidence
- **THEN** `repository-memory-sync` SHALL create a review queue item with `reason: no_matching_commit`

### Requirement: Per-type memory policy
`repository-memory-sync` SHALL apply different update policies per memory type: `sessions` and `pitfalls` auto-update; `specs` auto-update when a spec/change ID is identified; `modules` auto-update for diff-detected modules and follow a discovery-confirm flow for filesystem-discovered candidates; `decisions` and `architecture` produce candidates only; `evolution` updates only with stable commit ranges; `schemas` never update during sync.

#### Scenario: Session memory auto-update
- **WHEN** `repository-memory-sync` processes session evidence
- **THEN** it SHALL auto-update `sessions/` memory without requiring user confirmation

#### Scenario: Decision memory candidate
- **WHEN** `repository-memory-sync` detects a potential design decision
- **THEN** it SHALL NOT create a formal `decisions/` memory file; it SHALL create a review queue item for user confirmation

#### Scenario: Architecture memory candidate
- **WHEN** `repository-memory-sync` detects a potential architecture change
- **THEN** it SHALL NOT create a formal `architecture/` memory file; it SHALL create a review queue item for user confirmation

#### Scenario: Evolution memory with dirty worktree
- **WHEN** `repository-memory-sync` runs on a dirty worktree and detects evolution-relevant changes
- **THEN** it SHALL NOT update `evolution/` formal memory; it SHALL record a pending timeline entry in sync-history only

### Requirement: Dirty worktree support without auto-commit
`repository-memory-sync` SHALL allow memory synchronization on dirty working trees without making git commits. Memory generated from uncommitted changes SHALL be marked `pending_commit` with `evidence_mode: uncommitted_snapshot`.

#### Scenario: Sync on dirty worktree
- **WHEN** `repository-memory-sync` runs and the working tree has uncommitted changes
- **THEN** it SHALL proceed with sync and mark affected memory as `pending_commit` with `evidence_mode: uncommitted_snapshot`

#### Scenario: No automatic git commit
- **WHEN** `repository-memory-sync` detects uncommitted changes
- **THEN** it SHALL NOT create any git commits

### Requirement: Three public sync statuses
`repository-memory-sync` SHALL expose only three public sync statuses in memory frontmatter: `synced`, `pending_commit`, and `needs_user_review`. Detailed reconciliation reasons SHALL be stored in `review-queue.json` and `sync-history/`, not in memory frontmatter.

#### Scenario: Memory with pending reconciliation
- **WHEN** a memory snapshot is partially reconciled against subsequent commits
- **THEN** the memory frontmatter SHALL show `sync_status: needs_user_review` with `review_reason: partial_reconcile` in the review queue item, NOT a separate frontmatter status like `partially_reconciled`

#### Scenario: Memory with matched reconciliation
- **WHEN** a pending memory snapshot is fully matched to a subsequent commit
- **THEN** the memory frontmatter SHALL show `sync_status: synced`

### Requirement: Review queue management
`repository-memory-sync` SHALL write review candidates to `.ai-memory/review-queue.json` for items requiring user confirmation. The review queue SHALL be committed to git but SHALL NOT be loaded by `repository-memory-load` by default. Review items SHALL NOT become formal memory files until explicitly accepted.

#### Scenario: Creating a review queue item
- **WHEN** `repository-memory-sync` identifies a decision or architecture candidate
- **THEN** it SHALL create an entry in `review-queue.json` with `id`, `type`, `source_sync_id`, `reason`, `title`, `source_refs`, `status: open`, and `created_at`

#### Scenario: Processing open review items
- **WHEN** `repository-memory-sync` runs and finds open review items related to the current diff
- **THEN** it SHALL present the items to the user with options: Accept into memory, Keep pending, Discard, or Other (user-provided description)

#### Scenario: Accepted review item becomes formal memory
- **WHEN** the user accepts a review queue item
- **THEN** `repository-memory-sync` SHALL create the corresponding formal memory file, update the review queue item `status: resolved`, and add `resolved_as` pointing to the created memory file

#### Scenario: Dismissed review item
- **WHEN** the user dismisses a review queue item
- **THEN** `repository-memory-sync` SHALL update the review queue item `status: dismissed` with `dismissed_reason`

### Requirement: Sync history audit trail
`repository-memory-sync` SHALL write a sync report to `.ai-memory/sync-history/<sync_id>.md` for each sync run. Sync history SHALL be committed to git but SHALL NOT be indexed by `index.json` or loaded by `repository-memory-load` by default.

#### Scenario: Writing sync history
- **WHEN** `repository-memory-sync` completes a sync run
- **THEN** it SHALL create `.ai-memory/sync-history/sync-YYYY-MM-DD-NNN.md` containing changed files, evidence used, memory deltas, skipped types, and confidence notes

#### Scenario: Sync history not indexed
- **WHEN** `repository-memory-sync` rebuilds `index.json`
- **THEN** it SHALL NOT include entries from `sync-history/`

### Requirement: YAML frontmatter per memory file
Each memory file under `.ai-memory/` SHALL contain YAML frontmatter with required fields: `id`, `type`, `title`, `summary`, `sync_status`, `evidence_mode`, `linked_commits`, `linked_specs`, `linked_sessions`, `updated_at`, `confidence`, and `tags`.

#### Scenario: Module memory frontmatter
- **WHEN** a module memory file is created
- **THEN** it SHALL contain frontmatter with `type: module`, `sync_status: synced` or `pending_commit`, `evidence_mode: commit` or `uncommitted_snapshot`, and appropriate linkage fields

#### Scenario: Pending memory frontmatter
- **WHEN** a memory file is created from uncommitted changes
- **THEN** frontmatter SHALL include `sync_status: pending_commit`, `evidence_mode: uncommitted_snapshot`, `snapshot_id`, and `reconcile_after_commit: true`

### Requirement: OpenSpec change ID detection
`repository-memory-sync` SHALL detect OpenSpec change/spec IDs in the following priority order: (1) user explicit specification, (2) git diff touching exactly one `openspec/changes/<id>` path, (3) current working path inside `openspec/changes/<id>`, (4) exactly one active OpenSpec change, (5) archive path pointing to an archived change, (6) multiple candidates require user selection with Other/Skip options, (7) no candidates means skip specs memory.

#### Scenario: Git diff touches one OpenSpec change
- **WHEN** git diff touches files under `openspec/changes/my-feature/`
- **THEN** `repository-memory-sync` SHALL automatically select `my-feature` as the spec ID

#### Scenario: Multiple active OpenSpec changes with ambiguous diff
- **WHEN** git diff touches multiple OpenSpec changes or no OpenSpec paths
- **THEN** `repository-memory-sync` SHALL present candidates to the user with Other and Skip options

#### Scenario: No OpenSpec context
- **WHEN** no OpenSpec change or spec ID is detected
- **THEN** `repository-memory-sync` SHALL skip specs memory without error

### Requirement: Spec lineage for related changes
When multiple active OpenSpec changes form a lineage (B refines A), `repository-memory-sync` SHALL map them to a single spec memory file with lineage metadata rather than creating separate spec memories.

#### Scenario: Change B refines change A
- **WHEN** `repository-memory-sync` detects that active change B explicitly references or refines active change A
- **THEN** it SHALL create or update a single spec memory with `primary_change_id`, `active_change_ids`, and `change_lineage` metadata linking B as a refinement of A

#### Scenario: Lineage is ambiguous
- **WHEN** multiple active changes exist and their relationship cannot be automatically determined
- **THEN** `repository-memory-sync` SHALL ask the user to specify the relationship with options: Treat B as refinement of A, Treat A and B as independent, Treat B as superseding A, Other (user description), or Skip specs memory

### Requirement: Index rebuild with selective inclusion
`repository-memory-sync` SHALL rebuild `.ai-memory/index.json` by scanning formal memory directories (`modules/`, `architecture/`, `decisions/`, `pitfalls/`, `specs/`, `evolution/`) and including only entries with `sync_status: synced` or `pending_commit`. Entries with `sync_status: needs_user_review` SHALL be excluded. Entries in `sync-history/`, `sessions/`, `snapshots/`, `tmp/`, `cache/` SHALL be excluded.

#### Scenario: Synced and pending memory in index
- **WHEN** a memory file has `sync_status: synced` or `pending_commit`
- **THEN** `rebuild_index.py` SHALL include it in `index.json`

#### Scenario: Needs_user_review excluded from index
- **WHEN** a memory file has `sync_status: needs_user_review`
- **THEN** `rebuild_index.py` SHALL exclude it from `index.json`

### Requirement: Index entry summaries
Each entry in `.ai-memory/index.json` SHALL contain a `summary` field with 2-3 sentences explaining when an agent should load the memory file. Summaries SHALL NOT duplicate the full memory body.

#### Scenario: Valid index entry summary
- **WHEN** a memory file is indexed
- **THEN** its `index.json` entry SHALL have a `summary` field of 2-3 sentences that describes the memory content and when it is relevant to load

### Requirement: Manifest update
`repository-memory-sync` SHALL update `.ai-memory/manifest.json` after each sync run, setting `git.head`, `git.last_synced_commit`, `git.worktree_state`, `pending_snapshots`, and `last_sync` with a unique `sync_id`.

#### Scenario: Sync completes on clean worktree
- **WHEN** `repository-memory-sync` finishes a sync on a clean worktree
- **THEN** manifest SHALL be updated with the current HEAD as `git.last_synced_commit`, `git.worktree_state = clean`, and `last_sync` containing the `sync_id` and timestamp

#### Scenario: Sync completes on dirty worktree
- **WHEN** `repository-memory-sync` finishes a sync on a dirty worktree
- **THEN** manifest SHALL record `git.worktree_state = dirty` and `pending_snapshots` containing metadata about the uncommitted snapshot

### Requirement: Check for initialization before syncing
`repository-memory-sync` SHALL check for `.ai-memory/manifest.json` before proceeding. If it does not exist, `repository-memory-sync` SHALL ask the user whether to run `repository-memory-init` or skip initialization.

#### Scenario: Manifest exists
- **WHEN** `.ai-memory/manifest.json` exists
- **THEN** `repository-memory-sync` SHALL proceed with the sync workflow

#### Scenario: Manifest missing and user approves init
- **WHEN** `.ai-memory/manifest.json` does not exist and the user approves initialization
- **THEN** `repository-memory-sync` SHALL invoke `repository-memory-init` logic and then proceed with the sync

#### Scenario: Manifest missing and user declines init
- **WHEN** `.ai-memory/manifest.json` does not exist and the user declines initialization
- **THEN** `repository-memory-sync` SHALL stop and report that memory is not initialized

### Requirement: Module discovery via filesystem scan
`repository-memory-sync` SHALL run `discover_modules.py` during module classification to identify candidates from the filesystem that may not appear in the git diff. It SHALL compare discovery results against `discovery-prefs.json` and present new or previously-rejected candidates to the LLM with their structural metadata for recommendation.

#### Scenario: New candidate with metadata presented to LLM
- **WHEN** `discover_modules.py` returns a candidate with `disposition: new` and metadata including `file_types` and `has_build_file`
- **THEN** `repository-memory-sync` SHALL present the candidate with full metadata to the LLM for analysis and recommendation

#### Scenario: Known module not in git diff is skipped
- **WHEN** a candidate has `disposition: known` but no files in the current git diff range
- **THEN** `repository-memory-sync` SHALL skip the candidate without presenting it (no relevant changes)

#### Scenario: Previously rejected candidate re-evaluated
- **WHEN** a candidate has `disposition: previously_rejected`
- **THEN** `repository-memory-sync` SHALL present it with a "previously rejected" label and the original `reason_rejected`, allowing user to re-evaluate

### Requirement: User confirmation for discovered module candidates
For each new or previously-rejected module candidate, `repository-memory-sync` SHALL present the candidate with the LLM recommendation and ask the user to Accept, Reject, or Merge into an existing module.

#### Scenario: User accepts a discovered module
- **WHEN** the user accepts a module candidate
- **THEN** `repository-memory-sync` SHALL create the corresponding memory file and update `discovery-prefs.json` with `status: accepted`

#### Scenario: User rejects a discovered module
- **WHEN** the user rejects a module candidate with a reason
- **THEN** `repository-memory-sync` SHALL NOT create a memory file; it SHALL record the rejection in `discovery-prefs.json` with `status: rejected` and `reason_rejected`

#### Scenario: User merges candidate into existing module
- **WHEN** the user chooses to merge a candidate into an existing module
- **THEN** `repository-memory-sync` SHALL update the existing module memory file and record the merge in `discovery-prefs.json`

### Requirement: Script CLIs for sync operations
Sync scripts SHALL accept `--root` (repository root path) and `--json` (JSON output mode) arguments. Scripts that modify files SHALL accept `--write` to apply changes. All scripts SHALL output JSON results when `--json` is specified.

#### Scenario: detect_state.py with JSON output
- **WHEN** `python detect_state.py --root . --json` is executed
- **THEN** it SHALL output JSON containing git state, OpenSpec candidates, and pending snapshots

#### Scenario: reconcile_pending.py with write mode
- **WHEN** `python reconcile_pending.py --root . --write --json` is executed
- **THEN** it SHALL reconcile pending memory and write updated frontmatter and review queue items

#### Scenario: validate_memory.py validation output
- **WHEN** `python validate_memory.py --root . --json` is executed
- **THEN** it SHALL output JSON with validation results for manifest, index, review queue, discovery prefs, and memory frontmatter

#### Scenario: rebuild_index.py with write mode
- **WHEN** `python rebuild_index.py --root . --write --json` is executed
- **THEN** it SHALL rebuild `.ai-memory/index.json` and output the result

#### Scenario: update_manifest.py with sync ID
- **WHEN** `python update_manifest.py --root . --sync-id sync-2026-05-27-001 --json` is executed
- **THEN** it SHALL update `.ai-memory/manifest.json` and output the result

#### Scenario: discover_modules.py with JSON output
- **WHEN** `python discover_modules.py --root . --json` is executed
- **THEN** it SHALL output JSON with module candidates and stats summary
