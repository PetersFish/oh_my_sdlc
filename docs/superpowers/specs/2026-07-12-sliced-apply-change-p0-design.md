# Sliced Apply-Change Orchestration P0 Design

## Context

The current `dev-orchestrator` lifecycle can dispatch one `implement-agent` for the whole `apply_change` phase. For large changes, one implementation session may accumulate excessive context, repeated tool output, debugging history, and temporary todo state. Even when the model context window can technically hold that history, token cost, focus, and recoverability degrade as the session grows.

The existing architecture already provides several foundations:

- `implement-agent` is intended to handle one bounded work package per dispatch.
- Lifecycle hooks accept an optional `slice_id`.
- Agent evidence and handoffs can be stored under slice-specific paths.
- `workflow.py` is the sole owner of lifecycle state transitions.
- `dev-orchestrator` is a routing coordinator and must not perform technical task decomposition.

P0 turns `slice_id` from a dispatch label into a governed implementation lifecycle. It introduces dependency-aware but strictly sequential implementation slices, fresh implement-agent dispatch contexts, per-slice review, deterministic Git commit-range review boundaries, and a final aggregate review.

When a developer directly supplies an existing Superpowers spec/plan or OpenSpec change without slice metadata, `dev-orchestrator` must route to `plan-agent` for a constrained slicing assessment before implementation begins.

Automatic context compaction, token-budget enforcement, and parallel slice execution are deferred.

## Goals / Non-Goals

**Goals:**

- Let `plan-agent` assess whether implementation should remain one bounded package or be decomposed into multiple slices.
- Let `plan-agent` define structured, dependency-aware `implementation_slices[]` when slicing is warranted.
- Persist slicing assessment, slice definitions, lifecycle state, evidence, handoffs, and Git boundaries in workflow state.
- Let runtime deterministically select exactly one ready slice at a time.
- Dispatch a fresh `implement-agent` context for each slice.
- Integrate normal slice state advancement into existing `before-dispatch` and `after-dispatch` hooks.
- Require every slice to pass slice-scoped review before completion.
- Make `base_ref..<head_ref>` the authoritative change scope for slice review.
- Require aggregate review after all required slices complete and before `apply_change` completes.
- Treat workflow state, Git history, handoffs, verification evidence, and the live governed worktree as durable sources of truth.
- Treat `todowrite` as session-local execution state only.
- Preserve existing unsliced behavior through a validated `default` slice.

**Non-Goals:**

- Do not add automatic context compaction.
- Do not add token counting or context-budget enforcement.
- Do not support parallel slice execution in P0.
- Do not introduce per-slice branches or per-slice worktrees.
- Do not introduce integration branches, join heads, or runtime-generated integration slices.
- Do not let `dev-orchestrator` decide whether work is technically large, small, cohesive, or decomposable.
- Do not let `dev-orchestrator` create, merge, reorder, or redefine slices.
- Do not make todo state durable across sessions.
- Do not create a separate workflow run per slice.
- Do not require exactly one commit per slice.
- Do not rewrite accepted slice history during `apply_change`.
- Do not require public `slice-start` or `slice-complete` commands on the normal path.
- Do not change finish-agent ownership of archive and post-archive work.

## Decisions

### Decision 1: `plan-agent` Owns Slicing Assessment and Decomposition

`dev-orchestrator` never performs technical decomposition.

When current planning produces a new implementation plan, `plan-agent` must return a structured slicing assessment. When a developer supplies existing apply-ready artifacts without valid slice metadata, `dev-orchestrator` dispatches `plan-agent` with:

```text
planning_action = assess_implementation_slicing
```

This applies to:

- a Superpowers spec plus plan supplied through start-with-plan;
- a Superpowers plan without slice metadata;
- an OpenSpec change whose proposal, design, specs, or tasks contain no valid slice contract;
- legacy artifacts created before sliced orchestration.

The structured assessment is:

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

Plan-agent should choose `multi_slice` when the work materially contains one or more of:

- multiple independently testable behaviors;
- distinct module or architectural boundaries;
- clear dependency layers;
- independent acceptance criteria or focused verification boundaries;
- separable migration or backward-compatibility work;
- substantial unrelated context that one worker would otherwise retain;
- failure and retry scopes that should be isolated.

Plan-agent should choose `single_slice` when:

- the work is one technically cohesive behavior;
- separating tests from implementation would weaken TDD;
- expected changes are tightly coupled and must be reviewed together;
- decomposition would add coordination overhead without a meaningful recovery or review boundary.

Numeric signals are heuristics, not hard thresholds. Task counts and file counts alone must not determine slicing.

If confidence is low because the design lacks sufficient technical detail, plan-agent returns `blocked` with the missing inputs. It must not infer slices from task numbering alone.

### Decision 2: Slice Contract

For `multi_slice`, plan-agent returns `implementation_slices[]`:

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
    "docs/superpowers/specs/2026-07-12-sliced-apply-change-p0-design.md"
  ],
  "required": true
}
```

Rules:

- `slice_id` is unique within the run and stable across resume.
- `aggregate` is reserved and cannot be a plan-defined slice id.
- `depends_on` may reference only slice ids in the same run.
- The graph must be acyclic.
- A slice represents one independently verifiable implementation behavior.
- Tests and implementation for one behavior remain in the same slice when separation would prevent independent verification.
- Every required implementation task belongs to exactly one required slice unless explicitly marked cross-cutting.
- Declaration order is stable and becomes the P0 sequential tie-breaker.
- Planning may identify logical independence, but it must not require parallel execution for correctness.

For `single_slice`, runtime materializes one required `default` slice after accepting the assessment.

### Decision 3: Workflow State Is the Source of Truth

The run state gains:

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
    "slices": [
      {
        "slice_id": "workflow-slice-state",
        "title": "Persist implementation slice state",
        "task_refs": ["1.1", "1.2", "1.3"],
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
      }
    ]
  }
}
```

The top-level run remains authoritative for run and phase state. Slice state does not replace `current_phase`, top-level `status`, gates, phase evidence, or normal workflow ownership.

`before-dispatch(implement-agent)` must reject implementation while slicing assessment is `pending` or `blocked`.

### Decision 4: P0 Is Strictly Sequential

P0 supports dependency-aware readiness, not concurrent execution.

The only strategy is:

```text
strategy = sequential
```

At most one slice may be `in_progress` or `in_review` at any time. Runtime validation rejects multiple active slices even if those slices are logically independent.

When several slices are dependency-ready, `slice-next` returns exactly one using declaration order.

For:

```text
A depends_on []
B depends_on []
C depends_on [A, B]
```

with declaration order `A, B, C`, P0 executes:

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

A blocked slice may remain local while another independent slice is selected next, but only when no slice is active. This does not permit concurrent dispatch.

Parallel execution, multiple active slices, per-slice branches/worktrees, integration slices, dependency join heads, and merge-conflict governance are P1 scope.

### Decision 5: Readiness Is Deterministic and Runtime-Owned

A slice is ready when:

- its status is `pending` or `ready`;
- all required dependencies are `completed`;
- all required dependencies have `accepted_head_ref`;
- it is not cancelled;
- no other slice is `in_progress` or `in_review`.

Runtime exposes:

```bash
python3 .ai/workflows/scripts/workflow.py --root . slice-next
```

`slice-next`:

- is read-only;
- returns exactly one slice using declaration order;
- returns `dispatch_aggregate_review` when all required slices are completed;
- returns `all_slices_and_aggregate_complete` when aggregate review passed;
- returns structured `no_ready_slice` diagnostics when blocked;
- distinguishes completed work from blocked dependency graphs.

`dev-orchestrator` may dispatch only the exact slice returned by runtime.

### Decision 6: Normal Slice Advancement Is Atomic With Existing Hooks

P0 does not require public `slice-start` or `slice-complete` commands on the normal path.

Normal transitions are:

```text
pending/ready
  -- before-dispatch(implement-agent, slice_id) -->
in_progress
  -- after-dispatch(implement-agent success, slice_id) -->
in_review
  -- after-dispatch(review-agent passed, slice_id) -->
completed
```

`before-dispatch --agent implement-agent --slice-id <id>` must:

- require `current_phase=apply_change`;
- require completed slicing assessment;
- require `<id>` to equal the runtime-selected slice;
- reject dispatch while another slice is active;
- establish or validate the slice Git `base_ref`;
- atomically set the slice to `in_progress`;
- increment `attempt_count`;
- set `active_slice_id`;
- return the slice contract and runtime context.

`after-dispatch --agent implement-agent --slice-id <id>` must:

- persist evidence under that exact slice;
- validate `base_ref`, `head_ref`, and `commit_refs[]` on success;
- set successful implementation to `in_review`;
- recommend review-agent for the same slice;
- set failed or blocked work to a slice-local block;
- never mark a slice completed from implementation success alone.

`before-dispatch --agent review-agent --slice-id <id>` must:

- require that exact slice to be `in_review`;
- forward its slice contract, latest successful implementation evidence, dependency handoffs, and Git range;
- reject review of another slice.

`after-dispatch --agent review-agent --slice-id <id>` must:

- persist review evidence under that exact slice;
- on pass, record `accepted_head_ref=head_ref`, set `completed`, clear `active_slice_id`, and recompute readiness;
- on requested changes, preserve the original `base_ref`, return the slice to implementation-ready state, and preserve attempt history;
- on blocked or failed review, set a slice-local block.

### Decision 7: Slice Commands Are Query and Exceptional-Control Commands

Command names use the `slice-*` resource prefix to remain distinct from run-level commands.

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
- `slice-block` is exceptional control when normal `after-dispatch` cannot represent the block.
- `slice-resume` moves `blocked -> ready`, never directly to `in_progress`.
- `slice-cancel` requires a reason; cancelling a required slice requires explicit user-decision or approved exception evidence.

Existing run-level commands keep their meaning:

- `start` starts a workflow run.
- `resume` resumes a workflow run.
- `block` blocks the workflow run.
- `done` terminates the workflow run successfully.

Slice commands must not overwrite the top-level run block unless runtime determines that the whole run cannot progress.

### Decision 8: Slice Blocks Stay Local Until the Run Cannot Progress

A blocked slice does not automatically block the whole run.

Example:

```text
A: blocked
B: ready and independent
active_slice_id: null
run: running
```

Runtime may select B next, sequentially.

The run becomes top-level blocked only when:

- no slice is active;
- no required slice is ready;
- incomplete required work is blocked or transitively depends on blocked work;
- aggregate review cannot legally start.

The top-level block is derived and must not erase slice-local diagnostics.

### Decision 9: Every Slice Uses a Fresh Implement-Agent Context

Each slice receives a new implement-agent task context. A completed slice is never followed by another slice in the same worker conversation.

The worker receives only:

- workflow run id and current phase;
- `flow_type`;
- exact `slice_id`;
- structured slice contract;
- canonical runtime context;
- approved design artifact paths;
- direct dependency handoffs;
- current governed feature branch/worktree state;
- resolved provider dispatch contract when required.

It does not receive all prior transcripts or every historical handoff by default.

Implement-agent reconstructs `todowrite` from the slice contract. Todo is non-authoritative and session-local.

### Decision 10: Slice Handoffs Are Durable Checkpoints

Implement-agent writes:

```text
.ai/workflows/runs/active/<run_id>/handoffs/<slice_id>/implement-agent.md
```

Review-agent writes:

```text
.ai/workflows/runs/active/<run_id>/handoffs/<slice_id>/review-agent.md
```

A slice handoff includes:

- slice id and objective;
- completed and remaining task refs;
- decisions and constraints that dependent slices must preserve;
- current TDD state;
- Git `base_ref`, `head_ref`, and commit refs;
- changed files;
- focused and regression verification results;
- blockers and unresolved issues.

Dependent slices receive direct dependency handoffs unless the plan names additional required context.

### Decision 11: P0 Uses One Sequential Feature Branch and Worktree

All slices execute on the same governed feature branch/worktree selected by runtime.

Before the first implementation attempt for a slice:

- the exact worktree path must be known;
- source/test tracked, staged, and untracked state must be clean, except explicitly classified workflow artifacts;
- `base_ref` must equal current branch `HEAD`;
- for every slice after the first accepted slice, `base_ref` must equal the latest accepted sequential head.

If unrelated dirty changes exist, block with:

```text
slice_start_dirty_worktree
```

The worker must not silently commit, stash, discard, or absorb unrelated changes.

The sequential commit chain is:

```text
slice A: base=P0, head=A2
slice B: base=A2, head=B1
slice C: base=B1, head=C2
```

The invariant is:

```text
next_slice.base_ref == latest_accepted_slice.accepted_head_ref
```

For C depending on A and B, C begins only after both reviews pass. Because A and B were accepted serially on the same branch, current branch HEAD already contains both accepted change sets; no merge or join commit is required.

### Decision 12: Implement-Agent Commits Before Success

Implement-agent may use uncommitted TDD loops while working. Before `status=success`, it must:

1. pass focused and required regression verification;
2. ensure only current-slice source/test changes are present;
3. commit all current-slice implementation and test changes;
4. return immutable `base_ref`, current `head_ref`, and ordered `commit_refs[]`;
5. leave source/test worktree state clean, except explicitly classified workflow artifacts.

A slice may contain multiple coherent commits, but all commits must be contiguous in `base_ref..<head_ref>` and belong only to that slice.

Commit messages should include the slice id, for example:

```text
feat(workflow): persist slice state [slice:workflow-slice-state]
```

Successful implementation without a resolvable commit range is invalid and must not transition to `in_review`.

Implement-agent needs narrowly scoped `git add` and `git commit` permission. Destructive Git commands remain denied.

### Decision 13: Slice Review Uses Commit Range as Scope Authority

The cumulative worktree is not a reliable slice boundary after earlier slices have been accepted. Slice review uses:

```bash
git diff --name-status <base_ref>..<head_ref>
git diff --stat <base_ref>..<head_ref>
git diff <base_ref>..<head_ref> -- <path>
```

In worktree mode:

```bash
git -C <worktree_path> ...
```

The commit range is authoritative for current-slice files and hunks. Implement-agent `changed_files[]`, reasons, and verification coverage enrich the Git-derived range but do not define it.

Review-agent validates:

- current `HEAD` matches reported `head_ref`;
- `base_ref` equals the previous accepted sequential head;
- every Git-derived path appears in implementation evidence;
- every reported implementation path exists in the Git range;
- unexpected paths have approved scope-expansion explanations;
- changed hunks belong to the slice objective;
- adjacent-slice work is absent;
- no uncommitted source/test changes exist outside the range.

Mismatch produces:

```text
review_slice_change_set_mismatch
```

### Decision 14: Review Rejection Extends the Same Slice Range

When review requests changes:

- the original slice `base_ref` remains unchanged;
- a fresh implement-agent context adds correction commits;
- `head_ref` advances;
- the next review inspects the full original `base_ref..<new_head_ref>` range.

No reset, amend, squash, or history rewrite is required during apply-change.

The slice becomes completed only after review passes the current `head_ref`, which runtime records as `accepted_head_ref`.

### Decision 15: Slice Review and Aggregate Review Are Separate Gates

Every required slice must pass slice review before completion.

After all required slices complete, runtime sets:

```text
aggregate_review_status = ready
```

`dev-orchestrator` dispatches review-agent with reserved scope:

```text
slice_id = aggregate
review_scope = aggregate
```

`aggregate` is not an implementation slice and never appears in `implementation.slices[]`.

Aggregate review uses:

```text
workflow parent_ref .. latest accepted slice head_ref
```

It validates:

- complete requirement coverage;
- integration across all slice commits;
- final committed changed-file set;
- final full-regression evidence;
- plan/task checkbox completion;
- provider verification for spec-flow;
- no incomplete required slices or unresolved slice blocks;
- contiguous slice commit ranges;
- an accepted head for every completed slice;
- no uncommitted source/test changes.

Only aggregate review pass permits `complete-phase apply_change`.

### Decision 16: Legacy Unsliced Compatibility Uses `default`

After a valid `single_slice` assessment, runtime materializes:

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

Legacy state files remain readable. Existing dispatches that omit `--slice-id` may resolve to `default` only where compatibility rules allow.

Evidence under an unrelated explicit slice must never satisfy `default`, and `default` evidence must never satisfy another explicit slice.

### Decision 17: Runtime Validation Is Mandatory

Runtime rejects:

- duplicate slice ids;
- reserved `aggregate` ids in plan-defined slices;
- unknown dependencies;
- self-dependencies;
- cyclic graphs;
- incomplete slicing assessment before implementation;
- multiple active slices;
- non-contiguous sequential Git boundaries;
- successful implementation without valid refs;
- completed slices without passed review for current head;
- dependencies considered satisfied without accepted heads;
- aggregate review ready while required slices remain incomplete;
- `apply_change` completion without aggregate review pass;
- evidence recorded under a slice different from the explicit dispatch slice.

Validation errors include affected slice ids and deterministic remediation categories.

## Flow

```text
user supplies new or existing design artifacts
  |
  v
runtime checks slicing assessment
  |- missing -> plan-agent assess_implementation_slicing
  |- present -> validate assessment and slice graph
  v
strategy = sequential
  |
  v
slice-next returns one declaration-ordered ready slice A
  |
  v
before-dispatch implement-agent --slice-id A
  |- establish A.base_ref = current accepted branch HEAD
  v
fresh implement-agent A
  |- reconstruct local todo
  |- execute TDD
  |- commit current-slice changes
  |- return base/head/commits and handoff
  v
after-dispatch implement-agent A
  |- A: in_progress -> in_review
  v
review-agent A
  |- review A.base_ref..A.head_ref
  v
after-dispatch review-agent A
  |- record A.accepted_head_ref
  |- A: in_review -> completed
  |- clear active slice
  v
slice-next returns B, then C, sequentially
  v
all required slices completed
  |- aggregate_review_status = ready
  v
review-agent aggregate
  |- review parent_ref..latest accepted head
  v
aggregate_review_status = passed
  v
complete-phase apply_change
```

## Agent Contract Changes

### `plan-agent`

- Support `planning_action=assess_implementation_slicing`.
- Read the complete selected design artifact set.
- Return structured decision, confidence, reasons, signals, and slice graph.
- Preserve approved behavior; slicing reorganizes work but does not redesign requirements.
- Generate bounded slices from technical cohesion and independent verification boundaries.
- Preserve declaration order.
- Do not rely on fixed task/file counts.
- Do not require parallel execution metadata in P0.

### `dev-orchestrator`

- Detect `slicing_assessment_required` and dispatch plan-agent.
- Never judge task size or perform decomposition itself.
- Query `slice-next` during apply-change.
- Dispatch exactly one runtime-selected slice.
- Pass exact slice id, contract, direct dependency handoffs, Git boundary, and runtime context.
- Wait for slice review acceptance before querying the next slice.
- Dispatch aggregate review after all required slices complete.
- Never create per-slice branches, worktrees, merge commits, or integration slices.

### `implement-agent`

- Handle exactly one slice per dispatch.
- Use the runtime-provided shared governed feature branch/worktree.
- Require clean slice-start state.
- Treat todo as session-local.
- Do not continue into adjacent slices.
- Commit only current-slice changes before success.
- Return `base_ref`, `head_ref`, `commit_refs[]`, changed files, and verification evidence.
- Write durable handoff before success, block, or failure.

### `review-agent`

- Support `review_scope=slice` and `review_scope=aggregate`.
- For slice review, treat `base_ref..<head_ref>` as authoritative.
- Confirm sequential base/head invariants.
- Use `git -C` in worktree mode.
- Block on dirty source/test changes outside the range.
- For aggregate review, inspect the complete workflow parent-to-final-head range.
- Do not perform cross-branch merge or integration review in P0.

### Workflow Runtime

- Persist assessment and slice state.
- Enforce `strategy=sequential`.
- Maintain one optional `active_slice_id`.
- Return one slice from `slice-next`.
- Integrate normal transitions into existing dispatch hooks.
- Enforce accepted-head dependency readiness.
- Validate contiguous sequential commit ranges.
- Preserve run-level and slice-level block separation.

## Affected Files

| File | Change |
|---|---|
| `.ai/workflows/scripts/workflow.py` | Register slice query/control commands and route assessment/slice lifecycle behavior. |
| `.ai/workflows/scripts/workflow_runtime/state.py` | Add assessment state, slice normalization, graph validation, readiness, refs, and aggregate review state. |
| Existing runtime dispatch module | Integrate atomic slice transitions and validate assessment and Git boundaries. |
| Existing runtime command modules | Implement `slice-status`, `slice-next`, `slice-block`, `slice-resume`, and `slice-cancel`. |
| `skills/sdlc-project-bootstrap/templates/workflow/` | Synchronize live runtime changes into bootstrap templates. |
| `agents/plan-agent.md` | Add slicing assessment and structured decomposition contract. |
| `agents/dev-orchestrator.md` | Add assessment routing, sequential slice loop, and aggregate review dispatch. |
| `agents/implement-agent.md` | Add one-slice execution, clean boundary, commit contract, and durable checkpoint rules. |
| `agents/review-agent.md` | Add commit-range slice review and aggregate review scopes. |
| `.opencode/agents/*.md` | Regenerate affected distributed copies. |
| `.claude/agents/*.md` | Regenerate affected distributed copies. |
| `.cursor/agents/*.md` | Regenerate affected distributed copies. |
| Runtime test modules | Test assessment, graph validation, commands, transitions, refs, blocks, retries, and aggregate gate. |
| `tests/test_sdlc_orchestrator.py` | Test assessment routing and strictly sequential dispatch. |
| `tests/test_wrapper_contracts.py` | Test canonical/distributed agent contracts and structured fields. |

The implementation plan must resolve exact current runtime module paths rather than creating duplicate modules only to match this table.

## Risks / Trade-offs

**LLM assessment variability:** Structured rubric, reasons, confidence, runtime validation, and eval cases reduce but do not eliminate judgment variability.

**Additional dispatches:** Fresh implement and review contexts increase dispatch count but reduce context growth, retry scope, and hidden session state.

**Additional commits:** Slice commit boundaries increase commit count. This is intentional for deterministic attribution and review. Final squash belongs to branch-finish policy.

**Sequential wall-clock cost:** Independent slices do not run concurrently in P0. Reliability and state-machine clarity take priority. Parallel execution is a separate P1 strategy.

**Shared branch history:** Each accepted slice appends to one feature branch. Exact commit ranges retain slice attribution.

**Workflow artifact dirtiness:** Runtime state and handoffs may change after source commits. Cleanliness checks must classify governed workflow artifacts separately from source/test changes.

**Review correction history:** Corrections append commits rather than rewriting history, improving auditability but producing noisier intermediate history.

**Atomic hook/task gap:** `before-dispatch` mutates state before the external task call. If task invocation fails, runtime needs a deterministic reconciliation path through `slice-block` or an explicit dispatch-failure result.

**Cross-slice scope expansion:** Expected paths are guidance rather than a hard sandbox. Implement-agent must report expansion and reviewer must decide whether it remains within the slice objective.

## Acceptance Criteria

- Existing apply-ready artifacts without valid slice metadata cannot dispatch implement-agent directly.
- Dev-orchestrator routes missing-slice artifacts to plan-agent with `planning_action=assess_implementation_slicing`.
- Plan-agent returns structured `single_slice`, `multi_slice`, or `blocked` assessment with reasons and confidence.
- Runtime materializes `default` only after valid single-slice assessment or explicit legacy policy.
- Runtime rejects implementation while assessment is pending or blocked.
- Multi-slice output forms a complete, valid, acyclic graph.
- P0 runtime supports only `strategy=sequential`.
- At most one slice may be `in_progress` or `in_review`.
- When A and B are both ready, `slice-next` returns exactly one by declaration order.
- Dev-orchestrator never concurrently dispatches A and B.
- Before first implementation attempt, runtime records `base_ref` and rejects unrelated dirty state.
- Implement-agent success requires clean post-commit source/test state and valid `base_ref`, `head_ref`, and `commit_refs[]`.
- Implement-agent success moves only the same slice to `in_review`.
- Review-agent derives current-slice files and hunks from `base_ref..<head_ref>`.
- Review-agent does not use cumulative uncommitted worktree diff as slice scope authority.
- Review rejection preserves original `base_ref` and advances `head_ref` through appended correction commits.
- Slice completion records reviewed `accepted_head_ref`.
- The next slice starts only after current review passes.
- The next slice `base_ref` equals the latest accepted sequential head.
- C depending on A and B becomes ready only after both have completed review and recorded accepted heads.
- C starts from the sequential branch HEAD containing both accepted A and B changes.
- No P0 implementation creates per-slice branches, per-slice worktrees, integration branches, or integration slices.
- A blocked slice stays local while another independent slice may be selected sequentially.
- Run-level blocking occurs only when no active or ready required work remains.
- Evidence under one explicit slice cannot satisfy another slice or `default`.
- Every required slice passes slice review before completion.
- Completing all required slices makes aggregate review ready but does not complete apply-change.
- Aggregate review covers `workflow parent_ref..<latest accepted head_ref>`.
- Apply-change cannot complete until aggregate review passes.
- Canonical agents, distributed copies, live runtime, and bootstrap templates remain synchronized.
- Contract tests prove two independent ready slices execute serially.
- Contract tests prove `C depends_on [A, B]` starts only after both sequential reviews pass.
- Existing unsliced workflow tests continue to pass without changing run-level command semantics.
