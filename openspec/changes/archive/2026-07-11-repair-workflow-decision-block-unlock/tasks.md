## 1. Behavioral Regression Tests

- [x] 1.1 Add `test_corrected_valid_branch_finish_decision_clears_missing_decision_block` in `tests/test_workflow.py`: create a feature-branch/worktree run, persist the runtime-owned missing-decision block, record an allowed decision, and assert the saved state becomes `running` with `block is None`; before implementation it must fail because `record-context` leaves `status: blocked` and the block unchanged.
- [x] 1.2 Extend the same test to invoke `before-dispatch --agent finish-agent --phase archive_change` and assert `status: dispatched` without `run_is_blocked`; before implementation it must fail at the stale blocked-state guard.
- [x] 1.3 Add `test_corrected_valid_branch_finish_decision_clears_invalid_decision_block`: replace an invalid recorded decision with each representative allowed value and assert state normalization plus successful guarded dispatch; before implementation it must remain blocked.
- [x] 1.4 Add `test_invalid_branch_finish_decision_correction_preserves_block`: record another invalid value and assert the original blocked status and decision block remain; this protects the no-silent-default contract.
- [x] 1.5 Add `test_valid_branch_finish_decision_preserves_unrelated_block`: record an allowed decision while a worker/hook/domain block is active and assert the context changes but the unrelated block is byte-for-byte preserved.
- [x] 1.6 Add `test_branch_finish_decision_does_not_unblock_when_gate_not_required`: use main-checkout context without a feature branch and assert an unrelated block remains after recording a decision.
- [x] 1.7 Run the focused red test selection before implementation: `python3 -m pytest tests/test_workflow.py -v -k "corrected_valid_branch_finish_decision or invalid_branch_finish_decision_correction or valid_branch_finish_decision_preserves_unrelated_block or branch_finish_decision_does_not_unblock"`; confirm the positive recovery cases fail for stale block state while preservation cases establish the safety baseline.

## 2. Minimal State Reconciliation

- [x] 2.1 Add a focused helper in `.ai/workflows/scripts/workflow.py` that determines whether the tentative context validly resolves the runtime-owned branch-decision block, using `_resolve_branch_finish_decision` and structured block type/action metadata rather than broad message matching.
- [x] 2.2 Update `cmd_record_context` so a qualifying valid `branch_finish_decision` write atomically sets `status: running` and `block: None` before the existing save, while all non-qualifying writes preserve state.
- [x] 2.3 Run the focused test selection from task 1.7 and make each test-implementation pair pass before broadening verification.
- [x] 2.4 Run all branch-finish gate regressions: `python3 -m pytest tests/test_workflow.py -v -k "branch_finish_decision or branch_decision"`.

## 3. Full Verification And Governed Sync

- [x] 3.1 Run the workflow runtime suite: `python3 -m pytest tests/test_workflow.py -v`.
- [x] 3.2 Synchronize the live workflow runtime to the canonical bootstrap template and project-level derived copies: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .` followed by `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute`.
- [x] 3.3 Verify no workflow-template drift remains: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` and `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed`.
- [x] 3.4 Run the incremental repository derived-artifact check: `python3 scripts/sync_derived_artifacts.py --check --changed-files-from-git`.
- [x] 3.5 Re-run `python3 -m pytest tests/test_workflow.py -v` against synchronized artifacts and inspect `git diff --check` plus the final diff to confirm changes are limited to the runtime, its governed copies, tests, and this OpenSpec change.

## 4. EvalOps Assessment

- [x] 4.1 Record EvalOps as `not_required` for this change because all acceptance behavior is deterministic CLI/state-machine behavior; no AI behavior target, semantic grader, or durable `.ai/evals/` regression case is applicable.
