## Metadata

- **Run ID**: 2026-07-13-sliced-apply-change-assessment-gate
- **Slice ID**: default
- **Agent**: implement-agent
- **Phase**: apply_change
- **Flow Type**: lightweight-flow
- **Status**: success
- **Attempt**: 3

## Objective

Fix one remaining blocking issue from review-agent: "Exact slice-id enforcement remains too permissive for active not_required states". Remove backward-compat omission path so ALL implement-agent dispatches require `--slice-id` (Spec Invariants 8 and 12).

## Work Completed

### dispatch.py — remove backward-compat path

In `cmd_before_dispatch`, replaced the 30-line backward-compat logic in the `elif canonical_agent == "implement-agent":` block (lines 584-626) with a 10-line unconditional blocker. The old logic treated `assessment_status == "not_required"` as legacy, allowing single-default dispatch without `--slice-id`. The new logic always requires `--slice-id` for implement-agent, with no exception.

### Template sync

Applied the same change to:
- `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` (template copy)
- `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` (Claude distributed copy)
- `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` (Cursor distributed copy)

### Tests (test_workflow.py)

Updated 8 tests:
1. `test_implement_dispatch_without_slice_id_allowed_for_single_default` — changed from asserting rc=0 (allowed) to asserting rc!=0 (rejected with `missing_slice_id`)
2. `test_legacy_not_required_single_default_allows_omit_slice_id` — same: now asserts rejection instead of acceptance
3. `test_non_legacy_default_slice_requires_slice_id_for_dispatch` — updated docstring (test logic unchanged, already expects rejection)
4. `test_before_dispatch_allows_implement_agent_from_worker_failed_next_allowed_alias` — added `slice_id="default"`
5. `test_before_dispatch_supports_dash_and_underscore_agents` — added `slice_id="default"` for implement-agent/implement_agent, and restructured loop to create fresh state per dispatch
6. `test_legacy_run_without_execution_mode_defaults_to_main_checkout` — added `slice_id="default"`
7. `test_main_checkout_run_does_not_require_worktree_fields` — added `slice_id="default"`
8. `test_worktree_mode_records_and_exposes_all_fields` — added `slice_id="default"`
9. `test_base_ref_not_required_in_new_outputs` — added `slice_id="default"`
10. `test_before_dispatch_includes_runtime_context_with_change_id` — added `slice_id="default"`
11. `test_before_dispatch_runtime_context_includes_parent_ref_when_recorded` — added `slice_id="default"`

## Files/Artifacts Changed

| File | Status | Reason |
|------|--------|--------|
| `.ai/workflows/scripts/workflow_runtime/dispatch.py` | modified | Remove backward-compat omission; always require --slice-id |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` | modified | Template sync |
| `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` | modified | Distributed copy sync |
| `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` | modified | Distributed copy sync |
| `tests/test_workflow.py` | modified | Update 11 tests for new contract |

## Commands Run

```bash
# Focused tests (red phase)
python3 -m pytest tests/test_workflow.py -k "slice_id or implement_dispatch or execution_mode or not_required or single_default" -v --tb=short
# 4 failures as expected (RED phase)

# Focused tests (green phase)
python3 -m pytest tests/test_workflow.py -k "slice_id or implement_dispatch or execution_mode or not_required or single_default or supports_dash" -v --tb=short
# 21 passed (GREEN phase)

# Full regression
python3 -m pytest tests/test_workflow.py -v --tb=short
# 449 passed, 25 subtests passed

python3 -m pytest tests/test_wrapper_contracts.py -v --tb=short
# 306 passed, 2 subtests passed

python3 -m pytest tests/test_workflow_modules.py -v --tb=short
# 13 passed
```

## Evidence Summary

- **tdd_passed**: true — RED phase confirmed 4 failures exactly matching expected behavior change; GREEN phase confirmed all 21 focused tests pass after test+code updates
- **tasks_complete**: true
- **Full regression**: 768/768 tests passing (test_workflow.py: 449, test_wrapper_contracts.py: 306, test_workflow_modules.py: 13)
- **verification_summary**: { "status": "pass" }

## Issues

- `test_before_dispatch_supports_dash_and_underscore_agents` originally dispatched `implement-agent` and `implement_agent` sequentially on the same state, which caused the second dispatch to fail with `slice_not_ready` (slice already `in_progress` from first dispatch). Fixed by restructuring to create a fresh state per dispatch.

## Learnings

- The `assessment_status == "not_required"` value was ambiguous: it could mean either "legacy run with no slicing_assessment block" (via `.get("status", "not_required")`) or "explicitly materialized not_required via slice-init --skip-assessment". The fix resolves this ambiguity by removing the backward-compat path entirely — both cases now require --slice-id.
- The `active_slices` variable computed before the elif branch was still used internally in the old backward-compat logic. After removing that logic, `active_slices` is no longer referenced in the implement-agent missing-slice-id path, which is correct.

## Suggestions

- Consider adding a similar `missing_slice_id` blocker for `review-agent` without `--slice-id` — currently review-agent dispatch without `--slice-id` falls through all checks without validation.
- The `assessment_status` default of `"not_required"` via `.get("status", "not_required")` could be made more explicit — consider distinguishing "no assessment block at all" from "explicitly assessed as not_required".

## Blockers

None.

## Risks/Follow-Ups

- None. The change is surgical: it removes a backward-compat path that contradicts Spec Invariants 8 and 12. All active implement-agent dispatches now require `--slice-id`.
