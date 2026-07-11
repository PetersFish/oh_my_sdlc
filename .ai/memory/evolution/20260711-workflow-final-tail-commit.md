---
id: 20260711-workflow-final-tail-commit
type: evolution
title: 2026-07-11 — Workflow Final Tail Commit Command
summary: Added `workflow.py final-commit` command and dev-orchestrator "Final Tail Commit Protocol" so governance artifacts (history run dir, current.json, roadmap, memory, openspec/changes/archive, docs/superpowers/archive) are published through a single allowlist-scoped commit after a run reaches done, replacing direct git add/commit/push by the orchestrator.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_commits: ["b368a7f731ea3cf734827fee0b5484b72eb9319b"]
linked_specs: []
linked_sessions: ["2026-07-11-workflow-final-tail-commit"]
updated_at: 2026-07-11T00:00:00Z
tags: [workflow, final-commit, governance, dev-orchestrator, archive]
---

## New Capabilities

- **`final-commit` workflow command**: New `cmd_final_commit` in `workflow.py` runs after a workflow run reaches `done`. It validates the done history run exists, reads dirty paths, classifies them against an allowlist (history run dir scoped to the run_id, `.ai/workflows/runs/current.json`, `.ai/roadmap/`, `.ai/memory/`, `openspec/changes/archive/`, `docs/superpowers/archive/`), stages only allowed paths individually (never `git add -A`), commits with explicit pathspecs so pre-staged unrelated files are not included, optionally pushes, and reports `residual_dirty_paths`.
- **Allowlist-scoped staging**: The allowlist is scoped to the specific `run_id` for history run paths, preventing cross-run contamination. Pre-existing staged files outside the allowlist are preserved in the index and reported as residual.
- **Dev-orchestrator Final Tail Commit Protocol**: `dev-orchestrator` now captures the active `run_id` before advancing to `done`, then calls `workflow.py final-commit --run-id <run_id> --push`, then checks `git status --short` and reports clean status or `residual_dirty_paths`. Direct `git add`/`git commit`/`git push` for final governance artifact publishing is now forbidden.

## Contract Changes

- `workflow.py` added `final-commit` command, `--run-id` and `--push` CLI flags, `cmd_final_commit`, `_run_git`, `_git_status_porcelain`, `_git_dirty_paths`, `_final_commit_allowed_prefixes`, `_classify_final_commit_paths`, `_load_done_history_run_for_final_commit` helpers, and `subprocess` import.
- `dev-orchestrator.md` added "Final Tail Commit Protocol" section with required ordering and the explicit prohibition on direct git commands for final publishing.

## Distribution / Template Sync

- Canonical `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` updated with the new command.
- Live `.ai/workflows/scripts/workflow.py` synced.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/` verified in sync.
- `agents/dev-orchestrator.md` canonical and distributed copies updated.

## Test Coverage

- `tests/test_workflow.py` gained `TestFinalCommit` (11 tests): missing run_id, history run not found, not-done run, run_id mismatch, noop on clean tree, allowlisted history file commit, unrelated file exclusion, pre-staged unrelated file preservation, run_id-scoped allowlist, superpowers archive artifact commit, push success, noop-with-push, push failure reporting.
- `tests/test_wrapper_contracts.py` gained `TestDevOrchestratorFinalTailCommit` (6 tests): protocol section presence, run_id capture before done, final-commit command call, no-direct-git prohibition, git status check, residual_dirty_paths reporting.