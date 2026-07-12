# Sliced Apply-Change P0 Sequential Execution Clarification

## Context

The base P0 design and its slicing-assessment / commit-range addendum introduce dependency-aware implementation slices, fresh implement-agent dispatches, per-slice review, and deterministic Git review boundaries.

A dependency graph may contain multiple slices that are simultaneously dependency-ready. For example:

```text
A depends_on []
B depends_on []
C depends_on [A, B]
```

Although A and B are logically independent, executing them concurrently requires capabilities that are not part of the P0 reliability baseline: separate slice worktrees and branches, multiple active slice state, independent commit DAGs, accepted-head integration, merge-conflict governance, and an integration gate before C.

This clarification makes the P0 execution policy explicit: dependency-aware does not mean parallel. P0 remains strictly sequential. Parallel slice execution and dependency-join integration are deferred to P1.

This document is normative for:

- `docs/superpowers/specs/2026-07-12-sliced-apply-change-orchestration-design.md`
- `docs/superpowers/specs/2026-07-12-sliced-apply-change-orchestration-addendum.md`

Where those documents describe ready slices or independent blocked slices, this clarification controls P0 dispatch concurrency.

## Goals / Non-Goals

**Goals:**

- Make P0 slice execution strictly sequential and deterministic.
- Preserve dependency-aware readiness while allowing only one active implementation or slice review at a time.
- Keep each accepted slice commit range contiguous on one sequential feature branch.
- Ensure a dependent slice starts from the latest accepted predecessor state on that branch.
- Prevent implement-agent, review-agent, or dev-orchestrator from creating per-slice branches or worktrees for parallel execution in P0.
- Record parallel execution and dependency-join integration as explicit P1 follow-up scope.

**Non-Goals:**

- Do not execute independent ready slices concurrently.
- Do not introduce `strategy=dependency_parallel` in P0.
- Do not replace `active_slice_id` with multiple active slice ids in P0.
- Do not create one branch or worktree per slice in P0.
- Do not add runtime-generated integration slices in P0.
- Do not merge independently reviewed slice heads before dependent work in P0.
- Do not add `slice-ready` as a parallel batch-dispatch API in P0.
- Do not implement path-overlap or symbol-overlap based parallel eligibility in P0.

## Decisions

### Decision 1: P0 Supports Dependency-Aware Sequential Execution Only

P0 supports a dependency graph because dependencies determine when a slice is eligible to run. The graph does not authorize concurrent execution.

The runtime strategy is fixed to:

```json
{
  "implementation": {
    "strategy": "sequential",
    "active_slice_id": null
  }
}
```

At most one slice may have either of these statuses:

```text
in_progress
in_review
```

Runtime validation must reject states containing multiple active slices, even when those slices have no dependency relationship.

### Decision 2: `slice-next` Returns One Slice Using Declaration Order

When several slices are dependency-ready, `slice-next` returns exactly one slice.

Selection order is:

1. include only required, non-cancelled slices whose dependencies are completed;
2. exclude slices already active, completed, or blocked;
3. select the first eligible slice in the persisted declaration order.

For:

```text
A depends_on []
B depends_on []
C depends_on [A, B]
```

and declaration order `A, B, C`, the P0 execution order is:

```text
implement A
review A
accept A
implement B
review B
accept B
implement C
review C
accept C
aggregate review
```

The runtime must not return both A and B in one dispatch result.

### Decision 3: Independent Ready Work Does Not Keep a Blocked Run Progressing Concurrently

The base design allows a slice-scoped block to remain local when another independent slice is ready. Under P0, this means the runtime may select that other slice on the next sequential dispatch; it does not mean both slices may execute at once.

Example:

```text
A: blocked
B: ready and independent
run: running
active_slice_id: null
```

The next legal action may be sequential dispatch of B. While B is `in_progress` or `in_review`, no redispatch of A or any other slice is allowed.

### Decision 4: P0 Uses One Sequential Feature Branch and Commit Chain

All P0 slices execute on the same governed feature branch/worktree selected by the workflow runtime.

Each slice has a contiguous commit range:

```text
slice A: base_ref=P0, head_ref=A2
slice B: base_ref=A2, head_ref=B1
slice C: base_ref=B1, head_ref=C2
```

The invariant is:

```text
next_slice.base_ref == previous_accepted_slice.accepted_head_ref
```

For a slice with multiple dependencies, its `base_ref` is the current sequential branch HEAD after every dependency slice has been accepted. No merge or join commit is needed because predecessor slices have already been applied serially to the same branch.

### Decision 5: Slice Review Continues To Use Its Exact Commit Range

Sequential execution preserves unambiguous review scope:

```bash
git diff <slice.base_ref>..<slice.head_ref>
```

For worktree mode:

```bash
git -C <worktree_path> diff <slice.base_ref>..<slice.head_ref>
```

Review-agent must not use the full workflow range for normal slice review. The full range remains reserved for aggregate review.

Review rejection preserves the slice's original `base_ref`; correction commits advance only its `head_ref`. The next slice cannot start until the current slice has an `accepted_head_ref`.

### Decision 6: Dependency Completion Is Evaluated After Slice Review Acceptance

A dependency is satisfied only when the dependency slice is `completed` and has review evidence for its current `accepted_head_ref`.

Implement-agent success alone does not satisfy a dependency.

For C depending on A and B:

```text
C ready iff:
  A.status == completed
  AND A.accepted_head_ref is present
  AND B.status == completed
  AND B.accepted_head_ref is present
  AND no slice is active
```

Because A and B execute serially on one branch, C begins from the branch HEAD containing both accepted changes.

### Decision 7: Plan-Agent May Describe Parallel Potential but P0 Ignores It

Plan-agent may identify that two slices are logically independent, but P0 structured output must not require parallel execution metadata.

If planning output contains advisory fields such as:

```json
{
  "parallel_eligible": true,
  "parallel_group": "group-1"
}
```

P0 runtime must either ignore those optional advisory fields or reject them if the schema is intentionally strict. It must never use them to create concurrent dispatches.

The implementation plan must not add P1 fields merely to anticipate future behavior unless they are explicitly optional and have no P0 state-transition effect.

### Decision 8: Parallel Execution Is a Separate P1 Capability

P1 may introduce:

- `strategy=dependency_parallel`;
- multiple active slice state derived from slice statuses;
- one branch and worktree per parallel slice;
- slice-local `base_ref..<head_ref>` review ranges;
- accepted slice heads that diverge from a common parent;
- runtime-generated integration/join slices;
- integration branch or integration worktree ownership;
- merge-conflict handling and integration review;
- creation of dependent slice C from an accepted integration head;
- parallel capacity controls such as `max_parallel_slices`;
- path/symbol overlap analysis for parallel eligibility.

None of these are prerequisites, hidden extensions, or implied acceptance criteria for P0.

## P0 Flow

```text
plan-agent
  |- assess slicing when required
  |- produce dependency-aware implementation_slices[]
  v
runtime
  |- strategy = sequential
  |- compute dependency-ready slices
  |- choose first ready slice by declaration order
  v
implement-agent A
  |- work on shared governed feature branch/worktree
  |- commit A range
  v
review-agent A
  |- review A.base_ref..A.head_ref
  |- record A.accepted_head_ref
  v
runtime
  |- clear active_slice_id
  |- select next declaration-ordered ready slice
  v
implement-agent B
  |- base_ref = A.accepted_head_ref
  |- commit B range
  v
review-agent B
  |- review B.base_ref..B.head_ref
  |- record B.accepted_head_ref
  v
runtime
  |- A and B dependencies now satisfied
  |- select C
  v
implement-agent C
  |- base_ref = B.accepted_head_ref
  |- branch already contains accepted A + B changes
  v
review-agent C
  v
aggregate review
```

## Agent Contract Clarifications

### `plan-agent`

- Produce dependency-aware slices without requiring parallel execution.
- Preserve deterministic declaration order.
- Do not encode parallel execution as necessary for correctness.
- Keep slicing assessment focused on bounded context, technical cohesion, recoverability, and independent review boundaries.

### `dev-orchestrator`

- Call `slice-next` and dispatch only the single returned slice.
- Never dispatch two implement-agent lifecycle tasks concurrently in P0.
- Do not create per-slice branches, worktrees, merge commits, or integration slices.
- Wait for slice review acceptance before querying and dispatching the next slice.

### `implement-agent`

- Execute in the runtime-provided shared feature branch/worktree.
- Require `base_ref` to equal the current accepted sequential branch HEAD.
- Commit only the current slice range.
- Never begin adjacent or concurrently ready slices.

### `review-agent`

- Review only the selected slice commit range.
- Confirm the reported `base_ref` is the previously accepted sequential head.
- Confirm the current slice `head_ref` is on the same sequential feature branch.
- Do not perform cross-branch merge or integration review in P0.

### Workflow Runtime

- Enforce `strategy=sequential`.
- Maintain a single optional `active_slice_id`.
- Reject multiple active slice states.
- Return one ready slice from `slice-next`.
- Set a dependent slice ready only after all dependencies have accepted review heads.
- Validate contiguous accepted commit ranges on the sequential feature branch.

## Affected P0 Documents and Contracts

| Artifact | Clarification |
|---|---|
| `2026-07-12-sliced-apply-change-orchestration-design.md` | `dependency-aware` is sequential in P0; at most one active slice. |
| `2026-07-12-sliced-apply-change-orchestration-addendum.md` | Commit ranges form one contiguous sequential branch chain. |
| `agents/plan-agent.md` | Slicing does not imply or require parallel metadata. |
| `agents/dev-orchestrator.md` | Dispatch exactly one runtime-selected slice and wait for review acceptance. |
| `agents/implement-agent.md` | Use shared governed branch/worktree and current accepted head as base. |
| `agents/review-agent.md` | Review exact sequential slice range; no cross-branch integration. |
| Workflow runtime and templates | Enforce one active slice and declaration-order `slice-next`. |
| Runtime/orchestrator contract tests | Prove independent ready slices are still serialized. |

## Risks / Trade-offs

**Lost wall-clock parallelism:** Independent slices execute serially. P0 accepts this cost to stabilize state transitions, commit attribution, review retry behavior, and workflow recovery first.

**Longer shared branch history:** Each accepted slice appends commits to one feature branch. Commit-range review keeps attribution deterministic, and final squash remains a finish-stage policy decision.

**Dependency graph may look more capable than execution strategy:** The graph models correctness and readiness, not concurrency. Agent prompts and runtime outputs must use explicit sequential terminology to prevent over-interpretation.

**P1 migration:** Future parallel execution will change Git topology and runtime concurrency semantics. P1 must be designed as an explicit strategy addition rather than weakening P0 invariants in place.

## Acceptance Criteria

- P0 runtime exposes only `strategy=sequential` for sliced apply-change execution.
- At most one slice may be `in_progress` or `in_review` at any time.
- Runtime rejects state containing multiple active slices.
- When A and B are both ready, `slice-next` returns exactly one based on declaration order.
- Dev-orchestrator never concurrently dispatches A and B in P0.
- The next slice cannot start until the current slice has passed review and recorded `accepted_head_ref`.
- Slice B starts with `base_ref` equal to slice A's `accepted_head_ref` when A is the previously accepted sequential slice.
- Slice C depending on A and B becomes ready only after both have passed review.
- C starts from the sequential branch HEAD containing accepted changes from both A and B.
- No P0 implementation creates per-slice branches, per-slice worktrees, integration branches, or integration slices.
- Slice review remains authoritative over `base_ref..<head_ref>`.
- Aggregate review remains authoritative over `workflow parent_ref..<latest accepted head_ref>`.
- Contract tests cover two independent ready slices and prove they execute serially.
- Contract tests cover a join dependency `C depends_on [A, B]` and prove C starts only after both sequential reviews pass.
- Parallel slice execution, multiple active slices, and dependency-join integration remain explicitly deferred to P1.
