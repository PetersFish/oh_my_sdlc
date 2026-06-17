## Why

The `sdlc-roadmap` MVP can capture, list, connect roadmap items to OpenSpec changes, and complete roadmap items, but it still treats roadmap content as mostly static after capture. RM-SDLC-002 adds a revision workflow so roadmap items can be reviewed, revised, reordered, inserted, cancelled, and replanned with clear state transitions and traceable history.

## What Changes

- Replace the previous patch concept with roadmap revision semantics.
- Simplify roadmap item statuses to `idea`, `ready`, `active`, `done`, and `cancelled`.
- Add `roadmap review` to guide human + LLM review; only when review passes should it create OpenSpec artifacts and mark the item `ready`.
- Add `roadmap revise` for content changes with snapshots and changelog entries.
- Add `roadmap insert` for new roadmap items, with optional before/after placement and default append behavior.
- Add `roadmap reorder` for both priority and order changes.
- Add `roadmap cancel` for cancelling items while preserving history.
- Define `roadmap replan` as archive old unfinished plan plus create new `idea` items, preserving `done` and `cancelled` items and explicitly handling `active` items.
- Add apply-start state handling so a `ready` item becomes `active` only when implementation begins.
- Define roadmap-side `done` mutation and rely on the `sdlc-orchestrator` post-archive gate to route archived OpenSpec changes to `roadmap done`.
- Keep patch records, patch execution, deferred status, and superseded status out of scope.

## Capabilities

### New Capabilities

- `sdlc-roadmap-revision-workflow`: Roadmap V2 behavior for minimal status transitions, review-passed OpenSpec artifact creation, revise, insert, reorder, cancel, replan, changelog/snapshot history, apply-start activation, and orchestrator-routed completion.

### Modified Capabilities

- None.

## Impact

- Affected skill: `skills/sdlc-roadmap/SKILL.md` and runtime-distributed copies.
- Affected templates: `skills/sdlc-roadmap/templates/` for revisions, changelog, and snapshots.
- Affected scripts: `skills/sdlc-roadmap/scripts/validate.py`, `rebuild_index.py`, `list.py`, and report-oriented sync diagnostics.
- Affected roadmap data: `.ai/roadmap/areas/*/items/` and `.ai/roadmap/areas/*/revisions/`.
- Affected tests: roadmap status model, review workflow, revision history, replan, and post-archive sync tests.
