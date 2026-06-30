# Test Agent Handoff — run-artifacts-unify

## Metadata

- **Agent**: test-agent
- **Phase**: apply_change
- **Flow Type**: spec-flow
- **Change ID**: run-artifacts-unify
- **Run ID**: 2026-06-29-run-artifacts-unify
- **Slice ID**: default
- **Timestamp**: 2026-06-29T22:40:00

## Verification Summary

**Verdict: ✅ ALL CHECKS PASS**

| Check | Result | Detail |
|---|---|---|
| Focused Tests | ✅ 11/11 pass | All run-artifacts-unify TDD tests pass independently |
| Overfit Check | ✅ Pass | All 10 new tests verify real behavior, not implementation coincidences |
| Broader Regression | ✅ 310/310 pass | test_workflow (174), test_wrapper_contracts (131), test_init_foundations (5) |
| Edge Cases | ✅ Pass | Legacy migration, empty active/, advance-to-done, no dangling flat-json refs |
| TDD | ✅ Pass | All new behavior covered by focused tests with correct contracts |

## 1. Focused Test Rerun

```
python3 -m pytest tests/test_workflow.py -v -k "<run-artifacts patterns>"
```

All 11 tests pass:

| Test | Status |
|---|---|
| test_active_path_returns_run_json_in_directory | ✅ |
| test_save_run_state_creates_directory_with_run_json | ✅ |
| test_finalize_run_to_history_moves_entire_directory | ✅ |
| test_cmd_done_moves_entire_directory | ✅ |
| test_cancel_run_removes_entire_directory | ✅ |
| test_list_active_runs_from_directories | ✅ |
| test_governance_check_reads_history_dir | ✅ |
| test_legacy_migration_handoffs | ✅ |
| test_legacy_migration_logs | ✅ |
| test_legacy_migration_idempotent | ✅ |
| test_cancel_run_removes_active_file (existing test, updated) | ✅ |

## 2. Overfit Check

Applied the behavioral-test-design anti-overfit framework to all 10 new tests:

- **test_active_path_returns_run_json_in_directory**: Would fail if path returned flat `.json` → ✅ behavioral
- **test_save_run_state_creates_directory_with_run_json**: Checks directory existence, file existence, AND negative assertion on old flat path → ✅ behavioral (round-trip)
- **test_finalize_run_to_history_moves_entire_directory**: Checks handoff artifacts survive the move, not just run.json → ✅ behavioral
- **test_cmd_done_moves_entire_directory**: Integration test via CLI → ✅ behavioral
- **test_cancel_run_removes_entire_directory**: Creates handoff artifacts that would be left behind if only run.json were removed → ✅ behavioral
- **test_list_active_runs_from_directories**: Creates directory (not flat file), tests discovery → ✅ behavioral
- **test_governance_check_reads_history_dir**: Integration test that only creates directory format → tests new-format-only contract
- **test_legacy_migration_handoffs/logs**: Tests file movement AND legacy directory cleanup → ✅ behavioral
- **test_legacy_migration_idempotent**: Calls migration twice, verifies content intact → ✅ critical edge case

No test would pass under a broken implementation (e.g., directory created but run.json not written, files moved but legacy dir not cleaned, migration not idempotent).

## 3. Broader Regression

```
python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py tests/test_init_foundations.py -v
```

**310 passed, 15 subtests passed, 0 failures.** Full suite includes:
- `test_workflow.py`: 174 tests (all phases: start, status, advance, done, cancel, governance, dispatch hooks, preflight, ensure-run, roadmap promotion, OpenSpec ensure, EvalOps, memory sync)
- `test_wrapper_contracts.py`: 131 tests (result normalization, dispatch resolution, provider registry)
- `test_init_foundations.py`: 5 tests (directory creation, file copies, idempotency)

## 4. Edge Case Analysis

### 4.1 Legacy handoffs/logs migration
- ✅ `test_legacy_migration_handoffs`: Migrates `runs/handoffs/<id>/` → `active/<id>/handoffs/`
- ✅ `test_legacy_migration_logs`: Migrates `runs/logs/<id>/` → `active/<id>/logs/`
- ✅ `test_legacy_migration_idempotent`: Safe to run twice, `.migrated` sentinel prevents re-migration

### 4.2 Empty active/ directory
- ✅ `_list_active_runs()` checks `os.path.isdir(active_dir)` first → returns `[]`
- ✅ `_load_done_history_run_ids()` same guard → returns `set()`
- ✅ `cmd_governance_check()` same guard → no findings from empty history

### 4.3 Advancing through multiple phases
- ✅ `cmd_advance` non-terminal phases → `save_run_state()` creates directory if needed
- ✅ `cmd_advance` to `done` phase → `shutil.move(active_dir, history_dir)` atomically moves entire directory
- ✅ `cmd_done` → same `shutil.move` pattern

### 4.4 Dangling references to old flat `.json` path
- ✅ Canonical `workflow.py`: No remaining flat-path references (validated via grep)
- ✅ Test helpers: All 7 updated helpers use directory-based paths
- ⚠️ One vestigial pattern: `test_cancel_run_no_history_written` (line 2140) still has `os.path.basename(active_file).replace(".json", "")` — but is harmless because `basename()` now returns the directory name (which equals run_id), and `.replace(".json", "")` is a no-op
- ⚠️ Outdated comment line 2583: `"creates active/<run_id>.json"` → should say `"creates active/<run_id>/run.json"` (cosmetic)

### 4.5 Runtime contract integrity
- ✅ `save_run_state()` calls `_migrate_legacy_artifacts()` before writing
- ✅ `load_run_state()` calls `_migrate_legacy_artifacts()` before reading
- ✅ `cmd_cancel_run()` uses `shutil.rmtree()` on entire directory (not just `os.remove` on a file)
- ✅ `cmd_governance_check()` reads `history/<run_id>/run.json` only (new-style); no backward compat (per design D4 removal)

## 5. EvalOps

This change is a deterministic code/directory structure change. It does not involve AI behavior targets (skill routing, intent classification, etc.). The test suite (310 tests) provides sufficient behavioral coverage. No EvalOps regression capture is needed.

## Issues / Follow-Ups

### 5.1 Stale Distributed Skill Copies (follow-up, not blocker)
Distributed copies of `sdlc-project-bootstrap` under `.claude/skills/`, `.cursor/skills/`, and `.opencode/skills/` still contain the OLD flat `.json` path code. The canonical template and live code are correct. The implement-agent flagged this as Task 5.1 (template sync) and 5.2 (agent distribution). These are distribution follow-up tasks, not code bugs.

**Fix**: Run `meta-skill-lifecycle-governance` DISTRIBUTE action for the updated `sdlc-project-bootstrap` skill, plus `scripts/install_agents.py` for agent distribution.

### 5.2 Cosmetic Issues
- Line 2583 comment: `"creates active/<run_id>.json"` → should be `"creates active/<run_id>/run.json"`
- Line 2140: Vestigial `.replace(".json", "")` — harmless but could be cleaned up

## Verdict

All four verification checks pass. The implementation correctly unifies run artifacts under `<run_id>/` directories with `run.json` as canonical state. All path functions, save/load, finalize, advance/done, cancel, governance, and migration are verified through behavioral tests. The stale distributed copies are a distribution follow-up, not a code defect.

**Recommended next action**: `dispatch_review_agent`
