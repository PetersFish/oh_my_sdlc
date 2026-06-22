---
id: RM-ORCH-006
title: "Multi-Run Concurrent Support"
status: done
stage: v2
priority: p0
order: 25
depends_on:
  - RM-ORCH-001
openspec_change: multi-run-concurrent-support
created_at: 2026-06-22
started_at: 2026-06-22
completed_at: 2026-06-22
---

# Goal

Replace the single `.ai/workflows/runs/current.json` file with an `active/` directory that supports multiple concurrent workflow runs, so that parallel OpenSpec changes can each have their own active run without conflict.

# Problem Context

The current runtime uses a single `current.json` file as the active run slot. `cmd_start` treats any different-subject active run as a conflict and exits. This blocks legitimate parallel task workflows:

- **Scenario 1 (parallel changes)**: Start a run for change A. Before change A is done, begin work on change B. `cmd_start` finds change A's run in `current.json`, detects a different subject, and reports `conflict` — blocking change B's run.
- **Scenario 2 (session switching)**: Complete some phases for change A, then `/new` to a fresh session to continue change A. The new session has no context of the active run — `cmd_status` shows the run but there's no way to point the session at the correct run.

The fix: move run state to `active/<run_id>.json` while keeping `current.json` as a **pointer** file. The pointer is updated by entry points (`start`, `resume`, `preflight`), making session switching transparent — the next preflight call sets the pointer to the correct run.

# Scope

## In

- Add `.ai/workflows/runs/active/<run_id>.json` directory for per-run state storage.
- Keep `.ai/workflows/runs/current.json` as a pointer file: `{"run_id": "os-opencode_change-..."}`.
  - `load_run_state(root)` reads pointer → loads `active/<run_id>.json` (phase commands unchanged).
  - `save_run_state(root, state)` writes `active/<run_id>.json` + updates pointer.
  - Pointer is set by `cmd_start`, `cmd_resume`, and `cmd_preflight`.
- `cmd_start`: create `active/<run_id>.json` + set pointer. Reject if same `subject_id` already has an active run (conflict).
- `cmd_resume`: locate matching active run by `subject_type` + `subject_id`, set pointer. Require subject args.
- `cmd_done` / `cmd_advance` (done path): write history, remove from `active/`, clear pointer (`current.json` → `{}`).
- `cmd_status`: when no subject given, list all active runs; when specified, show single run status.
- `governance-check`: scan ALL `active/` files for `pending_hooks` (not just the pointed run) and `history/` for done evidence.
- `cmd_preflight` / `_evaluate_subject_run_context`: search `active/` by subject, set pointer.
- Update tests to cover: concurrent runs, resume by subject, status with multiple active runs, done cleanup from active directory and pointer clear.
- Sync canonical templates after implementation.

## Out

- No change to `history/` format or content.
- No change to workflow phase machine or transition logic.
- No change to the governance-check finding types — only the scan scope changes (`active/` + `history/` instead of `current.json` + `history/`).
- No automatic run prioritization or scheduling — concurrency is opt-in, not orchestrated.
- No locking or merge mechanism for concurrent runs touching the same subject.

# Design Notes

## Key Decisions

- Keep `current.json` as a pointer file (`{"run_id": "..."}`) rather than removing it. The pointer is session-scoped: 10 phase commands (`readiness`, `resolve`, `advance`, `done`, etc.) call `load_run_state(root)` with no args and transparently operate on the pointed run. Commands that need to scan all runs (`governance-check`, `status --all`) iterate `active/` directly.
- `load_run_state(root)` (no args) reads pointer → loads `active/<run_id>.json`. `load_run_state(root, run_id)` loads a specific active file for batch scanning.
- `save_run_state(root, state)` writes `active/<run_id>.json` AND updates `current.json` pointer — ensuring the pointer always tracks the last-touched run.
- Use a directory `active/` over a namespace-prefixed file (e.g., `current-<id>.json`) because directories are easier to scan, list, and operate on with standard filesystem tools.
- `run_id` is the filename key (e.g., `active/os-opencode_change-add-foo.json`). This keeps filenames self-describing and avoids needing to parse JSON to identify a run.
- `cmd_start` rejects duplicate active runs for the same `subject_id` (exactly one active run per subject).
- `cmd_resume` requires `--subject-type` + `--subject-id`; `cmd_status` without subject lists all active runs for session disambiguation.
- Pointer is set by every entry point: `cmd_start`, `cmd_resume`, `cmd_preflight`. Session switching is handled naturally — when the user continues work on a different change, the next `preflight` or `resume` call updates the pointer.
- Governance-check scans all `active/` files (not just pointed) for pending hooks. Dangling archive check continues to use history/ evidence.
- Legacy migration: not handled. No historical `current.json` burden exists in this project.

## Tradeoffs

- Scanning a directory for matching runs is slightly slower than reading a single file, but the number of active runs is small (typically 1-3).
- Keeping `current.json` as a pointer adds one more file to maintain, but avoids changing 10 phase command signatures.
- Losing the "exactly one active run" invariant means some commands need explicit subject disambiguation. The pointer file handles this transparently for single-subject sessions; `cmd_status` lists all active runs for multi-subject awareness.
- Concurrent runs touching the same roadmap item or same file could produce merge conflicts. This is a user-level concern, not a runtime-level concern — the runtime provides isolation, not synchronization.
- Pointer file guarantees that the 10 phase commands (`readiness`, `resolve`, `record-evidence`, `complete-phase`, `complete-hook`, `advance`, `block`, `done`, `status`, `validate`) need zero signature changes.

## Initial Approach

1. Add `active/` directory support. Modify `load_run_state(root)` and `save_run_state(root, state)`:
   - `load_run_state(root)`: read `current.json` pointer → load `active/<run_id>.json`
   - `load_run_state(root, run_id)`: load specific `active/<run_id>.json` (for batch scanning)
   - `save_run_state(root, state)`: write `active/<run_id>.json` + update `current.json` pointer
2. Add `_list_active_runs(root)` helper that scans `active/` directory.
3. Update `cmd_start`: create `active/<run_id>.json`, set pointer. Reject if same subject already active.
4. Update `cmd_resume`: find matching run by subject, set pointer. Require `--subject-type`/`--subject-id`.
5. Update `cmd_done` / `cmd_advance` (done path): write history, `os.remove` from `active/`, clear pointer (`{}`).
6. Update `cmd_status`: list all active runs by default, show pointer indicator; show single run if subject given.
7. Update `governance-check`: scan all `active/` and `history/` for evidence (not just pointed run).
8. Update `cmd_preflight` / `_evaluate_subject_run_context`: search `active/` by subject, set pointer.
9. Update all tests. Add concurrent-run scenarios.
10. Run full test suite and template drift check.

## Resolved Decisions

- **Same-subject duplicates**: Rejected. `cmd_start` SHALL report conflict if an active run already exists for the same `subject_id`. Exactly one active run per subject at any time.
- **`cmd_resume` without args**: Always requires `--subject-type` + `--subject-id`. Use `cmd_status` to list active runs when the subject is unknown.
- **Legacy migration**: Not handled. No existing `current.json` burden; keeping code simple.
- **Pointer file kept**: `current.json` remains as a pointer, avoiding signature changes to 10 phase commands. Entry points (`start`, `resume`, `preflight`) set the pointer; session switching is handled by the next entry-point call.

# Acceptance Criteria

- Two independent `cmd_start` calls with different `subject_id` each create their own `active/<run_id>.json` without conflict.
- `cmd_start` with a `subject_id` that already has an active run reports conflict.
- `cmd_resume --subject-type openspec_change --subject-id <id>` finds the correct run and sets the pointer.
- `cmd_status` without subject lists all active runs.
- `cmd_done` writes history, removes from `active/`, and clears the pointer (`current.json` → `{}`).
- `governance-check` detects `pending_hooks` from ANY active run (not just the pointed one) and `dangling_archive` using history evidence.
- `current.json` pointer is updated by `cmd_start`, `cmd_resume`, and `cmd_preflight`; phase commands read the pointer transparently.
- `python3 -m pytest tests/test_workflow.py -v` passes.
- Template drift check passes.

# Completion Notes

- Full implementation: active/ directory, pointer file, concurrent run support, 85 tests + 11 subtests passing.
- Code review found 3 post-implementation issues, all fixed before archive.
- Known gap: OpenCode plugin does not automatically trigger workflow post-archive hooks; manual state correction required for this run.
- Follow-up: automatic archive→roadmap/workflow lifecycle bridge needed.

# Design Reference

- `.ai/workflows/scripts/workflow.py` (`load_run_state`, `save_run_state`, `cmd_start`, `cmd_resume`, `cmd_done`, `cmd_advance`, `governance-check`)
- `.ai/workflows/runs/` (current single-file layout)
- `tests/test_workflow.py`
