# Sliced Apply-Change Orchestration Design

## Context

The current `dev-orchestrator` lifecycle dispatches one `implement-agent` for the whole `apply_change` phase. For large changes, a single implementation session can accumulate very large context, repeated tool output, debugging history, and temporary todo state. Even when the model context window can technically hold that history, token cost and execution reliability degrade as the session grows.

The existing architecture already contains the foundations for bounded implementation work:

- `implement-agent` is defined to handle exactly one bounded work package per dispatch.
- Lifecycle hooks accept an optional `slice_id`.
- Agent evidence and handoffs can be stored under a slice-specific path.
- `workflow.py` is the sole owner of workflow state transitions.
- `dev-orchestrator` is a routing coordinator and must not perform technical task decomposition.

However, the runtime does not yet persist an implementation slice graph, select the next ready slice, or advance slice state from normal `before-dispatch` / `after-dispatch` results. As a result, `slice_id` is currently a dispatch label rather than a complete execution lifecycle.

This P0 change introduces deterministic, sequential, dependency-aware implementation slices for `apply_change`. Each slice is executed in a fresh `implement-agent` dispatch context, reviewed independently, and persisted through workflow state and handoff artifacts. Context compaction and token-budget enforcement are intentionally deferred to later work.

## Goals / Non-Goals

**Goals:**

- Let `plan-agent` define a structured, dependency-aware set of implementation slices.
- Persist slice definitions and slice execution state in the workflow run state.
- Let `workflow.py` deterministically select the next ready slice.
- Dispatch a fresh `implement-agent` execution for each slice.
- Keep `dev-orchestrator` limited to routing; it selects runtime-approved slices but does not decompose implementation work.
- Integrate normal slice state transitions into existing `before-dispatch` and `after-dispatch` hooks.
- Review every implementation slice before it becomes complete.
- Require an aggregate review after all required slices are complete and before `apply_change` can complete.
- Treat workflow state, slice handoffs, verification evidence, and the live worktree as persistent sources of truth; `todowrite` remains session-local execution state.
- Preserve backward compatibility for existing unsliced runs through the `default` slice.

**Non-Goals:**

- Do not add automatic context compaction.
- Do not add token counting or context-budget enforcement.
- Do not support parallel slice execution in P0.
- Do not let `dev-orchestrator` create, merge, reorder, or technically redefine slices.
- Do not make todo state durable across sessions.
- Do not introduce a separate workflow run per slice.
- Do not require a public `slice-start` or `slice-complete` command on the normal success path.
- Do not change finish-agent ownership of archive and post-archive work.

## Decisions

### Decision 1: `plan-agent` Owns Technical Slice Decomposition

`plan-agent` must produce `implementation_slices[]` as part of its structured planning result when the planned change is large enough to require more than one bounded implementation package.

Each slice must contain:

```json
{
  "slice_id": "workflow-slice-state",
  "title": "Persist implementation slice state",
  "task_refs": ["1.1", "1.2", "1.3"],
  "depends_on": [],
  "objective": "Persist deterministic slice lifecycle state in the workflow run.",
  "scope": {
    "expected_paths": [
      ".ai/workflows/scripts/workflow_runtime/state.py",
      "tests/test_workflow.py"
    ]
  },
  "acceptance_criteria": [
    "Slice definitions survive workflow resume",
    "Legacy unsliced runs remain valid"
  ],
  "verification_commands": [
    "python3 -m pytest tests/test_workflow.py -k slice_state -v"
  ],
  "required_context_paths": [
    "docs/superpowers/specs/2026-07-12-sliced-apply-change-orchestration-design.md"
  ],
  "required": true
}
```

Rules:

- `slice_id` must be unique within the run and stable across resume.
- `depends_on` may reference only slice ids in the same run.
- The dependency graph must be acyclic.
- A slice should represent one independently verifiable implementation behavior.
- Tests and implementation for one behavior should remain in the same slice when separating them would prevent independent verification.
- `dev-orchestrator` must never infer slices from task numbering such as `1.1-1.7` by itself.
- If no explicit slice set is produced, runtime creates one backward-compatible required slice with `slice_id=default`.

### Decision 2: Workflow State Is the Slice Lifecycle Source of Truth

The run state gains an `implementation` object:

```json
{
  "implementation": {
    "strategy": "sequential",
    "aggregate_review_status": "pending",
    "active_slice_id": "workflow-slice-state",
    "slices": [
      {
        "slice_id": "workflow-slice-state",
        "title": "Persist implementation slice state",
        "task_refs": ["1.1", "1.2", "1.3"],
        "depends_on": [],
        "required": true,
        "status": "in_progress",
        "attempt_count": 1,
        "block": null,
        "implement_evidence": {},
        "review_evidence": {},
        "handoff_paths": []
      }
    ]
  }
}
```

Allowed slice statuses:

- `pending` — dependencies are not yet satisfied.
- `ready` — all required dependencies are complete and the slice may be dispatched.
- `in_progress` — implementation has been dispatched or implementation changes are awaiting slice review.
- `in_review` — implement-agent succeeded and review-agent is the next legal lifecycle worker.
- `blocked` — the slice cannot currently progress.
- `completed` — slice review passed.
- `cancelled` — the slice was explicitly cancelled under a valid user or runtime decision.

`implementation.active_slice_id` is optional and identifies the slice currently owned by a lifecycle dispatch. P0 uses `strategy=sequential`, so at most one non-terminal slice may be `in_progress` or `in_review` at a time.

The top-level run remains the source of truth for run and phase state. Slice state must not replace `current_phase`, top-level `status`, phase evidence, or normal workflow gates.

### Decision 3: Readiness Is Deterministic and Runtime-Owned

A slice is ready when all of the following are true:

- Its status is `pending` or `ready`.
- Every required slice in `depends_on` has status `completed`.
- It has not been cancelled.
- No other slice is currently `in_progress` or `in_review` under the sequential strategy.

Runtime exposes a read-only command:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-next
```

`slice-next`:

- Returns the next ready slice using declaration order as the deterministic tie-breaker.
- Does not modify state.
- Returns a structured `no_ready_slice` result when no slice is ready.
- Distinguishes `all_required_slices_completed` from `blocked_dependency_graph`.

`dev-orchestrator` may only dispatch the slice returned by runtime. It must not choose among ready slices using implementation judgment.

### Decision 4: Normal State Advancement Happens Inside Existing Dispatch Hooks

P0 does not require a public `slice-start` command for normal dispatch and does not require a public `slice-complete` command for normal success.

Normal transitions are atomic with the lifecycle hooks:

```text
pending/ready
  -- before-dispatch(implement-agent, slice_id) -->
in_progress
  -- after-dispatch(implement-agent success, slice_id) -->
in_review
  -- after-dispatch(review-agent passed, slice_id) -->
completed
```

This avoids an inconsistent state where `slice-start` succeeds but the worker is never dispatched, or where a manual `slice-complete` occurs without accepted review evidence.

`before-dispatch --agent implement-agent --slice-id <id>` must:

- Validate that the run is in `apply_change`.
- Validate that `<id>` is the runtime-selected ready slice.
- Reject dispatch when another slice is active.
- Atomically set the slice to `in_progress`.
- Increment `attempt_count`.
- Set `implementation.active_slice_id`.
- Return the slice contract in `runtime_context` or an adjacent structured field.

`after-dispatch --agent implement-agent --slice-id <id>` must:

- Persist implement-agent evidence under that exact slice.
- On success, set the slice to `in_review` and recommend `dispatch_review_agent` for the same slice.
- On blocked or failed result, set the slice to `blocked` with a slice-scoped block unless another explicit runtime rule applies.
- Never mark the slice completed directly from implement-agent success.

`before-dispatch --agent review-agent --slice-id <id>` must:

- Require the same slice to be `in_review`.
- Forward the slice contract and latest successful implement evidence.
- Reject review of another slice.

`after-dispatch --agent review-agent --slice-id <id>` must:

- Persist review evidence under that exact slice.
- On passed review, atomically set the slice to `completed`, clear `active_slice_id`, and recompute dependent slice readiness.
- On requested changes, return the slice to `ready` or `in_progress` according to the existing review result contract, while preserving prior attempt history.
- On blocked or failed review, set a slice-scoped block.

### Decision 5: Slice Commands Are Reserved for Query and Exceptional Control

Command names use the `slice-*` resource prefix so slice-level actions remain visibly separate from run-level commands such as `start`, `resume`, `block`, and `done`.

P0 adds:

```bash
workflow.py slice-status [--slice-id <id>]
workflow.py slice-next
workflow.py slice-block --slice-id <id> --value '<json>'
workflow.py slice-resume --slice-id <id>
workflow.py slice-cancel --slice-id <id> --reason <reason>
```

Semantics:

- `slice-status` is read-only.
- `slice-next` is read-only and deterministic.
- `slice-block` is for explicit exceptional control when normal `after-dispatch` processing cannot represent the block.
- `slice-resume` moves `blocked -> ready`; it does not move directly to `in_progress`.
- `slice-cancel` requires a reason. Cancelling a required slice requires an explicit user decision or approved runtime exception.

Existing run-level commands keep their current meanings:

- `start` creates or starts a workflow run.
- `resume` resumes a workflow run.
- `block` blocks the workflow run.
- `done` terminates the workflow run successfully.

Slice commands must not overwrite the top-level run block unless runtime determines the entire run cannot progress.

### Decision 6: Slice Blocks Remain Local Until the Run Cannot Progress

A blocked slice does not automatically block the whole workflow run.

Example:

```text
slice-A: blocked
slice-B: ready and independent
run: running
```

The run becomes blocked only when:

- No slice is active.
- No required slice is ready.
- At least one incomplete required slice is blocked or transitively depends on a blocked slice.
- Aggregate review cannot legally start.

When this occurs, runtime sets a top-level block such as:

```json
{
  "type": "slice_execution_blocked",
  "reason": "no_ready_required_slice",
  "blocked_slice_ids": ["slice-A"],
  "dependent_slice_ids": ["slice-B"],
  "next_allowed": [
    "slice-resume",
    "slice-cancel",
    "cancel_run"
  ]
}
```

The slice-local block remains stored on the slice. The top-level block is a derived workflow condition and must not erase local diagnostics.

### Decision 7: Every Slice Uses a Fresh Implement-Agent Dispatch Context

`dev-orchestrator` dispatches a new `implement-agent` task for each slice. A completed slice is not followed by another slice in the same worker conversation.

The new worker receives only the context required for its slice:

- workflow run id and current phase;
- `flow_type`;
- exact `slice_id`;
- structured slice contract;
- canonical `runtime_context`;
- approved design artifact paths;
- handoffs from direct dependency slices;
- current repository/worktree state;
- resolved provider dispatch contract when required.

It must not receive every prior worker transcript or all historical handoffs by default.

`implement-agent` reconstructs its own session-local todo list from the slice contract. Todo entries are an execution aid only and are not used as cross-session state.

### Decision 8: Slice Handoffs Are Durable Checkpoints

Each implement-agent dispatch writes a slice-specific handoff:

```text
.ai/workflows/runs/active/<run_id>/handoffs/<slice_id>/implement-agent.md
```

Each review-agent dispatch writes:

```text
.ai/workflows/runs/active/<run_id>/handoffs/<slice_id>/review-agent.md
```

A slice handoff must include:

- slice id and objective;
- completed task refs;
- remaining task refs, if blocked;
- decisions that subsequent dependent slices must preserve;
- current TDD state;
- changed files;
- focused and regression verification results;
- blockers;
- direct constraints for dependent slices.

The workflow state stores handoff paths and normalized evidence, but the handoff remains the readable recovery artifact.

Dependent slices receive handoffs only from their direct dependencies unless the plan explicitly names additional required context.

### Decision 9: Slice Review and Aggregate Review Are Separate Gates

Each slice must pass a slice-scoped review before it becomes `completed`.

Slice review validates:

- the slice acceptance criteria;
- changed-file scope;
- focused tests and reported regression evidence;
- consistency with dependency handoffs;
- absence of unapproved work from adjacent slices.

After all required slices are completed, runtime does not complete `apply_change` immediately. It sets:

```text
implementation.aggregate_review_status = ready
```

`dev-orchestrator` then dispatches `review-agent` in aggregate mode using a reserved slice identifier:

```text
slice_id = aggregate
```

Aggregate review validates:

- complete requirement coverage across all required slices;
- integration between slices;
- final live-worktree changed-file set;
- final full regression evidence;
- task and plan checkbox completion;
- provider verification for `spec-flow`;
- absence of incomplete required slices or unresolved slice blocks.

On aggregate review pass:

```text
implementation.aggregate_review_status = passed
```

Only then may the existing `complete-phase` path complete `apply_change`.

`aggregate` is a reserved review scope, not an implementation slice. It must not appear in `implementation.slices[]` and must never be dispatched to implement-agent.

### Decision 10: Legacy Unsliced Runs Use the `default` Slice

For compatibility, when an active or newly planned run has no `implementation_slices[]`, runtime materializes an implicit slice:

```json
{
  "slice_id": "default",
  "title": "Default implementation work package",
  "task_refs": [],
  "depends_on": [],
  "required": true,
  "status": "ready"
}
```

Existing dispatches that omit `--slice-id` continue to resolve to `default` where current compatibility rules permit.

Evidence from an unrelated explicit slice must never satisfy `default`, and `default` evidence must never satisfy another explicit slice.

Legacy state files remain readable. State normalization may add the implicit `implementation` object in memory and persist it on the next successful state mutation.

### Decision 11: State Validation Must Reject Invalid Slice Graphs and Transitions

Runtime validation must reject:

- duplicate slice ids;
- reserved ids such as `aggregate` in plan-defined slices;
- dependencies on unknown slice ids;
- self-dependencies;
- cyclic dependency graphs;
- multiple active slices under sequential strategy;
- completed slices without passed slice review evidence;
- aggregate review marked `ready` while required slices remain incomplete;
- `apply_change` completion without aggregate review pass;
- dispatch evidence recorded under a slice different from the explicit dispatch slice.

Validation errors must include the affected slice ids and a deterministic remediation category.

## Flow

```text
plan-agent
  |- produce implementation_slices[]
  v
workflow runtime
  |- validate graph
  |- persist slices
  |- compute initial ready slice
  v
dev-orchestrator
  |- slice-next
  |- before-dispatch implement-agent --slice-id A
  v
fresh implement-agent session A
  |- reconstruct local todo from slice contract
  |- execute TDD loop
  |- write slice handoff and evidence
  v
after-dispatch implement-agent --slice-id A
  |- A: in_progress -> in_review
  v
review-agent slice review A
  |- review only A changes and evidence
  v
after-dispatch review-agent --slice-id A
  |- A: in_review -> completed
  |- recompute ready dependencies
  v
dev-orchestrator repeats for B, C, ...
  v
all required slices completed
  |- aggregate_review_status: ready
  v
review-agent --slice-id aggregate
  |- validate final integration and full change set
  v
aggregate_review_status: passed
  v
complete-phase apply_change
```

## Agent Contract Changes

### `plan-agent`

- Add `implementation_slices[]` to the structured result contract.
- Generate one or more bounded slices from technical cohesion and independent verification boundaries.
- Validate task coverage: every required implementation task belongs to exactly one required slice unless explicitly marked cross-cutting.
- Do not use arbitrary fixed task counts as the primary slicing rule.

### `dev-orchestrator`

- Query `slice-next` during `apply_change`.
- Dispatch only the runtime-selected slice.
- Pass exact `slice_id`, slice contract, direct dependency handoffs, and runtime context.
- After slice review passes, query `slice-next` again.
- Dispatch aggregate review when runtime reports all required slices complete.
- Never perform technical decomposition or alter slice definitions.

### `implement-agent`

- Handle exactly one explicit slice per dispatch.
- Do not continue into adjacent slices.
- Build `todowrite` entries from the current slice contract.
- Treat todo as session-local and non-authoritative.
- Write a durable slice checkpoint before success, block, or failure.
- Include slice-scoped changed files and verification evidence.

### `review-agent`

- Support `review_scope=slice` for normal slice review.
- Support `review_scope=aggregate` for final integration review.
- For slice review, evaluate only the selected slice plus its dependency constraints.
- For aggregate review, evaluate the complete live worktree and all required slice evidence.

## Runtime Command Contract

### `slice-status`

Example:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-status
python3 .ai/workflows/scripts/workflow.py --root . slice-status --slice-id workflow-slice-state
```

Returns slice lifecycle state, dependency state, attempts, block, handoff paths, and review status.

### `slice-next`

Example:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-next
```

Possible outcomes:

- `dispatch_slice` with the selected slice contract.
- `dispatch_aggregate_review` when all required slices are completed.
- `all_slices_and_aggregate_complete` when aggregate review passed.
- `no_ready_slice` with blocked/dependency diagnostics.

### `slice-block`

Example:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-block \
  --slice-id workflow-slice-state \
  --value '{"reason":"environment_unavailable","message":"Required test service is unavailable."}'
```

This is not the normal agent-failure path; normal worker results are processed through `after-dispatch`.

### `slice-resume`

Example:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-resume \
  --slice-id workflow-slice-state
```

Valid only for a blocked slice whose dependencies remain satisfied. Resulting state is `ready`.

### `slice-cancel`

Example:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-cancel \
  --slice-id optional-doc-sync \
  --reason superseded
```

Required slices need explicit user decision evidence or an approved exception.

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Register `slice-status`, `slice-next`, `slice-block`, `slice-resume`, and `slice-cancel` commands and route to runtime modules. |
| `.ai/workflows/scripts/workflow_runtime/state.py` | Add implementation slice state normalization, validation, readiness computation, and aggregate review state. |
| `.ai/workflows/scripts/workflow_runtime/dispatch.py` or existing dispatch module | Integrate atomic slice transitions into `before-dispatch` and `after-dispatch`. |
| `.ai/workflows/scripts/workflow_runtime/commands.py` or relevant command modules | Implement slice query and exceptional-control commands. |
| `skills/sdlc-project-bootstrap/templates/workflow/` | Keep bootstrap runtime templates synchronized with live runtime changes. |
| `agents/plan-agent.md` | Add structured slice decomposition output contract. |
| `agents/dev-orchestrator.md` | Add slice selection loop, fresh worker dispatch, and aggregate review routing. |
| `agents/implement-agent.md` | Enforce one-slice execution, session-local todo, and durable slice checkpoints. |
| `agents/review-agent.md` | Add slice and aggregate review scopes. |
| `.opencode/agents/*.md` | Regenerate affected distributed agent copies. |
| `.claude/agents/*.md` | Regenerate affected distributed agent copies. |
| `.cursor/agents/*.md` | Regenerate affected distributed agent copies. |
| `tests/test_workflow.py` and runtime-focused test modules | Add slice state, graph validation, command, transition, blocking, resume, and aggregate gate tests. |
| `tests/test_sdlc_orchestrator.py` | Add orchestrator routing contract tests for runtime-selected slices and aggregate review. |
| `tests/test_wrapper_contracts.py` | Validate canonical/distributed agent prompt contracts and structured slice fields. |

The implementation plan must resolve the exact runtime module paths from the current repository structure rather than creating duplicate modules solely to match this table.

## Risks / Trade-offs

**More lifecycle states:** Slice persistence adds state-machine complexity. This is intentional because hidden session state is less reliable than explicit durable state. Validation and transition tests are mandatory.

**More agent dispatches:** Fresh implement and review sessions increase dispatch count. The expected trade-off is lower per-session context, clearer evidence, narrower retries, and more predictable token usage.

**Review overhead:** Per-slice review adds latency. P0 prioritizes reliability. Future work may support policy-based review batching without weakening aggregate review.

**Cross-slice changes:** A slice may discover a necessary change outside its declared expected paths. Expected paths are guidance rather than a hard sandbox, but the worker must report the expansion and reviewer must decide whether it remains within the slice objective.

**Dependency handoff incompleteness:** A weak handoff could deprive a dependent slice of required decisions. Handoff schema and review must require preservation constraints and unresolved issues.

**Legacy migration:** Implicit `default` slice normalization must not change evidence matching semantics or allow unrelated explicit-slice evidence to satisfy an unsliced run.

**Atomic hook behavior:** `before-dispatch` updates state before the external task tool call. If the actual worker invocation fails after the hook succeeds, runtime needs an explicit reconciliation path using `slice-block` or a dedicated dispatch failure result. P0 must test and document this failure mode.

## Acceptance Criteria

- `plan-agent` can return a valid `implementation_slices[]` contract with dependencies, acceptance criteria, verification commands, and required context.
- Runtime rejects duplicate ids, unknown dependencies, self-dependencies, cycles, and reserved `aggregate` ids.
- Runs without explicit slices receive one implicit required `default` slice.
- `slice-next` returns the first ready slice deterministically and does not mutate state.
- Under sequential strategy, runtime prevents two slices from being active simultaneously.
- `before-dispatch(implement-agent, slice_id)` atomically moves the selected ready slice to `in_progress` and records an attempt.
- Implement-agent success moves the same slice to `in_review`; it does not complete the slice.
- Review-agent pass moves the same slice to `completed`, clears the active slice, and recomputes dependent readiness.
- Evidence under one explicit slice cannot satisfy another slice.
- A blocked slice remains local while another independent required slice is ready.
- The run becomes top-level blocked when no active or ready required slice exists and incomplete required work is blocked.
- `slice-resume` moves a valid blocked slice to `ready`, not `in_progress`.
- Required slice cancellation requires explicit user-decision or exception evidence.
- `dev-orchestrator` dispatches only the slice returned by `slice-next` and does not perform technical decomposition.
- Each slice is dispatched in a fresh implement-agent task context.
- Implement-agent treats todo as session-local and writes a durable slice handoff before returning.
- Each required slice must pass slice review before becoming complete.
- Completing all required slices makes aggregate review ready but does not complete `apply_change`.
- `apply_change` cannot complete until aggregate review passes.
- Aggregate review uses the reserved `aggregate` scope and validates the final live worktree, complete verification evidence, and requirement coverage.
- Live runtime and bootstrap template copies remain synchronized.
- Canonical agent files and `.opencode`, `.claude`, and `.cursor` distributed copies remain synchronized.
- Existing unsliced workflow tests continue to pass without changing their expected run-level command semantics.
