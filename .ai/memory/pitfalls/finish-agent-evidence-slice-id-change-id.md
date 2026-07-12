---
id: pitfalls/finish-agent-evidence-slice-id-change-id
type: pitfalls
title: Terminal validation rejected finish-agent success when change_id differed from the default slice
summary: >-
  _missing_terminal_finish_agent_evidence derived relevant_slice_id as
  dispatch_intent_slice_id or change_id or "default". For unsliced runs
  that recorded finish-agent under "default" while context.change_id was
  set, the validator looked under change_id, missed the success result,
  and blocked terminal movement to done. Fix: build candidate_slice_ids
  list and accept success under any candidate.
parent_id: root
sync_status: synced
evidence_mode: commit
confidence: high
linked_specs: []
failure_evidence:
  - test: tests/test_workflow.py::TestTerminalEvidenceValidation::test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice
linked_commits: [db18359]
linked_sessions: []
updated_at: 2026-07-12T16:00:00Z
tags: [workflow, state, terminal, finish-agent, slice-id, evidence]
severity: high
status: mitigated
---

## Symptom

Unsliced lifecycle runs (no `dispatch_intent.slice_id`) that set
`context.change_id` could not advance from `post_archive_actions` to
`done`: terminal validation reported `missing_finish_agent_evidence` even
though `finish-agent` had recorded `status: success` under the `default`
slice.

## Root Cause

`state._missing_terminal_finish_agent_evidence` collapsed the slice-id
resolution to a single value: `dispatch_intent_slice_id or change_id or
"default"`. When `change_id` was set but the finish-agent result lived
under `"default"` (the normal unsliced path), the validator looked under
`change_id`, found nothing, and returned a blocking finding.

## Mitigation

- When a dispatch-intent slice is present, only that slice is checked
  (preserves the sliced-run contract).
- Otherwise the validator builds `candidate_slice_ids = ["default",
  change_id]` (if change_id differs) and accepts a `finish-agent` success
  under any candidate.
- The returned finding (if any) includes `candidate_slice_ids` for
  diagnostics.

## Detection

`python3 -m pytest tests/test_workflow.py::TestTerminalEvidenceValidation::test_advance_accepts_default_finish_agent_evidence_when_no_dispatch_slice -v`