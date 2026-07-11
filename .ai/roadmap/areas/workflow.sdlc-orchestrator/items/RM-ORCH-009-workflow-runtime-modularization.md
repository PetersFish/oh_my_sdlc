---
id: RM-ORCH-009
title: "Workflow Runtime Modularization"
status: done
stage: v2
priority: p1
order: 48
depends_on:
  - RM-ORCH-008
openspec_change: modularize-workflow-runtime
created_at: 2026-06-26
started_at: null
completed_at: 2026-07-12
---

# Goal

Split the large workflow runtime into stable responsibility-based modules while preserving the existing `workflow.py` CLI facade and all observable behavior.

# Problem Context

`workflow.py` has grown into a multi-responsibility runtime that handles state I/O, workflow definition validation, domain loaders, policy registry, command handlers, governance diagnostics, transition helpers, and CLI dispatch. This makes future iteration expensive, increases token usage for changes, and raises the risk of accidentally modifying unrelated behavior.

After the agent-backed lifecycle wrapper architecture lands, modularization becomes urgent because future wrapper and state-machine work will otherwise continue to accumulate in one large file.

# Scope

## In

- Keep `.ai/workflows/scripts/workflow.py` as the user-facing CLI entry point.
- Split stable responsibilities into modules such as state I/O, workflow definition handling, domain loaders, policy registry, governance diagnostics, command handlers, and CLI glue.
- Preserve command names, arguments, exit codes, JSON outputs, and run file layout.
- Preserve the workflow runtime as the only writer of `.ai/workflows/runs/` state.
- Add or update tests that prove behavior did not change across the module split.
- Sync live workflow files to bootstrap templates and distributed copies.

## Out

- No semantic redesign of phases or transitions.
- No class-based state machine rewrite yet.
- No change to roadmap, OpenSpec, memory, or EvalOps domain ownership.
- No new orchestration agent behavior beyond preserving the existing runtime contract.

# Design Notes

## Key Decisions

- Treat modularization as a behavior-preserving refactor.
- Keep `workflow.py` as a thin CLI facade to avoid breaking documented commands and external plugin references.
- Extract modules around existing responsibility seams rather than inventing new abstractions.
- Use existing tests as the regression harness, adding focused tests only where module boundaries introduce new risk.

## Tradeoffs

- Module splitting reduces future maintenance cost but creates short-term churn across templates and distributed copies.
- Keeping the CLI facade limits the cleanup possible in this phase, but it protects external callers and documentation.
- A behavior-preserving split does not fully solve state-machine design complexity, but it creates the seam needed for a later OO transition.

## Initial Approach

1. Establish a baseline test run before refactoring.
2. Extract pure or near-pure helpers first: workflow definition validation, state I/O, and domain loaders.
3. Extract policy registry and governance diagnostics after the lower-level modules are stable.
4. Keep command handlers compatible and gradually import extracted helpers.
5. Run full workflow tests and template drift checks after each substantial split.

## Open Questions

- Should modules live beside `workflow.py` under `.ai/workflows/scripts/`, or should bootstrap templates use a package directory?
- How much of `tests/test_workflow.py` should remain end-to-end versus gaining module-level unit tests?

# Acceptance Criteria

- `workflow.py` remains executable at `.ai/workflows/scripts/workflow.py` with the same command surface.
- Existing workflow tests pass after the split.
- External documentation and plugin commands that call `workflow.py` remain valid.
- State writes remain confined to `.ai/workflows/runs/` for workflow runtime mutations.
- Bootstrap templates include the same module layout as the live runtime.
- Template sync and distributed-copy checks pass.

# Promotion Notes

Promote immediately after `agent-backed-lifecycle-wrapper-architecture` is implemented and stabilized enough that the minimal workflow contract is known.

# Completion Notes

Archived as `openspec/changes/archive/2026-07-11-modularize-workflow-runtime/`. Main spec synced to `openspec/specs/workflow-runtime-modularity/spec.md`.

Accomplished:
- Split `workflow.py` into responsibility-based modules under `.ai/workflows/scripts/workflow_runtime/` (state, definitions, domains, policies, governance, dispatch, lifecycle, cli, core) while preserving `workflow.py` as the user-facing CLI facade.
- Preserved all command names, arguments, exit codes, JSON outputs, and run file layout. State writes remain confined to `.ai/workflows/runs/`.
- Bootstrap templates and distributed copies (`.opencode/`, `.claude/`, `.cursor/`) include the same module layout via `sdlc-project-bootstrap/templates/workflow/workflow_runtime/`.
- Added `tests/test_workflow_modules.py` covering module boundaries; existing workflow tests pass.

Deferred / follow-up:
- RM-ORCH-010 (Class-Based Workflow State Machine) remains the next phase; the module split creates the seam for that OO transition but does not implement it.
- Open design question on test granularity (end-to-end vs module-level unit tests) deferred to RM-ORCH-010.

No separate memory sync triggered from this item; durable facts will be captured via the post-archive OpenSpec memory sync for this change.

# Design Reference

- `docs/manual/design/state_machine_design.md`
- `.ai/workflows/scripts/workflow.py`
- `tests/test_workflow.py`
- `skills/sdlc-project-bootstrap/templates/workflow/`
