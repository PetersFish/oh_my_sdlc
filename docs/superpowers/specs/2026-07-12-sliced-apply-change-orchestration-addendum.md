# Sliced Apply-Change Orchestration Addendum

## Context

The base design in `docs/superpowers/specs/2026-07-12-sliced-apply-change-orchestration-design.md` assumes that `plan-agent` has produced `implementation_slices[]` when slicing is appropriate. Two entry and review-boundary cases require additional specification:

1. A developer may directly provide an existing Superpowers spec and plan, or an existing OpenSpec change, whose artifacts predate sliced orchestration and therefore contain no slice contract.
2. A slice-scoped `review-agent` must distinguish the exact changes belonging to the current slice from changes already accepted in earlier slices.

This addendum extends the P0 design without adding context compaction, token budgeting, parallel slice execution, or a separate workflow run per slice.

## Goals / Non-Goals

**Goals:**

- Require a plan-agent slicing assessment when apply-ready design artifacts contain no explicit slice contract.
- Allow plan-agent to return either one bounded default package or a dependency-aware multi-slice decomposition.
- Make the slicing decision explainable and machine-validatable rather than relying on an unstructured LLM judgment.
- Establish a deterministic Git boundary for every implementation slice.
- Let review-agent inspect the current slice through an exact commit range rather than an accumulated live-worktree diff.
- Preserve aggregate review over the complete change relative to the workflow parent reference.

**Non-Goals:**

- Do not let dev-orchestrator perform technical decomposition.
- Do not force slicing merely because task numbering is long.
- Do not use estimated token count as the only slicing criterion.
- Do not require exactly one commit per slice.
- Do not allow implement-agent to commit unrelated pre-existing dirty changes.
- Do not merge, squash, or rewrite accepted slice commits during apply_change.

## Decisions

### Decision 1: Missing Slice Contracts Trigger Plan-Agent Assessment

When the user selects existing apply-ready artifacts and those artifacts do not contain a valid `implementation_slices[]` contract, `dev-orchestrator` must not immediately materialize `default` and dispatch implement-agent.

Instead, it dispatches `plan-agent` in a constrained assessment mode:

```text
planning_action = assess_implementation_slicing
```

This applies to:

- Superpowers spec plus plan supplied through start-with-plan;
- a Superpowers plan supplied without slice metadata;
- an OpenSpec change whose proposal/design/spec/tasks artifacts contain no slice contract;
- legacy planning artifacts created before sliced orchestration was introduced.

The assessment is lifecycle planning work. It must use the normal governed plan-agent dispatch path and must not be performed directly by dev-orchestrator.

### Decision 2: Plan-Agent Uses an Explicit Slicing Rubric

An LLM can assess implementation size and cohesion, but its judgment is advisory unless expressed through a structured rubric and validated by runtime.

Plan-agent must evaluate at least these dimensions:

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

Plan-agent should choose `multi_slice` when one or more of the following materially apply:

- the work contains multiple independently testable behaviors;
- implementation crosses distinct modules or architectural boundaries;
- tasks form clear dependency layers;
- different groups of changes have independent acceptance criteria or focused verification commands;
- migration/backward-compatibility work can be separated from primary behavior;
- one worker would otherwise need to retain substantial unrelated context;
- failure or retry should be isolated to a bounded package.

Plan-agent should choose `single_slice` when:

- the work represents one cohesive behavior;
- separating tests from implementation would weaken TDD or independent verification;
- expected changes are tightly coupled and must be reviewed together;
- decomposition would create coordination overhead without a meaningful recovery or review boundary.

Numeric signals are heuristics, not hard thresholds. For example, a change touching many generated copies may remain one cohesive slice, while a three-file change containing two independent migrations may require multiple slices.

If confidence is low because artifacts lack technical detail, plan-agent returns `blocked` with the missing planning inputs. It must not invent a decomposition from task numbers alone.

### Decision 3: Runtime Persists the Assessment Result

The workflow run state records the assessment independently of slice lifecycle state:

```json
{
  "implementation": {
    "slicing_assessment": {
      "status": "not_required|pending|completed|blocked",
      "decision": "single_slice|multi_slice",
      "assessed_by": "plan-agent",
      "assessment_handoff_path": "...",
      "reasons": []
    },
    "slices": []
  }
}
```

Rules:

- Planning produced by the current workflow may populate slices directly and set assessment status to `completed`.
- Existing artifacts without slice metadata set assessment status to `pending`.
- `before-dispatch(implement-agent)` must reject dispatch while assessment status is `pending` or `blocked`.
- A `single_slice` result materializes one explicit or backward-compatible `default` slice.
- A `multi_slice` result must provide a valid acyclic `implementation_slices[]` graph.
- Runtime validates coverage, ids, dependencies, and reserved identifiers before apply execution begins.

### Decision 4: Slice Review Uses a Commit-Range Boundary

The accumulated live worktree is insufficient to identify the current slice after earlier slices have modified the same checkout. Plain `git diff` shows all uncommitted changes and cannot reliably attribute individual hunks to one slice.

P0 therefore requires every slice to expose an immutable review boundary:

```json
{
  "slice_id": "workflow-slice-state",
  "base_ref": "<commit-sha-before-this-slice>",
  "head_ref": "<commit-sha-after-current-implementation-attempt>",
  "commit_refs": ["<sha-1>", "<sha-2>"]
}
```

Review-agent uses:

```bash
git diff --name-status <base_ref>..<head_ref>
git diff --stat <base_ref>..<head_ref>
git diff <base_ref>..<head_ref> -- <path>
```

In worktree mode every command must use:

```bash
git -C <worktree_path> ...
```

The commit range, not implement-agent's prose or expected path list, is the authoritative slice change set.

### Decision 5: Slice Start Requires a Clean Commit Boundary

Before the first implement-agent dispatch for a slice, runtime or the worker must establish:

- the exact worktree path;
- a clean tracked and untracked worktree, except explicitly allowlisted workflow artifacts outside implementation scope;
- `base_ref = HEAD`;
- for dependent slices, `base_ref` must equal the latest accepted slice head on the sequential feature branch.

If unrelated dirty changes exist, the slice must block with a deterministic reason such as:

```text
slice_start_dirty_worktree
```

The worker must not silently include, discard, stash, or commit unrelated changes.

This requirement makes each slice range contiguous and prevents attribution ambiguity.

### Decision 6: Implement-Agent Commits Before Returning Success

Implement-agent may use normal uncommitted TDD loops while working. Before returning `status=success`, it must:

1. ensure focused and required regression verification passed;
2. ensure the worktree contains only current-slice changes;
3. commit all current-slice implementation and test changes on the feature branch;
4. return `base_ref`, `head_ref`, and ordered `commit_refs[]`;
5. ensure the worktree is clean after the commit, except explicitly permitted workflow artifacts.

P0 does not require exactly one commit. A slice may contain several coherent commits, but all commits must be contiguous within `base_ref..<head_ref>` and belong only to that slice.

Commit messages should include the slice id, for example:

```text
feat(workflow): persist slice state [slice:workflow-slice-state]
```

A successful implement result without a resolvable commit range is invalid and must not transition the slice to `in_review`.

### Decision 7: Review Rejection Extends the Same Slice Range

If review-agent requests changes:

- the slice returns to an implementation-ready state;
- its original `base_ref` remains unchanged;
- a fresh implement-agent dispatch applies corrections and creates one or more additional commits;
- `head_ref` advances to the latest correction commit;
- the next review inspects the complete range from the original `base_ref` to the new `head_ref`.

This preserves the full slice change set across retries without requiring history rewriting or fixup squashing during apply_change.

The slice becomes `completed` only after review passes for the current `head_ref`. Runtime records the accepted head as `accepted_head_ref`.

### Decision 8: Aggregate Review Uses the Workflow Parent Range

Aggregate review is not limited to the most recent slice. It uses:

```text
workflow parent_ref .. latest accepted slice head_ref
```

Aggregate review validates:

- the full committed implementation range;
- integration across all slice commits;
- required slice acceptance evidence;
- final regression evidence;
- no uncommitted source/test changes remain;
- commit ranges are contiguous and each completed slice has an accepted head.

Workflow artifacts intentionally written after commits must be classified separately and must not obscure source-code cleanliness checks.

### Decision 9: Changed-File Evidence Is Derived From Git, Then Enriched

Implement-agent still returns `changed_files[]`, reasons, and verification coverage, but those fields are descriptive evidence rather than the scope authority.

Runtime/review-agent derives the authoritative path set from `base_ref..<head_ref>` and validates:

- every Git-derived path appears in implement-agent evidence;
- every reported implementation path exists in the Git-derived range;
- unexpected paths are explained as approved scope expansion;
- changed hunks belong to the current slice objective;
- adjacent-slice work is absent.

Mismatch produces:

```text
review_slice_change_set_mismatch
```

### Decision 10: Direct Artifacts Follow a Pre-Apply Assessment Flow

The start-with-existing-artifacts flow becomes:

```text
user supplies existing spec/plan or OpenSpec change
  |
  v
dev-orchestrator validates artifact selection
  |
  v
runtime detects missing implementation_slices[]
  |
  v
before-dispatch plan-agent (assess_implementation_slicing)
  |
  v
plan-agent returns single_slice or multi_slice
  |
  v
runtime validates and persists assessment + slice graph
  |
  v
slice-next
  |
  v
before-dispatch implement-agent --slice-id <id>
```

The user does not need to manually decide whether slicing is required unless plan-agent returns low-confidence questions or the proposed decomposition changes the approved requirement scope.

## Agent Contract Changes

### `plan-agent`

- Support `planning_action=assess_implementation_slicing`.
- Read the complete selected design artifact set before assessing.
- Return structured signals, decision, reasons, confidence, and slices.
- Preserve the original requirements; slicing may reorganize implementation work but must not redesign the approved behavior.

### `dev-orchestrator`

- Detect runtime result `slicing_assessment_required`.
- Dispatch plan-agent rather than materializing `default` itself.
- Forward selected artifact paths and runtime context.
- Resume apply execution only after runtime accepts the assessment result.
- Never decide that a task is large or small itself.

### `implement-agent`

- Establish or consume the runtime-provided slice `base_ref`.
- Require clean slice-start state.
- Commit current-slice changes before success.
- Return `base_ref`, `head_ref`, and `commit_refs[]`.
- Never commit unrelated pre-existing changes or workflow artifacts outside the commit policy.

### `review-agent`

- Treat `base_ref..<head_ref>` as the authoritative slice review scope.
- Validate that the current HEAD matches the reported `head_ref` before review.
- Use commit-range diff commands, with `git -C` in worktree mode.
- Block on dirty source/test changes outside the reported commit range.
- Continue to use dependency handoffs and slice acceptance criteria to judge semantic correctness.

## Affected Files

| File | Change |
|---|---|
| `docs/superpowers/specs/2026-07-12-sliced-apply-change-orchestration-design.md` | Base P0 design extended by this addendum. |
| `.ai/workflows/scripts/workflow_runtime/state.py` | Persist slicing assessment and per-slice commit boundary fields. |
| `.ai/workflows/scripts/workflow_runtime/dispatch.py` or current dispatch module | Route missing-slice artifacts to plan-agent assessment; validate refs during implement/review transitions. |
| `.ai/workflows/scripts/workflow.py` | Expose assessment result handling through existing lifecycle commands. |
| `agents/plan-agent.md` | Add slicing assessment mode and rubric. |
| `agents/dev-orchestrator.md` | Add missing-slice assessment routing. |
| `agents/implement-agent.md` | Add clean-boundary and slice commit contract. |
| `agents/review-agent.md` | Add commit-range slice review protocol. |
| `skills/sdlc-project-bootstrap/templates/workflow/` | Synchronize runtime templates. |
| `tests/test_workflow.py` and runtime test modules | Test assessment gating, reference validation, dirty-worktree blocks, retries, and aggregate ranges. |
| `tests/test_sdlc_orchestrator.py` | Test plan-agent assessment routing for existing artifacts. |
| `tests/test_wrapper_contracts.py` | Test canonical and distributed agent contracts. |

## Risks / Trade-offs

**LLM assessment variability:** The rubric reduces but does not eliminate judgment variability. Runtime validates shape and graph correctness, while plan-agent must provide reasons and confidence. Eval cases should cover clearly small, clearly large, and ambiguous plans.

**Additional commits:** Slice boundaries create more commits. This is intentional for traceability and deterministic review. Squashing, if desired, belongs to the explicit branch-finish decision rather than apply_change.

**Commit permissions:** Implement-agent requires narrowly scoped `git add` and `git commit` permissions. Broad destructive Git commands remain denied.

**Workflow artifact dirtiness:** Handoffs and runtime state may change after implementation commits. The implementation-cleanliness policy must distinguish governed workflow artifacts from source/test changes.

**Review-before-commit alternative:** Reviewing an uncommitted cumulative worktree avoids intermediate commits but cannot reliably attribute hunks after multiple slices without building a separate snapshot/patch store. P0 chooses commits because Git already provides an immutable, inspectable boundary.

**Rejected slice commits remain visible:** Review corrections append commits rather than rewriting history. This improves auditability but produces noisier history. Final squash remains a finish-stage option.

## Acceptance Criteria

- Existing apply-ready artifacts without `implementation_slices[]` cannot dispatch implement-agent directly.
- Dev-orchestrator routes missing-slice artifacts to plan-agent with `planning_action=assess_implementation_slicing`.
- Plan-agent can return a structured `single_slice`, `multi_slice`, or `blocked` assessment with reasons and confidence.
- Runtime materializes `default` only after a valid single-slice assessment or through explicit legacy compatibility policy.
- Runtime rejects implement dispatch while slicing assessment is pending or blocked.
- Multi-slice assessment produces a valid, complete, acyclic slice graph.
- Before first implementation of a slice, runtime records a commit `base_ref` and rejects unrelated dirty worktree state.
- Implement-agent success requires a clean post-commit worktree and valid `base_ref`, `head_ref`, and `commit_refs[]`.
- Review-agent derives the current slice file and hunk scope from `base_ref..<head_ref>`.
- Review-agent does not use the cumulative uncommitted worktree as the slice scope authority.
- Review rejection preserves the original `base_ref`, and correction commits advance `head_ref`.
- A completed slice stores the reviewed `accepted_head_ref`.
- Aggregate review covers `workflow parent_ref..<latest accepted head_ref>` and rejects unresolved source/test dirtiness.
- Implement-agent evidence must match the Git-derived slice change set.
- Canonical agents, distributed copies, live runtime, and bootstrap templates remain synchronized.
