## Why

Roadmap-linked SDLC runs currently declare lifecycle hooks for ready/apply-start/done, but the ready and apply-start transitions are not validated as strongly as the done hook. This lets a workflow appear to progress even when the roadmap item state mutation did not actually happen.

## What Changes

- Harden roadmap-governed workflow transitions for linked roadmap items using a dedicated `roadmap-agent` lifecycle worker that invokes the existing `sdlc-roadmap` skill for domain mutations.
- Add runtime hook validation for `roadmap_status_ready_if_linked` and `roadmap_apply_start_if_ready` so hook completion requires observed roadmap state changes, not just pending-hook removal.
- Update dev-orchestrator/finish-agent prompt guidance only as needed so roadmap work is routed to `roadmap-agent` rather than unsafe general-task dispatch, while the orchestrator remains routing-only.
- Add focused tests for ready/apply-start/done transition governance and orchestration boundaries.
- Keep workflow runtime and template/distribution changes minimal and synchronized.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `sdlc-workflow-engine`: Strengthen runtime requirements for roadmap lifecycle hook validation at create/apply/archive boundaries.
- `sdlc-orchestrator`: Clarify routing behavior for roadmap-governed work so roadmap mutations are delegated to `sdlc-roadmap` rather than performed by the orchestrator.
- `sdlc-roadmap`: Clarify expected roadmap worker behavior for linked item transitions from idea/planned to ready, ready to active, and active to done.

## Impact

- Affected workflow runtime files: `.ai/workflows/scripts/workflow.py`, `.ai/workflows/definitions/sdlc-main.yaml`, and synced bootstrap template copies.
- Affected prompts: canonical agent prompts under `agents/` and mechanically distributed copies if prompt text changes.
- Affected tests: workflow runtime tests, wrapper/prompt contract tests, and roadmap/orchestrator tests as needed.
- Introduces one focused lifecycle subagent prompt, `roadmap-agent`, backed by the existing `sdlc-roadmap` skill; no new roadmap domain model or external dependency is introduced.
