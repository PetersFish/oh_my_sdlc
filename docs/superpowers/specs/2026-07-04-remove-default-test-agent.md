# Remove Default Test-Agent Role Spec

## Purpose

Remove `test-agent` from the default SDLC subagent lifecycle and make testing a distributed responsibility across planning, implementation, review, and EvalOps gates.

The intended operating model is Superpowers-style execution: keep the common path simple, keep the active implementation context hot, use TDD inside the implementation loop, and rely on review for quality gates rather than adding a mandatory verification session between implementation and review.

## Context

The repository's SDLC direction currently favors agent-backed lifecycle wrappers while preserving deterministic workflow governance in `workflow.py`. The current RM-ORCH-007 design already states that the default specialized lifecycle agents are `plan-agent`, `implement-agent`, `review-agent`, and `finish-agent`, and that `test-agent` must not be introduced as a default specialized agent.

The remaining risk is design drift: historical snapshots, completion notes, templates, future agent specs, or prompt text may still refer to a default `test-agent` lifecycle split. If those references remain, future implementation work may recreate the extra session hop even though the intended common path no longer needs it.

This spec defines the desired model and the reviewable acceptance criteria before making implementation changes.

## Problem

A mandatory `test-agent` creates avoidable overhead in the normal development loop:

1. `implement-agent` has the freshest context about changed files, design decisions, new tests, and likely failure causes.
2. Moving full regression execution to `test-agent` forces a cold session to rediscover implementation context.
3. If tests fail, the workflow bounces failure evidence back to `implement-agent`, increasing token cost, latency, and handoff ambiguity.
4. Test overfitting detection is a review-quality concern, not primarily a test-execution concern.
5. The existing workflow gates can require `tdd_passed`, regression evidence, EvalOps evidence, and review evidence without requiring a separate default testing agent.

## Goals

- Remove `test-agent` from the default lifecycle mental model.
- Keep normal TDD, focused tests, full regression, and failure repair inside `implement-agent`.
- Move test quality, overfitting detection, assertion strength, and verification evidence review into `review-agent`.
- Preserve optional independent verification as a future wrapper concept for high-risk or exceptional cases.
- Keep `workflow.py` as the deterministic owner of lifecycle state, gates, hooks, and transitions.
- Maintain compatibility with Superpowers-style task execution: small, direct, reviewable, and evidence-first.
- Produce a clean plan that can be executed incrementally and reviewed before modifying runtime behavior.

## Non-Goals

- Do not delete historical archive snapshots solely to rewrite history.
- Do not remove deterministic test requirements from workflow gates.
- Do not weaken TDD expectations.
- Do not remove EvalOps golden evaluation gates for EvalOps-gated changes.
- Do not add a new `verification-agent` in this change.
- Do not redesign the entire SDLC workflow state machine.
- Do not modify upstream Superpowers skills.
- Do not make `review-agent` execute full implementation debugging by default.

## Desired Lifecycle Model

```text
plan-agent
  -> clarify scope
  -> produce TDD-aware plan
  -> name focused verification commands
  -> name full regression commands
  -> identify EvalOps candidates

implement-agent
  -> execute implementation slice
  -> write or update tests
  -> run TDD red/green loop
  -> run focused tests
  -> run full regression command set
  -> debug and fix failures related to the current slice
  -> return structured implementation and verification evidence

review-agent
  -> review code changes
  -> review test quality
  -> detect overfitting risk
  -> inspect verification evidence
  -> route concrete findings back to implement-agent

finish-agent
  -> archive or finish branch
  -> run roadmap, memory, and workflow cleanup hooks
```

## Responsibility Boundaries

### plan-agent

`plan-agent` owns planning, not execution.

Responsibilities:

- Select the appropriate planning backend, such as OpenSpec propose/new/continue or Superpowers `writing-plans`.
- Define acceptance criteria.
- Define expected TDD behavior.
- Name focused test commands and full regression commands.
- Identify EvalOps-gated targets or explain why EvalOps does not apply.
- Produce handoff material precise enough for `implement-agent` to execute without inventing scope.

Non-responsibilities:

- Does not edit implementation files.
- Does not run tests.
- Does not complete workflow phases by assertion alone.

### implement-agent

`implement-agent` owns the normal implementation and verification loop.

Responsibilities:

- Execute the planned implementation slice.
- Add or update tests that encode the intended behavior.
- For behavior changes, use TDD red/green/refactor where practical.
- Run focused tests relevant to the changed slice.
- Run the agreed full regression command set before declaring implementation complete.
- When verification fails and the failure is likely caused by the current slice, debug and fix within the same session.
- Return structured evidence: commands run, pass/fail results, files touched, unresolved blockers, known verification gaps.

Non-responsibilities:

- Does not approve its own test quality as final.
- Does not claim lifecycle completion without review and workflow gates.
- Does not bypass EvalOps gates for AI behavior changes.

### review-agent

`review-agent` owns quality judgment after implementation evidence exists.

Responsibilities:

- Review implementation correctness and maintainability.
- Review whether tests assert behavior rather than implementation details.
- Detect weak or overfit tests.
- Check whether edge cases, negative cases, and regression cases are covered.
- Check whether mocks hide the real behavior path.
- Check whether snapshots or golden files were updated with adequate rationale.
- Verify that focused tests and full regression evidence are present and credible.
- Route concrete findings back to `implement-agent`.

Non-responsibilities:

- Does not become the default full-regression executor.
- Does not perform broad debugging unless explicitly asked.
- Does not finish or archive the change.

### finish-agent

`finish-agent` owns closure only after implementation and review gates are satisfied.

Responsibilities:

- Archive OpenSpec changes when using `spec-flow`.
- Run Superpowers `finishing-a-development-branch` when using `lightweight-flow`.
- Resolve roadmap and memory hooks.
- Ensure workflow cleanup is completed through `workflow.py`.

Non-responsibilities:

- Does not approve unreviewed implementation.
- Does not ignore pending hooks.

## Optional Independent Verification Wrapper

A future optional verification wrapper may be introduced, but it must not be part of the default lifecycle.

Valid trigger examples:

- High-risk cross-module changes.
- Repeated verification failures after implement-agent repair attempts.
- Suspected flaky tests or environment-specific failures.
- Release or integration gates.
- EvalOps regression capture for durable AI behavior failures.
- Parallel implementation packages requiring final integration verification.

Default rule:

> If a failure is directly related to the current implementation slice and `implement-agent` still has active context, repair should remain with `implement-agent`.

## Test Overfitting Review Criteria

`review-agent` should treat the following as findings:

- Tests assert private implementation details instead of observable behavior.
- Tests duplicate the implementation logic rather than checking expected outcomes.
- Tests only cover the happy path while acceptance criteria imply edge cases.
- Assertions are weakened to make the implementation pass.
- Mocks replace the behavior that actually needs validation.
- Snapshot or golden outputs are refreshed without explaining semantic intent.
- Regression tests do not fail against the original bug or missing behavior.
- Full regression evidence is absent, stale, or not linked to the change.

## Required Repository Changes

The implementation plan should inspect and update these categories:

1. Active roadmap and design docs that still name default `test-agent`.
2. Agent specs or templates that create or reference `test-agent` as a default role.
3. Orchestrator prompts or skills that route normal verification to `test-agent`.
4. Tests or eval cases that expect `test-agent` as a mandatory lifecycle participant.
5. Documentation examples that show `test-agent` in the common path.

Historical archives and snapshots may remain unchanged unless they are copied into active templates or used by current instructions.

## Acceptance Criteria

- No active default lifecycle documentation says `test-agent` is a required specialized agent.
- Active lifecycle mapping lists `plan-agent`, `implement-agent`, `review-agent`, and `finish-agent` as default roles.
- `implement-agent` is documented as owning normal TDD, focused tests, full regression, and failure-fix loops.
- `review-agent` is documented as owning test quality review, overfitting detection, and verification evidence review.
- Optional independent verification is documented only as a risk-triggered future wrapper, not a default session.
- Any remaining `test-agent` references are either historical/archive-only or explicitly marked non-default.
- Existing workflow gates for TDD, EvalOps, review, archive, roadmap, memory, and workflow completion remain intact.
- The plan includes verification commands for searching remaining references and running relevant tests.

## Review Questions

1. Should optional independent verification be named `verification-wrapper`, `verification-worker`, or left unnamed until needed?
2. Should review-agent be allowed to request a one-off independent verification run, or should only `dev-orchestrator` decide that?
3. Should full regression commands be fixed per repository, inferred from plan artifacts, or carried in workflow context?
4. Should repeated implement-agent test failures have a numeric threshold before optional independent verification is considered?
5. Should `review-agent` block on missing full regression evidence for all changes, or only behavior-changing code changes?
