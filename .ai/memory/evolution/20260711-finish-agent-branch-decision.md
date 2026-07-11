---
id: 20260711-finish-agent-branch-decision
type: evolution
title: 2026-07-11 — Finish-Agent Branch Decision Gate and Terminal Ownership
summary: Added explicit branch finish decision gate (merge_local/create_pr/keep_branch/discard), separated implementation from workflow commits, defined memory sync target ref rules per branch decision, enforced finish-agent terminal boundaries, replaced misleading archive evidence with semantic fields, and implemented lightweight-flow Superpowers plan/spec archive moves into typed subdirectories.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_commits: ["80f8c9d74076fbabbed088e45edb33f1be91c437"]
linked_specs: [finish-agent-branch-decision-and-terminal-ownership]
linked_sessions: []
updated_at: 2026-07-11T00:00:00Z
tags: [workflow, finish-agent, branch, archive, governance, dev-orchestrator]
---

## New Capabilities

- **Branch finish decision gate**: Implemented explicit `branch_finish_decision` gate requiring user selection of `merge_local`, `create_pr`, `keep_branch`, or `discard` before branch-affecting finish actions. Main-checkout mode without feature branch exempts the gate (Spec Decision 3).
- **No silent defaults**: Finish-agent and runtime must not silently choose branch outcome (Spec Decision 2).
- **Branch action semantics**: Defined evidence contracts for each branch decision (Spec Decision 5): merge_local records merged base commit, create_pr records PR-ready evidence, keep_branch preserves feature branch, discard requires explicit confirmation.
- **Implementation vs workflow commit separation**: Defined two commit classes — implementation commits (source, tests, docs) live on feature branch; workflow commits (run state, memory sync, archive moves) live on control checkout (Spec Decision 6).
- **Memory sync target ref rules**: Memory sync records explicit target ref type/ref/commit based on branch decision (Spec Decision 7).
- **Semantic archive evidence**: Replace `archive_path_exists: true` with `archive_action_completed`, `archive_artifact_path`, `archive_not_required_reason`, `archived_design_artifact_paths`, and `source_design_artifact_paths` (Spec Decision 10).
- **Lightweight-flow archive moves**: Completed lightweight-flow runs move matching plan files to `docs/superpowers/archive/plans/` and spec files to `docs/superpowers/archive/specs/` with typed archive subdirectories (Spec Decision 11).
- **Absolute path normalization**: `_archive_lightweight_superpowers_artifacts()` normalizes absolute runtime design artifact paths to repo-relative before Superpowers classification, fixing a blocker where absolute paths from the runtime context were dropped before archive moves.

## Contract Changes

- `finish-agent` prompt now hard-requires branch decision gate, lightweight-flow artifact archive into typed subdirectories, forbids silent branch outcome, and forbids terminal workflow finalization (Spec Decision 12).
- `dev-orchestrator` prompt now owns user branch decision collection and records selection before redispatching finish-agent (Spec Decision 13).
- `finish-agent` must not execute `workflow.py done`, terminal `advance` to history, or manual run directory movement (Spec Decision 8).
- Final `finish-agent` evidence in `run.json` must include `agent_results` before history movement (Spec Decision 9).

## Distribution / Template Sync

- Canonical `agents/dev-orchestrator.md` and `agents/finish-agent.md` updated.
- Distributed copies synced to `.opencode/`, `.claude/`, and `.cursor/`.
- Live `.ai/workflows/scripts/workflow.py` synced to canonical `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`.
- All derived agent and template copies verified in sync.

## Test Coverage

- New behavior tests in `tests/test_workflow.py`: branch decision gate (missing, allowed values, no default, main-checkout compatibility), absolute runtime path archive moves, missing source blocking, semantic evidence fields, collision handling.
- New prompt-contract tests in `tests/test_wrapper_contracts.py`: finish-agent terminal boundaries, dev-orchestrator branch decision collection.
- Full regression: 1152 tests passing.
