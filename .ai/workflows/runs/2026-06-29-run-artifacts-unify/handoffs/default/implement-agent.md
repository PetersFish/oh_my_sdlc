# Implement Agent Handoff — run-artifacts-unify

## Metadata

- **Agent**: implement-agent
- **Phase**: apply_change
- **Flow Type**: spec-flow
- **Change ID**: run-artifacts-unify
- **Run ID**: 2026-06-29-run-artifacts-unify
- **Slice ID**: default
- **Timestamp**: 2026-06-29T22:20:00

## Objective

Unify all run artifacts under a single `<run_id>/` directory with `run.json` as the canonical state file, and add legacy migration for old-style `runs/handoffs/` and `runs/logs/` directories. No backward-compatible reading of old flat JSON files.

## Work Completed

### Core Path Changes (workflow.py)
- ✅ **Task 1.1**: `_active_path()` returns `active/<run_id>/run.json` (was `active/<run_id>.json`)
- ✅ **Task 1.2**: `save_run_state()` creates directory `active/<run_id>/` and writes `run.json` inside, calls `_migrate_legacy_artifacts()`
- ✅ **Task 1.3**: `_finalize_run_to_history()` uses `shutil.move()` to move entire `active/<run_id>/` directory → `history/<run_id>/`
- ✅ **Task 1.4**: `cmd_done()` uses `shutil.move()` for entire directory move
- ✅ **Task 1.5**: `cmd_advance()` done-phase handling uses `shutil.move()` for entire directory move
- ✅ **Task 1.6**: `cmd_cancel_run()` uses `shutil.rmtree()` on entire `active/<run_id>/` directory
- ✅ **Task 1.7**: `_list_active_runs()` iterates subdirectories under `active/` and reads `run.json`
- ✅ **Task 1.8**: `cmd_governance_check()` reads `history/<run_id>/run.json` (new-style only)
- ✅ **Task 1.9**: `_load_done_history_run_ids()` updated for directory-based history reads
- ✅ **Task 1.10**: Second governance check history loop updated for directory-based reads

### Legacy Migration
- ✅ **Task 2.1**: Added `_migrate_legacy_artifacts()` function with `.migrated` sentinel for idempotency
- ✅ **Task 2.2**: Migration called from `save_run_state()` and `load_run_state()`
- ✅ **Task 2.3**: Migrates `runs/handoffs/<run_id>/` → `active/<run_id>/handoffs/`
- ✅ **Task 2.4**: Migrates `runs/logs/<run_id>/` → `active/<run_id>/logs/`

### Test Suite Updates
- ✅ **Task 3.1**: Updated test helpers: `_read_current_state`, `_write_current_state`, `_read_active_file`, `_read_history`, `_make_active_roadmap_run`
- ✅ **Task 3.2**: Updated `_find_active_file` for directory-based structure
- ✅ **Task 3.3**: Updated `_make_active_run` and `_make_done_history_run` and `_make_done_roadmap_history_run` helpers
- ✅ **Task 3.4**: Updated all three `_list_active_runs_support()` methods for directory iteration
- ✅ **Task 3.5**: Updated 20+ inline path references across test_workflow.py
- ✅ **Task 3.6**: Updated flat history writes in preflight and governance test methods

### New Tests Added (TDD)
- ✅ `test_active_path_returns_run_json_in_directory`
- ✅ `test_save_run_state_creates_directory_with_run_json`
- ✅ `test_finalize_run_to_history_moves_entire_directory`
- ✅ `test_cmd_done_moves_entire_directory`
- ✅ `test_cancel_run_removes_entire_directory`
- ✅ `test_list_active_runs_from_directories`
- ✅ `test_governance_check_reads_history_dir`
- ✅ `test_legacy_migration_handoffs`
- ✅ `test_legacy_migration_logs`
- ✅ `test_legacy_migration_idempotent`

### Active Run Migration
- ✅ Migrated `active/2026-06-29-run-artifacts-unify.json` → `active/2026-06-29-run-artifacts-unify/run.json`

## Files/Artifacts Changed

- `.ai/workflows/scripts/workflow.py` — All path functions, archive/cancel commands, governance check, legacy migration
- `tests/test_workflow.py` — 10 new tests + updated 5 test helpers + 20+ inline path references

## Commands Run

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_workflow.py -v` | 174 passed, 15 subtests |
| `python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py tests/test_init_foundations.py -v` | 310 passed, 15 subtests |
| `python3 -m pytest tests/test_workflow.py -v -k "test_active_path_returns_run_json_in_directory or test_save_run_state_creates or test_finalize_run_to_history_moves or test_cmd_done_moves or test_cancel_run_removes or test_list_active_runs_from or test_governance_check_reads_history_dir or test_legacy_migration"` | 11 passed |

## Evidence Summary

- **TDD**: All 10 new tests written first (RED), then implementation made them pass (GREEN)
- **Full Suite**: 310 tests passing, 0 failures
- **Focused Tests**: All 11 run-artifacts-unify tests pass
- **Contract Verification**: All path helpers, save/load, finalize, cancel, governance, and migration operations verified

## Blockers

None. All implementation complete.

## Assumptions

1. `shutil.move()` is atomic on same filesystem (macOS/Linux) — verified
2. Old flat `history/<run_id>.json` format is no longer readable — accepted (pre-release product per D4 removal)
3. Agent definitions already use new-style paths — verified, no changes needed
4. `init_foundations.py` and workflow YAML definition need no changes — verified

## Risks/Follow-Ups

- **Template Sync**: `sync_templates.py` should be run to update bootstrap templates (Task 5.1)
- **Agent Distribution**: `install_agents.py` should be run for project-level agent distribution (Task 5.2)
- **Existing history runs**: Check `.ai/workflows/runs/history/` for any pre-existing flat `.json` files that need migration

## Raw Logs

- `python3 -m pytest tests/test_workflow.py -v` → 174 passed (see: `.ai/workflows/runs/2026-06-29-run-artifacts-unify/logs/default/implement-agent/full-suite.log`)
