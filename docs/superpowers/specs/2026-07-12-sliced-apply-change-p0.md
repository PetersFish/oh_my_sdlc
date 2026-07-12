# Sliced Apply-Change Orchestration P0

## Context

Large `apply_change` work can push one `implement-agent` session into excessive context. P0 turns the existing `slice_id` label into a governed lifecycle with bounded work packages, fresh agent contexts, slice review, deterministic Git boundaries, and final aggregate review.

Existing Superpowers or OpenSpec artifacts without slice metadata must first be assessed by `plan-agent`. Automatic compaction, token budgeting, and parallel slices are deferred.

## Goals

- `plan-agent` decides `single_slice`, `multi_slice`, or `blocked`.
- Runtime persists slice graph, lifecycle state, evidence, handoffs, and Git refs.
- `dev-orchestrator` dispatches exactly one runtime-selected slice at a time.
- Each slice uses a fresh `implement-agent` context and passes review.
- Slice review uses `base_ref..<head_ref>` as the authoritative scope.
- All required slices must pass aggregate review before `apply_change` completes.
- `todowrite` remains session-local.

## Non-Goals

- No context compaction or token-budget enforcement.
- No parallel execution, per-slice branches/worktrees, join heads, or integration slices.
- No technical decomposition by `dev-orchestrator`.
- No separate workflow run per slice.
- No exactly-one-commit rule or apply-phase history rewriting.
- No public `slice-start` or `slice-complete` on the normal path.

## Decisions

### 1. Plan-Agent Owns Slicing

For new planning and existing artifacts without slice metadata, `plan-agent` returns:

```json
{
  "slicing_assessment": {
    "decision": "single_slice|multi_slice|blocked",
    "confidence": "high|medium|low",
    "reasons": [],
    "signals": {
      "independent_behaviors": 0,
      "dependency_layers": 0,
      "expected_core_files": 0,
      "cross_module_boundaries": 0,
      "independent_verification_boundaries": 0,
      "migration_or_compatibility_work": false,
      "multiple_external_integrations": false,
      "high_debug_uncertainty": false
    },
    "implementation_slices": []
  }
}
```

Existing artifacts use `planning_action=assess_implementation_slicing`. Counts are heuristics, not hard thresholds. Low-confidence missing detail returns `blocked`; task numbering alone never defines slices.

### 2. Slice Contract

Each multi-slice entry contains:

```json
{
  "slice_id": "workflow-slice-state",
  "title": "Persist implementation slice state",
  "task_refs": ["1.1", "1.2"],
  "depends_on": [],
  "objective": "One independently verifiable behavior.",
  "scope": {"expected_paths": []},
  "acceptance_criteria": [],
  "verification_commands": [],
  "required_context_paths": [
    "docs/superpowers/specs/2026-07-12-sliced-apply-change-p0.md"
  ],
  "required": true
}
```

Ids are unique and stable; `aggregate` is reserved; dependencies are local and acyclic; every required task is covered exactly once unless cross-cutting; declaration order is stable. A valid single-slice assessment materializes required slice `default`.

### 3. Runtime State

```json
{
  "implementation": {
    "strategy": "sequential",
    "slicing_assessment": {
      "status": "not_required|pending|completed|blocked",
      "decision": "single_slice|multi_slice",
      "assessed_by": "plan-agent",
      "assessment_handoff_path": "...",
      "reasons": []
    },
    "aggregate_review_status": "pending|ready|passed|blocked",
    "active_slice_id": null,
    "slices": [{
      "slice_id": "default",
      "depends_on": [],
      "required": true,
      "status": "pending|ready|in_progress|in_review|blocked|completed|cancelled",
      "attempt_count": 0,
      "block": null,
      "base_ref": "",
      "head_ref": "",
      "accepted_head_ref": "",
      "commit_refs": [],
      "implement_evidence": {},
      "review_evidence": {},
      "handoff_paths": []
    }]
  }
}
```

Implementation dispatch is rejected while assessment is pending or blocked. Top-level run and phase state remain authoritative.

### 4. Sequential Dependency Execution

P0 is dependency-aware but strictly sequential. At most one slice is `in_progress` or `in_review`. If A and B are both ready and C depends on both, declaration order produces:

```text
implement/review A -> implement/review B -> implement/review C -> aggregate review
```

C becomes ready only after A and B are `completed` with `accepted_head_ref`. Parallel execution is P1.

### 5. Runtime-Owned Selection

`slice-next` is read-only and returns exactly one of:

- `dispatch_slice` with one declaration-ordered ready slice;
- `dispatch_aggregate_review`;
- `all_slices_and_aggregate_complete`;
- `no_ready_slice` diagnostics.

A slice is ready only when dependencies are accepted, it is not cancelled, and no other slice is active. `dev-orchestrator` dispatches only the returned slice.

### 6. Atomic Hook Transitions

```text
ready -> before-dispatch(implement-agent) -> in_progress
in_progress -> after-dispatch(implement success) -> in_review
in_review -> after-dispatch(review pass) -> completed
```

`before-dispatch` validates phase, assessment, exact selected slice, no active sibling, and Git base. `after-dispatch` persists evidence under the exact slice. Implement success never completes a slice. Review pass records `accepted_head_ref=head_ref`, clears `active_slice_id`, and recomputes readiness. Requested changes preserve original `base_ref` and attempt history.

### 7. Commands

```bash
workflow.py slice-status [--slice-id <id>]
workflow.py slice-next
workflow.py slice-block --slice-id <id> --value '<json>'
workflow.py slice-resume --slice-id <id>
workflow.py slice-cancel --slice-id <id> --reason <reason>
```

Normal progression remains inside dispatch hooks. `slice-resume` means `blocked -> ready`. Required cancellation needs explicit decision evidence. Run-level `start`, `resume`, `block`, and `done` retain their meanings.

### 8. Local Blocks

A blocked slice does not automatically block the run. The run blocks only when no slice is active, no required slice is ready, incomplete required work is blocked or transitively blocked, and aggregate review cannot begin.

### 9. Fresh Context and Handoffs

Every slice gets a new implement-agent task with only its contract, runtime context, approved design artifacts, direct dependency handoffs, repository/worktree state, and provider contract. Todo is reconstructed locally.

Handoffs live under:

```text
.ai/workflows/runs/active/<run_id>/handoffs/<slice_id>/implement-agent.md
.ai/workflows/runs/active/<run_id>/handoffs/<slice_id>/review-agent.md
```

They record task refs, decisions, TDD state, changed files, verification, blockers, and dependent-slice constraints.

### 10. Sequential Commit Boundary

All P0 slices use one governed feature branch/worktree. Before a slice starts, source/test state is clean and `base_ref=HEAD`; later slices start from the previous accepted sequential head.

Before success, implement-agent verifies, commits only current-slice source/test changes, returns `base_ref`, `head_ref`, ordered `commit_refs[]`, and leaves source/test state clean. Multiple contiguous commits are allowed. Review corrections append commits while preserving original `base_ref`.

```text
next_slice.base_ref == previous_accepted_slice.accepted_head_ref
```

Unrelated dirty state blocks with `slice_start_dirty_worktree`; the worker must not stash, discard, or commit it.

### 11. Review Scope

Slice review derives scope from Git:

```bash
git diff --name-status <base_ref>..<head_ref>
git diff --stat <base_ref>..<head_ref>
git diff <base_ref>..<head_ref> -- <path>
```

Worktree mode uses `git -C <worktree_path>`. `changed_files[]` enriches but does not define scope. Evidence mismatch produces `review_slice_change_set_mismatch`.

### 12. Aggregate Review

After required slices complete, aggregate review uses reserved scope `aggregate` and range:

```text
workflow parent_ref .. latest accepted slice head_ref
```

It validates requirement coverage, cross-slice integration, final regression, task completion, provider verification, contiguous accepted ranges, no unresolved blocks, and no uncommitted source/test changes. Only a pass allows `complete-phase apply_change`.

### 13. Legacy Compatibility

Legacy unsliced execution uses `default` only after valid single-slice assessment or explicit compatibility handling. Evidence remains slice-strict.

## Agent Changes

- `plan-agent`: slicing assessment and decomposition contract.
- `dev-orchestrator`: missing-slice assessment routing, `slice-next` loop, aggregate review routing, no decomposition or concurrency.
- `implement-agent`: one slice, local todo, clean base, commit range, verification evidence, durable checkpoint.
- `review-agent`: `review_scope=slice|aggregate`, commit-range review, ref/worktree validation.

## Affected Areas

- `.ai/workflows/scripts/workflow.py`
- `.ai/workflows/scripts/workflow_runtime/state.py`
- existing dispatch and command runtime modules
- `skills/sdlc-project-bootstrap/templates/workflow/`
- canonical plan/dev-orchestrator/implement/review agent prompts
- `.opencode`, `.claude`, `.cursor` distributed copies
- runtime, orchestrator, and wrapper-contract tests

Implementation must resolve current module paths instead of creating duplicate conceptual modules.

## Acceptance Criteria

- Existing apply-ready artifacts without slices route to plan-agent assessment.
- Structured single/multi/blocked assessment is validated and persisted.
- Runtime rejects invalid ids, coverage, dependencies, cycles, and multiple active slices.
- `slice-next` is deterministic and non-mutating.
- Normal transitions are atomic with dispatch hooks.
- Every slice uses a fresh context and durable handoff.
- Successful implementation has a valid contiguous commit range.
- Slice review uses `base_ref..<head_ref>` and stores `accepted_head_ref`.
- Review retries preserve original base and append correction commits.
- A and B execute sequentially even when both are ready; C waits for both accepted heads.
- Aggregate review is mandatory before `apply_change` completion.
- Live runtime, templates, canonical agents, and distributed copies remain synchronized.
- Existing unsliced run-level semantics continue to pass.
