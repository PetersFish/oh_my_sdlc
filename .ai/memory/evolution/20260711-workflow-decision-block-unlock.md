---
id: 20260711-workflow-decision-block-unlock
type: evolution
title: 2026-07-11 — Workflow Decision Block Unlock
summary: Fixed stale decision block persistence by adding atomic reconciliation in cmd_record_context — recording a corrected valid branch_finish_decision now clears only the decision-specific block and restores the run to running, while preserving unrelated blocks and invalid corrections. Added narrow structured block-recognition predicates and behavioral regression coverage.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_commits: ["4523caf4297c8b933fe7d234ed54b54ae7b21681"]
linked_specs: [repair-workflow-decision-block-unlock]
linked_sessions: []
updated_at: 2026-07-11T00:00:00Z
tags: [workflow, decision-block, branch-finish, reconciliation, record-context, governance]
---

## New Capabilities

- **Decision block reconciliation at the context mutation boundary**: `cmd_record_context` now evaluates whether a recorded `branch_finish_decision` resolves the currently persisted branch-decision block. When all reconciliation predicates hold (run blocked, key is `branch_finish_decision`, tentative decision status `ok`, persisted block is the branch-decision gate), the same state save atomically sets `status` to `running` and `block` to `None`.
- **Narrow structured block recognition**: Block identification uses the runtime's own decision-specific reason/type/action metadata (`user_decision_required` type + `ask_user_branch_finish_decision` next action), not message substring matching. Only the runtime's own branch-decision blocks are eligible.
- **Unrelated block preservation**: Valid decision writes against unrelated blocks update context but preserve the block. Invalid or incomplete corrections leave state blocked.

## Contract Changes

- `.ai/workflows/scripts/workflow.py` `cmd_record_context` gained reconciliation logic after tentative context validation.
- `openspec/specs/sdlc-workflow-engine/spec.md` updated with the decision block unlock requirement.
- No new workflow commands or CLI flags.

## Distribution / Template Sync

- Canonical `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` synced.
- Distributed copies under `.opencode/`, `.claude/`, `.cursor/` verified in sync via pre-commit hook.
- `agents/dev-orchestrator.md` canonical and distributed copies updated (agent activation metadata).

## Test Coverage

- `tests/test_workflow.py` gained behavioral regressions: missing-to-valid correction transitions to running with block null, finish-agent dispatch succeeds after correction, invalid correction remains blocked, valid decision does not clear unrelated block, main checkout without branch gate not spuriously unblocked.
- Full regression `python3 -m pytest tests/test_workflow.py -v` passes.