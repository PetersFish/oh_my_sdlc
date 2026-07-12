# Implement Agent Handoff — workflow-finalization-repair

## Metadata

- **workflow_run_id**: 2026-07-12-workflow-finalization-repair
- **phase**: apply_change
- **slice_id**: default
- **flow_type**: lightweight-flow
- **execution_mode**: main_checkout
- **change_id**: workflow-finalization-repair
- **agent**: implement-agent
- **status**: success
- **primary_design_path**: docs/superpowers/plans/2026-07-12-workflow-finalization-repair.md
- **base_branch**: main
- **parent_ref**: a4d77be
- **worktree_path**: /Users/yuping/Documents/workspace/oh_my_skills

## Objective

Fix two workflow finalization defects:

1. Terminal movement refused to move runs to history when finish-agent evidence was recorded under `agent_results.default` while terminal validation expected it under `context.change_id`.
2. `workflow.py final-commit` committed history artifacts but left deleted `.ai/workflows/runs/active/<run_id>/...` files dirty, because the final-commit allowlist did not include target active-run deletion paths.

## Work Completed

### Task 1: Terminal Evidence Default-Slice Regression (TDD red→green)

- Added `test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice` in `TestTerminalEvidenceValidation`.
- Verified RED: test failed with `missing_finish_agent_evidence` for slice `terminal-default-slice`.
- Replaced single-slice resolution in `_missing_terminal_finish_agent_evidence()` with candidate-list resolution:
  - When `evidence.agent_phase.slice_id` is present, only that exact slice is checked (preserves explicit-slice strictness).
  - When no dispatch slice is present, candidates are `["default", context.change_id]` (deduped), so unsliced lifecycle runs that recorded finish-agent under `default` can complete terminal movement.
  - Blocker payload now includes `candidate_slice_ids` for diagnostics.
- Verified GREEN: all 8 `TestTerminalEvidenceValidation` tests pass, including the existing strict unrelated-slice and relevant-slice tests.

### Task 2: Final Commit Active Deletion Regression (TDD red→green)

- Added `_make_tracked_active_run_files` helper in `TestFinalCommit`.
- Added `test_final_commit_commits_target_active_run_deletions` — baseline-commits an active run, removes it, writes a history run, runs `final-commit`, asserts active deletions and history additions are committed and git status is clean for the run paths.
- Added `test_final_commit_does_not_commit_target_active_run_non_deletions` — a dirty untracked active file must remain in `residual_dirty_paths` and not be committed.
- Verified RED: deletion test failed (active deletion paths not in `staged_paths`); safety test passed pre-implementation as expected.
- Implemented status-aware classification in `governance.py`:
  - Added `_is_delete_status(status_code)` helper.
  - Added `_classify_final_commit_entries(entries, run_id)` that allowlists prefixes plus deletion entries under `.ai/workflows/runs/active/<run_id>/`.
  - Retained `_classify_final_commit_paths(dirty_paths, run_id)` path-only (does not allow active-run cleanup, documented as retained for existing callers/tests).
  - Updated `cmd_final_commit()` step 2-3 to use status-aware classification.
  - Updated step 6 staged-paths filter from prefix matching to membership in `allowed_dirty`, so pre-existing staged files outside the allowlist (including active non-deletion files) are excluded while active deletion paths are included.
- Verified GREEN: all 15 `TestFinalCommit` tests pass, including the pre-staged-unrelated-file safety test.

### Task 3: Sync Runtime Templates And Distributed Copies

- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` synced live runtime `state.py` and `governance.py` to canonical templates.
- `--distribute` updated `.opencode/`, `.claude/`, `.cursor/` distributed copies.
- `--check` and `--check-distributed` both passed with no drift.
- `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` passed.

### Task 4: Final Verification

- Focused: `tests/test_workflow.py::TestTerminalEvidenceValidation tests/test_workflow.py::TestFinalCommit` — 23 passed.
- Full workflow file: `tests/test_workflow.py` — 325 passed, 25 subtests passed.
- Full regression: `tests/` — 1204 passed, 49 subtests passed.
- Derived artifacts check: PASS.
- CLI smoke `workflow.py --help`: exits 0 and lists `final-commit`.
- `scripts/check_plan_checkboxes.py` on the plan: ok, all checkboxes complete.
- Commit steps skipped per plan instruction (outer workflow owns commits); this is main_checkout, not a branch.

## Files/Artifacts Changed

| Path | Status | Reason |
|---|---|---|
| `.ai/workflows/scripts/workflow_runtime/state.py` | modified | candidate-list terminal evidence resolution |
| `.ai/workflows/scripts/workflow_runtime/governance.py` | modified | status-aware final-commit classification + staging |
| `tests/test_workflow.py` | modified | new regression tests + helper |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py` | modified | canonical template sync from live runtime |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py` | modified | canonical template sync from live runtime |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py` | modified | distribution |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py` | modified | distribution |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py` | modified | distribution |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py` | modified | distribution |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py` | modified | distribution |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/governance.py` | modified | distribution |
| `docs/superpowers/plans/2026-07-12-workflow-finalization-repair.md` | modified | plan checkboxes synced |

### Out-of-scope dirty paths (not produced by this implementation)

- `.ai/workflows/runs/current.json` — pointer set by the outer SDLC orchestrator run `2026-07-12-workflow-finalization-repair`.
- `.ai/workflows/runs/active/2026-07-12-workflow-finalization-repair/` — the orchestrator's own active run directory.
- `.ai/workflows/runs/active/.DS_Store` — gitignored, macOS filesystem metadata.

These are orchestrator-owned runtime state, not test churn. Tests use temporary directories and leave no repository artifacts.

## Commands Run

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation::test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice -v` | RED: fail (expected) |
| `python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation -v` | pass (8/8) |
| `python3 -m pytest tests/test_workflow.py::TestFinalCommit::test_final_commit_commits_target_active_run_deletions tests/test_workflow.py::TestFinalCommit::test_final_commit_does_not_commit_target_active_run_non_deletions -v` | RED: deletion fail, safety pass (expected pre-implementation) |
| `python3 -m pytest tests/test_workflow.py::TestFinalCommit -v` | pass (15/15) |
| `python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation tests/test_workflow.py::TestFinalCommit -v` | pass (23/23) |
| `python3 -m pytest tests/test_workflow.py -v` | pass (325 tests, 25 subtests) |
| `python3 -m pytest tests/ -v` | pass (1204 tests, 49 subtests) |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` | SYNCED |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute` | DISTRIBUTED |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` | OK |
| `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed` | OK |
| `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git` | OK |
| `python3 .ai/workflows/scripts/workflow.py --help` | exits 0, lists final-commit |
| `python3 scripts/check_plan_checkboxes.py docs/superpowers/plans/2026-07-12-workflow-finalization-repair.md` | ok, all checkboxes complete |

## Evidence Summary

- tasks_complete: true
- tdd_passed: true
- All focused tests green; full regression green (1204 passed, 0 failed).
- verification_summary.status: pass.

## Issues

None blocking. One observation: the git status shows the orchestrator's own active run directory and current.json pointer as dirty. These belong to the outer workflow run that dispatched this implement-agent and must not be cleaned by the implementation.

## Learnings

- The existing `_classify_final_commit_paths` path-only classifier is retained because it is a pure path function and existing callers/tests use it; active-run deletion handling requires status awareness, which lives in the new `_classify_final_commit_entries` companion.
- Updating the staged-path filter in step 6 from prefix matching to membership-in-`allowed_dirty` was required because the prefix list intentionally excludes active-run paths; a membership check against the status-aware allowlist preserves the no-`git add -A` guarantee and excludes pre-existing staged unrelated files.
- Terminal evidence strictness is preserved because explicit dispatch slice (`evidence.agent_phase.slice_id`) short-circuits to a single-candidate list; the candidate list only broadens for genuinely unsliced runs.

## Suggestions

- Consider adding the orchestrator's active run directory to a documented allowlist in the finish-agent's producer-owned cleanup notes, so future finish-agents do not mistake their own run state for implementation churn.
- Consider adding a `candidate_slice_ids` field to the terminal blocker schema documentation so downstream consumers know it is available.

## Risks/Follow-Ups

- None. Both defects have regression tests; existing strict-slice and pre-staged-unrelated-file invariants remain green.

## Assumptions

- Commits are owned by the outer workflow; local commit steps in the plan were intentionally skipped per the plan's explicit instruction.
- Distributed template drift is the canonical source of truth; the aggregate derived artifacts check confirms parity.

## Raw Logs

Raw output stored inline in this handoff's Commands Run section. The full pytest output for `tests/ -v` was truncated by the tool runner and saved by the environment to the tool output cache; no separate raw log file was written because the run was fully green and the summary lines are captured above.