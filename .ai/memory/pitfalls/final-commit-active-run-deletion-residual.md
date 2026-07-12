---
id: pitfalls/final-commit-active-run-deletion-residual
type: pitfalls
title: final-commit left active-run directory deletions residual, blocking clean finalization
summary: >-
  final-commit classified dirty paths by prefix allowlist only, so the
  expected deletion of .ai/workflows/runs/active/<run>/ (the move-to-history
  step) was never admitted to the commit. The finalized tree stayed dirty
  and governance-check could loop. Fix: status-aware classification admits
  active-run paths whose git status code indicates deletion.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_specs: []
failure_evidence:
  - test: tests/test_workflow.py::TestFinalCommit::test_final_commit_commits_target_active_run_deletions
  - test: tests/test_workflow.py::TestFinalCommit::test_final_commit_does_not_commit_target_active_run_non_deletions
linked_commits: [db18359]
linked_sessions: []
updated_at: 2026-07-12T16:00:00Z
tags: [workflow, final-commit, governance, active-run, finalization]
severity: high
status: mitigated
---

## Symptom

After a run moved from `active/` to `history/` (directory rename/delete),
`workflow.py final-commit` reported the deleted `active/<run>/` paths as
`residual_dirty_paths` and refused to commit them. The finalized tree never
became clean, so downstream `governance-check` could loop on the same dirty
paths.

## Root Cause

`governance._classify_final_commit_paths` inspected path strings only, with
no access to the git status code. It could not distinguish an active-run
**deletion** (expected cleanup) from an unexpected dirty active-run
artifact, so it left both in `residual`.

## Mitigation

- Added `_classify_final_commit_entries(status_code, path)` which admits
  active-run paths whose status code contains `D` (deleted).
- `cmd_final_commit` now reads `git status --porcelain` entries (not just
  names) and uses the status-aware classifier.
- Staged-path filtering uses the resulting allowed set, preventing
  pre-existing staged files outside the commit scope from being swept in.
- The path-only classifier is retained for existing callers/tests.

## Detection

`python3 -m pytest tests/test_workflow.py::TestFinalCommit -v`