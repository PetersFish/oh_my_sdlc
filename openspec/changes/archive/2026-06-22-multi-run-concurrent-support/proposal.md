## Why

The SDLC workflow runtime currently uses a single `.ai/workflows/runs/current.json` file as the active run slot. `cmd_start` treats any different-subject active run as a conflict and exits. This blocks legitimate parallel workflow runs — for example, starting a run for change B while change A is still active. The runtime must support multiple concurrent runs so parallel OpenSpec changes can each have their own active run without conflict.

## What Changes

- Persistent run state layout changes from single `current.json` to `active/<run_id>.json` directory with `current.json` as a pointer-only file.
- `load_run_state(root)` reads the pointer, then loads `active/<run_id>.json`. Phase command signatures unchanged.
- `load_run_state(root, run_id)` loads a specific active run for batch scanning.
- `save_run_state(root, state)` writes `active/<run_id>.json` and updates the pointer.
- `cmd_start`: creates `active/<run_id>.json`, sets pointer. Rejects same-subject duplicates (conflict).
- `cmd_resume`: locates matching active run by subject, sets pointer. Requires `--subject-type` + `--subject-id`.
- `cmd_done` / `cmd_advance` (done path): write history, remove from `active/`, clear pointer (`current.json` → `{}`).
- `cmd_status`: without subject, lists all active runs; with subject, shows single run status.
- `cmd_preflight` / `_evaluate_subject_run_context`: search `active/` by subject, set pointer.
- `governance-check`: scan all `active/` files for `pending_hooks` (not just the pointed run).
- Add `_list_active_runs(root)` helper for directory scanning.
- Update all tests, add concurrent-run scenarios.
- Sync canonical templates.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `sdlc-workflow-engine`: Run state persistence model changes from single-file to directory-based multi-run. `current.json` becomes a pointer-only file containing `{"run_id": "<run_id>"}` and full run state lives only in `active/<run_id>.json`. `load_run_state`, `save_run_state`, `cmd_start`, `cmd_resume`, `cmd_done`, `cmd_advance`, `cmd_status`, `cmd_preflight`, and `governance-check` are all updated.

## Impact

- `.ai/workflows/scripts/workflow.py` — core run state management and all affected commands
- `.ai/workflows/runs/` — new `active/` directory layout
- `tests/test_workflow.py` — updated and new test scenarios
- Template files synced after implementation
