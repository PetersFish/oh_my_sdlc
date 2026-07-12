---
id: 20260712-finalization-repair
type: evolution
title: 2026-07-12 - Finalization Repair (active-run deletion + finish-agent slice-id)
summary: >-
  Two finalization-path bug fixes in the workflow runtime: (1) final-commit
  now commits expected active-run directory deletions using status-aware
  classification, unblocking clean finalization; (2) terminal validation now
  accepts finish-agent success under either "default" or change_id slice,
  unblocking done advancement for unsliced runs.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_commits: ["db18359"]
linked_specs: []
linked_sessions: []
updated_at: 2026-07-12T16:00:00Z
tags: [workflow, final-commit, terminal, governance, state, bugfix]
---

## New Capabilities

- `governance._classify_final_commit_entries` — status-aware classifier that
  admits active-run paths whose git status code indicates deletion.
- `cmd_final_commit` now reads `git status --porcelain` entries and uses the
  status-aware classifier; staged-path filtering uses the resulting allowed
  set to exclude pre-existing staged files outside the commit scope.
- `state._missing_terminal_finish_agent_evidence` now builds a
  `candidate_slice_ids` list and accepts finish-agent success under any
  candidate; the returned finding includes the candidate list.

## Contract Changes

- `final-commit` may now stage and commit deletions of
  `.ai/workflows/runs/active/<run>/` paths (the move-to-history step),
  which were previously left residual.
- Terminal validation no longer reinterprets `context.change_id` as the
  required slice for unsliced runs; `default` remains valid when no
  dispatch-intent slice is present.

## Distribution / Template Sync

- Canonical `skills/sdlc-project-bootstrap/templates/workflow/workflow_runtime/{governance,state}.py` updated.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/` synced.
- Pre-commit hook confirmed all governed files in sync at commit time.

## Verification Evidence

- `python3 -m pytest tests/test_workflow.py -v` (1204 passed, 0 failed)
- `python3 -m pytest tests/test_workflow.py::TestFinalCommit -v`
- `python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation -v`
- Pre-commit hook: OK all governed files in sync, all distributed copies match canonical, all skill distributions match canonical.

## Pitfall Memory

- `pitfalls/final-commit-active-run-deletion-residual.md`
- `pitfalls/finish-agent-evidence-slice-id-change-id.md`

## Architecture Memory

- `architecture/workflow-runtime-architecture.md` updated with the
  refinements section (commit db18359).