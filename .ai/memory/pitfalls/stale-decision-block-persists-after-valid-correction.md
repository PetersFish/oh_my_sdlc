---
id: pitfalls/stale-decision-block-persists-after-valid-correction
type: pitfalls
title: Recording a corrected valid branch_finish_decision leaves stale decision block intact, blocking guarded dispatch and advancement
summary: cmd_record_context updated context but preserved status=blocked and the decision block, so a run blocked for a missing/invalid branch_finish_decision could not recover by recording a corrected value — guarded dispatch (before-dispatch) and advancement still rejected the run even though the original decision error was resolved.
sync_status: synced
evidence_mode: commit
linked_commits: ["4523caf4297c8b933fe7d234ed54b54ae7b21681"]
linked_specs: [repair-workflow-decision-block-unlock]
linked_sessions: []
updated_at: 2026-07-11T00:00:00Z
confidence: high
tags: [workflow, decision-block, branch-finish, stale-state, record-context, dispatch]
---

# Stale decision block persists after valid correction

## Failure

When a workflow run was blocked for a missing or invalid `branch_finish_decision`, recording a corrected valid value through `record-context` updated the run's `context` field but left `status: blocked` and the original `block` intact. Subsequent guarded commands (`before-dispatch` for finish-agent, `advance` for phase-complete runs) still rejected the run with `run_is_blocked`, even though the decision error that caused the block had been resolved.

## Root Cause

`cmd_record_context` treated context recording as a pure context-field mutation. It did not evaluate whether the newly recorded key/value resolved the currently persisted block. The branch-finish gate is evaluated later in `cmd_before_dispatch`, so the blocked status persisted across the context write and blocked all downstream guarded paths.

## Fix

`cmd_record_context` now evaluates reconciliation predicates after building and validating the tentative context: run is blocked, recorded key is `branch_finish_decision`, tentative decision status is `ok`, and the persisted block represents the branch-decision gate (identified by its decision-specific reason/type/action metadata). When all hold, the same state save sets `status` to `running` and `block` to `None` atomically with the context write. Unrelated blocks and invalid corrections are preserved.

## Detection

Executable behavioral regression tests in `tests/test_workflow.py` invoke the CLI helper against temporary workflow state:
- Missing-to-valid correction transitions to `running` with `block: null` and allows `before-dispatch`/`advance` to proceed.
- Invalid correction remains blocked.
- Valid decision does not clear an unrelated block.
- Main checkout without a branch gate is not spuriously unblocked.

## Lessons

- A mutation that validates and stores one field must consider whether that field resolves an existing blocked state; otherwise the run becomes internally contradictory (valid context + stale block).
- Block reconciliation should be narrow and decision-specific, not a generic recompute-all-blocks pass, to avoid clearing unrelated worker/hook/evalops/domain blocks.
- Block recognition must use structured reason/type/action metadata, not message substring matching.