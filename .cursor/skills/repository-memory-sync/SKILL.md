---
name: repository-memory-sync
description: Use when syncing repository memory after code changes, git commits, session work, OpenSpec verification, or when the user asks to update `.ai-memory/`. Do not use for initializing memory or loading memory context.
license: MIT
---

# Repository Memory Sync

Synchronize repository memory after changes. Classify evidence into memory types, apply per-type policies, handle dirty worktrees, manage pending reconciliation, write sync-history audit trail.

## When to Use

- After code changes that affect structure, behavior, or contracts.
- After git commits that introduce meaningful deltas.
- At the end of work sessions.
- After OpenSpec verification completes.
- When the user explicitly requests memory sync.
- When the user asks to update `.ai-memory/`.

## Required Inputs

- Repository root path (defaults to `.`).
- Optional: OpenSpec change ID.
- Optional: Session context (what was worked on).
- Optional: User decisions for candidate items.

## Workflow

1. **Check manifest.** Verify `.ai-memory/manifest.json` exists. If missing, ask user whether to initialize via `repository-memory-init`. Do not proceed without a manifest.
2. **Load existing memory.** Run `repository-memory-load` first if `.ai-memory/index.json` exists, to ensure classification and deduplication work against current memory state.
3. **Detect repository state.** Run `detect_state.py` to determine commit range, dirty worktree status, and changed paths.
4. **Reconcile pending snapshots.** Run `reconcile_pending.py` to resolve any `pending_commit` entries from prior dirty-worktree syncs that have since been committed.
5. **Compute sync inputs.** Assemble:
   - Stable committed range (from last-synced commit to HEAD).
   - Unstable working-tree snapshot (unstaged/uncommitted changes).
   - Optional OpenSpec context (change ID, artifacts, lineage).
 6. **Classify memory candidates by type.** Apply per-type policies (see Per-Type Policy Table below).

    **Module discovery sub-steps:**

    6a. **Run discover_modules.py.** Execute `scripts/discover_modules.py --root <root> --json` to scan the filesystem for module candidates. The script recursively discovers non-hidden directories (default max_depth=5) that satisfy Rule A (≥1 direct file) or Rule B (≥2 direct subdirectories), collecting language-neutral structural metadata (extension histogram, build-file detection, top-level filenames).

    6b. **Cross-reference with discovery-prefs.json.** Compare candidate paths against `.ai-memory/discovery-prefs.json` `module_map` to determine `disposition`: `new` (not in map), `known` (status: accepted), or `previously_rejected` (status: rejected).

    6c. **Classify changed-files modules.** For each changed path or observation from git diff, determine which existing module memory type it maps to and whether it is auto-update or candidate-only (existing behavior).

    6d. **LLM evaluate discovery candidates.** For `new` and `previously_rejected` candidates, analyze structural metadata (file_types, has_build_file, top_level_files, depth, children_count) and recommend: Accept (create independent module memory), Reject (not a module), or Merge (into an existing module).

    6e. **User confirmation for discovery candidates.** Present recommendations to user:
    - **Accept** — create module memory file with YAML frontmatter, write to `discovery-prefs.json` with `status: accepted`.
    - **Reject** — write to `discovery-prefs.json` with `status: rejected` and reason.
    - **Merge** — update existing module memory file, write to `discovery-prefs.json` with `status: accepted` pointing to the existing `memory_id`.
    Known candidates (from diffs) auto-update without confirmation.

 7. **Auto-update eligible types.** For sessions, pitfalls, specs, modules (diff-detected), and evolution: write memory deltas directly.
 8. **Present candidates for user confirmation.** For decisions and architecture types, present each candidate with options:
    - **Accept** — write to formal memory.
    - **Skip** — discard this candidate.
    - **Save as proposed** — write to review queue for later confirmation.
    - **Other** — user specifies alternative disposition.
 9. **Handle `needs_user_review` items.** Create entries in `.ai-memory/review-queue.json`. Do NOT create formal memory files for these items.
10. **Validate.** Run `validate_memory.py` to check schema conformance, reference integrity, and policy compliance.
11. **Rebuild index.** Run `rebuild_index.py`, excluding `needs_user_review` items and restricted paths (`sync-history/`, `sessions/`, `snapshots/`, `tmp/`, `cache/`).
12. **Update manifest.** Run `update_manifest.py` to record sync timestamp, last-synced commit, and stats.
13. **Write sync history.** Create `.ai-memory/sync-history/<sync_id>.md` with the audit trail for this run (see sync-history template).
14. **Present review queue to user.** For any items in the review queue, offer:
    - **Accept into memory** — promote to formal memory file.
    - **Keep pending** — leave in review queue.
    - **Discard** — remove from review queue.
    - **Other** — user specifies.
15. **Output sync summary.** Report docs updated, types skipped, evidence used, pending items, review queue items, discovery stats, and remaining gaps.

## Per-Type Policy Table

| Memory Type | Auto-Update | Local-Only | Requires User Confirm | Needs Stable Commit | Notes |
|---|---|---|---|---|---|
| `sessions` | Yes | Yes | No | No | Cumulative session log; always local-only |
| `pitfalls` | Yes (with real failure evidence) | No | No | No | Must have stack trace, failing test, or observed misbehavior |
| `specs` | Yes (with identified spec/change ID) | No | No | No | Requires OpenSpec change ID or explicit spec reference |
| `modules` | Yes (diff-detected) / Confirm (discovery) | No | Yes (discovery) | No | Diff-detected auto-update (`pending_commit` on dirty); discovery candidates require user confirmation |
| `decisions` | No | No | Yes | No | Candidate only; user must confirm before formal memory |
| `architecture` | No | No | Yes | No | Candidate only; user must confirm before formal memory |
| `evolution` | Yes | No | No | Yes | Only written when a stable commit range is available |
| `schemas` | Validation only | No | No | No | Checked for conformance; never auto-created |

## Dirty Worktree Policy

- Allow sync on dirty worktrees. Do not require a clean working tree.
- Mark memory deltas from uncommitted changes as `pending_commit` with `evidence_mode: uncommitted_snapshot`.
- Never auto-commit these entries. They remain in memory with the `pending_commit` flag.
- On the next sync, `reconcile_pending.py` checks whether `pending_commit` entries have been committed. If so, it upgrades their `evidence_mode` and clears the `pending_commit` flag.

## OpenSpec ID Detection Priority

When determining which OpenSpec change(s) are relevant:

1. **User explicit specification.** The user names a change ID directly.
2. **Git diff touches one `openspec/changes/<id>`.** If changed files map to exactly one change directory, use that ID.
3. **Current path inside `openspec/changes/<id>`.** If the working directory or active file is inside an OpenSpec change directory, use that ID.
4. **Exactly one active OpenSpec change.** If there is only one un-archived change in `openspec/changes/`, use that ID.
5. **Archive path.** If the diff touches `openspec/archive/<id>`, use that archived change ID.
6. **Multiple candidates.** If multiple changes match, present options and ask the user: Accept one, Other, or Skip all.
7. **No candidates.** Skip specs memory for this sync cycle.

## Spec Lineage

When multiple active OpenSpec changes form a lineage (change B refines change A), map them to a single spec memory entry with lineage metadata. When lineage relationships are ambiguous, show the user options for how to relate them.

## Review Queue Policy

- `needs_user_review` items are written to `.ai-memory/review-queue.json`.
- They are NOT written as formal memory files.
- The review queue is committed to git but only read by `repository-memory-sync`.
- On the next sync, open review queue items are processed first, before classifying new changes.
- Review queue entries are never loaded by `repository-memory-load`.

## Sync History

- Each sync writes `.ai-memory/sync-history/<sync_id>.md` using the sync-history template.
- Sync history files are committed to git.
- They are NOT indexed by `index.json`.
- They are NOT loaded by `repository-memory-load` by default.
- The `sync_id` format is `YYYYMMDD-HHMMSS` or a UUID if timestamps are insufficient.

## Guardrails

- Do NOT auto-commit to git. The user controls version control.
- Do NOT create formal memory for `needs_user_review` items.
- Do NOT index `sync-history/`, `sessions/`, `snapshots/`, `tmp/`, `cache/` in `index.json`.
- Do NOT load `review-queue.json` by default during memory-load.
- Do NOT allow `needs_user_review` items into `index.json`.
- Do NOT overwrite existing memory without evidence (commit, spec, session observation).
- Do NOT treat `pending_commit` memory as stable fact. It is provisional until reconciled.
- If `.ai-memory/manifest.json` is missing, direct the user to `repository-memory-init` rather than creating it.
- Do NOT create module memory for candidates marked as rejected in `discovery-prefs.json` without explicit user re-confirmation.
- Modules from discovery must use `evidence_mode: discovery` and `linked_sessions` referencing the current session.

## Output

After sync, report:

```
Memory Sync Complete — <sync_id>

Updated: <list of memory docs updated by type>
Skipped: <types skipped and why>
Evidence: <commit range, OpenSpec change IDs, session observations used>
Pending: <items marked pending_commit>
Review Queue: <items in review-queue awaiting user decision>
Gaps: <areas where evidence was insufficient to update memory>
```