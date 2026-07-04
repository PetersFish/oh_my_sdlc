# Remove Default Test-Agent Role Spec

## Purpose

Remove `test-agent` from the default SDLC subagent lifecycle and make testing a distributed responsibility across planning, implementation, review, and EvalOps gates.

The intended operating model is Superpowers-style execution: keep the common path simple, keep the active implementation context hot, use TDD inside the implementation loop, and rely on review for quality gates rather than adding a mandatory verification session between implementation and review.

## Context

The repository's SDLC direction now centers on `dev-orchestrator` plus specialized agent files under `agents/`. The active `sdlc-main` workflow routes SDLC phases to `dev-orchestrator`, not to the legacy `sdlc-orchestrator` skill. `dev-orchestrator` is the routing coordinator and must dispatch specialized agents rather than doing planning, implementation, verification, review, or finishing work itself.

The current agent tree still contains active `test-agent` files. Those files describe a default verification subagent dispatched after `implement-agent`, which conflicts with the desired common path. The cleanup must therefore remove or de-register active `test-agent` files, not merely reword roadmap documentation.

There is also a legacy `skills/sdlc-orchestrator/SKILL.md` family and corresponding EvalOps assets. Based on current workflow and `dev-orchestrator` configuration, this skill should be treated as a retirement candidate rather than a file to update. It may be deleted after dependency checks confirm no active runtime, installer, bootstrap, eval, or test path still requires it.

## Problem

A mandatory `test-agent` creates avoidable overhead in the normal development loop:

1. `implement-agent` has the freshest context about changed files, design decisions, new tests, and likely failure causes.
2. Moving full regression execution to `test-agent` forces a cold session to rediscover implementation context.
3. If tests fail, the workflow bounces failure evidence back to `implement-agent`, increasing token cost, latency, and handoff ambiguity.
4. Test overfitting detection is a review-quality concern, not primarily a test-execution concern.
5. The existing workflow gates can require `tdd_passed`, regression evidence, EvalOps evidence, and review evidence without requiring a separate default testing agent.

## Goals

- Remove `test-agent` from the default lifecycle mental model and from active agent runtime loading.
- Keep normal TDD, focused tests, full regression, and failure repair inside `implement-agent`.
- Move test quality, overfitting detection, assertion strength, and verification evidence review into `review-agent`.
- Preserve optional independent verification as a future wrapper concept for high-risk or exceptional cases.
- Keep `workflow.py` as the deterministic owner of lifecycle state, gates, hooks, and transitions.
- Make `finish-agent` capture a clean commit id before memory/roadmap hook synchronization and commit again after workflow cleanup if generated hook artifacts remain.
- Retire legacy `sdlc-orchestrator` skill assets if dependency audit confirms `dev-orchestrator` no longer depends on them.
- Maintain compatibility with Superpowers-style task execution: small, direct, reviewable, and evidence-first.

## Non-Goals

- Do not delete historical archive snapshots solely to rewrite history.
- Do not remove deterministic test requirements from workflow gates.
- Do not weaken TDD expectations.
- Do not remove EvalOps golden evaluation gates for EvalOps-gated changes that still target active agents or skills.
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
  -> pre-hook commit and push
  -> resolve roadmap and memory hooks
  -> complete workflow cleanup through workflow.py
  -> post-hook dirty-tree check
  -> second commit and push if sync-generated files remain
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
- Before resolving roadmap or memory hooks, check repository status, commit all already-approved implementation/archive changes, push, and record the resulting commit id for memory sync.
- Resolve memory and roadmap hooks only after the pre-hook commit id exists.
- Ensure workflow cleanup is completed through `workflow.py` after hook resolution.
- After hook resolution and workflow cleanup, inspect the repository again. If memory sync, roadmap sync, template sync, or workflow hook completion generated additional files, commit and push those files in a second commit.
- Emit evidence for both commit checkpoints: pre-hook commit id and optional post-hook commit id.

Non-responsibilities:

- Does not approve unreviewed implementation.
- Does not ignore pending hooks.
- Does not hide uncommitted generated artifacts after hook execution.

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

## Legacy `sdlc-orchestrator` Skill Retirement

The legacy `skills/sdlc-orchestrator/SKILL.md` file should not be updated as part of this cleanup unless a dependency audit proves it is still active.

Retirement criteria:

- `agents/dev-orchestrator.md` does not list `sdlc-orchestrator` in required skills or skill permissions.
- `.ai/workflows/definitions/sdlc-main.yaml` does not list `sdlc-orchestrator` as an active worker.
- Agent installation, activation, and rendering scripts do not read or distribute it as a required asset.
- Bootstrap templates do not install it as the default orchestrator entrypoint.
- Tests do not require the legacy skill for active runtime behavior.
- EvalOps targets for `skill.sdlc-orchestrator` are either deleted, archived, or explicitly marked as historical after the active agent target replaces them.

If all checks pass, delete the canonical legacy skill and its distributed copies instead of editing them:

- `skills/sdlc-orchestrator/`
- `.opencode/skills/sdlc-orchestrator/`
- `.claude/skills/sdlc-orchestrator/`
- `.cursor/skills/sdlc-orchestrator/`

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
2. Active agent specs and distributed copies that define or reference `test-agent` as a default role.
3. Active `finish-agent` specs and distributed copies so commit/push checkpoints happen before hook synchronization and after workflow cleanup.
4. Legacy `sdlc-orchestrator` skill assets and EvalOps assets, deleting them if no active dependency remains.
5. Orchestrator prompts, tests, or eval cases that route normal verification to `test-agent`.
6. Documentation examples that show `test-agent` in the common path.

Historical archives and snapshots may remain unchanged unless they are copied into active templates or used by current instructions.

## Acceptance Criteria

- No active default lifecycle documentation says `test-agent` is a required specialized agent.
- Active runtime agent files no longer include `agents/test-agent.md` or distributed `test-agent` copies unless explicitly retained as disabled/historical examples.
- Active lifecycle mapping lists `plan-agent`, `implement-agent`, `review-agent`, and `finish-agent` as default roles.
- `implement-agent` is documented as owning normal TDD, focused tests, full regression, and failure-fix loops.
- `review-agent` is documented as owning test quality review, overfitting detection, and verification evidence review.
- `finish-agent` performs a pre-hook commit and push before memory/roadmap hook resolution and records that commit id for memory sync.
- `finish-agent` performs workflow cleanup through `workflow.py`, then performs a post-cleanup dirty-tree check and creates a second commit and push if generated files remain.
- Optional independent verification is documented only as a risk-triggered future wrapper, not a default session.
- Any remaining `test-agent` references are either historical/archive-only or explicitly marked disabled/non-default.
- Legacy `sdlc-orchestrator` skill assets are deleted when dependency checks prove they are unused, or the blocker is documented with the exact active dependency.
- Existing workflow gates for TDD, EvalOps, review, archive, roadmap, memory, and workflow completion remain intact.
- The plan includes verification commands for active agent cleanup, legacy skill dependency checks, finish-agent commit checkpoints, and relevant tests.

## Review Questions

1. Should optional independent verification be named `verification-wrapper`, `verification-worker`, or left unnamed until needed?
2. Should review-agent be allowed to request a one-off independent verification run, or should only `dev-orchestrator` decide that?
3. Should full regression commands be fixed per repository, inferred from plan artifacts, or carried in workflow context?
4. Should repeated implement-agent test failures have a numeric threshold before optional independent verification is considered?
5. Should `review-agent` block on missing full regression evidence for all changes, or only behavior-changing code changes?
6. Should retired `skill.sdlc-orchestrator` EvalOps cases be deleted, moved to an archive area, or migrated to `agent.dev-orchestrator` coverage?
7. What commit message convention should `finish-agent` use for the pre-hook commit and the post-hook generated-artifacts commit?
