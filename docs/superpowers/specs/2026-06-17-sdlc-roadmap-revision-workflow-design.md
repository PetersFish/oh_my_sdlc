# SDLC Roadmap Revision Workflow Design

## Context

RM-SDLC-002 adds V2 behavior to the `sdlc-roadmap` skill. The MVP already provides roadmap init, capture, list, OpenSpec change linkage, and done. V2 must solve the workflow gap between initial brainstorming output and a refined, implementation-ready roadmap: review, revise, insert, reorder, cancel, and replan with traceable history.

RM-SDLC-001 is complete, so this item can proceed without a dependency warning. The repository currently uses OpenSpec's `spec-driven` schema; workflow discipline remains in Superpowers skills and must not move into the OpenSpec schema.

## Goals

- Simplify roadmap status to `idea`, `ready`, `active`, `done`, and `cancelled`.
- Add `roadmap review` so human + LLM review can create OpenSpec artifacts and move items from `idea` to `ready` only when review passes.
- Add `roadmap revise`, `roadmap insert`, `roadmap reorder`, `roadmap cancel`, and `roadmap replan`.
- Add changelog entries for all roadmap mutations.
- Add snapshots for semantic content revisions and cancellations.
- Define roadmap-side `done` mutation and rely on `sdlc-orchestrator` post-archive routing to trigger it.

## Non-Goals

- Do not add patch terminology, patch records, or `/patch.apply`.
- Do not execute code changes from roadmap records; implementation still follows normal development, TDD, debugging, review, and verification workflows.
- Do not keep `planned`, `deferred`, or `superseded` as V2 workflow statuses.
- Do not add revision revert or draft states in this version.
- Do not replace OpenSpec proposal/design/tasks/spec behavior.

## Recommended Approach

Use a roadmap revision workflow boundary.

The skill document owns command semantics and user-facing orchestration. Scripts own deterministic consistency work: validation, sync checks, index rebuilds, and small file updates where the expected mutation is mechanical. The system should avoid becoming a patch tracker or task manager.

Alternatives considered:

- Patch tracking: rejected because the user wants to revise roadmap definitions, not manage small patch records.
- Script-heavy automation: more deterministic, but too much surface area for V2 and risks turning roadmap into an execution engine.
- Revision workflow: enough deterministic support for consistency while preserving the roadmap/OpenSpec/Superpowers boundary.

## Design

`roadmap review` reviews `idea` items. If review does not pass, no OpenSpec change is created and the item remains `idea`. If review passes, the workflow creates complete OpenSpec artifacts, sets `openspec_change`, and moves the item to `ready`. After an item becomes ready, the workflow checks for remaining unreviewed items and asks whether to continue review or start applying a ready change.

`ready` means OpenSpec artifacts are complete and implementation can start. `active` begins only when apply or implementation starts, at which point `started_at` is set.

`roadmap revise` updates item content after saving a snapshot and appending a changelog entry. `ready` items with core semantic revisions may return to `idea`; `active` revisions warn about OpenSpec sync risk.

`roadmap insert` creates new `idea` items. Without position arguments it appends; with `--before` or `--after` it inserts at a specific location.

`roadmap reorder` updates priority, order, or both without changing item status.

`roadmap cancel` marks items cancelled without deleting them. It saves a snapshot and changelog entry. Active cancellation requires choosing between keeping active or cancelling and removing the OpenSpec change.

`roadmap replan` archives `idea` and `ready` plans into a batch revision, preserves `done` and `cancelled`, explicitly handles `active`, and creates new `idea` items. OpenSpec archive success is handled by `sdlc-orchestrator` as a post-archive gate; it routes matching active roadmap items to `sdlc-roadmap done`.

`validate.py` should validate the minimal status model and revision/changelog structures. `sync.py` should compare active and archived OpenSpec changes with roadmap references, reporting mismatches without silently changing unrelated files.

## Testing

- Unit tests for minimal status validation and migration-sensitive behavior.
- Unit tests for review workflow, failed review no-op behavior, review-passed OpenSpec artifact creation, and `idea -> ready` transition.
- Unit tests for apply-start `ready -> active` transition.
- Unit tests for revise snapshot and changelog behavior.
- Unit tests for insert, reorder, cancel, and replan behavior.
- Unit tests or documentation checks for orchestrator post-archive gate expectations, plus roadmap-side `done` mutation.
- Regression tests that existing roadmap item validation and listing behavior still pass.

## Open Questions Resolved

- Automation boundary: roadmap revision workflow, not patch tracking.
- Patch terminology and execution: explicitly out of scope.
- Revision lifecycle: no revert or draft state in V2.
