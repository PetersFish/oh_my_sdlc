# Sync History: 20260711-workflow-decision-block-unlock

## Changed Files

- `.ai/workflows/scripts/workflow.py` (decision block reconciliation in cmd_record_context)
- `tests/test_workflow.py` (behavioral regressions for missing-to-valid, invalid-to-valid, unrelated-block, no-gate main-checkout)
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (canonical template sync)
- `.opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `.cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- `agents/dev-orchestrator.md` + distributed agent copies (activation metadata)
- `openspec/specs/sdlc-workflow-engine/spec.md` (decision block unlock requirement)
- `openspec/changes/archive/2026-07-11-repair-workflow-decision-block-unlock/` (archived change artifacts)
- `.ai/workflows/runs/active/2026-07-11-repair-workflow-decision-block-unlock/` (run state + handoffs)

## Evidence Used

- Commit range: `b368a7f731ea3cf734827fee0b5484b72eb9319b..4523caf4297c8b933fe7d234ed54b54ae7b21681`
- OpenSpec change ID: `repair-workflow-decision-block-unlock` (archived)
- Implement-agent TDD evidence: focused tests pass, full regression passes, provider apply verification all_done (17/17)
- Review-agent: accepted, verification_passed true
- Finish-agent archive: provider_verification openspec.archive verified, active_changes_remaining 0, specs_synced true

## Memory Deltas

- `specs/repair-workflow-decision-block-unlock.md` — new spec memory documenting the decision block unlock contract.
- `pitfalls/stale-decision-block-persists-after-valid-correction.md` — new pitfall documenting the stale-block persistence failure, root cause, fix, and detection.
- `evolution/20260711-workflow-decision-block-unlock.md` — new evolution entry for the workflow runtime reconciliation capability.

## Skipped

- `architecture`: no candidates — this is a narrow runtime fix, not an architecture decision.
- `decisions`: no candidates requiring user confirmation — the design decision is captured in the spec/pitfall memory.
- `modules`: no new module discovery candidates; diff-detected modules (workflow, tests, agents) already have existing memory and were not semantically changed in module boundaries.
- `sessions`: local-only session log not written in this sync cycle.

## Review Required

None.

## Confidence

High — all memory deltas are backed by committed evidence and archived OpenSpec artifacts.