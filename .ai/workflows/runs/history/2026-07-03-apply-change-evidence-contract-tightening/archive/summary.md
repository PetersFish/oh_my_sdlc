# Archive Summary

## Metadata
- **Run ID**: 2026-07-03-apply-change-evidence-contract-tightening
- **Flow Type**: lightweight-flow
- **Subject Type**: spec_change
- **Subject ID**: apply-change-evidence-contract-tightening
- **Phase**: archive_change
- **Archived At**: 2026-07-04T13:22:53Z

## Change Summary

### Objective
Tighten the `apply_change` evidence contract so the implement -> test -> review chain can complete deterministically without manual evidence patching or false blocks.

### Problem Solved
The prior workflow could reach a state where implementation and verification were effectively complete, but the workflow run could not complete the phase because agent result contracts and workflow phase evidence requirements did not align. This caused repeated loops through implement/test/review even when the underlying code changes were already correct.

### Key Changes Made

1. **Agent Prompt Contracts Tightened**
   - `review-agent.md`: Success contract now includes `apply_change` phase evidence keys
   - `implement-agent.md`: Normal handoff to verification is success, not blocked
   - `dev-orchestrator.md`: Review dispatch includes phase evidence requirements

2. **Runtime Evidence Aggregation**
   - `workflow.py`: `after-dispatch` validates `apply_change` using aggregated evidence view
   - Evidence merges: current agent + existing state + prior successful agent results
   - Resolved evidence promoted back into state for runtime source-of-truth

3. **Verification Basis Guard**
   - `eval_passed_or_human_decision_recorded` requires prior successful `test-agent` evidence
   - Guard reads `state.evidence.agent_results[slice_id]["test-agent"]` directly

4. **Handoff History Preservation**
   - Dual-write model: latest handoff + timestamped history copy
   - History directory: `handoffs/<slice>/history/`
   - Preserves attempt-by-attempt traceability

5. **Block-State Consistency**
   - `after-dispatch` persists worker-failure blocks consistently
   - Block state matches transition output messaging

6. **Template Sync/Distribution**
   - Canonical workflow template synced to distributed copies
   - All distributed copies (`.opencode/`, `.claude/`, `.cursor/`) verified in sync

## Evidence of Completion

### Agent Results
| Agent | Status | Key Evidence |
|-------|--------|--------------|
| implement-agent | success | tasks_complete, tdd_passed, focused_tests pass |
| test-agent | success | verification_passed, regression_passed, 1007 tests pass |
| review-agent | success | review_decision: accepted, all blockers resolved |

### Test Results
- Focused workflow tests: 32 passed
- Wrapper contract tests: 437 passed, 28 subtests
- Full regression: 1007 passed, 50 subtests
- Sync/distribution drift tests: all passed

### Verification Checks
- `sync_templates.py --check`: OK (canonical ↔ live in sync)
- `sync_templates.py --check-distributed`: OK (all distributed copies match canonical)

## Design Artifacts
- **Plan**: `docs/superpowers/plans/2026-07-03-apply-change-evidence-contract-tightening.md`
- **Design Spec**: `docs/superpowers/specs/2026-07-03-apply-change-evidence-contract-tightening-design.md`

## Files Modified
- `agents/dev-orchestrator.md` (canonical + distributed)
- `agents/implement-agent.md` (canonical + distributed)
- `agents/review-agent.md` (canonical + distributed)
- `.ai/workflows/scripts/workflow.py` (live runtime)
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (canonical template)
- `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (distributed)
- `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (distributed)
- `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (distributed)
- `tests/test_workflow.py` (behavioral tests)
- `tests/test_wrapper_contracts.py` (prompt contract tests)

## Learnings
1. **Distribution drift is subtle**: Canonical was correct; only distributed copies were stale. `--check-distributed` is the correct gate.
2. **Aggregated evidence is essential**: Multi-worker phases need runtime-level evidence aggregation, not per-worker duplication.
3. **Verification basis must be grounded**: `eval_passed_or_human_decision_recorded` should read from actual test-agent success, not self-report.
4. **Handoff history needs durability**: Overwriting latest handoff loses attempt history; dual-write preserves traceability.

## Suggestions for Future Work
- Add `sync_templates.py --check-distributed` to CI to catch drift before test-agent verification
- Consider a single review-agent assertion helper for "canonical == live == distributed" check
- Generalize aggregated evidence model to other multi-worker phases if needed

## Roadmap Status
- No roadmap item linked (`no_linked_item` resolution)
- This change was a workflow infrastructure improvement, not a product feature

## Archive Status
- [x] All tasks complete
- [x] TDD passed
- [x] Eval passed / human decision recorded
- [x] Review accepted
- [x] Template sync verified
- [x] Memory sync pending
