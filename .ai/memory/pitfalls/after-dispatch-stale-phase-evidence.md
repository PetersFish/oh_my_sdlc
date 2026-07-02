---
id: pitfalls/after-dispatch-stale-phase-evidence
type: pitfalls
title: after-dispatch can preserve stale phase evidence or fake progress when worker contracts are inconsistent
summary: >-
  In workflow runs, `after-dispatch` phase evidence promotion must overwrite
  stale values only from a clean worker success. If success results carry
  blockers, or if phase evidence is only set-once, the run can stay blocked on
  old false evidence or appear to progress with contradictory worker output.
severity: high
evidence_mode: uncommitted_snapshot
linked_commits: []
linked_sessions: []
linked_specs:
  - roadmap-hook-governance-hardening
sync_status: pending_commit
evidence:
  - error: after plan left stale `spec_artifacts_done: false` even after a successful replanned result
  - error: implement-agent reported `status: success` with blockers, causing apply lifecycle confusion
  - failing_test: tests/test_workflow.py
  - fix: `cmd_after_dispatch` only promotes phase evidence from success without blockers and overwrites stale values for the current phase
  - fix: implement-agent contract now requires `blocked` when verification or sync work is still pending
  - fix_location: .ai/workflows/scripts/workflow.py and agents/implement-agent.md
tags:
  - after-dispatch
  - evidence-promotion
  - worker-contract
  - roadmap-agent
  - apply-change
updated_at: 2026-07-02T11:20:00Z
confidence: high
---

# after-dispatch stale phase evidence / contradictory worker success

## Symptom

- `after plan` can leave the run missing the real successful evidence because an
  old false value is never overwritten.
- `after implement` can look like a success while still producing blockers,
  forcing runtime blocking with confusing worker state.

## Root Cause

Two contract failures combined:

1. `cmd_after_dispatch` previously only wrote phase-level evidence when the key
   did not already exist, so stale `false` values survived a later successful
   worker result.
2. `implement-agent` allowed `success + blockers`, which is contradictory for a
   phase-completing worker and makes runtime routing ambiguous.

## Fix

- Promote phase evidence only from `status=success` with no blockers.
- Overwrite stale values for the current phase when a later clean success
  arrives.
- Require `implement-agent` to return `blocked` instead of `success` whenever
  verification, template sync, or distribution work remains.

## Prevention

- Treat `success + blockers` as a contract bug in worker prompts.
- When phase evidence is re-derived from a later successful worker result,
  overwrite the stale value rather than preserving first-write wins semantics.
