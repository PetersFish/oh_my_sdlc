## 1. Core Run State Management

- [x] 1.1 Add `_list_active_runs(root)` helper that scans `active/` directory and returns list of (run_id, dict) tuples
- [x] 1.2 Modify `load_run_state(root)` to read pointer from `current.json`, then load pointed `active/<run_id>.json`; return None if pointer is empty or file missing
- [x] 1.3 Add `load_run_state(root, run_id)` overload for explicit batch loading of a specific `active/<run_id>.json`
- [x] 1.4 Modify `save_run_state(root, state)` to write `active/<run_id>.json` AND update `current.json` pointer to `{"run_id": "<run_id>"}`

## 2. Command Updates

- [x] 2.1 Update `cmd_start`: create `active/<run_id>.json` + set pointer; reject if same `subject_id` already has an active run (conflict with exit code 1)
- [x] 2.2 Update `cmd_resume`: require `--subject-type` + `--subject-id`; when missing, report an error with active run summaries; when present, locate matching active run by subject, set pointer, recalculate readiness
- [x] 2.3 Update `cmd_done`: after writing history and marking done, remove `active/<run_id>.json` and clear pointer to `{}`
- [x] 2.4 Update `cmd_advance` (done path): after writing history in the terminal path, remove `active/<run_id>.json` and clear pointer to `{}`
- [x] 2.5 Update `cmd_status`: when pointer is valid, show pointed run full state; when pointer is empty or stale, report that state and list active run summaries; when subject given, show matching run full state
- [x] 2.6 Update `cmd_preflight` / `_evaluate_subject_run_context`: search `active/` by subject, set pointer before evaluating policy

## 3. Governance Update

- [x] 3.1 Update `cmd_governance_check`: scan ALL `active/*.json` files for `pending_hooks` (not just the pointed run); continue using `history/` for dangling archive evidence

## 4. Tests

- [x] 4.1 Add test: two independent `cmd_start` calls with different `subject_id` each create their own `active/<run_id>.json`
- [x] 4.2 Add test: `cmd_start` with duplicate `subject_id` reports conflict
- [x] 4.3 Add test: `cmd_resume --subject-type openspec_change --subject-id <id>` finds correct run and sets pointer
- [x] 4.4 Add test: `cmd_status` without subject lists all active runs
- [x] 4.5 Add test: `cmd_done` writes history, removes from `active/`, clears pointer
- [x] 4.6 Add test: `governance-check` detects `pending_hooks` from ANY active run
- [x] 4.7 Add test: `cmd_preflight` searches `active/` by subject and sets pointer
- [x] 4.8 Run full test suite: `python3 -m pytest tests/test_workflow.py -v`

## 5. Template Sync

- [x] 5.1 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` to sync canonical templates
- [x] 5.2 Run `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` to verify no drift
