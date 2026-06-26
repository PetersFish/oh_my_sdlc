## Why

The workflow runtime needs a small set of explicit contract fields before the agent-backed wrapper architecture can rely on it safely. Adding those fields now keeps `workflow.py` as the deterministic state owner while avoiding a broader rewrite before the wrapper migration starts.

## What Changes

- Add explicit `flow_type` support to workflow run state and run creation commands, defaulting to `spec-flow`
- Allow `lightweight-flow` inference from subject type only when the user confirms the inferred choice before the workflow continues
- Add workflow-definition support for phase-level `evidence_keys`
- Require `complete-phase` to fail closed when declared evidence keys are missing or empty
- Preserve existing run storage, command names, transition model, and JSON output shape outside the new contract validation
- Keep live workflow runtime files and canonical workflow templates in sync after implementation

## Capabilities

### New Capabilities

- `workflow-phase-evidence-contracts`: Phase definitions can declare required evidence keys that must be present before a phase can be completed

### Modified Capabilities

- `sdlc-workflow-engine`: Workflow run state and command behavior now include explicit `flow_type` handling, confirmation-gated lightweight-flow inference, and fail-closed evidence-key validation during phase completion

## Impact

- Affected code: `.ai/workflows/scripts/workflow.py`, `.ai/workflows/definitions/sdlc-main.yaml`
- Affected specs: `openspec/specs/sdlc-workflow-engine/spec.md` (delta), new `openspec/changes/workflow-state-machine-contract-enhancements/specs/workflow-phase-evidence-contracts/spec.md`
- Related change: `openspec/changes/agent-backed-lifecycle-wrapper-architecture/`
- No intended changes to workflow module ownership, top-level command surface, or full runtime architecture
