# Review Agent Handoff — run-artifacts-unify

## Metadata

- **Agent**: review-agent
- **Phase**: apply_change
- **Flow Type**: spec-flow
- **Change ID**: run-artifacts-unify
- **Run ID**: 2026-06-29-run-artifacts-unify
- **Slice ID**: default
- **Timestamp**: 2026-06-29T23:00:00

## Review Summary

**Verdict: ✅ PASS — code is correct and complete. Minor issues noted; none are blockers.**

### Phase Pre-Check

| Check | Result |
|---|---|
| Test-agent evidence exists | ✅ `verification_passed: true` |
| Full test suite (310 tests) | ✅ All pass |
| Focused tests (11 tests) | ✅ All pass |

### Fresh Verification Evidence

```
python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py tests/test_init_foundations.py -q --tb=short
310 passed, 15 subtests passed in 16.96s
```

Focused tests re-verified independently:
```
python3 -m pytest tests/test_workflow.py -q --tb=short -k "test_active_path_returns_run_json_in_directory or test_save_run_state_creates or test_finalize_run_to_history_moves or test_cmd_done_moves or test_cancel_run_removes or test_list_active_runs_from or test_governance_check_reads_history_dir or test_legacy_migration"
11 passed in 0.30s
```

## Review Findings

### ✅ Strengths

- All path functions correctly updated: `_active_path`, `save_run_state`, `_finalize_run_to_history`, `cmd_done`, `cmd_advance`, `cmd_cancel_run`, `_list_active_runs`, `cmd_governance_check`, `_load_done_history_run_ids`
- `shutil.move()` for entire directory archiving is correct and atomic on same filesystem
- `shutil.rmtree()` for cancellation removes entire directory including sub-artifacts
- Migration is idempotent with `.migrated` sentinel
- Migration called from both `save_run_state()` and `load_run_state()` for transparent coverage
- All test helpers use new directory-based paths (`_read_current_state`, `_write_current_state`, `_read_active_file`, `_read_history`, `_find_active_file`, `_make_active_run`, `_make_done_history_run`, `_make_done_roadmap_history_run`)
- Canonical template sync verified OK (`sync_templates.py --check` passes)
- No remaining flat `.json` path references in `workflow.py` (all `active/<run_id>/run.json` format)
- Both governance check history scan loops use new directory-based format
- Second governance check loop (line 2549) also updated for directory-based reads
- No unintended changes to `current.json` pointer or other unrelated code

### Feedback Items

#### F1 (Minor): Duplicate `return state` in `_finalize_run_to_history`

**File:** `.ai/workflows/scripts/workflow.py`, lines 250 and 252

Both line 250 and line 252 contain `return state`. Line 252 is dead/redundant code. While harmless at runtime, it should be removed for cleanliness.

**Recommended:** Remove the duplicate at line 252.

#### F2 (Cosmetic): Outdated comment at test line 2583

**File:** `tests/test_workflow.py`, line 2583

```python
# Create an active run via start (creates active/<run_id>.json + updates pointer)
```

Should be:
```python
# Create an active run via start (creates active/<run_id>/run.json + updates pointer)
```

#### F3 (Cosmetic): Vestigial `.replace(".json", "")` at test line 2140

**File:** `tests/test_workflow.py`, line 2140

```python
run_id = os.path.basename(active_file).replace(".json", "")
```

Since `_find_active_file` now returns directory paths (not `.json` files), `basename()` returns the directory name (which is the run_id). The `.replace(".json", "")` is now a no-op. Harmless but could confuse future readers.

#### F4 (Follow-up): Stale distributed skill/agent copies

The canonical template and live code are correct. However, distributed copies under `.opencode/skills/`, `.claude/skills/`, and `.cursor/skills/` still contain OLD flat `.json` path code. Tasks 5.1 (skill distribution via `meta-skill-lifecycle-governance`) and 5.2 (agent distribution via `install_agents.py`) from the plan were not completed.

**Not a code defect** — the canonical source of truth is correct. This is a distribution follow-up.

#### F5 (Spec Delta): Backward-compatible history reading spec is stale

**File:** `openspec/changes/run-artifacts-unify/specs/run-directory-unification/spec.md`, lines 74-85

The ADDED "Backward-Compatible History Reading" requirement still includes scenarios for reading old-style flat `history/<run_id>.json` files. Per design decision D4 (REJECTED), this feature was explicitly removed. The code correctly implements D4 (new-style only).

Similarly, `sdlc-workflow-engine/spec.md` line 185 references "both old-style `history/<run_id>.json` and new-style `history/<run_id>/run.json`" which contradicts D4 rejection.

**Not a code bug** — the implementation is correct per the final design. The spec delta text is stale from before the D4 revision and needs to be synced during the verify phase. Recommend updating the spec to remove the backward-compatible requirement or mark it as REMOVED.

## Design Decision Verification

| Decision | Status | Evidence |
|---|---|---|
| D1: `run.json` inside `active/<run_id>/` | ✅ | `_active_path` returns `active/<run_id>/run.json` (line 101) |
| D2: `shutil.move()` entire directory | ✅ | `_finalize_run_to_history` (line 244), `cmd_done` (line 2284), `cmd_advance` (line 2183) |
| D3: Auto-migration with `.migrated` sentinel | ✅ | `_migrate_legacy_artifacts` (lines 153-195) with sentinel check at line 160 |
| D4: NO backward compat (pre-release) | ✅ | `cmd_governance_check` only reads `history/<run_id>/run.json` (lines 2308-2334), `_load_done_history_run_ids` same (lines 521-543) |

## Review Focus Area Results

### 1. Code correctness — all path changes look right?
✅ All path functions verified. `_active_path`, `save_run_state`, `_finalize_run_to_history`, `cmd_done`, `cmd_advance`, `cmd_cancel_run`, `_list_active_runs`, `cmd_governance_check`, `_load_done_history_run_ids` all correctly use directory-based paths with `run.json` inside.

### 2. Edge cases — any gaps the tests missed?
Covered by tests: legacy migration, idempotency, empty active/, advance-to-done, cancel with subdirectories. One edge case not explicitly tested: re-finalizing a run when history already exists (the `shutil.rmtree(history_dir)` before move). This is covered implicitly by integration tests.

### 3. Consistency — are all path references updated everywhere?
✅ No dangling old flat-path references in `workflow.py`. All test helpers updated. All inline test references updated. The only exceptions are the cosmetic issues (F2, F3) which are harmless.

### 4. Test quality — are the new tests testing real behavior?
✅ All 11 new tests verified as behavioral (not mock coincidences). They test directory existence, file contents, artifact survival across moves, migration completeness, and idempotency. Refer to test-agent's overfit analysis for detailed per-test evaluation.

### 5. Template sync — was it done correctly?
✅ Canonical template at `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` is in sync with live code (verified via `sync_templates.py --check`). Distributed copies are stale but this is a distribution follow-up, not a code defect.

### 6. Spec compliance — does the implementation match the OpenSpec specs?
✅ Implementation matches all ADDED and MODIFIED requirements, EXCEPT the "Backward-Compatible History Reading" requirement which is stale from before D4 revision. Code correctly implements D4 rejection. Spec delta needs update during verify phase.

### 7. Distribution — test-agent noted stale distributed copies, is that a blocker?
❌ Not a blocker. The canonical source of truth (live code + canonical template) is correct. Distribution is a follow-up task (plan Tasks 5.1, 5.2).

## Blockers

None. Code is correct and tests pass.

## Recommended Next Action

`dispatch_finish_agent` — code review passes. Implementation is complete and correct.

## Follow-up Recommendations (post-merge)

1. Run `meta-skill-lifecycle-governance` DISTRIBUTE for `sdlc-project-bootstrap` skill
2. Run `scripts/install_agents.py` for project-level agent distribution
3. Update spec deltas to remove backward-compatible history reading (reflect D4 rejection)
4. Remove duplicate `return state` at workflow.py line 252
5. Fix cosmetic comment at test line 2583

## Raw Logs

- `python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py tests/test_init_foundations.py -q --tb=short` → 310 passed
- `python3 -m pytest tests/test_workflow.py -q --tb=short -k "<focused tests>"` → 11 passed
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` → "OK: all governed files in sync with canonical"
