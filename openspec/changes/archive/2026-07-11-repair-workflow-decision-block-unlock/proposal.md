## Why

When a workflow branch decision is missing or invalid, the runtime can persist a blocked run. Recording a corrected, valid branch value updates context but leaves the stale block intact, so guarded dispatch or advancement still rejects the run even though the original decision error has been resolved.

## What Changes

- Reconcile decision-related block state whenever workflow context records a corrected branch decision.
- Clear only the stale block caused by the now-valid decision and restore the run to `running`; preserve unrelated block types and invalid or incomplete corrections.
- Ensure the repaired run can proceed through the normal guarded dispatch/advance path without a separate manual unblock operation.
- Add behavioral regression coverage for invalid-to-valid correction, missing-to-valid correction, unrelated-block preservation, and invalid-correction preservation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sdlc-workflow-engine`: Require corrected valid branch decisions to reconcile stale decision blocks and permit normal workflow progress while preserving unrelated blocks.

## Impact

- Affected runtime: `.ai/workflows/scripts/workflow.py`, especially context recording and decision-block reconciliation.
- Affected tests: `tests/test_workflow.py` temporary-workspace behavioral tests.
- Derived artifacts: canonical workflow template and project-level distributed workflow copies must be synchronized after the live runtime change.
- No external API, dependency, or breaking schema change.
