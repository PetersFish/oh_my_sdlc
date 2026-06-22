---
id: RM-ORCH-005
title: "Workflow Run Required For Roadmap And OpenSpec Actions"
status: idea
stage: v2
priority: p0
order: 40
depends_on:
  - RM-ORCH-001
  - RM-ORCH-004
openspec_change: null
created_at: 2026-06-21
started_at: null
completed_at: null
---

# Goal

Every Roadmap and OpenSpec stateful mutation SHALL require a matching workflow run before execution. If no run exists, the system SHALL automatically create one and position it at the correct phase. The user SHALL NOT manually start runs before roadmap operations.

# Problem Context

Current design has a governance gap:

- OpenSpec lifecycle actions (`openspec_create`, `openspec_continue`, `openspec_apply`, `openspec_archive`) are registered as governed actions with preflight enforcement. However, due to RM-ORCH-004 (done `current.json` not yet cleared), a new run cannot start while a done run's `current.json` persists.
- Roadmap mutations (`roadmap_insert`, `roadmap_capture`, `roadmap_review`, `roadmap_revise`, `roadmap_cancel`, `roadmap_done`) have NO governed actions registered in `workflow.py`. The `sdlc-roadmap` skill performs direct file mutations without any runtime preflight or phase tracking.
- The `sdlc-main` workflow defines `create_roadmap` and `review_roadmap` phases, but the `roadmap-first` orchestrator route does not wire them into runtime start/preflight/complete-phase/advance before delegating to `sdlc-roadmap`.
- `governance-check` only detects dangling archived OpenSpec changes and pending hooks; it does not detect Roadmap mutations that lack workflow evidence.

As a result, roadmap items can be created, revised, reviewed, and cancelled entirely outside workflow governance. This breaks the "stateful SDLC" contract that the orchestrator promises.

# Scope

## In

- Register new governed actions in `workflow.py` for Roadmap lifecycle: `roadmap_capture`, `roadmap_insert`, `roadmap_review`, `roadmap_revise`, `roadmap_cancel`, `roadmap_done`.
- Update `sdlc-orchestrator` `roadmap-first` route: SHALL run `verify-foundations`, then `workflow.py preflight --action <roadmap-action>`, then start/resume/advance run as needed, then delegate to `sdlc-roadmap` as worker, then `record-evidence` + `complete-phase` + `advance`.
- Update `sdlc-roadmap` skill documentation: SHALL NOT own workflow lifecycle. Roadmap mutations are workers invoked by the orchestrator after runtime gates pass.
- Repair OpenSpec preflight: after RM-ORCH-004 clears done `current.json`, `openspec_create` preflight SHALL correctly start a new run for a fresh change instead of reporting `conflict_active_run`.
- Extend `governance-check` to detect Roadmap mutations without workflow evidence (at minimum: roadmap items with `status: active` that have no matching workflow run, and archived items with linked `openspec_change` that have no workflow run).
- Add policy for `roadmap_insert` and `roadmap_capture` with `creates_run=True` and appropriate `allowed_phases={create_roadmap}`.
- Add policy for `roadmap_review` with `allowed_phases={review_roadmap}`.
- Add deterministic phase inference for `roadmap_item` subject type.

## Out

- `sdlc-roadmap` SHALL NOT directly call `workflow.py start` or `workflow.py preflight`. It remains a worker.
- No modification to upstream OpenSpec worker skills.
- No change to `roadmap list` (read-only operation).
- No auto-healing of governance gaps from the plugin side.

# Design Notes

## Key Decisions

- Roadmap governed actions mirror the OpenSpec pattern: `roadmap_insert` is like `openspec_create`, requiring a run at `create_roadmap` phase before mutation.
- The orchestrator is the sole lifecycle coordinator. Roadmap skills are workers invoked only after runtime gates pass.
- `roadmap_capture` and `roadmap_insert` policies set `creates_run=True`, matching `dangling_archive_repair` semantics.
- `roadmap_review` maps to `review_roadmap` phase; `roadmap_done` maps to `post_archive_actions` (as a hook worker, not an independent action).
- Extend `_infer_phase` to handle `roadmap_item` subject type: if no change id, infer `create_roadmap`.
- `governance-check` detection scope expands from "dangling archive" to "ungoverned stateful mutation". Implementation: scan all areas for items with `status: active` and cross-check against active runs and history.

## Tradeoffs

- Adding governed actions increases `workflow.py` surface but makes the governance contract consistent across all stateful operations.
- Extending `governance-check` to detect ungoverned roadmap items adds scan complexity but closes the detection gap.
- Keeping `sdlc-roadmap` as a worker without lifecycle ownership preserves separation of concerns but requires consistent orchestrator adherence.

## Initial Approach

1. RM-ORCH-004 must complete first (done `current.json` cleared) so new runs can start without conflict.
2. Add Roadmap governed actions to `workflow.py` policy registry. Each action maps to the appropriate `sdlc-main` phase.
3. Wire `roadmap-first` route in orchestrator to call runtime before dispatching roadmap worker.
4. Update `sdlc-roadmap` skill doc with boundary rule: orchestrator owns lifecycle, roadmap only performs mutation.
5. Extend `governance-check` with roadmap item detection.
6. Add corresponding tests in `test_workflow.py`.
7. Sync templates and distributed copies.

## Open Questions

- Should `roadmap_done` always be invoked from `post_archive_actions` (as today's hook pattern), or should it also support direct invocation with its own phase? (Recommend: keep current hook pattern for done-after-archive, add separate governed action only for manual `roadmap done` without OpenSpec link.)
- How should `governance-check` handle roadmap items that were created before this governance rule was enforced? (Recommend: report as finding with explicit remediation, NOT auto-repair.)

# Acceptance Criteria

- `workflow.py preflight --action roadmap_insert --subject-type roadmap_item --subject-id RM-ORCH-XXX` returns valid decision (not `unknown_action`).
- Creating a roadmap item via orchestrator router results in a workflow run at `create_roadmap` phase.
- OpenSpec create preflight starts a new run after RM-ORCH-004 is implemented (no `conflict_active_run` from stale done current).
- `sdlc-roadmap skill` documentation states that roadmap does NOT own workflow lifecycle.
- `governance-check` detects active roadmap items without matching workflow runs.
- `python3 -m pytest tests/test_workflow.py -v` passes with new coverage.
- Template drift check passes.

# Promotion Notes

Promote after RM-ORCH-004 clears the done current conflict. The OpenSpec change should include policy registration, orchestrator route wiring, skill doc updates, governance-check extension, and test coverage.

# Completion Notes

Not started.

# Design Reference

- `.ai/workflows/definitions/sdlc-main.yaml` (`create_roadmap`, `review_roadmap` phases)
- `.ai/workflows/scripts/workflow.py` (policy registry, phase inference, governance-check)
- `skills/sdlc-orchestrator/SKILL.md` (roadmap-first route, runtime preflight requirement)
- `skills/sdlc-roadmap/SKILL.md` (roadmap insert/capture/review capabilities)
- `openspec/specs/sdlc-workflow-engine/spec.md` (run state schema, phase inference, governance)
