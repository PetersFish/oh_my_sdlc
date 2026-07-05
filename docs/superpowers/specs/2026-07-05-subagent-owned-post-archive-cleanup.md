# Subagent-Owned Lifecycle Cleanup

## Context

The workflow runtime still carries a `post_hooks` / `pending_hooks` model that
was created before the subagent execution model existed. In that older model,
the skill orchestrator needed runtime hooks as a defensive checklist so memory
sync, roadmap transitions, and archive cleanup would not be skipped.

The current architecture has dedicated lifecycle agents. In particular,
`finish-agent` can own archive and post-archive cleanup end to end, while
`roadmap-agent` owns roadmap lifecycle state changes when a roadmap item is the
primary subject.

The current hybrid model creates a split source of truth:

- `finish-agent` can return evidence such as `pending_hooks_empty: true`.
- `workflow.py complete-phase` later enqueues runtime `pending_hooks` from the
  phase definition.
- `workflow.py advance` blocks on the runtime queue even if the agent has
  already completed the cleanup work.

This happened in the lightweight-flow run for
`roadmap-agent-primary-subject-gating`: `finish-agent` reported cleanup success,
but `complete-phase archive_change` then enqueued `memory_sync`, causing
`advance` to fail with `post hook memory_sync is pending, complete hooks first`.

## Goal

Move normal lifecycle cleanup ownership from runtime hooks to subagents.

For normal `sdlc-main` flow execution:

- roadmap lifecycle transitions are handled by phase agents or `roadmap-agent`.
- `archive_change` archives or finalizes the change.
- `post_archive_actions` dispatches `finish-agent` for cleanup.
- `finish-agent` performs memory sync, roadmap completion checks, derived
  artifact sync, commit/push checkpoints, and clean-tree verification.
- The runtime validates cleanup through phase evidence, not through a mutable
  `pending_hooks` queue.

Legacy hook commands may remain for repairing old runs and exceptional recovery,
but the normal workflow path must not enqueue or depend on `post_hooks` for any
phase.

## Non-Goals

- Do not remove `finish-agent`.
- Do not remove `roadmap-agent`.
- Do not remove `complete-hook` in the first implementation pass.
- Do not rewrite the entire workflow runtime.
- Do not change the meaning of `primary_subject.type`.
- Do not weaken roadmap item lifecycle validation for roadmap-governed runs.
- Do not auto-complete memory sync without explicit finish-agent evidence.

## Design Decision

Adopt a compatibility-preserving migration:

```text
Normal sdlc-main execution: subagent-owned cleanup
Legacy repair / recovery: runtime complete-hook remains available
```

This keeps historical runs repairable while removing the double-accounting that
causes normal active runs to disagree with agent evidence.

## Runtime Behavior

### Normal Roadmap Lifecycle Transitions

Normal flow must not use runtime hooks for roadmap transitions. These old hook
responsibilities move to phase agents:

| Old runtime hook | New normal-flow owner |
|---|---|
| `roadmap_spec_link_if_ready` | plan-agent / dev-orchestrator records spec-link evidence, with roadmap-agent used only for roadmap-item primary subjects |
| `roadmap_status_ready_if_linked` | roadmap-agent handles readiness when the primary subject is a roadmap item |
| `roadmap_apply_start_if_ready` | implement/review handoff records apply-start evidence or roadmap-agent performs the state transition for roadmap-item primary subjects |
| `roadmap_done_if_relevant` | finish-agent performs the completion check during `post_archive_actions`, coordinating with roadmap-agent when needed |

The runtime remains responsible for phase sequencing and evidence validation; it
does not own domain-state transitions through normal-path hooks.

### Normal Lightweight Flow

Expected phase sequence:

1. `apply_change`: implement-agent and review-agent complete implementation and
   review.
2. `archive_change`: finish-agent performs the archive/finalization step and
   returns `archive_path_exists`.
3. `post_archive_actions`: finish-agent performs cleanup and returns cleanup
   evidence.
4. `done`: runtime finalizes the run after cleanup evidence is present.

`archive_change` must not enqueue `memory_sync` as a runtime `pending_hook`.

### Normal Spec Flow

Spec-flow uses the same lifecycle split:

1. `archive_change`: finish-agent runs provider-backed archive work and returns
   `archive_path_exists`.
2. `post_archive_actions`: finish-agent runs memory sync, roadmap completion
   checks, derived sync, and final clean-tree checks.

Provider-specific archive behavior remains in `finish-agent`; hook queue
behavior does not remain in the normal path.

### Roadmap-Governed Runs

For `primary_subject.type == "roadmap_item"`, roadmap lifecycle changes remain
explicit and governed. The normal cleanup phase may dispatch or coordinate with
`roadmap-agent` for roadmap completion, but completion is represented as
finish-agent evidence rather than a runtime `roadmap_done_if_relevant` hook.

For `primary_subject.type != "roadmap_item"`, roadmap cleanup evidence records
that no roadmap completion action was required.

### Legacy Repair

`complete-hook` remains available for existing active runs that already contain
`pending_hooks`, dangling archive repair, and manual recovery. Legacy hook
commands keep the current domain validation behavior until a later deletion
change explicitly removes them.

Legacy repair behavior is not used by the normal `sdlc-main` phase path after
this change.

## Evidence Contract

### archive_change

`archive_change` requires only archive evidence:

```json
{
  "archive_path_exists": true
}
```

`finish-agent` must not claim `pending_hooks_empty` during `archive_change`,
because normal cleanup has not happened yet.

### post_archive_actions

`post_archive_actions` requires cleanup evidence:

```json
{
  "memory_sync_done": true,
  "roadmap_done_checked": true,
  "derived_artifacts_synced": true,
  "post_hook_dirty_tree": false,
  "cleanup_complete": true
}
```

`cleanup_complete` is true only when finish-agent has completed all required
post-archive work for the current flow and subject type.

`post_hook_dirty_tree` is retained as an evidence name for continuity, but it no
longer implies a runtime hook queue. It means no cleanup-generated dirty files
remain after post-archive cleanup.

## Workflow Definition Changes

In `.ai/workflows/definitions/sdlc-main.yaml`:

- Remove normal-path `post_hooks` from phases.
- Keep `archive_change.next: post_archive_actions`.
- Change `post_archive_actions.exit_criteria` from `pending_hooks_empty` to
  `cleanup_complete`.
- Add `post_archive_actions.evidence_keys` for cleanup evidence.
- Add replacement evidence keys where old roadmap hooks previously represented
  normal lifecycle transitions.

Expected shape:

```yaml
archive_change:
  exit_criteria:
    - archive_path_exists
  evidence_keys:
    - archive_path_exists
  next: post_archive_actions

post_archive_actions:
  exit_criteria:
    - cleanup_complete
  evidence_keys:
    - memory_sync_done
    - roadmap_done_checked
    - derived_artifacts_synced
    - post_hook_dirty_tree
    - cleanup_complete
  next: done
```

Roadmap-related phase evidence names should be explicit rather than hook-shaped.
For example, use names such as `roadmap_spec_link_checked`,
`roadmap_ready_checked`, `roadmap_apply_start_checked`, and
`roadmap_done_checked` instead of treating `roadmap_*` hook names as runtime
queue entries.

## Runtime Changes

`workflow.py` should preserve legacy hook commands but stop treating phase
`post_hooks` as part of the normal lifecycle.

Required runtime behavior:

- `complete-phase` should not enqueue normal-path hooks for phases that no
  longer define `post_hooks`.
- `advance` should not block on a phase's normal-path `post_hooks` when the
  workflow definition has none.
- Existing active runs with `pending_hooks` continue to be blocked until repaired
  or explicitly completed through the legacy path.
- New runs should only contain `pending_hooks` when created for an explicit
  legacy repair path.
- `after-dispatch` should reject or block `finish-agent` success if:
  - phase is `archive_change`, and
  - the agent claims cleanup-only evidence such as `pending_hooks_empty` or
    `cleanup_complete` before `post_archive_actions`.

## Agent Contract Changes

### finish-agent

Update `finish-agent` to separate archive work from cleanup work.

During `archive_change`, finish-agent owns:

- archive/finalization
- archive evidence
- handoff artifact

During `post_archive_actions`, finish-agent owns:

- pre-cleanup commit checkpoint if needed
- repository memory sync
- roadmap completion check or roadmap-agent coordination
- derived artifact sync
- generated artifact commit/push if needed
- final dirty-tree verification
- cleanup evidence

### dev-orchestrator

Update orchestration guidance:

- Do not expect runtime `post_hooks` in normal flow.
- Dispatch finish-agent in both `archive_change` and `post_archive_actions`.
- Treat post-archive cleanup evidence as the source of truth for completion.
- Treat roadmap lifecycle evidence as agent evidence, not as runtime hook queue
  state.
- Use legacy `complete-hook` only for repairing pre-existing pending hook state.

## Acceptance Criteria

1. Normal `archive_change` completion does not add `memory_sync` to
   `pending_hooks`.
2. Normal `archive_change` advances to `post_archive_actions` after
   `archive_path_exists` evidence is present.
3. `post_archive_actions` dispatches finish-agent and requires
   `cleanup_complete` evidence before advancing.
4. `post_archive_actions` requires evidence for memory sync, roadmap completion
   check, derived artifact sync, and clean-tree verification.
5. `finish-agent` success in `archive_change` is blocked if it claims
   cleanup-only evidence before `post_archive_actions`.
6. Existing runs that already contain `pending_hooks` remain repairable through
   `complete-hook`.
7. Roadmap-governed runs still perform roadmap completion checks, but normal
   completion is represented as finish-agent evidence instead of runtime hooks.
8. Non-roadmap spec/lightweight runs record that roadmap completion was checked
   and not required.
9. Normal roadmap lifecycle transitions do not enqueue `roadmap_*` runtime hooks
   in new runs.
10. Legacy repair commands still validate and complete existing `roadmap_*` and
    `memory_sync` pending hooks.
11. `tests/test_workflow.py` covers the new phase progression and legacy repair
   behavior.
12. `tests/test_wrapper_contracts.py` covers updated finish-agent and
    dev-orchestrator prompt contracts.
13. Workflow template copies and distributed agent copies are synced.

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/definitions/sdlc-main.yaml` | Remove normal-path post hooks and make post-archive cleanup evidence-driven |
| `.ai/workflows/scripts/workflow.py` | Preserve legacy complete-hook path, reject premature cleanup claims, rely on phase evidence for normal flow |
| `skills/sdlc-project-bootstrap/templates/workflow/` | Sync workflow runtime and definition templates |
| `agents/finish-agent.md` | Split archive_change and post_archive_actions responsibilities |
| `agents/dev-orchestrator.md` | Route post_archive_actions through finish-agent instead of hook queue expectations |
| distributed agent copies | Sync updated agent prompts |
| distributed workflow template copies | Sync updated workflow templates |
| `tests/test_workflow.py` | Add phase progression, cleanup evidence, and legacy repair tests |
| `tests/test_wrapper_contracts.py` | Add prompt-contract tests for hook-free normal flow |

## Migration Notes

Existing active runs may still contain `pending_hooks`. They should not be
rewritten silently. Operators can finish those runs through the current legacy
repair command:

```bash
python3 .ai/workflows/scripts/workflow.py --root . complete-hook --hook memory_sync --resolution synced
```

New runs created after this change should not enqueue normal cleanup hooks.

## Risks

- If finish-agent evidence is too weak, cleanup can appear complete without
  durable memory sync or clean-tree verification. Mitigate with explicit
  evidence keys and tests.
- If roadmap completion validation is moved without preserving current checks,
  roadmap-governed runs can regress. Mitigate by porting the validation into
  finish-agent / roadmap-agent coordination tests.
- If legacy hook behavior is removed too early, existing active runs become
  harder to repair. Keep `complete-hook` in the first implementation pass.
