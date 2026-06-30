# Plan Agent Handoff — run-artifacts-unify-followup

## Metadata
- **Agent**: plan-agent
- **Phase**: create_change
- **Flow Type**: lightweight-flow
- **Run ID**: 2026-06-29-run-artifacts-unify-followup
- **Slice ID**: default
- **Status**: success
- **Recommended Next Agent**: dev-orchestrator (await user plan approval)

## Objective
Create a follow-up implementation plan covering root-cause analysis, historical artifact repair for three runs, and removal of `_migrate_legacy_artifacts`.

## Work Completed
- Reviewed workflow runtime paths and finalization logic in `.ai/workflows/scripts/workflow.py`.
- Reviewed workflow definition, agent prompts, and representative archived run state/handoff evidence.
- Reviewed current filesystem state for the three affected runs under `.ai/workflows/runs/` and `.ai/workflows/runs/history/`.
- Produced a durable implementation plan with TDD order, repair strategy, and recurrence-prevention coverage.

## Files/Artifacts Changed
- `.ai/workflows/runs/2026-06-29-run-artifacts-unify-followup/plans/default/plan.md` — created
- `.ai/workflows/runs/2026-06-29-run-artifacts-unify-followup/handoffs/default/plan-agent.md` — created

## Commands Run (none)
None.

## Evidence Summary
- Runtime archives `active/<run_id>/` but current agent/docs/tests still reference sibling `.ai/workflows/runs/<run_id>/...` artifact paths.
- `_migrate_legacy_artifacts` only handles legacy `runs/handoffs/<run_id>` and `runs/logs/<run_id>`; it does not repair sibling per-run directories or plans.
- Two affected runs still use flat `history/<run_id>.json` files, so repair must also create history directories and relocate `run.json`.
- Plan includes failing-first behavior tests, tested repair strategy for the three named runs, prompt/doc alignment, template sync, and removal of `_migrate_legacy_artifacts`.

## Blockers
None.

## Assumptions
- A deterministic runtime/helper-based repair path is acceptable for the three named runs.
- Lightweight-flow follow-up should update docs/prompts/tests where needed for consistency, but not create OpenSpec artifacts.

## Risks/Follow-Ups
- Some existing tests currently encode the wrong path contract and will need deliberate replacement rather than blind update.
- Distributed agent copies and workflow templates must stay in sync with canonical files.
- Historical repair should be idempotent to avoid damaging already-moved artifacts during retries.

## Raw Logs (none)
None.
