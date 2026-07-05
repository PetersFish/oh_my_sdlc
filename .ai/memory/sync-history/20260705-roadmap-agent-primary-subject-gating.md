# Sync History: 20260705-roadmap-agent-primary-subject-gating

## Changed Files

- `.ai/workflows/scripts/workflow.py` — added primary-subject gating helpers and hook filter
- `agents/dev-orchestrator.md` — documented primary-subject gating rule
- `tests/test_workflow.py` — added 6 new tests, updated 3 pre-existing
- `tests/test_wrapper_contracts.py` — added 1 new test
- Distributed copies synced via `sync_derived_artifacts.py`

## Evidence Used

- Commit range: `c42b2115..4628303f` (pre-hook checkpoint)
- Change ID: `roadmap-agent-primary-subject-gating`
- Flow type: lightweight-flow (no OpenSpec change)
- Roadmap: no_linked_item

## Memory Deltas

- `modules/agents.md` — updated with new commit, session, and update note for primary-subject gating
- `sessions/2026-07-05-roadmap-agent-primary-subject-gating.md` — new session entry

## Skipped

- architecture: no candidates
- decisions: no candidates
- pitfalls: no failure evidence
- specs: no OpenSpec change ID detected (lightweight-flow)
- evolution: no meaningful structural evolution beyond module update

## Review Required

None.

## Confidence

High — auto-update on diff-detected module change. All tests passing (1056/1056).
