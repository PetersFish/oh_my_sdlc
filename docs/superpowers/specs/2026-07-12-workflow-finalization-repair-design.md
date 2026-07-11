# Workflow Finalization Repair Design

## Problem

Two workflow finalization issues were observed during run `2026-07-11-RM-ORCH-009`.

First, terminal movement refused to move the run to history because finish-agent evidence was recorded under `agent_results.default`, while `_missing_terminal_finish_agent_evidence()` expected it under `agent_results.modularize-workflow-runtime`. The mismatch happens because terminal validation falls back from missing dispatch slice to `context.change_id`, while normal unsliced lifecycle dispatch records results under `default`.

Second, `workflow.py final-commit --run-id ... --push` committed history artifacts but left deleted `.ai/workflows/runs/active/<run_id>/...` files dirty. Those deletions are expected when active runs move to history, but final-commit currently allowlists only history paths, `current.json`, roadmap, memory, OpenSpec archive, and Superpowers archive paths.

## Goals

- Preserve strict slice validation when an explicit dispatch slice exists.
- Support unsliced lifecycle runs that use `default`.
- Ensure final tail commit publishes the complete active-to-history state transition for the target run.
- Keep final-commit narrowly scoped and avoid committing unrelated active-run paths.
- Add executable regression tests for both issues.

## Non-Goals

- Do not redesign slice semantics across all workflow phases.
- Do not change implement/review/finish agent output contracts.
- Do not broaden final-commit to `git add -A`.
- Do not clean unrelated dirty files.

## Design

### 1. Terminal Finish-Agent Evidence Resolution

Update `_missing_terminal_finish_agent_evidence(state)` in `workflow_runtime/state.py`.

Current behavior computes one `relevant_slice_id`:

1. `evidence.agent_phase.slice_id`
2. `context.change_id`
3. `default`

New behavior:

- If `evidence.agent_phase.slice_id` is present, require finish-agent success under that exact slice.
- If no explicit dispatch slice is present, treat the run as unsliced and accept finish-agent success under:
  - `default`
  - `context.change_id`
- If neither candidate contains successful finish-agent evidence, return `missing_finish_agent_evidence` with candidate slice ids in the error payload.

This preserves the existing safety test where evidence under an unrelated slice must not satisfy a run with explicit dispatch slice `relevant-slice`.

### 2. Final Tail Commit Active-Run Deletion Handling

Update final-commit classification in `workflow_runtime/governance.py`.

Current behavior loses status information by converting `git status --porcelain -uall` to paths only. This prevents distinguishing expected same-run active deletions from unsafe active additions.

New behavior:

- Use status-aware entries from `_git_status_porcelain(root)` during classification.
- Continue allowing existing prefixes:
  - `.ai/workflows/runs/history/<run_id>/`
  - `.ai/workflows/runs/current.json`
  - `.ai/roadmap/`
  - `.ai/memory/`
  - `openspec/changes/archive/`
  - `docs/superpowers/archive/`
- Additionally allow only deletion entries under:
  - `.ai/workflows/runs/active/<run_id>/`
- Do not allow untracked or modified files under `.ai/workflows/runs/active/<run_id>/`.

`cmd_final_commit()` will stage these allowed deletion paths with explicit pathspecs, preserving the no-`git add -A` guarantee.

## Test Plan

Add or adjust tests in `tests/test_workflow.py`.

### Terminal Evidence Tests

- Add regression test:
  - Given `context.change_id = "change-x"`
  - Given no `evidence.agent_phase.slice_id`
  - Given successful finish-agent evidence under `agent_results.default`
  - When terminal `advance` or `done` runs
  - Then movement succeeds.

- Keep existing explicit-slice tests:
  - finish-agent evidence under unrelated slice is rejected when dispatch intent slice is set.
  - finish-agent evidence under explicit relevant slice succeeds.

### Final Commit Tests

- Add regression test:
  - Baseline commits an active run under `.ai/workflows/runs/active/<run_id>/`.
  - Simulate movement by deleting active files and writing corresponding history run files.
  - Run `final-commit --run-id <run_id>`.
  - Assert committed files include both history additions/modifications and active-run deletions.
  - Assert git status is clean for those run paths.

- Add safety test:
  - Create dirty untracked or modified file under `.ai/workflows/runs/active/<run_id>/`.
  - Run `final-commit`.
  - Assert it remains in `residual_dirty_paths` and is not committed.

## Acceptance Criteria

- Unsliced post-archive runs can reach `done` with successful finish-agent evidence under `default`.
- Explicit slice terminal validation remains strict.
- Final tail commit commits target-run active deletion paths created by active-to-history movement.
- Final tail commit does not commit unrelated active-run paths or non-deletion active files.
- Focused workflow tests pass.
- Full test suite passes.
