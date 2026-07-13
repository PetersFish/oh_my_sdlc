# Implement-Agent Handoff — Review Blocker Fixes

## Metadata
- **Run ID**: 2026-07-13-sliced-apply-change-assessment-gate
- **Slice ID**: default (retry attempt 2)
- **Agent**: implement-agent
- **Phase**: apply_change
- **Flow Type**: lightweight-flow
- **Status**: success
- **Dispatched**: 2026-07-13T13:00:00Z

## Objective
Fix three blocking issues identified by review-agent for the "Sliced Apply-Change Assessment Gate" feature.

## Work Completed

### Issue 2a: implement-agent dispatch without --slice-id still allowed for single default slices
**Fix**: In `dispatch.py` `cmd_before_dispatch`, changed the implement-agent missing-slice-id logic to require `--slice-id` whenever `slicing_assessment.status != "not_required"` (i.e., for all new persisted implementation states). Backward-compat skip for omitted `--slice-id` now only applies to legacy runs where `assessment_status == "not_required"`.

**Files changed**:
- `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py`
- `tests/test_workflow.py` (tests added)

### Issue 2b: pending/blocked assessment gating not applied symmetrically to review-agent
**Fix**: In `dispatch.py` `cmd_before_dispatch`, assessment pending/blocked gating now applies symmetrically to BOTH `implement-agent` and `review-agent`. Previously only `implement-agent` was blocked; now `review-agent` is also blocked when `assessment_status` is `pending` or `blocked`.

**Files changed**:
- `.ai/workflows/scripts/workflow_runtime/dispatch.py`
- `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py`
- `tests/test_workflow.py` (tests added)

### Issue 2c: assessment materialization does not validate required schema fields
**Fix**: In `state.py` `materialize_slicing_assessment` and new helper `_validate_multi_slice_contract`, added validation for:
- non-empty reasons (required for all assessment decisions)
- valid confidence values (`high|medium|low`)
- signals object with all 8 required fields (type-checked)
- task_coverage for multi-slice assessments
- scope and verification_commands in multi-slice slice contracts

New constants: `VALID_ASSESSMENT_CONFIDENCE`, `SIGNALS_REQUIRED_FIELDS`, `MULTI_SLICE_REQUIRED_SLICE_FIELDS`.

**Files changed**:
- `.ai/workflows/scripts/workflow_runtime/state.py`
- `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py`
- `tests/test_workflow.py` (tests added, helpers updated)

## Files Changed
| File | Status | Reason |
|------|--------|--------|
| `.ai/workflows/scripts/workflow_runtime/dispatch.py` | modified | Issues 2a + 2b fixes |
| `.ai/workflows/scripts/workflow_runtime/state.py` | modified | Issue 2c validation |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/dispatch.py` | modified | Template sync |
| `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/state.py` | modified | Template sync |
| `tests/test_workflow.py` | modified | 12 new tests, 2 helper updates |

## Commands Run
| Command | Result |
|---------|--------|
| `pytest` (full suite) | 1348 pass, 4 pre-existing failures |

## Evidence Summary
- **TDD passed**: Yes — all new tests were written failing first, then made green
- **Focused tests**: 12 new tests covering all three issues
- **Full regression**: 1348/1352 pass (4 pre-existing failures in unrelated `test_repository_memory_reconciliation.py` — references missing `skills/sdlc-repository-memory-sync/scripts/reconcile_modules.py`)
- **Template sync**: Canonical `.ai/` → `skills/sdlc-project-bootstrap/templates/` sync complete

## Verification Summary
```json
{
  "verification_summary": {
    "status": "pass_with_accepted_preexisting_failures",
    "full_regression": {
      "command": "pytest",
      "passed": 1348,
      "failed": 4,
      "accepted_preexisting_failures": [
        {
          "test": "tests/test_repository_memory_reconciliation.py::TestStaleActiveModuleDetection::test_reconciliation_reports_stale_active_module",
          "reason": "Unrelated worktree test file references non-existent reconcile_modules.py",
          "confirmation": "File tests/test_repository_memory_reconciliation.py is an untracked worktree artifact, not part of this change",
          "owner": "environment_fixture"
        },
        {
          "test": "tests/test_repository_memory_reconciliation.py::TestStaleActiveModuleDetection::test_repair_removes_deleted_skill_from_active_registry",
          "reason": "Unrelated worktree test file references non-existent reconcile_modules.py",
          "confirmation": "File tests/test_repository_memory_reconciliation.py is an untracked worktree artifact, not part of this change",
          "owner": "environment_fixture"
        },
        {
          "test": "tests/test_repository_memory_reconciliation.py::TestStaleActiveModuleDetection::test_repair_removes_deleted_skill_from_active_parent_index",
          "reason": "Unrelated worktree test file references non-existent reconcile_modules.py",
          "confirmation": "File tests/test_repository_memory_reconciliation.py is an untracked worktree artifact, not part of this change",
          "owner": "environment_fixture"
        },
        {
          "test": "tests/test_repository_memory_reconciliation.py::TestStaleActiveModuleDetection::test_historical_artifacts_are_preserved",
          "reason": "Unrelated worktree test file references non-existent reconcile_modules.py",
          "confirmation": "File tests/test_repository_memory_reconciliation.py is an untracked worktree artifact, not part of this change",
          "owner": "environment_fixture"
        }
      ]
    }
  }
}
```

## Issues
1. **Bash command restrictions**: The runtime deny rule for `*` on bash commands blocked `pytest <args>`, `python3 -m pytest`, and most other python commands. Only bare `pytest` and git observation commands were allowed. Worked around by using bare `pytest` for verification.
2. **Import mismatch**: Untracked `scripts/repro_test.py` conflicts with `repro_test.py` during pytest collection. Worked around temporarily with `pyproject.toml` (removed after testing — standard `python3 -m pytest tests/ -v` avoids this issue).
3. **Template sync scope**: Distributed copies under `.claude/`, `.cursor/`, `.opencode/` were NOT synced. The finish-agent handles distributed-copy drift per the derived-sync restriction boundary.

## Learnings
1. The assessment gating was intentionally asymmetrical to allow review-agent to bypass the initial slicing assessment gate (legacy design). Making it symmetric required updating 3 test helpers that had installed `assessment_status="completed"` for backward compat — changed them to `"not_required"` to preserve dispatch behavior for non-assessment-gate tests.
2. The `materialize_slicing_assessment` validation was designed as a "trust the plan-agent" pass-through. Adding strict validation required updating the `_multi_assessment_result` test helper to include the new required fields (`task_coverage`, `scope`, `verification_commands`).

## Suggestions
1. Consider adding a `conftest.py` with `collect_ignore = ["scripts/"]` to avoid the import mismatch issue between `scripts/repro_test.py` and `repro_test.py` in the worktree.
2. The bash permission rules need adjustment — `pytest *` and `python3 -m pytest *` allow patterns are being overridden by the `*` deny rule, making all test-runs require bare `pytest` without arguments.

## Blockers
None.

## Risks/Follow-Ups
- The distributed template copies under `.claude/`, `.cursor/`, `.opencode/` will drift until finish-agent runs `sync_derived_artifacts.py --fix`.
- The `pyproject.toml` (temporarily used during testing) has been removed.
- Existing tests that explicitly tested the old backward-compat behavior (`test_implement_dispatch_without_slice_id_allowed_for_single_default`) were updated to reflect the new contract.
