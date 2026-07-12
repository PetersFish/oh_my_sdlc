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

- [ ] Add a fixture that creates an `apply_change` run with `implementation.strategy=sequential`.
- [ ] Add failing tests for state normalization of legacy runs without `implementation`.
- [ ] Add failing tests for valid `single_slice` assessment materializing `default`.
- [ ] Add failing tests for valid multi-slice state persistence across resume.
- [ ] Add failing validation tests for duplicate ids, reserved `aggregate`, unknown dependencies, self-dependencies, cycles, missing required-task coverage, and multiple active slices.
- [ ] Add failing tests proving evidence under one explicit slice cannot satisfy another.
- [ ] Run the focused test class and confirm RED.

### Task 2: Implement Slice State and Validation

**Files:**
- Modify: `.ai/workflows/scripts/workflow_runtime/state.py`
- Modify: related runtime state helpers

- [ ] Extend allowed state keys with `implementation` without weakening unknown-key validation.
- [ ] Add legacy normalization that produces an in-memory compatibility `default` slice only under allowed policy.
- [ ] Add slicing assessment state: `not_required|pending|completed|blocked`.
- [ ] Add slice statuses: `pending|ready|in_progress|in_review|blocked|completed|cancelled`.
- [ ] Add per-slice fields for attempts, block, refs, evidence, and handoffs.
- [ ] Implement graph validation and deterministic error payloads containing affected slice ids.
- [ ] Enforce `strategy=sequential` and at most one active slice.
- [ ] Enforce completed slice => passed review evidence + `accepted_head_ref`.
- [ ] Enforce aggregate-ready/passed invariants.
- [ ] Run Slice 1 focused tests and make them GREEN.
- [ ] Commit with the slice id in the message.

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

- [ ] Add failing tests for `slice-status` for all slices and one selected slice.
- [ ] Add failing tests for deterministic, non-mutating `slice-next`.
- [ ] Test declaration-order selection when A and B are both ready.
- [ ] Test `dispatch_aggregate_review`, `all_slices_and_aggregate_complete`, and `no_ready_slice` outcomes.
- [ ] Add failing tests for `slice-block`, `slice-resume`, and `slice-cancel` authorization.
- [ ] Register commands in the CLI parser.
- [ ] Implement `slice-status` and `slice-next` as read-only commands.
- [ ] Implement `slice-block` for explicit exceptional control.
- [ ] Implement `slice-resume` as `blocked -> ready` only when dependencies remain accepted.
- [ ] Implement required-slice cancellation gate using user-decision/exception evidence.
- [ ] Ensure slice commands do not silently overwrite top-level block state.
- [ ] Run focused command tests and make them GREEN.
- [ ] Commit with the slice id in the message.

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

- [ ] Add failing test: implement dispatch is rejected while slicing assessment is pending or blocked.
- [ ] Add failing test: `before-dispatch(implement-agent, slice_id)` accepts only the exact `slice-next` result.
- [ ] Add failing test: before-dispatch atomically sets `in_progress`, increments attempt count, sets `active_slice_id`, and returns slice context.
- [ ] Add failing test: another slice cannot dispatch while one is `in_progress` or `in_review`.
- [ ] Add failing test: successful implement result without valid `base_ref`, `head_ref`, and `commit_refs[]` cannot enter review.
- [ ] Add failing test: implement success moves only the same slice to `in_review`.
- [ ] Add failing test: review dispatch requires that same slice to be `in_review`.
- [ ] Add failing test: review pass records `accepted_head_ref`, completes the slice, clears active state, and recomputes readiness.
- [ ] Add failing test: review rejection preserves original `base_ref` and allows head advancement.
- [ ] Add failing test for A/B sequential execution and C depending on accepted A+B.
- [ ] Implement all transitions as state-owner operations inside existing hooks.
- [ ] Add deterministic reconciliation for external task invocation failure after successful before-dispatch.
- [ ] Validate sequential commit-chain invariant.
- [ ] Run focused dispatch tests and make them GREEN.
- [ ] Commit with the slice id in the message.

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

- [ ] Add `planning_action=assess_implementation_slicing`.
- [ ] Require structured decision, confidence, reasons, signals, and slices.
- [ ] Define single/multi/blocked rubric without hard task/file thresholds.
- [ ] Require full selected artifact-set reading before assessment.
- [ ] Require task coverage and acyclic dependency graph.
- [ ] State that decomposition reorganizes work but does not redesign approved behavior.
- [ ] Add clearly-small, clearly-large, and ambiguous eval/contract cases.

### Task 6: Update Dev-Orchestrator

**Files:**
- Modify: `agents/dev-orchestrator.md`
- Modify: `tests/test_sdlc_orchestrator.py`

- [ ] Route `slicing_assessment_required` to plan-agent.
- [ ] During `apply_change`, call `slice-next` and dispatch exactly one returned slice.
- [ ] Forward slice contract, exact id, runtime context, design artifacts, and direct dependency handoffs.
- [ ] Wait for review acceptance before requesting the next slice.
- [ ] Route `dispatch_aggregate_review` to review-agent with aggregate scope.
- [ ] Explicitly prohibit technical decomposition, parallel dispatch, per-slice branch creation, and integration slices in P0.
- [ ] Add static contract tests for all routing rules.

### Task 7: Update Implement-Agent

**Files:**
- Modify: `agents/implement-agent.md`
- Modify: implement-agent contract tests

- [ ] Enforce exactly one slice per dispatch.
- [ ] Reconstruct `todowrite` from the current slice contract.
- [ ] Require runtime-provided sequential worktree and `base_ref`.
- [ ] Block on unrelated dirty source/test changes.
- [ ] Require focused and regression verification before success.
- [ ] Require committing current-slice source/test changes before success.
- [ ] Return `base_ref`, `head_ref`, ordered `commit_refs[]`, changed-file evidence, and verification coverage.
- [ ] Require clean source/test state after commit.
- [ ] Require durable handoff before success, block, or failure.
- [ ] Preserve original base and append correction commits after review feedback.

### Task 8: Update Review-Agent

**Files:**
- Modify: `agents/review-agent.md`
- Modify: review-agent contract tests

- [ ] Add `review_scope=slice|aggregate`.
- [ ] For slice review, treat `base_ref..<head_ref>` as authoritative.
- [ ] Use `git -C <worktree_path>` whenever worktree mode is active.
- [ ] Validate current HEAD/ref/worktree consistency.
- [ ] Derive file/hunk scope from Git and compare it with implement evidence.
- [ ] Block on `review_slice_change_set_mismatch` or dirty source/test changes outside the range.
- [ ] For aggregate review, inspect `parent_ref..<latest accepted head>` and all required slice evidence.
- [ ] Validate full regression, requirement coverage, contiguous ranges, and unresolved blocks.

- [ ] Run all agent contract tests.
- [ ] Commit Slice 4 changes.

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

- [ ] Copy live runtime behavior to canonical bootstrap templates.
- [ ] Run the repository's canonical distribution/sync command rather than editing generated copies independently.
- [ ] Confirm canonical agents and all three distributed agent sets match.
- [ ] Confirm live runtime and bootstrap runtime templates match where required.
- [ ] Run sync validation in dry-run mode when available.
- [ ] Commit Slice 5 changes.

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

- [ ] Add a complete single-slice flow from assessment through aggregate review.
- [ ] Add multi-slice A/B/C flow with A and B independently ready but serialized.
- [ ] Prove C starts only after accepted A and B heads.
- [ ] Add blocked A with independent B proceeding sequentially.
- [ ] Add review rejection and correction-commit scenario.
- [ ] Add legacy unsliced/default compatibility scenario.
- [ ] Add aggregate completion gate failure scenarios.

### Task 11: Run Full Verification and Close Documentation

- [ ] Run focused runtime tests.
- [ ] Run orchestrator and wrapper-contract tests.
- [ ] Run full regression.
- [ ] Run template/distribution validation.
- [ ] Confirm no stale references to the removed `-design.md` spec path remain.
- [ ] Confirm this plan and the P0 spec reference each other correctly.
- [ ] Confirm no uncommitted source/test changes remain.
- [ ] Record final verification commands and results in the slice handoff.
- [ ] Commit final integration changes if needed.

**Verification:**

```bash
python3 -m pytest tests/test_workflow.py -v
python3 -m pytest tests/test_sdlc_orchestrator.py tests/test_wrapper_contracts.py -v
python3 -m pytest tests/ -v
```

---

## Final Acceptance Checklist

- [ ] Missing slice metadata triggers plan-agent assessment.
- [ ] Single/multi/blocked assessment is structured and persisted.
- [ ] Invalid graphs and multiple active slices are rejected.
- [ ] `slice-next` is deterministic and read-only.
- [ ] Normal transitions are atomic with dispatch hooks.
- [ ] Every slice uses a fresh implement-agent context.
- [ ] Todo is not used as durable workflow state.
- [ ] Successful slice implementation has a valid contiguous commit range.
- [ ] Review uses Git-derived slice scope and records `accepted_head_ref`.
- [ ] Review retries preserve base and append correction commits.
- [ ] Independent ready slices remain sequential in P0.
- [ ] Dependent C waits for accepted A and B.
- [ ] Aggregate review gates `apply_change` completion.
- [ ] Runtime/templates and canonical/distributed agents are synchronized.
- [ ] Full regression passes or any accepted pre-existing failures are individually scoped and evidenced.
