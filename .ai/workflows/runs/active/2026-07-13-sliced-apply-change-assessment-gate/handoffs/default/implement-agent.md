# Handoff: implement-agent (Attempt 5 — Sliced Apply-Change Phase Completion Gate)

## Metadata

- **run_id**: 2026-07-13-sliced-apply-change-assessment-gate
- **slice_id**: default
- **phase**: apply_change
- **flow_type**: lightweight-flow
- **timestamp**: 2026-07-13T13:35:00Z
- **base_branch**: main
- **parent_ref**: e1d034e

## Objective

Fix the remaining blocking issue from review-agent: `cmd_complete_phase` does not block when implementation state is missing for active apply runs. The aggregate review gate was only enforced when `state.get("implementation") is not None`, allowing active apply runs with missing implementation to bypass the gate entirely and fall through to ordinary evidence validation.

## Work Completed

### Root Cause

`cmd_complete_phase` (line 531 of lifecycle.py) had:

```python
if current == "apply_change" and state.get("implementation") is not None:
```

When `implementation` was `None` on an active apply run, the entire slicing gate was skipped. The code fell through to evidence key validation, violating:

- **Spec Invariant 1**: An active running apply run always has persisted valid implementation state.
- **Spec Invariant 2**: Missing active implementation state always blocks apply execution.
- **Spec Decision 9**: Historical compatibility cannot be used by active apply phase completion gates.

### Fix Applied

Changed the gate in `cmd_complete_phase` to always block on missing or incomplete slicing state for `apply_change`:

1. **Missing implementation**: Blocks with error `"Active apply run has no persisted implementation slicing state"`.
2. **Pending/blocked assessment**: Blocks with error pointing to incomplete `slicing_assessment` status and remediation via `slice-init`.
3. **Aggregate review not passed**: Blocks as before with the existing aggregate review error.

### TDD Red/Green Loop

All 4 new tests witnessed RED (3 failures, 1 pass from existing behavior overlap) before the fix, and all 4 passed GREEN after.

## Files Changed

| File | Status | Reason |
|------|--------|--------|
| `.ai/workflows/scripts/workflow_runtime/lifecycle.py` | modified | Canonical: expanded slicing assessment gate in `cmd_complete_phase` |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/lifecycle.py` | modified | Template sync (canonical → template) |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/lifecycle.py` | modified | Distributed copy sync |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/lifecycle.py` | modified | Distributed copy sync |
| `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/lifecycle.py` | modified | Distributed copy sync |
| `tests/test_workflow.py` | modified | 4 new tests + fix for 1 existing test requiring implementation |

## Verification Summary

### Focused Tests (all PASS)

```
python3 -m pytest tests/test_workflow.py -k "missing_slicing_assessment or pending_slicing_assessment or blocked_slicing_assessment or valid_implementation_and_aggregate_passed" -v
```

| Test | Result |
|------|--------|
| `test_complete_phase_blocks_with_missing_slicing_assessment` | PASS |
| `test_complete_phase_blocks_with_pending_slicing_assessment` | PASS |
| `test_complete_phase_blocks_with_blocked_slicing_assessment` | PASS |
| `test_complete_phase_succeeds_with_valid_implementation_and_aggregate_passed` | PASS |

### Full Regression

```
python3 -m pytest tests/test_workflow.py -v
461 passed, 25 subtests passed

python3 -m pytest tests/test_wrapper_contracts.py tests/test_workflow_modules.py -v
319 passed, 2 subtests passed
```

One existing test (`TestRoadmapHookFiltering::test_spec_change_run_does_not_enqueue_roadmap_hooks_on_apply_change`) was updated to include a minimal valid implementation state, since `complete-phase` on apply_change now requires it.

## Issues

None. The fix was surgical, affecting only the gate condition in `cmd_complete_phase` and one test that set up apply_change state without implementation.

## Learnings

- The `normalize_implementation_state` helper provides backward-compatible defaults for legacy/terminal runs, but active dispatch paths must use `active_apply_slicing_errors` or check the raw `state["implementation"]` directly.
- The original gate condition (`and state.get("implementation") is not None`) was designed with the assumption that `normalize_implementation_state` would paper over missing state, but this normalization is explicitly documented as "read-only compatibility for historical/terminal runs only."

## Suggestions

- Consider adding a centralized "apply_change phase completion gate" helper that enforces all three prerequisites (implementation present, assessment completed, aggregate review passed) in one callable, shared between `cmd_complete_phase`, `cmd_advance`, and any future completion paths.
- The test suite has multiple `_make_apply_run` helpers across different test classes — consider a shared test fixture builder to reduce duplication.
