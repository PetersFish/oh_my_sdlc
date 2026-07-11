# Metadata

- Agent: implement-agent
- Workflow run: `2026-07-11-RM-ORCH-009`
- Slice: `default`
- Phase: `apply_change`
- Flow type: `spec-flow`
- Status: success
- Change: `modularize-workflow-runtime`
- Dispatch: repair remaining review-agent blocker (extra-file removal in sync/distribute)

# Objective

Fix the remaining review-agent blocker: `sync_files()` and `distribute_to_all()` only copied GOVERNED entries and never removed extra `.py` files in canonical or distributed `workflow_runtime` trees. Read-only drift checks detected extras but mutating repair paths could not restore parity, violating the spec scenario "Complete synchronization restores parity" and task 5.3.

# Work Completed

- Added two RED repair round-trip tests in `tests/test_sync_templates.py`:
  - `test_sync_removes_extra_runtime_module_in_canonical`: injects an extra `.py` in canonical templates, runs `sync` (live -> canonical), asserts the extra is removed and a subsequent `--check` exits 0.
  - `test_distribute_removes_extra_runtime_module_in_distributed`: injects an extra `.py` in a distributed copy, runs `--distribute`, asserts the extra is removed in all distributed copies and a subsequent `--check-distributed` exits 0.
- Verified both tests fail before implementation (sync/distribute left extras in place).
- Implemented `_remove_extra_runtime_files()` helper in `sync_templates.py` that deletes `.py` files in a `workflow_runtime` directory not in `_GOVERNED_RUNTIME_FILES`.
- Wired the helper into `sync_files()` (removes extras in canonical `workflow_runtime`) and `distribute_to_all()` (removes extras in each distributed `workflow_runtime`).
- Ran `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git` to propagate the canonical `sync_templates.py` change to `.opencode`, `.claude`, and `.cursor` copies (test harness executes the `.opencode` copy).
- Verified GREEN: both new focused tests pass.
- Verified live repo parity: `--check` and `--check-distributed` both exit 0.
- Verified derived-artifact sync: `--check --changed-files-from-git` exits 0.
- Full regression: `python3 -m pytest tests/ -v` -> 1201 passed, 49 subtests passed.

# Files/Artifacts Changed

Behavioral change (this dispatch):
- `tests/test_sync_templates.py` — added two repair round-trip tests (extra-file removal).
- `skills/sdlc-project-bootstrap/scripts/sync_templates.py` — added `_remove_extra_runtime_files()` helper; wired removal into `sync_files()` and `distribute_to_all()`.
- `.opencode/skills/sdlc-project-bootstrap/scripts/sync_templates.py` — distributed copy synced from canonical.
- `.claude/skills/sdlc-project-bootstrap/scripts/sync_templates.py` — distributed copy synced from canonical.
- `.cursor/skills/sdlc-project-bootstrap/scripts/sync_templates.py` — distributed copy synced from canonical.
- Distributed `.skill-install.json` files refreshed by the derived-artifact sync full mode (sync-rule change triggered full mode).

Pre-existing from prior dispatches in the same change (carried in worktree, not touched this dispatch):
- `.ai/workflows/scripts/workflow_runtime/` (new package)
- `.ai/workflows/scripts/workflow.py` (reduced to facade)
- `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/` and distributed copies
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` and distributed copies
- `skills/sdlc-project-bootstrap/scripts/init_foundations.py` and distributed copies
- `tests/test_workflow_modules.py`, `tests/test_init_foundations.py`
- `openspec/changes/modularize-workflow-runtime/` (proposal, design, tasks, spec)
- Workflow run state under `.ai/workflows/runs/active/2026-07-11-RM-ORCH-009/`

# Commands Run

- `python3 -m pytest tests/test_sync_templates.py::TestSyncTemplatesDistributed::test_sync_removes_extra_runtime_module_in_canonical tests/test_sync_templates.py::TestSyncTemplatesDistributed::test_distribute_removes_extra_runtime_module_in_distributed -v` (RED: 2 failed; GREEN: 2 passed)
- `python3 scripts/sync_derived_artifacts.py --fix --changed-files-from-git` (OK: all 80 fix suites in sync)
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` (OK)
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed` (OK)
- `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` (OK: all 6 check suites in sync)
- `python3 -m pytest tests/ -v` (1201 passed, 49 subtests passed)

# Evidence Summary

- tasks_complete: true
- tdd_passed: true (RED observed for both new tests before implementation; GREEN observed after)
- focused_tests:
  - `test_sync_removes_extra_runtime_module_in_canonical`: pass
  - `test_distribute_removes_extra_runtime_module_in_distributed`: pass
- full_regression: pass (1201 passed, 0 failed)
- live_drift_check: pass
- distributed_drift_check: pass
- derived_artifact_sync_check: pass
- verification_passed: true

# Blockers

None.

# Assumptions

- Execution mode is `main_checkout` per `runtime_context`; no worktree path is reported.
- The canonical source for `sync_templates.py` is `skills/sdlc-project-bootstrap/scripts/sync_templates.py`; the test harness executes the `.opencode` distributed copy, so the derived-artifact sync must propagate the change before GREEN verification.
- Repair is narrowly scoped to `.py` files in `workflow_runtime/` directories only; non-`.py` files and files outside that subtree are untouched.

# Risks/Follow-Ups

- The `_remove_extra_runtime_files()` helper only removes `.py` extras. If future governed content includes non-`.py` files under `workflow_runtime/`, the detection and removal sets should be generalized.
- The full derived-artifact sync ran in full mode because `sync_templates.py` is a sync-rule file; this refreshed all `.skill-install.json` files, which is expected churn for this change.

# Issues

None during this dispatch.

# Learnings

- When a test harness executes a distributed copy of a script, the canonical fix must be propagated (via derived-artifact sync) before the focused test can observe GREEN. RED is observable against the stale distributed copy because the behavior is unchanged; GREEN requires the fix to reach the copy under test.
- Detection and repair are separate contracts: a green read-only drift check does not prove the mutating sync command can restore parity. Pair every drift scenario (missing, stale, extra) with a repair round trip.

# Suggestions

- Consider adding a meta-test that asserts the distributed `sync_templates.py` hash equals the canonical hash, so canonical-fix-without-distribution is caught by the test suite itself rather than only by the derived-artifact sync gate.
- Consider generalizing the extra-file detection/removal to non-`.py` files if the governed runtime inventory grows.

# Raw Logs

- `python3 -m pytest tests/ -v` -> 1201 passed, 49 subtests passed in 47.68s (full output captured by tool runner)