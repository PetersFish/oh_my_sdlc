---
id: pitfalls/roadmap-done-hook-recreates-active-run
type: pitfalls
title: roadmap_done_if_relevant hook recreates active run after self-finalization, causing governance-check infinite loop
summary: >-
  When the current workflow run is the linked roadmap_item run being finalized,
  `complete-hook roadmap_done_if_relevant` calls `_finalize_run_to_history()`
  (which deletes `active/<run>.json`), then falls through to `save_run_state()`
  which recreates the active file. The result is the same run coexists in both
  `history/` and `active/`, and `governance-check` forever reports
  `stale_active_roadmap_run`.
severity: high
evidence_mode: commit
linked_commits: ["171d4a8c6e20f59618c4b0c91d5fb1c3e5eb7967"]
linked_sessions: []
linked_specs:
  - workflow-state-machine-contract-enhancements
sync_status: synced
evidence:
  - error: governance-check infinite loop with stale_active_roadmap_run for RM-ORCH-008
  - failing_test: tests/test_workflow.py::TestPostArchiveHooks::test_roadmap_done_hook_does_not_recreate_current_run_after_finalizing_itself
  - test_traceback: "AssertionError: {'version': 1, 'run_id': '2026-06-20-RM-SELF-001' ...} is not None"
  - repro: create active roadmap run with roadmap link showing status=done + completed_at, add roadmap_done_if_relevant to pending_hooks, run complete-hook
  - fix: added self-finalization early-return branch in cmd_complete_hook (workflow.py:1554-1561); when linked run matches current run, finalize-and-return instead of falling through to save_run_state
  - fix_location: .ai/workflows/scripts/workflow.py:1554-1561
  - root_cause: _finalize_run_to_history removes active file but cmd_complete_hook continues to call save_run_state which writes the in-memory state back to active/
tags:
  - roadmap_done_if_relevant
  - governance-check
  - stale_active_roadmap_run
  - complete_hook
  - finalize
  - active-run-resurrection
  - workflow-state-machine
updated_at: 2026-06-26T21:00:00Z
confidence: high
---

# roadmap_done_if_relevant hook recreates active run after self-finalization

## Symptom

`governance-check` loops forever, reporting `stale_active_roadmap_run` on every invocation:

```
Active roadmap_item run "2026-06-26-RM-ORCH-008" remains running after
roadmap item "RM-ORCH-008" became done. The active run is stale.
```

The same run ID exists in both `history/` and `active/`. Running `cancel-run`
removes the active copy, but the hook itself recreates it on every completion.

## Root Cause

In `cmd_complete_hook` (`workflow.py:1545-1562`), when the `roadmap_done_if_relevant`
hook detects the linked roadmap_item run is already done:

1. `_find_active_run_by_subject(...)` returns the current run itself (since the
   current run IS the linked roadmap run)
2. `_finalize_run_to_history(...)` writes a `done` copy to `history/` and
   removes `active/<run_id>.json`
3. But control falls through to the bottom of `cmd_complete_hook`, which calls
   `save_run_state(root, state)` — this writes the in-memory `state` dict back
   to `active/<run_id>.json`, resurrecting the stale active run.

## Fix

Added a self-finalization guard at `workflow.py:1554-1561`:

```python
if linked_item_run.get("run_id") == state.get("run_id"):
    pending.remove(hook_name)
    completed = state.setdefault("completed_hooks", [])
    if hook_name not in completed:
        completed.append(hook_name)
    finalized = _finalize_run_to_history(root, state)
    print(json.dumps(finalized, indent=2))
    return
_finalize_run_to_history(root, linked_item_run)
```

When the linked run IS the current run, the hook finalizes the current state
(with completed hook recorded), outputs the finalized state, and returns
immediately — never reaching the bottom-of-function `save_run_state`.

## Reproduction

```python
state = {
    "run_id": "test-run",
    "primary_subject": {"type": "roadmap_item", "id": "RM-TEST"},
    "context": {"change_id": "test-change", "roadmap_item_id": "RM-TEST"},
    "pending_hooks": ["roadmap_done_if_relevant"],
    "evidence": {
        "roadmap_link": {"count": 1, "items": [{
            "item_id": "RM-TEST", "status": "done",
            "completed_at": "2026-01-01"
        }]},
    },
    ...
}
# complete-hook roadmap_done_if_relevant → active file must not exist after
```

## Prevention

When a hook finalizes the current run (not a different linked run),
`cmd_complete_hook` MUST return immediately after finalization. Do not let
control fall through to `save_run_state`.

Review all hook implementations that call `_finalize_run_to_history` for this
pattern.
