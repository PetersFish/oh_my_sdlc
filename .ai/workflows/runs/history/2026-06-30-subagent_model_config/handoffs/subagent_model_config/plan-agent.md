## Metadata

- Run ID: 2026-06-30-subagent_model_config
- Slice ID: subagent_model_config
- Agent: plan-agent
- Phase: create_change
- Flow Type: spec-flow
- Status: blocked
- Recommended Next Agent: fix_workflow_context

## Objective

Review `docs/manual/design/subagent_model_config_design.md` and produce an implementation plan for centralized per-subagent model configuration without implementing code.

## Work Completed

- Loaded repository memory relevant to `agents/` and prior distribution behavior.
- Reviewed the design doc in full.
- Inspected current `scripts/install_agents.py`, related tests, canonical agent frontmatter, distributed agent copies, and bootstrap skill/tests.
- Identified design strengths plus gaps around canonical cleanup, dry-run semantics, refresh UX, metadata semantics, and bootstrap-scope fit.
- Wrote a durable implementation plan artifact for user approval.
- Revised the plan after user feedback; resolved the bootstrap-boundary question as an accepted decision: no new skill in this change.
- Refreshed the plan to record final user approval and the accepted item 5 decision.

## Files/Artifacts Changed

- `.ai/workflows/runs/active/2026-06-30-subagent_model_config/plans/subagent_model_config/plan.md`
- `.ai/workflows/runs/active/2026-06-30-subagent_model_config/handoffs/subagent_model_config/plan-agent.md`

## Commands Run (none)

- None

## Evidence Summary

- Design is viable and sufficiently detailed to plan implementation.
- Main review findings:
  - canonical `agents/*.md` cleanup is required;
  - `setup_agents.py --dry-run` needs explicit semantics;
  - config refresh should prefer activation-only/non-destructive routing;
  - install metadata must remain distinct from activation drift;
  - bootstrap integration must respect current initialization-only scope.
- User accepted the item 5 recommendation, converting it into an implementation decision:
  - keep `sdlc-project-bootstrap` initialization-only;
  - do not create `sdlc-agent-config` in this change;
  - let script-level routing cover refresh flows for now.
- Produced a TDD-aware implementation order with focused tests and exact verification commands.

## Blockers

- Spec-flow provider-owned artifact generation cannot be completed in this dispatch because the resolved wrapper dispatch contract and verifier details were not provided to plan-agent.

## Assumptions

- `subagent_model_config` is the slice identifier to use for this planning artifact.
- User has approved the plan; remaining blocker is workflow-context/provider dispatch, not requirements clarification.
- Distributed agent copies remain derived artifacts and will be regenerated during implementation rather than edited manually.

## Risks/Follow-Ups

- Final implementation should keep activation behavior and install behavior independently testable.
- A separate future change may introduce a dedicated maintenance skill if refresh workflows prove frequent enough; it is explicitly out of scope for this change.

## Raw Logs (none)

- None
