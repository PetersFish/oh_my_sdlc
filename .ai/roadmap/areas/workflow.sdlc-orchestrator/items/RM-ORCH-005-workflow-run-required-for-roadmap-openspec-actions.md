---
id: RM-ORCH-005
title: "Workflow Run Required For Roadmap And OpenSpec Actions"
status: done
stage: v2
priority: p0
order: 40
depends_on:
  - RM-ORCH-001
  - RM-ORCH-006
openspec_change: workflow-run-required-for-roadmap-and-openspec-actions
created_at: 2026-06-20
started_at: 2026-06-22
completed_at: 2026-06-23
---

# Goal

Every Roadmap and OpenSpec stateful mutation SHALL require a matching workflow run before execution. If no run exists, the system SHALL automatically create one and position it at the correct phase. The user SHALL NOT manually start runs before roadmap operations.

# Problem Context

Current design has a governance gap:

- OpenSpec lifecycle actions (`openspec_create`, `openspec_continue`, `openspec_apply`, `openspec_archive`) are registered as governed actions with preflight enforcement. RM-ORCH-006's multi-run pointer model is the prerequisite for reliably starting or resuming the correct run when multiple active runs exist.
- Roadmap mutations (`roadmap_insert`, `roadmap_capture`, `roadmap_review`, `roadmap_revise`, `roadmap_cancel`, `roadmap_reorder`, `roadmap_replan`, `roadmap_done`) have NO governed actions registered in `workflow.py`. The `sdlc-roadmap` skill performs direct file mutations without any runtime preflight or phase tracking.
- The `sdlc-main` workflow defines `create_roadmap` and `review_roadmap` phases, but the `roadmap-first` orchestrator route does not wire them into runtime start/preflight/complete-phase/advance before delegating to `sdlc-roadmap`.
- `governance-check` only detects dangling archived OpenSpec changes and pending hooks; it does not detect Roadmap mutations that lack workflow evidence.

As a result, roadmap items can be created, revised, reviewed, and cancelled entirely outside workflow governance. This breaks the "stateful SDLC" contract that the orchestrator promises.

Additionally, roadmap item promotion to an OpenSpec change creates a second, duplicate workflow run: the `roadmap_item` run exists but `openspec_create` preflight only finds `openspec_change` subjects. Because the runtime does not link the two subjects, promotion spawns a second `openspec_change` run instead of advancing the canonical `roadmap_item` run into the `create_change` phase.

# Scope

## In

- Register new governed actions in `workflow.py` for Roadmap lifecycle: `roadmap_capture`, `roadmap_insert`, `roadmap_review`, `roadmap_revise`, `roadmap_cancel`, `roadmap_reorder`, `roadmap_replan`, `roadmap_done`.
- Update `sdlc-orchestrator` `roadmap-first` route: SHALL run `verify-foundations`, then `workflow.py preflight --action <roadmap-action>`, then start/resume/advance run as needed, then delegate to `sdlc-roadmap` as worker, then `record-evidence` + `complete-phase` + `advance`.
- Update `sdlc-roadmap` skill documentation: SHALL NOT own workflow lifecycle. Roadmap mutations are workers invoked by the orchestrator after runtime gates pass.
- Repair OpenSpec preflight after RM-ORCH-006: `openspec_create` preflight SHALL correctly create or point to the matching active run instead of depending on a single full-state `current.json` slot.
- Enforce canonical-run promotion semantics: when a `roadmap_item` run exists and the linked `openspec_change` matches the preflight subject, `openspec_create` preflight SHALL accept the roadmap item run as the canonical run instead of requiring a new `openspec_change` run. The run's `context.change_id` is set during promotion, and the run advances to `create_change`.
- Extend `governance-check` to detect Roadmap mutations without workflow evidence (at minimum: roadmap items with `status: active` that have no matching workflow run, and archived items with linked `openspec_change` that have no workflow run).
- Add policy for `roadmap_insert` and `roadmap_capture` with `creates_run=True` and appropriate `allowed_phases={create_roadmap}`.
- Add policy for `roadmap_review` with `allowed_phases={review_roadmap}`.
- Add deterministic phase inference for `roadmap_item` subject type.
- Add a single-subject runtime primitive for replanned item run invalidation, e.g. `cancel-run --subject-type roadmap_item --subject-id <item-id> --reason replanned`. It SHALL remove the matching active run file and clear `current.json` if it points to that run, without writing history.
- Define `roadmap_replan` as a governed batch mutation: preflight gates the replan itself; after the roadmap worker returns evidence, the orchestrator SHALL loop over cancelled old item IDs and created new item IDs using single-subject runtime primitives.

## Out

- `sdlc-roadmap` SHALL NOT directly call `workflow.py start` or `workflow.py preflight`. It remains a worker.
- No modification to upstream OpenSpec worker skills.
- No change to `roadmap list` (read-only operation).
- No governance for `roadmap_init`; initialization remains a bootstrap/setup exception.
- No bulk workflow API for replan run cleanup or creation; orchestrator loops over single-subject runtime primitives.
- No auto-healing of governance gaps from the plugin side.

# Design Notes

## Key Decisions

- Roadmap governed actions mirror the OpenSpec pattern: `roadmap_insert` is like `openspec_create`, requiring a run at `create_roadmap` phase before mutation.
- The orchestrator is the sole lifecycle coordinator. Roadmap skills are workers invoked only after runtime gates pass.
- `roadmap_capture` and `roadmap_insert` policies set `creates_run=True`, matching `dangling_archive_repair` semantics.
- `roadmap_review` maps to `review_roadmap` phase; `roadmap_done` maps to `post_archive_actions` (as a hook worker, not an independent action).
- `roadmap_revise`, `roadmap_cancel`, and `roadmap_reorder` are governed mutations but do not advance the current workflow phase. They require a matching run for auditability, then leave `current_phase` unchanged.
- `roadmap_replan` is a governed batch mutation. It does not introduce a bulk workflow API; instead, the orchestrator consumes replan evidence and loops over single-subject runtime primitives.
- Replanned old item runs are invalidated through a runtime `cancel-run` primitive that deletes the active run and clears the pointer when needed. It does not write history because replanned runs are explicitly abandoned.
- Newly created roadmap items from replan each receive their own workflow run by calling the existing single-subject start path in a loop.
- Roadmap promotion to OpenSpec uses a single canonical run: the `roadmap_item/RM-XXX` run is the canonical subject. Promotion writes `context.change_id` into that run and the run advances to `create_change`. A second `openspec_change/<change-id>` run SHALL NOT be created when a linked roadmap item run already exists.
- `openspec_create` preflight SHALL scan active runs for one whose `context.change_id` or linked roadmap item matches the requested change id. If found, set pointer to that run, validate against `create_change` phase, and return `allowed: true` without requiring a new run.
- `roadmap_init` is intentionally outside governance because it bootstraps the roadmap substrate itself.
- Extend `_infer_phase` to handle `roadmap_item` subject type: if no change id, infer `create_roadmap`.
- `governance-check` detection scope expands from "dangling archive" to "ungoverned stateful mutation". Implementation: scan all areas for items with `status: active` and cross-check against active runs and history.

## Resolved Decisions

- `roadmap_done` remains a `post_archive_actions` hook worker for done-after-archive. Manual `roadmap done` without an OpenSpec link gets a separate governed action.
- Existing roadmap items created before this rule are reported by `governance-check` with explicit remediation. They are not auto-repaired.
- `roadmap_replan` evidence SHALL include cancelled old roadmap item IDs, created new roadmap item IDs, and the batch revision path.
- Existing duplicate runs (roadmap item run + openspec change run for the same promotion) are cleaned up: the `roadmap_item` run is preserved as canonical, the `openspec_change` run is cancelled, and its evidence is migrated.

## Tradeoffs

- Adding governed actions increases `workflow.py` surface but makes the governance contract consistent across all stateful operations.
- Extending `governance-check` to detect ungoverned roadmap items adds scan complexity but closes the detection gap.
- Keeping `sdlc-roadmap` as a worker without lifecycle ownership preserves separation of concerns but requires consistent orchestrator adherence.
- Reusing single-subject runtime primitives keeps batch replan behavior simple and debuggable, at the cost of orchestrator-side loops and partial-failure reporting.

## Initial Approach

1. RM-ORCH-006 must complete first so Roadmap/OpenSpec governed actions can target the correct active run through the `current.json` pointer model.
2. Add Roadmap governed actions to `workflow.py` policy registry. Each action maps to the appropriate `sdlc-main` phase.
3. Wire `roadmap-first` route in orchestrator to call runtime before dispatching roadmap worker.
4. Update `sdlc-roadmap` skill doc with boundary rule: orchestrator owns lifecycle, roadmap only performs mutation.
5. Add `cancel-run` or equivalent single-subject invalidation primitive for replanned roadmap items.
6. Extend `governance-check` with roadmap item detection.
7. Add corresponding tests in `test_workflow.py`.
8. Sync templates and distributed copies.

# Acceptance Criteria

- `workflow.py preflight --action roadmap_insert --subject-type roadmap_item --subject-id RM-ORCH-XXX` returns valid decision (not `unknown_action`).
- `workflow.py preflight --action roadmap_replan --subject-type roadmap_item --subject-id RM-ORCH-XXX` returns valid decision (not `unknown_action`).
- Creating a roadmap item via orchestrator router results in a workflow run at `create_roadmap` phase.
- OpenSpec create preflight starts or points to the correct run after RM-ORCH-006 is implemented (no dependency on a single full-state `current.json` slot).
- `sdlc-roadmap skill` documentation states that roadmap does NOT own workflow lifecycle.
- `roadmap_revise`, `roadmap_cancel`, and `roadmap_reorder` are governed without advancing `current_phase`.
- `roadmap_replan` returns evidence containing cancelled old item IDs, created new item IDs, and the batch revision path.
- Replan invalidates old item runs by looping over a single-subject runtime primitive that deletes the active run and clears `current.json` if needed, without writing history.
- Replan creates workflow runs for new roadmap items by looping over the existing single-subject start path.
- No bulk workflow API is introduced for roadmap replan.
- `roadmap_init` remains ungoverned as a bootstrap/setup exception.
- `openspec_create` preflight with a linked active `roadmap_item` run returns `allowed: true` (not `missing_active_run`) and does not create a second run.
- Promotion from roadmap item to OpenSpec change reuses the canonical `roadmap_item` run; no duplicate `openspec_change` run is created.
- `governance-check` detects active roadmap items without matching workflow runs.
- `python3 -m pytest tests/test_workflow.py -v` passes with new coverage.
- Template drift check passes.

# Promotion Notes

Promote after RM-ORCH-006 defines multi-run active state and the `current.json` pointer model. The OpenSpec change should include policy registration, orchestrator route wiring, skill doc updates, `roadmap_replan` evidence handling, the `cancel-run` runtime primitive, governance-check extension, and test coverage.

# Completion Notes

Implemented workflow runtime governance for all roadmap mutations (capture, insert, review, revise, cancel, reorder, replan, done). Added canonical-run promotion from roadmap items to OpenSpec changes, replan follow-up coordination with single-subject loop primitives, and extended governance-check for roadmap items. EvalOps coverage added with 4 golden regression cases and 24/24 golden eval pass. Documented orchestrator-roadmap boundary in both SKILL.md files. All phases completed: create_change → apply_change → archive_change → post_archive_actions → done.

**Accomplished:**
- 8 roadmap governed actions registered in workflow.py policy
- Roadmap-first runtime governance (verify-foundations → preflight → dispatch)
- Canonical-run promotion (roadmap_item run is canonical, no duplicate openspec_change run)
- Replan follow-up coordination (cancel-run loop + start loop)
- Governance-check extension (ungoverned roadmap items, duplicate promotion, archived linked items)
- 12 new tests (105 total, all passing)
- 4 golden EvalOps regression cases (24/24 golden eval pass)
- Skill documentation for orchestrator and roadmap boundary

**Deferred:**
- Promptfoo runner/output-level filtering for model thinking blocks (deferred by user decision)

**Follow-up items:**
- Consider pre-existing 4 golden eval failure fixes across other targets

# Design Reference

- `.ai/workflows/definitions/sdlc-main.yaml` (`create_roadmap`, `review_roadmap` phases)
- `.ai/workflows/scripts/workflow.py` (policy registry, phase inference, governance-check)
- `skills/sdlc-orchestrator/SKILL.md` (roadmap-first route, runtime preflight requirement)
- `skills/sdlc-roadmap/SKILL.md` (roadmap insert/capture/review capabilities)
- `openspec/specs/sdlc-workflow-engine/spec.md` (run state schema, phase inference, governance)
