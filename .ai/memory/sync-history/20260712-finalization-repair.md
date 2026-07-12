# Sync History: 20260712-finalization-repair

## Changed Files

- `.ai/workflows/scripts/workflow_runtime/governance.py` — status-aware `_classify_final_commit_entries`, `cmd_final_commit` uses porcelain entries.
- `.ai/workflows/scripts/workflow_runtime/state.py` — `candidate_slice_ids` list in `_missing_terminal_finish_agent_evidence`.
- `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/{governance,state}.py` — canonical templates synced.
- `.opencode/`, `.claude/`, `.cursor/` distributed template copies synced.
- `tests/test_workflow.py` — 145 lines added (TestFinalCommit active-run deletion cases, TestTerminalEvidenceValidation default-slice case).
- `docs/superpowers/plans/2026-07-12-workflow-finalization-repair.md` → `docs/superpowers/archive/plans/...` (archive move).
- `docs/superpowers/specs/2026-07-12-workflow-finalization-repair-design.md` → `docs/superpowers/archive/specs/...` (archive move).

## Evidence Used

- Commit range: `f04a9d6..db18359` (pre-cleanup checkpoint `db18359`).
- Test evidence:
  - `tests/test_workflow.py::TestFinalCommit::test_final_commit_commits_target_active_run_deletions`
  - `tests/test_workflow.py::TestFinalCommit::test_final_commit_does_not_commit_target_active_run_non_deletions`
  - `tests/test_workflow.py::TestTerminalEvidenceValidation::test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice`
- Pre-commit hook: all governed files in sync, all distributed copies match canonical, all skill distributions match canonical.

## Memory Deltas

- `architecture/workflow-runtime-architecture.md` — updated `linked_commits` to include `db18359`, added "Refinements (2026-07-12, commit db18359)" section documenting governance.py status-aware classification and state.py candidate_slice_ids.
- `pitfalls/final-commit-active-run-deletion-residual.md` — NEW. Active-run directory deletions left residual by path-only classifier, blocking clean finalization.
- `pitfalls/finish-agent-evidence-slice-id-change-id.md` — NEW. Terminal validation rejected finish-agent success when change_id differed from default slice.
- `evolution/20260712-finalization-repair.md` — NEW. Evolution entry for the two finalization-path bug fixes.

## Skipped

- `sessions`: no session log update performed (lightweight-flow post_archive_actions cleanup; session log auto-update not required for cleanup-only dispatch).
- `specs`: no OpenSpec change ID detected for this lightweight-flow run; specs memory not updated.
- `decisions`: no new decisions; the governance/state refinements are bug fixes under the existing `decisions/workflow-runtime-modularization.md` contract, not new decisions.
- `modules` (discovery): no new module candidates; `workflow_runtime/` already tracked under `architecture/workflow-runtime-architecture.md`.
- `schemas`: validation only, no schema changes.

## Review Required

None. All candidates were auto-update eligible (architecture diff-detected, pitfalls with test evidence, evolution with stable commit range).

## Confidence

High. All memory deltas backed by committed code and passing tests.