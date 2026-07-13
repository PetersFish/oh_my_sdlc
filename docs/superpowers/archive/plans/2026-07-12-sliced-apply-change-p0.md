# Sliced Apply-Change Orchestration P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Execute one bounded slice at a time and keep checkboxes synchronized.

**Goal:** Add deterministic, sequential, dependency-aware implementation slices to `apply_change`, including plan-agent slicing assessment, runtime lifecycle state, per-slice commit-range review, fresh implement-agent contexts, and mandatory aggregate review.

**Architecture:** `plan-agent` owns technical slicing assessment. Workflow runtime owns slice graph validation, readiness, state transitions, blocking, Git-ref integrity, and aggregate gating. `dev-orchestrator` only routes the runtime-selected slice. `implement-agent` executes and commits one slice. `review-agent` reviews one commit range or the final aggregate range.

**Tech Stack:** Python standard library, existing modular workflow runtime, Git CLI, pytest/unittest, Markdown agent contracts, Superpowers/OpenSpec artifacts, template/distributed-copy sync tooling.

**Primary Spec:** `docs/superpowers/specs/2026-07-12-sliced-apply-change-p0.md`

---

## Implementation Slices

```json
{
  "slicing_assessment": {
    "decision": "multi_slice",
    "confidence": "high",
    "reasons": [
      "Runtime state, dispatch transitions, agent contracts, and Git review boundaries are independently testable behaviors.",
      "The change crosses runtime, orchestration, worker, review, template, and test boundaries.",
      "Each package can be reviewed with a focused verification scope."
    ],
    "implementation_slices": [
      {
        "slice_id": "slice-state-model",
        "task_refs": ["1", "2"],
        "depends_on": [],
        "objective": "Persist and validate slicing assessment and sequential slice lifecycle state."
      },
      {
        "slice_id": "slice-runtime-commands",
        "task_refs": ["3"],
        "depends_on": ["slice-state-model"],
        "objective": "Expose deterministic slice query and exceptional-control commands."
      },
      {
        "slice_id": "slice-dispatch-transitions",
        "task_refs": ["4"],
        "depends_on": ["slice-state-model", "slice-runtime-commands"],
        "objective": "Integrate atomic slice transitions into before-dispatch and after-dispatch."
      },
      {
        "slice_id": "slice-agent-contracts",
        "task_refs": ["5", "6", "7", "8"],
        "depends_on": ["slice-dispatch-transitions"],
        "objective": "Update plan, orchestrator, implement, and review agent contracts."
      },
      {
        "slice_id": "slice-template-distribution",
        "task_refs": ["9"],
        "depends_on": ["slice-state-model", "slice-runtime-commands", "slice-dispatch-transitions", "slice-agent-contracts"],
        "objective": "Synchronize live runtime and canonical agent changes to templates and distributed copies."
      },
      {
        "slice_id": "slice-integration-verification",
        "task_refs": ["10", "11"],
        "depends_on": ["slice-template-distribution"],
        "objective": "Run aggregate regression, contract validation, and documentation consistency checks."
      }
    ]
  }
}
```

P0 executes these slices strictly in declaration/dependency order. Do not parallelize them.

## File Structure

Resolve exact current module locations before editing. Expected areas:

- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: existing workflow runtime dispatch module
- Modify: existing workflow runtime command/CLI module
- Modify: `agents/plan-agent.md`
- Modify: `agents/dev-orchestrator.md`
- Modify: `agents/implement-agent.md`
- Modify: `agents/review-agent.md`
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/`
- Regenerate: `.opencode`, `.claude`, `.cursor` copies
- Modify: runtime-focused tests, `tests/test_sdlc_orchestrator.py`, `tests/test_wrapper_contracts.py`

Do not create duplicate runtime modules merely to match conceptual names from the spec.

---

## Slice 1: State Model and Validation

### Task 1: Add Failing Slice-State Tests

**Files:**
- Modify: runtime-focused workflow tests

- [x] Add a fixture that creates an `apply_change` run with `implementation.strategy=sequential`.
- [x] Add failing tests for state normalization of legacy runs without `implementation`.
- [x] Add failing tests for valid `single_slice` assessment materializing `default`.
- [x] Add failing tests for valid multi-slice state persistence across resume.
- [x] Add failing validation tests for duplicate ids, reserved `aggregate`, unknown dependencies, self-dependencies, cycles, missing required-task coverage, and multiple active slices.
- [x] Add failing tests proving evidence under one explicit slice cannot satisfy another.
- [x] Run the focused test class and confirm RED.

### Task 2: Implement Slice State and Validation

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: related runtime state helpers

- [x] Extend allowed state keys with `implementation` without weakening unknown-key validation.
- [x] Add legacy normalization that produces an in-memory compatibility `default` slice only under allowed policy.
- [x] Add slicing assessment state: `not_required|pending|completed|blocked`.
- [x] Add slice statuses: `pending|ready|in_progress|in_review|blocked|completed|cancelled`.
- [x] Add per-slice fields for attempts, block, refs, evidence, and handoffs.
- [x] Implement graph validation and deterministic error payloads containing affected slice ids.
- [x] Enforce `strategy=sequential` and at most one active slice.
- [x] Enforce completed slice => passed review evidence + `accepted_head_ref`.
- [x] Enforce aggregate-ready/passed invariants.
- [x] Run Slice 1 focused tests and make them GREEN.
- [x] Commit with the slice id in the message.

**Verification:**

```bash
python3 -m pytest tests/test_workflow.py -k "slice_state or slicing_assessment or slice_graph" -v
```

---

## Slice 2: Runtime Slice Commands

### Task 3: Add and Implement Slice Query/Control Commands

**Files:**
- Modify: `.ai/workflows/scripts/workflow.py`
- Modify: existing command runtime module
- Modify: runtime CLI tests

- [x] Add failing tests for `slice-status` for all slices and one selected slice.
- [x] Add failing tests for deterministic, non-mutating `slice-next`.
- [x] Test declaration-order selection when A and B are both ready.
- [x] Test `dispatch_aggregate_review`, `all_slices_and_aggregate_complete`, and `no_ready_slice` outcomes.
- [x] Add failing tests for `slice-block`, `slice-resume`, and `slice-cancel` authorization.
- [x] Register commands in the CLI parser.
- [x] Implement `slice-status` and `slice-next` as read-only commands.
- [x] Implement `slice-block` for explicit exceptional control.
- [x] Implement `slice-resume` as `blocked -> ready` only when dependencies remain accepted.
- [x] Implement required-slice cancellation gate using user-decision/exception evidence.
- [x] Ensure slice commands do not silently overwrite top-level block state.
- [x] Run focused command tests and make them GREEN.
- [x] Commit with the slice id in the message.

**Verification:**

```bash
python3 -m pytest tests/test_workflow.py -k "slice_status or slice_next or slice_block or slice_resume or slice_cancel" -v
```

---

## Slice 3: Dispatch Lifecycle and Git Refs

### Task 4: Integrate Atomic Slice Transitions

**Files:**
- Modify: existing workflow runtime dispatch module
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: dispatch/runtime tests

- [x] Add failing test: implement dispatch is rejected while slicing assessment is pending or blocked.
- [x] Add failing test: `before-dispatch(implement-agent, slice_id)` accepts only the exact `slice-next` result.
- [x] Add failing test: before-dispatch atomically sets `in_progress`, increments attempt count, sets `active_slice_id`, and returns slice context.
- [x] Add failing test: another slice cannot dispatch while one is `in_progress` or `in_review`.
- [x] Add failing test: successful implement result without valid `base_ref`, `head_ref`, and `commit_refs[]` cannot enter review.
- [x] Add failing test: implement success moves only the same slice to `in_review`.
- [x] Add failing test: review dispatch requires that same slice to be `in_review`.
- [x] Add failing test: review pass records `accepted_head_ref`, completes the slice, clears active state, and recomputes readiness.
- [x] Add failing test: review rejection preserves original `base_ref` and allows head advancement.
- [x] Add failing test for A/B sequential execution and C depending on accepted A+B.
- [x] Implement all transitions as state-owner operations inside existing hooks.
- [x] Add deterministic reconciliation for external task invocation failure after successful before-dispatch.
- [x] Validate sequential commit-chain invariant.
- [x] Run focused dispatch tests and make them GREEN.
- [x] Commit with the slice id in the message.

**Verification:**

```bash
python3 -m pytest tests/test_workflow.py -k "before_dispatch and slice or after_dispatch and slice or accepted_head_ref" -v
```

---

## Slice 4: Agent Contracts

### Task 5: Update Plan-Agent

**Files:**
- Modify: `agents/plan-agent.md`
- Modify: plan-agent contract/eval tests

- [x] Add `planning_action=assess_implementation_slicing`.
- [x] Require structured decision, confidence, reasons, signals, and slices.
- [x] Define single/multi/blocked rubric without hard task/file thresholds.
- [x] Require full selected artifact-set reading before assessment.
- [x] Require task coverage and acyclic dependency graph.
- [x] State that decomposition reorganizes work but does not redesign approved behavior.
- [x] Add clearly-small, clearly-large, and ambiguous eval/contract cases.

### Task 6: Update Dev-Orchestrator

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Modify: `tests/test_sdlc_orchestrator.py`

- [x] Route `slicing_assessment_required` to plan-agent.
- [x] During `apply_change`, call `slice-next` and dispatch exactly one returned slice.
- [x] Forward slice contract, exact id, runtime context, design artifacts, and direct dependency handoffs.
- [x] Wait for review acceptance before requesting the next slice.
- [x] Route `dispatch_aggregate_review` to review-agent with aggregate scope.
- [x] Explicitly prohibit technical decomposition, parallel dispatch, per-slice branch creation, and integration slices in P0.
- [x] Add static contract tests for all routing rules.

### Task 7: Update Implement-Agent

**Files:**
- Modify: `agents/implement-agent.md`
- Modify: implement-agent contract tests

- [x] Enforce exactly one slice per dispatch.
- [x] Reconstruct `todowrite` from the current slice contract.
- [x] Require runtime-provided sequential worktree and `base_ref`.
- [x] Block on unrelated dirty source/test changes.
- [x] Require focused and regression verification before success.
- [x] Require committing current-slice source/test changes before success.
- [x] Return `base_ref`, `head_ref`, ordered `commit_refs[]`, changed-file evidence, and verification coverage.
- [x] Require clean source/test state after commit.
- [x] Require durable handoff before success, block, or failure.
- [x] Preserve original base and append correction commits after review feedback.

### Task 8: Update Review-Agent

**Files:**
- Modify: `agents/review-agent.md`
- Modify: review-agent contract tests

- [x] Add `review_scope=slice|aggregate`.
- [x] For slice review, treat `base_ref..<head_ref>` as authoritative.
- [x] Use `git -C <worktree_path>` whenever worktree mode is active.
- [x] Validate current HEAD/ref/worktree consistency.
- [x] Derive file/hunk scope from Git and compare it with implement evidence.
- [x] Block on `review_slice_change_set_mismatch` or dirty source/test changes outside the range.
- [x] For aggregate review, inspect `parent_ref..<latest accepted head>` and all required slice evidence.
- [x] Validate full regression, requirement coverage, contiguous ranges, and unresolved blocks.

- [x] Run all agent contract tests.
- [x] Commit Slice 4 changes.

**Verification:**

```bash
python3 -m pytest tests/test_sdlc_orchestrator.py tests/test_wrapper_contracts.py -v
```

---

## Slice 5: Template and Distributed-Copy Synchronization

### Task 9: Synchronize Canonical Changes

**Files:**
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/`
- Regenerate: `.opencode`, `.claude`, `.cursor` runtime templates and affected agents
- Modify: sync/contract tests as needed

- [x] Copy live runtime behavior to canonical bootstrap templates.
- [x] Run the repository's canonical distribution/sync command rather than editing generated copies independently.
- [x] Confirm canonical agents and all three distributed agent sets match.
- [x] Confirm live runtime and bootstrap runtime templates match where required.
- [x] Run sync validation in dry-run mode when available.
- [x] Commit Slice 5 changes.

**Verification:**

```bash
python3 scripts/sync_templates.py --dry-run
python3 -m pytest tests/test_wrapper_contracts.py -v
```

Use the actual supported sync command if the repository differs.

---

## Slice 6: Integration and Aggregate Verification

### Task 10: Add End-to-End Sequential Slice Scenarios

**Files:**
- Modify: integration/runtime tests

- [x] Add a complete single-slice flow from assessment through aggregate review.
- [x] Add multi-slice A/B/C flow with A and B independently ready but serialized.
- [x] Prove C starts only after accepted A and B heads.
- [x] Add blocked A with independent B proceeding sequentially.
- [x] Add review rejection and correction-commit scenario.
- [x] Add legacy unsliced/default compatibility scenario.
- [x] Add aggregate completion gate failure scenarios.

### Task 11: Run Full Verification and Close Documentation

- [x] Run focused runtime tests.
- [x] Run orchestrator and wrapper-contract tests.
- [x] Run full regression.
- [x] Run template/distribution validation.
- [x] Confirm no stale references to the removed `-design.md` spec path remain.
- [x] Confirm this plan and the P0 spec reference each other correctly.
- [x] Confirm no uncommitted source/test changes remain.
- [x] Record final verification commands and results in the slice handoff.
- [x] Commit final integration changes if needed.

**Verification:**

```bash
python3 -m pytest tests/test_workflow.py -v
python3 -m pytest tests/test_sdlc_orchestrator.py tests/test_wrapper_contracts.py -v
python3 -m pytest tests/ -v
```

---

## Final Acceptance Checklist

- [x] Missing slice metadata triggers plan-agent assessment.
- [x] Single/multi/blocked assessment is structured and persisted.
- [x] Invalid graphs and multiple active slices are rejected.
- [x] `slice-next` is deterministic and read-only.
- [x] Normal transitions are atomic with dispatch hooks.
- [x] Every slice uses a fresh implement-agent context.
- [x] Todo is not used as durable workflow state.
- [x] Successful slice implementation has a valid contiguous commit range.
- [x] Review uses Git-derived slice scope and records `accepted_head_ref`.
- [x] Review retries preserve base and append correction commits.
- [x] Independent ready slices remain sequential in P0.
- [x] Dependent C waits for accepted A and B.
- [x] Aggregate review gates `apply_change` completion.
- [x] Runtime/templates and canonical/distributed agents are synchronized.
- [x] Full regression passes or any accepted pre-existing failures are individually scoped and evidenced.
