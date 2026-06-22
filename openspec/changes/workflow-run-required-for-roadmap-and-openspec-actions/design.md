## Context

The SDLC runtime already governs OpenSpec lifecycle actions through preflight policies and multi-run active state. Roadmap actions remain outside that model: roadmap capture, insert, review, revise, cancel, reorder, replan, and done mutate durable roadmap state without a matching workflow run or evidence trail.

This change closes that gap while preserving existing boundaries: `sdlc-orchestrator` coordinates lifecycle and gates, `sdlc-roadmap` performs roadmap mutations, and `workflow.py` owns run state and preflight decisions.

## Goals / Non-Goals

**Goals:**

- Make roadmap stateful mutations governed by workflow runtime preflight.
- Add `roadmap_item` subject support to workflow phase inference and run lookup.
- Route roadmap-first actions through runtime verification before worker dispatch.
- Require roadmap mutation evidence that the orchestrator can record and use for follow-up runtime actions.
- Support `roadmap_replan` as a governed batch mutation using orchestrator loops over single-subject primitives.
- Add a single-subject run invalidation primitive for replanned roadmap items.
- Enforce canonical-run promotion: roadmap item promotion to OpenSpec change SHALL reuse the existing `roadmap_item` run as the canonical run rather than creating a second `openspec_change` run.
- Detect ungoverned roadmap state through governance-check.

**Non-Goals:**

- Do not make `sdlc-roadmap` start, resume, preflight, advance, or complete workflow runs.
- Do not create a bulk workflow API for replan.
- Do not create a second `openspec_change` workflow run when a linked `roadmap_item` run already exists for promotion.
- Do not govern read-only `roadmap list`.
- Do not govern bootstrap-only `roadmap_init`.
- Do not modify upstream OpenSpec worker skills.
- Do not auto-repair legacy ungoverned roadmap state.

## Decisions

### Decision: Add Roadmap Governed Actions

Register roadmap lifecycle actions through the existing policy registry rather than adding action-specific branches inside `cmd_preflight`.

Actions:

- `roadmap_capture`, `roadmap_insert`: create or require a run at `create_roadmap`
- `roadmap_review`: require a run at `review_roadmap`
- `roadmap_revise`, `roadmap_cancel`, `roadmap_reorder`: require a matching run but do not advance phase
- `roadmap_replan`: require preflight for the batch mutation, then use evidence-driven follow-up actions
- `roadmap_done`: govern manual done and preserve the existing post-archive hook path for archive-driven done

Alternative considered: keep roadmap actions outside runtime and rely on documentation. This was rejected because it preserves the same governance gap this change is meant to close.

### Decision: Keep Roadmap Worker Boundary Thin

`sdlc-roadmap` SHALL remain the owner of roadmap files and revision history, but it SHALL NOT own workflow lifecycle. It returns evidence after mutations; orchestrator records that evidence and performs runtime commands.

Alternative considered: let `sdlc-roadmap` call `workflow.py` directly. This was rejected because it would duplicate orchestrator responsibilities and couple roadmap mechanics to runtime lifecycle coordination.

### Decision: Replan Uses Single-Subject Runtime Loops

`roadmap_replan` is a batch roadmap mutation, but the runtime should not grow a bulk replan API. Instead:

1. The orchestrator preflights `roadmap_replan`.
2. The roadmap worker performs replan and returns evidence: cancelled old item IDs, created new item IDs, and batch revision path.
3. The orchestrator loops over cancelled old item IDs and calls a single-subject invalidation primitive.
4. The orchestrator loops over created new item IDs and calls the existing single-subject start path.

Alternative considered: add `workflow.py bulk-replan-runs`. This was rejected because it would make the runtime understand roadmap batch semantics and make partial failures harder to report.

### Decision: Add Single-Subject `cancel-run` Primitive

Replanned roadmap item runs are explicitly abandoned, not completed. A runtime primitive such as `cancel-run --subject-type roadmap_item --subject-id <id> --reason replanned` SHALL remove the matching active run and clear `current.json` if it points to that run, without writing history.

Alternative considered: have agents delete `active/<run_id>.json` directly. This was rejected because it violates runtime ownership of workflow state and increases corruption risk.

### Decision: Canonical-Run Promotion From Roadmap Item To OpenSpec Change

Roadmap item promotion to an OpenSpec change SHALL NOT create a second workflow run. Instead, the existing `roadmap_item/RM-XXX` run serves as the canonical run for the entire lifecycle:

1. The roadmap item run starts at `create_roadmap` or `review_roadmap`.
2. When promotion creates an OpenSpec change, the orchestrator writes the `change_id` into that run's `context.change_id`.
3. `openspec_create` preflight, upon seeing an `openspec_change` subject, SHALL also scan for a matching active `roadmap_item` run whose `context.change_id` or linked roadmap item frontmatter points to the requested change id.
4. If found, the run pointer is set to the roadmap item run, phase validation proceeds against `create_change`, and preflight returns `allowed: true` — no new run is started.
5. Direct OpenSpec changes (without a linked roadmap item) still create `openspec_change/<change-id>` runs as before.

Alternative considered: allow dual runs and link them through roadmap frontmatter. This was rejected because it creates ambiguous lifecycle ownership, makes governance-check harder (which run owns pending hooks?), and requires complex handoff logic between two active runs.

### Decision: Governance-Check Reports, Does Not Repair

`governance-check` SHALL report active roadmap items without matching workflow evidence and archived linked items without matching workflow history or active remediation runs. It SHALL include explicit remediation commands and stop conditions, but it SHALL remain read-only.

## Risks / Trade-offs

- More governed actions increase `workflow.py` policy surface -> keep registrations declarative via `@register_policy` and add focused tests for each action.
- Replan loops can partially fail -> require the orchestrator summary to report per-item success/failure and leave unresolved items visible.
- Legacy roadmap items may report governance findings -> report remediation commands instead of auto-mutating existing roadmap or runtime state.
- `cancel-run` without history removes traceability for abandoned runs -> preserve replan rationale in roadmap batch revision and changelog instead.
- Roadmap-first routing becomes stricter -> document explicit opt-out only where appropriate and keep `roadmap list` read-only/unblocked.
- Promotion creates duplicate runs if canonical-run check is missed -> add preflight linked-run lookup as the first path; add tests for the common promotion scenario.

## Migration Plan

1. Add roadmap action policies and tests in isolated workflow runtime fixtures.
2. Add `roadmap_item` phase inference and run lookup tests.
3. Add `cancel-run` primitive and tests for pointer clearing and no-history behavior.
4. Add canonical-run promotion: extend `openspec_create` preflight to find linked roadmap item runs.
5. Update orchestrator and roadmap skill docs including promotion canonical-run semantics.
6. Extend governance-check read-only diagnostics and tests.
7. Clean up existing duplicate promotion runs.
8. Sync workflow templates and distributed skill copies.
9. Run `python3 -m pytest tests/test_workflow.py -v` and template drift checks.

Rollback: revert the policy registrations and documentation changes. Existing roadmap files remain valid because the change does not migrate roadmap item schema.
