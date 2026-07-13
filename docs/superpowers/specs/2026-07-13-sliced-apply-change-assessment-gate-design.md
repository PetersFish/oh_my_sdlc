# Sliced Apply-Change Assessment Gate Design

## Context

The P0 sliced apply-change implementation governs slice selection, implementation,
review, Git boundaries, and aggregate review after an `implementation` block already
exists in workflow state. It does not reliably create that state or force an
assessment before implementation begins.

This leaves a deterministic bypass:

- `workflow.py start` creates apply-ready runs without `implementation`.
- `before-dispatch` enforces slice rules only when `implementation` is present.
- missing state is normalized in memory to `not_required` plus a `default` slice for
  legacy compatibility.
- the start-with-plan orchestrator path skips plan-agent and dispatches
  implement-agent directly.
- plan-agent describes a slicing assessment output, but the runtime does not
  validate and materialize that output into `implementation.slices`.

As a result, a newly created run can bypass the sliced lifecycle even when it was
created after sliced apply-change support was installed.

## Goals

- Make a validated slicing decision a mandatory precondition for executable
  `apply_change` work.
- Block implementation when slice metadata is missing, pending, blocked, or invalid.
- Route a blocked run to plan-agent for slicing assessment without making plan-agent
  a normal apply-change worker.
- Persist plan-agent assessment output as deterministic runtime-owned slice state.
- Provide an explicit and auditable repair command for active legacy runs that lack
  `implementation`.
- Permit an explicit no-decomposition decision only when it records a non-empty
  reason and materializes a governed `default` slice.
- Use one review for a single required slice and retain aggregate review for
  multi-slice changes.
- Preserve read-only compatibility for historical and terminal runs without letting
  that compatibility weaken active-run dispatch gates.

## Non-Goals

- Do not redesign approved plans or specifications during slicing assessment.
- Do not add parallel slice execution.
- Do not add a new workflow phase solely for assessment.
- Do not move plan-agent into the normal `apply_change` phase agent map.
- Do not silently rewrite active legacy runs while loading, resuming, validating, or
  displaying status.
- Do not modify source files or worktree changes when repairing workflow state.
- Do not remove per-slice Git refs, evidence, or review boundaries.
- Do not require aggregate review for a single required slice.

## Decisions

### Decision 1: Validated Slice State Is an Apply Precondition

An apply run is executable only when its persisted `implementation` block contains a
valid completed or explicitly waived assessment and a valid slice graph.

The following states cannot dispatch implement-agent or review-agent:

- `implementation` missing on an active apply run;
- `slicing_assessment.status=pending`;
- `slicing_assessment.status=blocked`;
- malformed assessment metadata;
- empty or invalid slices;
- a slice graph that fails runtime validation.

The runtime must enforce this at both boundaries:

1. when a run becomes apply-ready; and
2. in `before-dispatch`, as defense in depth.

An agent prompt is not an enforcement boundary.

### Decision 2: Apply May Be Selected but Must Remain Blocked

An existing approved design may cause phase inference to select `apply_change`.
Phase selection does not imply permission to execute apply workers.

When assessment is required, the run state is:

```json
{
  "current_phase": "apply_change",
  "status": "blocked",
  "block": {
    "type": "slicing_assessment_required",
    "message": "Apply cannot continue without validated implementation slices",
    "next_allowed": ["dispatch_plan_agent"]
  },
  "implementation": {
    "strategy": "sequential",
    "slicing_assessment": {
      "status": "pending",
      "decision": "",
      "assessed_by": "",
      "assessment_handoff_path": "",
      "reasons": []
    },
    "aggregate_review_status": "pending",
    "active_slice_id": null,
    "slices": []
  }
}
```

This avoids a backward phase transition and preserves existing plan approval. The
run is in the apply phase for workflow identity, but apply execution is blocked.

### Decision 3: Plan-Agent Is a Block Remediation Worker

Plan-agent is not added to `PHASE_AGENT_MAP["apply_change"]`.

It may be dispatched from a blocked apply run only when all of these are true:

- `block.type == "slicing_assessment_required"`;
- `block.next_allowed` contains `dispatch_plan_agent`;
- the requested action is `assess_implementation_slicing`;
- the persisted assessment status is `pending` or `blocked`;
- the dispatch includes the approved primary design path and complete design artifact
  list.

The dispatch intent must persist the remediation action so `after-dispatch` can
reject unrelated or stale plan-agent results.

### Decision 4: Assessment Does Not Redesign Approved Behavior

For an existing plan, plan-agent reads the complete selected artifact set and only
organizes approved work into implementation slices. It must not change requirements,
architecture, acceptance criteria, or user-approved behavior.

The assessment result contains:

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

Task numbering alone is not sufficient evidence for multi-slice decomposition.

### Decision 5: Runtime Materializes Assessment Atomically

Plan-agent proposes an assessment. The runtime owns persisted state.

On successful `after-dispatch` for the exact assessment intent, the runtime must:

1. validate the result schema;
2. validate the decision and required fields;
3. validate slice ids, task coverage, dependencies, and graph acyclicity;
4. convert the result into the canonical `implementation` state model;
5. validate the complete materialized state;
6. persist the new state atomically;
7. clear `slicing_assessment_required` only after persistence succeeds;
8. return `call_slice_next` as the next action.

Invalid, incomplete, or blocked results leave the run blocked. Partial state must
not be written.

### Decision 6: Single-Slice Assessment Materializes `default`

A completed `single_slice` assessment produces exactly one required slice:

```json
{
  "slice_id": "default",
  "depends_on": [],
  "required": true,
  "status": "pending",
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
```

The default slice uses the same implementation, Git-ref, evidence, and review
lifecycle as every other slice.

### Decision 7: Explicit No-Decomposition Requires a Reason

The only assessment bypass is an explicit no-decomposition decision recorded in run
state. It is represented as:

```json
{
  "status": "not_required",
  "decision": "single_slice",
  "assessed_by": "user",
  "assessment_handoff_path": "",
  "reasons": ["User explicitly selected a single governed implementation slice"]
}
```

The runtime accepts `not_required` only when:

- `decision` is `single_slice`;
- `assessed_by` is non-empty;
- `reasons` contains at least one non-empty reason;
- exactly one required `default` slice is materialized;
- the complete implementation state validates.

Missing `implementation` is never equivalent to `not_required`.

### Decision 8: Active Legacy Runs Require Explicit Repair

An active apply run without `implementation` must not be silently migrated during
load, status, resume, validation, or dispatch.

The runtime provides:

```bash
python3 .ai/workflows/scripts/workflow.py --root . \
  slice-init \
  --reason "legacy run predates persisted slicing assessment"
```

The command:

- is limited to active `apply_change` runs;
- creates pending implementation state;
- sets the `slicing_assessment_required` blocker;
- records timestamped migration evidence and the supplied reason;
- clears an unconsumed implement-agent dispatch intent only when no matching agent
  result exists;
- does not touch repository source, tests, plans, or other worktree files;
- is idempotent for an already initialized valid run;
- refuses to overwrite a malformed partial implementation block.

An explicit user decision may initialize a governed single slice directly:

```bash
python3 .ai/workflows/scripts/workflow.py --root . \
  slice-init \
  --skip-assessment \
  --reason "User explicitly selected one governed implementation slice"
```

This writes the `not_required` assessment and `default` slice described above.

### Decision 9: Historical Compatibility Is Read-Only

Historical, completed, archived, or terminal runs without `implementation` may still
be displayed and inspected through compatibility normalization.

That compatibility must not be used by:

- active apply readiness;
- active apply validation;
- `before-dispatch`;
- `slice-next` on an active run;
- phase completion gates.

Active behavior always uses persisted state.

### Decision 10: Single Slice Has One Review

For exactly one required slice, slice review is also the complete change review.

After that review passes, the runtime must:

- mark the default slice `completed`;
- record `accepted_head_ref` and review evidence;
- clear `active_slice_id`;
- set `aggregate_review_status=passed`;
- make `slice-next` return `all_slices_and_aggregate_complete`.

No aggregate review agent is dispatched.

For two or more required slices, completion of all required slice reviews sets
`aggregate_review_status=ready`; `slice-next` then returns
`dispatch_aggregate_review`.

### Decision 11: Orchestrator Must Follow Runtime Output

The start-with-plan path skips design generation, not slicing assessment.

The required routing sequence is:

```text
start/resume
    -> inspect run status
    -> slicing assessment blocker?
        -> dispatch plan-agent remediation
        -> persist valid assessment
        -> clear blocker
    -> slice-next
    -> implement exactly the returned slice
    -> review that slice
    -> next slice or aggregate review
```

Dev-orchestrator must not infer slices, select a slice without `slice-next`, or treat
an existing implementation plan as proof that slice metadata exists.

## State Invariants

1. An active running apply run always has persisted valid implementation state.
2. Missing active implementation state always blocks apply execution.
3. Pending or blocked assessment cannot dispatch implementation or review workers.
4. Plan-agent is never a normal apply-change worker.
5. Only the exact slicing remediation intent may update assessment state.
6. Invalid assessment output cannot clear the blocker.
7. `not_required` always has a non-empty reason and a governed default slice.
8. Implement-agent always receives the exact slice selected by `slice-next`.
9. A single required slice receives exactly one review.
10. Multiple required slices receive per-slice reviews and one aggregate review.
11. Repair commands never modify worktree source or documentation files.
12. Historical compatibility cannot authorize active dispatch.

## Error Model

Missing active implementation state:

```json
{
  "reason": "missing_slicing_assessment",
  "message": "Active apply run has no persisted implementation slicing state",
  "recommended_action": "run_slice_init"
}
```

Assessment required:

```json
{
  "reason": "slicing_assessment_pending",
  "message": "Apply is blocked until plan-agent produces a valid slicing assessment",
  "recommended_action": "dispatch_plan_agent_for_slicing_assessment"
}
```

Invalid remediation dispatch:

```json
{
  "reason": "plan_agent_not_assessment_remediation",
  "message": "Plan-agent may enter blocked apply only for assess_implementation_slicing",
  "recommended_action": "use_assessment_remediation_action"
}
```

Invalid assessment result:

```json
{
  "reason": "invalid_slicing_assessment",
  "message": "Assessment result did not produce a valid implementation slice graph",
  "recommended_action": "redispatch_plan_agent_with_validation_findings"
}
```

Missing explicit bypass reason:

```json
{
  "reason": "missing_no_decomposition_reason",
  "message": "A no-decomposition decision requires a non-empty reason",
  "recommended_action": "record_explicit_reason"
}
```

## Testing Strategy

### Fresh-run integration

- starting from an existing approved plan creates a blocked apply run with pending
  assessment;
- direct implement dispatch fails;
- `slice-next` reports assessment required;
- only the assessment remediation dispatch is accepted;
- a valid result persists slices and unblocks the run;
- `slice-next` selects the first declared ready slice.

### Legacy-run repair

- missing active implementation blocks dispatch;
- status and resume do not silently migrate state;
- `slice-init --reason` creates pending state and audit evidence;
- repeated initialization is idempotent;
- malformed partial state is not overwritten;
- unconsumed stale implement intent is cleared with evidence;
- worktree files remain unchanged.

### Assessment materialization

- valid single assessment creates only `default`;
- valid multi assessment preserves stable order and dependencies;
- duplicate ids, `aggregate`, unknown dependencies, cycles, incomplete task coverage,
  and malformed fields leave the run blocked;
- blocked plan-agent results preserve blocker details;
- stale or unrelated plan-agent results cannot update implementation state.

### Explicit no-decomposition

- missing reason is rejected;
- empty reason is rejected;
- valid explicit decision materializes default and unblocks apply;
- implement dispatch still requires runtime-selected default slice.

### Review behavior

- single slice review pass sets aggregate status directly to passed;
- single slice does not dispatch aggregate review;
- multi-slice completion sets aggregate status to ready;
- multi-slice apply cannot complete until aggregate review passes.

### Regression

- existing slice dependency and Git-ref tests remain green;
- create-change planning still uses plan-agent normally;
- blocked apply replan behavior for requirement ambiguity remains intact;
- terminal historical runs remain readable;
- workflow templates and distributed agent copies remain synchronized.

## Migration of the Current Run

The active `repository-memory-structural-reconciliation` run was created without
persisted implementation state and contains an implement-agent dispatch intent. After
the runtime fix is installed, it should be repaired with `slice-init --reason` and
then routed to plan-agent assessment.

The repair must not revert or delete worktree files created by the cancelled worker.
Those files require a separate explicit user decision.

## Acceptance Criteria

- A fresh apply-ready run cannot dispatch implement-agent before assessment.
- A missing active implementation block produces a deterministic blocker.
- Apply remains blocked until runtime-validated slice metadata is persisted.
- Plan-agent is available only through the slicing remediation route.
- The runtime atomically materializes valid single- and multi-slice assessments.
- Explicit no-decomposition requires a reason and still uses a default slice.
- Legacy active runs are repaired only through an explicit command.
- Historical runs remain readable without authorizing active dispatch.
- Single-slice work receives one slice review and no aggregate review.
- Multi-slice work retains per-slice and aggregate reviews.
- The current run can be repaired and resumed without recreating it.
- Focused workflow, wrapper, and full repository tests pass.
- Derived workflow templates and agent copies have no drift.

## Open Questions

None. The approved boundaries are:

- assessment is mandatory unless explicitly waived with a reason;
- missing metadata blocks apply;
- plan-agent is a remediation worker, not a normal apply worker;
- legacy repair is explicit and auditable;
- a default slice remains governed;
- single-slice review replaces redundant aggregate review.
