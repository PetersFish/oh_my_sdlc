---
id: specs/repair-workflow-decision-block-unlock
type: specs
title: Workflow decision block unlock contract
summary: Defines and verifies that recording a corrected valid branch_finish_decision reconciles the stale decision-specific block atomically, restoring the run to running with block null while preserving unrelated blocks and invalid corrections.
sync_status: synced
evidence_mode: spec_reference
linked_commits: ["4523caf4297c8b933fe7d234ed54b54ae7b21681"]
linked_specs: [repair-workflow-decision-block-unlock]
linked_sessions: []
updated_at: 2026-07-11T00:00:00Z
confidence: high
tags: [workflow, decision-block, branch-finish, reconciliation, openspec]
owned_paths:
  - openspec/changes/archive/2026-07-11-repair-workflow-decision-block-unlock/specs/sdlc-workflow-engine/spec.md
path_hints:
  - .ai/workflows/scripts/workflow.py
  - skills/sdlc-project-bootstrap/templates/workflow/workflow.py
keywords: [decision-block, branch-finish-decision, unblock, reconcile, record-context, running]
test_paths:
  - tests/test_workflow.py
spec_paths:
  - openspec/changes/archive/2026-07-11-repair-workflow-decision-block-unlock/specs/sdlc-workflow-engine/spec.md
---

# Workflow decision block unlock contract

## Current Understanding

`repair-workflow-decision-block-unlock` is complete, verified, and archived. The effective contract requires:

- `cmd_record_context` must evaluate whether a recorded `branch_finish_decision` resolves the currently persisted branch-decision block after building and validating the tentative context.
- Reconciliation predicates (all required): run is currently `blocked`; recorded key is `branch_finish_decision`; tentative context resolves to decision status `ok`; persisted block represents the branch-decision gate (identified by its decision-specific reason/type/action metadata — `user_decision_required` type plus `ask_user_branch_finish_decision` next action).
- When all predicates hold, the same state save must set `status` to `running` and `block` to `None` atomically with the context write.
- Missing or invalid corrections leave state blocked. Valid decision writes against unrelated blocks update context but preserve the block.
- The repair must not use message substring matching as the primary block-recognition contract.

## Evidence

- OpenSpec change archived at `openspec/changes/archive/2026-07-11-repair-workflow-decision-block-unlock/`.
- Implement-agent TDD passed; focused tests for missing-to-valid, invalid-to-valid, unrelated-block preservation, and no-gate main-checkout all pass.
- Full regression `python3 -m pytest tests/test_workflow.py -v` passes.
- Review-agent accepted.

## Operational Guidance

- A run previously blocked for a missing or invalid `branch_finish_decision` recovers automatically when `record-context` stores an allowed decision value — no separate manual unblock command.
- Do not add a general-purpose force-unblock command; the reconciliation is narrow to decision-specific blocks.
- Live runtime is the implementation source; canonical and distributed workflow template copies must be synchronized after changes.

## Update Notes

Added during post-archive memory sync for `repair-workflow-decision-block-unlock`.