# Review-Agent Handoff

## Metadata
- **Agent**: review-agent
- **Phase**: apply_change
- **Slice**: default
- **Run ID**: 2026-07-03-apply-change-evidence-contract-tightening
- **Flow**: lightweight-flow

## Objective
Code review and completion gating (retry round) after test-agent verification passed, confirming the two prior review blockers are genuinely fixed in code and that no contract drift, missing sync/distribution, or superficial tests remain.

## Review Summary

### Prior Blocker Verification
Both prior blockers were verified against the live runtime AND canonical template source (not just test presence):

1. **apply_change handoff history preserving attempt history (incl. failed/blocked)** — FIXED
   - `.ai/workflows/scripts/workflow.py:1806` defines `_write_handoff_history_copy(root, handoff_path)`.
   - `cmd_after_dispatch` at `.ai/workflows/scripts/workflow.py:1898-1906` invokes it for `phase == "apply_change"` whenever `artifacts.handoff_path` points at an existing latest handoff, regardless of worker success/blocked/failed status.
   - Canonical template `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` has the same helper and call site at the same line numbers.
   - Behavioral tests `TestApplyChangeHandoffHistory` exercise failed-implement, failed-test, AND blocked-review paths; each invokes `after-dispatch` and asserts the timestamped history copy exists in `history/`. These are real filesystem round-trip tests, not string-presence.

2. **eval_passed_or_human_decision_recorded verification-basis guard** — FIXED
   - `.ai/workflows/scripts/workflow.py:1961-1977` requires prior successful `test-agent` evidence (`status == "success"` AND `verification_passed` OR `regression_passed`) before allowing `eval_passed_or_human_decision_recorded` to stand.
   - Guard is not self-reported by review-agent: it reads `state.evidence.agent_results[slice_id]["test-agent"]` directly.
   - Canonical template mirrors the guard at the same line numbers.
   - Behavioral tests `TestApplyChangeVerificationBasis` cover (a) no prior test-agent → blocks, (b) failed prior test-agent → still blocks, (c) successful prior test-agent → accepts (in `TestDispatchHooks::test_after_dispatch_review_acceptance_can_finalize_eval_key_from_test_agent_success`).

### Contract Drift / Sync / Distribution
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check` → OK: all governed files in sync with canonical.
- `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed` → OK: all distributed copies match canonical.
- Distributed workflow template copies (`.opencode/`, `.claude/`, `.cursor/`) are in sync — the retry-round implement-agent drift fix worked.

### Test Quality (no superficial acceptance)
- Focused: `python3 -m pytest tests/test_workflow.py -k "TestApplyChangeHandoffHistory or TestApplyChangeVerificationBasis or after_dispatch" -v` → 32 passed.
- Pair: `python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py -v` → 437 passed, 28 subtests passed.
- Full regression: `python3 -m pytest tests/` → 1007 passed.
- New blocker tests invoke `after-dispatch` and assert observable state/filesystem outcomes, satisfying the behavioral-test-design discipline (no string-presence proxies for executable behavior).

### Scope Control
The retry-round implement-agent change was scoped to distributed workflow template copies only (no canonical code change). The earlier blocker fixes are intact in canonical + live runtime.

## Evidence Summary
- verification_passed: true (test-agent evidence, fresh re-run confirms)
- tdd_passed: true (drift fix only; canonical behavior unchanged)
- eval_passed_or_human_decision_recorded: true (test-agent verification succeeded and review accepts)
- review_complete: true
- review_decision: accepted
- tasks_complete: true
- criteria_satisfied: tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded

## Issues
None. Both prior blockers are resolved in code with behavioral test coverage. No contract drift, no missing distribution, no superficial tests.

## Learnings
- The retry-round blocker was a pure distribution drift artifact: canonical was already correct, only the 3 distributed copies were stale. `sync_templates.py --distribute` resolved it.
- Verifying both line-number parity (canonical ↔ live ↔ distributed) AND behavioral test coverage (not just test name presence) is what distinguishes "blocker fixed" from "blocker tests added."
- `--check-distributed` is the correct gate for catching this class of drift; `--check` only catches canonical ↔ live drift.

## Suggestions
- Add `sync_templates.py --check-distributed` to CI to catch distributed-copy drift before it blocks test-agent verification (also suggested by upstream agents — reinforcing).
- Consider a single review-agent assertion helper that checks "canonical == live == distributed" for the workflow template in one call, so future reviewers don't have to chain `--check` + `--check-distributed` manually.

## Final Acceptance
Review accepts the apply_change phase for slice `default`. All apply_change phase evidence keys are present, verification basis is grounded in prior test-agent success, and the phase contract is satisfied. The workflow runtime may proceed to `complete_phase`.