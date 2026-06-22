---
id: RM-ORCH-004
title: "Verify Done Run Cleanup From Active Directory"
status: idea
stage: v2
priority: p1
order: 35
depends_on:
  - RM-ORCH-006
openspec_change: null
created_at: 2026-06-21
started_at: null
completed_at: null
---

# Goal

After RM-ORCH-006 introduces the `active/` directory and `current.json` pointer, verify and spec that done runs are properly cleaned: `active/<run_id>.json` removed, pointer cleared (`current.json` → `{}`), and history written — ensuring no zombie runs remain.

# Problem Context

RM-ORCH-006 keeps `current.json` as a pointer (`{"run_id": "..."}`) and stores run state in `active/<run_id>.json`. The done path (`cmd_done`, `advance -> done`) must: write `history/<run_id>.json`, remove `active/<run_id>.json`, and clear the pointer. This item verifies cleanup correctness across all codepaths, updates the spec to match the new model, and catches edge cases (e.g., what if `os.remove` fails, what if the file is already missing, what if pointer points to a removed run).

# Scope

## In

- Update spec (`openspec/specs/sdlc-workflow-engine/spec.md`): document the `active/` + `current.json` pointer layout, and the done cleanup contract (remove active file, clear pointer, write history).
- Audit all done-entry codepaths in `workflow.py` for consistent `active/` removal AND pointer clear.
- Add tests: after done via `advance` and `cmd_done`, assert `active/<run_id>.json` absent, pointer cleared, and `history/<run_id>.json` present.
- Handle edge case: `cmd_done` on an already-removed active file (idempotent — write history if missing, clear pointer, succeed).
- Handle edge case: pointer points to a non-existent active file (status reports `stale_pointer`, governance-check reports it).
- Sync canonical templates and distributed copies.
- Run full test suite and template drift check.

## Out

- No changes to the active/ directory structure or multi-run model (handled by RM-ORCH-006).
- No changes to history format.

# Design Notes

## Key Decisions

- Done cleanup (RM-ORCH-006's implementation): `active/` → write `history/<run_id>.json` → remove from `active/` → clear `current.json` pointer (`{}`). This item verifies all three steps are consistent.
- Pointer clear is the natural "no active run" signal — `load_run_state(root)` reads empty pointer → returns `None`, same as before.
- `cmd_done` on a run whose active file is already missing (e.g., interrupted cleanup) SHALL be idempotent: write history if missing, clear pointer, succeed.
- `status` detecting a pointer to a missing active file SHALL report `stale_pointer` rather than `no_active_run`, surfacing the inconsistency.
- Spec update covers the full file layout: `active/` for in-progress runs, `current.json` as pointer, `history/` for completed runs.

## Initial Approach

1. Update spec to document the `active/` → `history/` cleanup contract.
2. Audit `cmd_done` and `cmd_advance` (done path) for consistent `active/` removal.
3. Add idempotency handling for already-missing active files.
4. Add tests for both done-entry paths and the idempotent edge case.
5. Run full test suite: `python3 -m pytest tests/test_workflow.py -v`.
6. Run template sync and drift check.

# Acceptance Criteria

- After `cmd_done` or `advance -> done`, `active/<run_id>.json` does NOT exist.
- After done, `current.json` pointer is cleared (`{}`).
- `history/<run_id>.json` contains the complete final run state.
- `cmd_done` on a run whose active file is already missing succeeds (idempotent).
- `cmd_status` with a stale pointer (active file missing) reports `stale_pointer`.
- Spec (`openspec/specs/sdlc-workflow-engine/spec.md`) documents the `active/` + pointer + `history/` layout.
- `python3 -m pytest tests/test_workflow.py -v` passes.
- Template drift check passes.

# Completion Notes

Not started.

# Design Reference

- `openspec/specs/sdlc-workflow-engine/spec.md` (Run State Schema)
- `.ai/workflows/scripts/workflow.py` (`cmd_advance`, `cmd_done`, `cmd_status`, `load_run_state`)
- `.ai/workflows/runs/current.json` (pointer file)
- `tests/test_workflow.py`
- RM-ORCH-006 (multi-run active/ directory + pointer — prerequisite)
