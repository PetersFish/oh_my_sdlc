## Why

Currently, run JSON files (`.ai/workflows/runs/active/<run_id>.json`) and run artifacts (handoffs, logs, plans) are stored in separate locations without centralized management. When archiving runs, the JSON file moves from `active/` to `history/`, but the associated handoffs, logs, and plans under `<run_id>/` remain scattered. This breaks the conceptual integrity of a "run" as a unit of work and complicates cleanup, inspection, and migration.

## What Changes

- **BREAKING**: Run JSON files move from `active/<run_id>.json` to `active/<run_id>/run.json` and from `history/<run_id>.json` to `history/<run_id>/run.json`
- The run directory now contains all artifacts: `run.json`, `plans/`, `handoffs/`, `logs/`
- Archiving (`done`/`advance` to done) moves the entire `<run_id>/` directory from `active/` to `history/`
- Cancelling a run removes the entire `active/<run_id>/` directory
- Listing active runs discovers run directories instead of flat JSON files
- Auto-migrate legacy `runs/handoffs/<run_id>/` and `runs/logs/<run_id>/` top-level directories into the unified `<run_id>/` structure
- Agent definitions (plan, implement, test, review, finish, dev-orchestrator) already use `<run_id>/handoffs/` and `<run_id>/logs/` paths — no path changes needed

## Capabilities

### New Capabilities
- `run-directory-unification`: Consolidate all run artifacts (JSON, plans, handoffs, logs) under a single `<run_id>/` directory with `run.json` as the run state file
- `run-legacy-migration`: Auto-migrate top-level `runs/handoffs/<run_id>/` and `runs/logs/<run_id>/` directories into the unified `<run_id>/` structure

### Modified Capabilities
- `sdlc-workflow-engine`: Run state file paths change from flat JSON to nested directory structure; archiving and cancellation operations change from file-level to directory-level operations

## Impact

- `.ai/workflows/scripts/workflow.py`: `_active_path()`, `_finalize_run_to_history()`, `cmd_done()`, `cmd_cancel_run()`, `_list_active_runs()`, `cmd_advance()`, `cmd_governance_check()`, `save_run_state()`
- `skills/sdlc-project-bootstrap/scripts/init_foundations.py`: `DIRS` list (no change needed but validates)
- `tests/test_workflow.py`: all path references to `active/<run_id>.json` and `history/<run_id>.json`
- `tests/test_init_foundations.py`: path validation
- `tests/test_wrapper_contracts.py`: path assertions
- 27 existing history JSON files need migration (or backward-compatible read support)
- 2 existing run directories with handoffs/logs/plans need to be checked for legacy migration
- Agent definitions: no changes needed (already use unified paths)
- Skill bootstrap templates: sync required after workflow.py changes
