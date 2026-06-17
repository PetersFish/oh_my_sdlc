## Context

`sdlc-roadmap` currently provides the MVP lifecycle for long-term roadmap management: initialize, capture, list, connect roadmap items to OpenSpec changes, and mark done. The next version should not become a patch tracker or mini task manager. It should make roadmap files easier to refine and govern after brainstorming creates initial items.

The repository uses `.ai/roadmap/` as the canonical roadmap runtime path and OpenSpec's `spec-driven` schema for formal change artifacts. Roadmap remains a thin orchestration layer above OpenSpec and Superpowers.

## Goals / Non-Goals

**Goals:**

- Simplify roadmap state to the states needed for brainstorming, review, implementation, completion, and cancellation.
- Add a review workflow that creates OpenSpec artifacts and marks roadmap items `ready` only after review passes.
- Add revision workflows for content edits, ordering/priority changes, insertion, cancellation, and whole-area replanning.
- Add unified changelog behavior and snapshots only where old semantic content must be preserved.
- Define roadmap-side completion behavior and rely on `sdlc-orchestrator` to trigger it from the post-archive gate.

**Non-Goals:**

- No patch terminology, patch records, or `/patch.apply` behavior.
- No separate `planned`, `deferred`, or `superseded` statuses in V2.
- No automatic implementation or debugging from roadmap operations.
- No replacement for OpenSpec proposal/design/tasks/spec behavior.

## Decisions

### Decision 1: Use Minimal Roadmap Statuses

Roadmap items use `idea`, `ready`, `active`, `done`, and `cancelled`.

Rationale: the user workflow is brainstorming/capture, review/refine, create OpenSpec change, complete, or cancel. `planned`, `deferred`, and `superseded` add project-management complexity without serving the current workflow.

Alternatives considered:

- Keep the existing larger status set: rejected because `planned`, `deferred`, and `superseded` overlap with review/reorder/cancel operations.
- Collapse to only `idea`, `active`, and `done`: rejected because `ready` is a useful gate before OpenSpec creation and `cancelled` preserves explicit non-work history.

### Decision 2: Creates OpenSpec Artifacts And Marks Ready When Review Passed

`roadmap review` guides a human + LLM review of a roadmap item. If review does not pass, the item remains `idea` and no OpenSpec change is created. If review passes, the workflow creates complete OpenSpec artifacts and then marks the item `ready` with `openspec_change` set.

After an item becomes `ready`, the workflow checks whether more `idea` items remain. If they do, it asks whether to continue reviewing or start applying a ready change. If no unreviewed items remain, it asks whether to start applying a ready change.

Rationale: readiness should mean the item is already specified as a formal OpenSpec change and is ready for implementation, not merely reviewed in chat.

### Decision 3: Revise Means Content Correction With History

`roadmap revise RM-xxx` changes semantic item content such as Goal, Scope, Acceptance Criteria, Promotion Notes, or Design Reference. It writes a snapshot before modifying the file and appends a changelog entry.

Rationale: content revisions overwrite the source-of-truth roadmap item, so the previous version must remain traceable.

### Decision 4: Insert And Reorder Keep Commands Small

`roadmap insert` covers both append and positional insertion. With no position it appends to the end; with `--before` or `--after` it inserts at that location.

`roadmap reorder` covers both priority and order changes. It can update `priority`, positional order, or both.

Rationale: append is a special case of insert, and prioritization is part of deciding implementation order. Keeping one command for each concept avoids command sprawl while preserving separate `priority` and `order` fields.

### Decision 5: Cancel Preserves History Without Deleting Items

`roadmap cancel RM-xxx` marks the item `cancelled`, writes a changelog entry, and saves a snapshot before the state change. If the item is `active`, the user must choose between keeping it active or cancelling it and removing the linked OpenSpec change.

Rationale: cancelled roadmap items are historical planning decisions and should not disappear. Active items need explicit OpenSpec handling to avoid dangling changes.

### Decision 6: Replan Replaces Unfinished Plans In Bulk

`roadmap replan` archives the old unfinished plan and creates a new set of `idea` items. It preserves `done` and `cancelled` items. For each `active` item, the user chooses `keep active` or `cancel and remove OpenSpec change`.

Rationale: replan is not a single-item edit. It is an area-level replacement of unfinished planning while preserving completed and cancelled history.

### Decision 7: Changelog Is Universal, Snapshots Are Selective

Every roadmap mutation writes `revisions/changelog.md`. Snapshots are required for `revise` and `cancel`, optional as a batch revision for `replan`, and not required for `insert`, `review`, `reorder`, apply-start activation, or `done` unless content is also revised.

Rationale: changelog provides a single audit trail. Snapshots should be reserved for operations that overwrite semantic content or terminate an item to avoid unnecessary file growth.

### Decision 8: Orchestrator Owns Post-Archive Roadmap Sync Trigger

When an OpenSpec archive succeeds, `sdlc-orchestrator` owns the post-archive gate. It finds roadmap items whose `openspec_change` matches the archived change and routes to `sdlc-roadmap done <item-id>` when exactly one active item is linked.

`sdlc-roadmap` owns the mutation after it is invoked: `active -> done`, `completed_at`, completion notes, index rebuild, and validation.

Rationale: archive is an OpenSpec lifecycle event outside roadmap's control. The orchestrator is the stable cross-skill coordination point, while roadmap remains responsible for safe roadmap state updates.

### Decision 9: Apply Start Marks Roadmap Active

A roadmap item remains `ready` after OpenSpec artifacts are created. It becomes `active` only when apply or implementation starts.

Rationale: artifact creation is planning/specification work. `active` should represent execution work in progress.

## Risks / Trade-offs

- Removing statuses may break existing roadmap data -> Migration should map `planned` to `idea`, `deferred` to reordered `idea` or `ready`, and `superseded` to `cancelled` plus replacement notes.
- Review workflow may become too chatty -> Only ask for the next action after a roadmap becomes `ready`.
- Active cancellation can destroy useful OpenSpec discussion -> Before removing a change, record the change id/path and cancellation reason in the replan or cancel revision.
- Keeping `priority` and `order` separate may confuse users -> Expose one `reorder` command while documenting that priority and order are different fields.

## Migration Plan

- Update skill documentation and templates to remove patch terminology.
- Update validation to accept only the minimal status set once existing roadmap data is migrated.
- Add changelog and snapshot conventions under each area's `revisions/` directory.
- Update runtime-distributed `sdlc-roadmap` skill copies after canonical behavior is updated.
- Rebuild roadmap indexes after item status/title/scope changes.

## Open Questions

None. The approved model is a roadmap revision workflow, not a patch workflow.
