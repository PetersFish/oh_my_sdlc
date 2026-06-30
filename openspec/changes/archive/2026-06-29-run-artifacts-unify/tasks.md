## 1. Core Path Changes in workflow.py

- [ ] 1.1 Change `_active_path()` to return `active/<run_id>/run.json` instead of `active/<run_id>.json`
- [ ] 1.2 Change `save_run_state()` to create `active/<run_id>/` directory and write `run.json` inside it
- [ ] 1.3 Change `_finalize_run_to_history()` to move entire `active/<run_id>/` directory to `history/<run_id>/` using `shutil.move()`
- [ ] 1.4 Change `cmd_done()` to move entire `active/<run_id>/` directory to `history/<run_id>/` instead of writing individual JSON and removing file
- [ ] 1.5 Change `cmd_advance()` done-phase handling (lines 2082-2121) to move entire directory instead of individual file operations
- [ ] 1.6 Change `cmd_cancel_run()` to remove entire `active/<run_id>/` directory using `shutil.rmtree()` instead of removing single file
- [ ] 1.7 Change `_list_active_runs()` to iterate subdirectories under `active/` and read `run.json` from each
- [ ] 1.8 Change `cmd_governance_check()` to read `active/<run_id>/run.json` (directories) and `history/<run_id>/run.json` (new-style only; no backward-compatible fallback for old flat JSON files)

## 2. Legacy Migration

- [ ] 2.1 Add `_migrate_legacy_artifacts(root, run_id)` function that moves `runs/handoffs/<run_id>/` to `active/<run_id>/handoffs/` and `runs/logs/<run_id>/` to `active/<run_id>/logs/`
- [ ] 2.2 Add migration sentinel check to prevent re-migration (use `.migrated` file in the run directory)
- [ ] 2.3 Call `_migrate_legacy_artifacts()` from `save_run_state()` and `load_run_state()` on first access

## 3. Test Updates

- [ ] 3.1 Update all `_read_active_file()` and `_read_current_state()` helpers in test_workflow.py to use `active/<run_id>/run.json` paths
- [ ] 3.2 Update all `_write_current_state()` and `_make_active_*_run()` helpers to create directories and write `run.json` inside
- [ ] 3.3 Update all inline `active/<run_id>.json` path references in test_workflow.py (lines 792, 2904, 2940, 2984, 3038, 3523-3524, 3616)
- [ ] 3.4 Update `_read_history()` to use `history/<run_id>/run.json` (new-style only)
- [ ] 3.5 Update test_init_foundations.py to verify directory structure includes `runs/history/` (no change needed but verify)
- [ ] 3.6 Update test_wrapper_contracts.py path assertions (lines 813, 818, 832, 1188, 1197)
- [ ] 3.7 Add new test: verify active run directory is created with `run.json` inside
- [ ] 3.8 Add new test: verify `done` moves entire directory from `active/` to `history/`
- [ ] 3.9 Add new test: verify `cancel-run` removes entire `active/<run_id>/` directory
- [ ] 3.10 Add new test: verify `_list_active_runs()` discovers run directories
- [ ] 3.11 Add new test: verify legacy migration moves `handoffs/` and `logs/` into run directory
- [ ] 3.12 Add new test: verify governance_check reads from new-style `history/<run_id>/run.json`

## 4. Verification

- [ ] 4.1 Run full test suite: `python3 -m pytest tests/test_workflow.py tests/test_init_foundations.py tests/test_wrapper_contracts.py -v`
- [ ] 4.2 Run full test suite with all tests: `python3 -m pytest tests/ -v`
- [ ] 4.3 Verify existing active run is handled (migrate `active/2026-06-29-run-artifacts-unify.json` to `active/2026-06-29-run-artifacts-unify/run.json`)
- [ ] 4.4 Verify agent definitions still reference correct paths (no changes needed)

## 5. Template Sync

- [ ] 5.1 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` to sync workflow.py changes to bootstrap templates
- [ ] 5.2 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` to verify no drift
- [ ] 5.3 Distribute agent definitions: `python3 scripts/install_agents.py --target ./.opencode/agents --force` and other targets
