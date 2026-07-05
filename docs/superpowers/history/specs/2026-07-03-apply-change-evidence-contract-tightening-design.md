# Apply Change Evidence Contract Tightening

## Context

The current `apply_change` lifecycle in the SDLC workflow can reach a state where implementation and verification are effectively complete, but the workflow run cannot complete the phase because agent result contracts and workflow phase evidence requirements do not align.

The observed failure mode in run `2026-07-03-dev-orchestrator-roadmap-agent-coop` was:

- `implement-agent` completed the required code changes.
- `test-agent` completed focused and regression verification.
- `review-agent` accepted the change.
- `workflow.py after-dispatch` still blocked phase completion because the final review result did not include the `apply_change` phase evidence keys required by workflow definition.

This produced repeated loops through implement/test/review even when the underlying code changes were already correct.

## Goals

- Tighten the `apply_change` evidence contract so final review can complete the phase without ambiguity.
- Make `review-agent` explicitly emit the phase-completion evidence required by `apply_change` success.
- Allow workflow runtime to validate `apply_change` using aggregated phase evidence rather than only the current agent payload.
- Define a stable ownership model for `eval_passed_or_human_decision_recorded`.
- Preserve handoff history for repeated implement/test/review attempts within the same slice.
- Normalize agent status semantics so "ready for downstream verification" is not treated as a blocker.

## Non-Goals

- Do not redesign `create_change`, `archive_change`, or `post_archive_actions` in this change.
- Do not replace the current multi-agent `apply_change` structure with a single-worker phase model.
- Do not generalize the new aggregation semantics to all phases yet.
- Do not change product-level roadmap/spec behavior unrelated to workflow evidence contracts.

## Decisions

### Decision 1: `review-agent` success must emit `apply_change` phase evidence

When `review-agent` returns `status: "success"` for `apply_change`, its `evidence` payload must include:

- `tasks_complete: true`
- `tdd_passed: true`
- `eval_passed_or_human_decision_recorded: true`
- `review_complete: true`
- `verification_passed: true`
- `review_decision: "accepted"`
- `criteria_satisfied: "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded"`

Rationale:

- `apply_change` is completed by the lifecycle chain, but the final worker must provide evidence compatible with workflow phase completion.
- Keeping review-only semantics is insufficient because `after-dispatch` validates phase evidence against the worker result.

### Decision 2: `dev-orchestrator` must pass phase evidence requirements into review dispatch

When dispatching `review-agent` for `apply_change`, `dev-orchestrator` must include the current phase's:

- `evidence_keys`
- `exit_criteria`
- summarized successful `test-agent` evidence relevant to phase completion

Rationale:

- The review worker should not infer workflow completion requirements from prose or prior failures.
- The dispatch prompt must carry the runtime contract explicitly.

### Decision 3: `after-dispatch` must validate against aggregated phase evidence for `apply_change`

For successful `apply_change` lifecycle results, phase evidence validation will use an aggregated view built from:

1. the current worker `agent_evidence`
2. existing `state.evidence`
3. prior successful agent results in `state.evidence.agent_results[<slice>]`

The aggregated evidence will be used for:

- checking required `evidence_keys`
- checking required `exit_criteria`

The runtime remains the source of truth by promoting resolved values back into `state.evidence`.

Rationale:

- The current implementation only checks the current worker payload, which forces duplication and causes false blocks even when prior lifecycle evidence already exists.
- `apply_change` is intentionally collaborative across implement/test/review; the runtime should recognize that structure.

### Decision 4: `eval_passed_or_human_decision_recorded` is finalized at review acceptance

For `apply_change`, `eval_passed_or_human_decision_recorded` becomes true only when final review accepts the change after successful test verification.

The approval basis is:

- `test-agent` evidence includes `verification_passed: true`
- `test-agent` evidence includes successful regression coverage for the slice
- `review-agent` accepts the change

Rationale:

- This keeps implement-agent focused on code changes.
- It prevents the field from being guessed too early.
- It matches the current lifecycle where review is the final gate before phase completion.

### Decision 5: Handoff history must be append-only per attempt

Each implement/test/review dispatch continues writing the latest handoff at the existing path, and additionally writes a timestamped history copy under a per-slice history directory.

Example:

- latest: `.ai/workflows/runs/active/<run_id>/handoffs/default/review-agent.md`
- history: `.ai/workflows/runs/active/<run_id>/handoffs/default/history/review-agent-<timestamp>.md`

Rationale:

- The current workflow overwrites the latest handoff and loses attempt history.
- Long remediation loops need durable attempt-by-attempt traceability.

### Decision 6: Waiting for downstream verification is success, not blocked

For `implement-agent`, when code work is complete and the next valid step is independent verification, the result must be:

- `status: "success"`
- `recommended_next_action: "dispatch_test_agent"`

This condition must not be represented as:

- `status: "blocked"`
- blocker reason like `verification_pending`

Rationale:

- Downstream verification is part of the happy path, not a worker failure.
- Treating it as blocked confuses workflow state and after-dispatch policy.

## Scope

This change applies only to the `apply_change` phase and its lifecycle participants:

- `dev-orchestrator`
- `implement-agent`
- `test-agent`
- `review-agent`
- `workflow.py after-dispatch` runtime logic
- handoff artifact generation for apply-change workers

No phase contract changes are required for:

- `create_change`
- `archive_change`
- `post_archive_actions`

## Architecture

### Current Problem

The current flow uses three specialized workers in sequence:

1. implement-agent
2. test-agent
3. review-agent

But `after-dispatch` validates phase completion using only the current worker result. This creates a mismatch because:

- `implement-agent` owns implementation evidence
- `test-agent` owns verification evidence
- `review-agent` owns acceptance evidence

Yet the phase contract expects a single success payload to satisfy the full `apply_change` evidence set.

### New Model

The improved `apply_change` model keeps the same worker sequence but makes the contract explicit:

1. `implement-agent` completes implementation and returns success for handoff to verification.
2. `test-agent` independently verifies implementation and records verification evidence.
3. `review-agent` accepts or rejects the slice and emits final phase-completion evidence.
4. `after-dispatch` validates `apply_change` using an aggregated evidence view rather than only one payload.

This keeps worker roles separate while allowing the runtime to complete the phase deterministically.

## Runtime Behavior Changes

### `after-dispatch` evidence aggregation

Introduce an `apply_change`-specific evidence aggregation path that merges:

- current agent evidence
- existing promoted phase evidence in state
- relevant slice-local successful worker evidence

Aggregation precedence:

1. current agent evidence
2. existing state evidence
3. prior successful agent results for the slice

This allows final acceptance to rely on already-proven state without requiring every downstream worker to restate all upstream data manually.

### `criteria_satisfied` handling

For `apply_change`, the accepted success payload must include exact workflow criteria names as a comma-delimited string. The runtime will continue using those names for completion checks.

### Block-state consistency

If `after-dispatch` determines a worker success result is still invalid for phase completion, it must produce a workflow-block outcome that is consistent with persisted run state and transition messaging.

This design does not fully redesign block persistence, but the implementation should avoid states where:

- transition output says "block"
- while run state still appears unblocked/running without a recorded workflow block reason

## Agent Contract Changes

### `review-agent`

Update the prompt and JSON success examples so `apply_change` review success includes both:

- review semantics
- phase-completion semantics

### `implement-agent`

Update prompt examples and status guidance so normal handoff to verification is emitted as success, not blocked.

### `dev-orchestrator`

Update review dispatch instructions so the review worker receives explicit phase contract details and is told to satisfy them in its final acceptance envelope.

## Handoff Artifact Changes

For apply-change workers, handoff writing will follow a dual-write model:

- overwrite latest handoff path for convenience
- append timestamped copy into `handoffs/<slice>/history/`

This applies to:

- `implement-agent`
- `test-agent`
- `review-agent`

History files are diagnostic artifacts and do not replace the latest handoff path expected by existing readers.

## Affected Files

- `agents/dev-orchestrator.md`
- `agents/implement-agent.md`
- `agents/review-agent.md`
- `.ai/workflows/scripts/workflow.py`
- `skills/sdlc-project-bootstrap/templates/workflow/workflow.py`
- project-level distributed workflow template copies
- project-level distributed agent copies
- `tests/test_workflow.py`
- `tests/test_wrapper_contracts.py`

## Testing Strategy

### Prompt/contract tests

- `review-agent` success contract includes `tasks_complete`, `tdd_passed`, and `eval_passed_or_human_decision_recorded` for `apply_change`
- `implement-agent` no longer models downstream verification as blocked
- `dev-orchestrator` review dispatch prompt mentions phase evidence requirements

### Runtime tests

- `after-dispatch` accepts valid review success evidence for `apply_change`
- `after-dispatch` can satisfy `apply_change` checks using aggregated evidence when appropriate
- missing `eval_passed_or_human_decision_recorded` still blocks completion
- successful worker dispatch writes latest and history handoffs
- downstream verification pending is not treated as an implementation blocker

### Regression tests

- `tests/test_workflow.py`
- `tests/test_wrapper_contracts.py`
- relevant sync/drift tests for workflow templates and distributed agent copies

## Risks

- Aggregated evidence logic could accidentally over-generalize beyond `apply_change` if implemented too broadly.
- Dual-write handoff history could create noisy artifacts if naming rules are inconsistent.
- Review success contract must stay aligned with runtime evidence rules, or the same mismatch will reappear in a different form.

## Mitigations

- Scope aggregation explicitly to `apply_change`.
- Keep history-writing logic deterministic and timestamp-based.
- Add prompt-contract and runtime tests that assert the exact required evidence keys.

## Success Criteria

- A successful implement -> test -> review chain can complete `apply_change` without manual evidence patching.
- `review-agent` final acceptance is sufficient for workflow completion when upstream verification has passed.
- `implement-agent` no longer returns blocked for normal verification handoff.
- Repeated review/test cycles preserve durable handoff history.
- Existing behavior for other phases remains unchanged.
