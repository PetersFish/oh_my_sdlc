---
id: RM-ORCH-004
title: "Clear Current Run On Done"
status: idea
stage: v2
priority: p0
order: 30
depends_on:
  - RM-ORCH-001
openspec_change: null
created_at: 2026-06-21
started_at: null
completed_at: null
---

# Goal

When a workflow run reaches `done`, the runtime SHALL remove `.ai/workflows/runs/current.json` so that only active runs occupy the current state slot. Completed runs SHALL exist only in history.

# Problem Context

The current spec explicitly requires `Current run remains latest after done` — after a run reaches `done`, `.ai/workflows/runs/current.json` retains the full done state alongside the history copy. This creates several problems:

- **Semantic confusion**: `current.json` implies an active run, but a done run is by definition not active. Keeping done state in `current` blurs the line between active and historical runs.
- **Dual-write drift**: `current.json` and `history/<run_id>.json` receive `updated_at` at different points in the lifecycle (`advance -> done` writes history before `save_run_state`, while `cmd_done` writes history after status change), leading to inconsistent timestamps between the two copies.
- **Governance ambiguity**: `governance-check` must reason about whether a done `current.json` counts as "governed" or "active", adding unnecessary branching.
- **Resume ambiguity**: `status` with a done `current.json` must distinguish "no active run" from "last run is done", increasing client-side branching.

The fix: treat `current.json` strictly as the active-run slot. On `done`, write the complete history record and delete `current.json`.

# Scope

## In

- Modify spec: replace `Current run remains latest after done` with `Current run is cleared after done`.
- Update `cmd_advance` (`advance -> done` path): after writing history, delete `current.json` instead of also saving to current.
- Update `cmd_done`: after writing history, delete `current.json`.
- Update `workflow.py status`: when no `current.json` exists, return `no_active_run`.
- Update tests: assert that after `done`, history exists and `current.json` does NOT exist.
- Sync canonical templates: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` and distributed copies.
- Run full test suite and template drift check.

## Out

- No changes to `governance-check` logic — it already uses history as valid governance evidence.
- No changes to resume semantics beyond the natural consequence of `current.json` absence.
- No changes to history file format or content.
- No migration of existing done `current.json` files — handled by the runtime on next `start`.

# Design Notes

## Key Decisions

- Delete `current.json` rather than writing a pointer/redirect. A pointer adds complexity without clear benefit: `status` already knows to check history for `no_active_run`, and `governance-check` reads history directly.
- Both `advance -> done` and `cmd_done` paths SHALL follow the same pattern: write history first, then delete current. This eliminates the dual-write timestamp bug.
- `status` with no active run and no current file returns `no_active_run` — same as before when `load_run_state` returns None.
- History lookup by `run_id` is sufficient. No global "last completed run" index is needed.

## Tradeoffs

- Deleting `current.json` means `status` cannot report "last run was X" without scanning history. This is acceptable because the orchestrator and governance-check already scan history when needed.
- A pointer file would enable faster "last run" lookup but introduces its own sync problems (what if pointer and history diverge?). Deletion is simpler and more reliable.
- Tests that previously relied on done `current.json` for assertions will need to use history instead.

## Initial Approach

1. Modify the spec at `openspec/specs/sdlc-workflow-engine/spec.md` to replace the `Current run remains latest after done` scenario.
2. In `workflow.py`, update the two done-entry points:
   - `cmd_advance`: when `next_phase == "done"`, write history, then `os.remove` current.json instead of `save_run_state`.
   - `cmd_done`: write history, then remove `current.json`.
   - Write a helper `_finalize_done(root, state)` to avoid duplication.
3. Update tests in `tests/test_workflow.py` to verify current.json is absent after done.
4. Run full test suite: `python3 -m pytest tests/test_workflow.py -v`.
5. Run template sync: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .`.
6. Run template drift check: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` and `--check-distributed`.

## Open Questions

- Should `load_run_state` be the sole function to check for active runs, or should `status` add a "last completed" convenience field? (Recommended: keep `load_run_state` simple, add convenience only if needed.)

# Acceptance Criteria

- After `workflow.py advance` or `workflow.py done` reaches `done` status, `.ai/workflows/runs/current.json` does NOT exist.
- `.ai/workflows/runs/history/<run_id>.json` contains the complete final run state.
- `workflow.py governance-check` does NOT report a dangling archive for a change with a done history run.
- `workflow.py status` with no active run returns `no_active_run`.
- `workflow.py start` works correctly with no `current.json` present.
- `python3 -m pytest tests/test_workflow.py -v` passes.
- Template drift check passes: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check --check-distributed`.

# Completion Notes

Not started.

# Design Reference

- `openspec/specs/sdlc-workflow-engine/spec.md` (Run State Schema, current to change)
- `.ai/workflows/scripts/workflow.py` (cmd_advance, cmd_done, cmd_status)
- `tests/test_workflow.py`
