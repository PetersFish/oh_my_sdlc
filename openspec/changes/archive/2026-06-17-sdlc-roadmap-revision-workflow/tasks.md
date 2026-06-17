## 1. Roadmap Model And Migration

- [x] 1.1 Update canonical `sdlc-roadmap` skill documentation to use statuses `idea`, `ready`, `active`, `done`, and `cancelled`
- [x] 1.2 Remove `planned`, `deferred`, `superseded`, and patch terminology from V2 workflow documentation
- [x] 1.3 Define migration guidance for existing `planned`, `deferred`, and `superseded` roadmap data
- [x] 1.4 Update roadmap item template fields and body guidance for the revised model

## 2. Review Workflow

- [x] 2.1 Document `roadmap review RM-xxx` for guided review of a specified `idea` item
- [x] 2.2 Document `roadmap review` for listing unreviewed `idea` items and prompting user selection
- [x] 2.3 Define review checklist covering goal, scope, acceptance criteria, dependencies, priority, and order
- [x] 2.4 Implement or document that failed review keeps the item `idea` and creates no OpenSpec change
- [x] 2.5 Implement or document review-passed creation of complete OpenSpec artifacts
- [x] 2.6 Implement or document `idea -> ready` only after review passes and OpenSpec artifacts are complete
- [x] 2.7 Add post-ready prompt logic to continue review or start applying a ready change

## 3. Revision Commands

- [x] 3.1 Document `roadmap revise RM-xxx` with snapshot-before-edit and changelog behavior
- [x] 3.2 Document `roadmap insert` with default append and optional `--before`/`--after` placement
- [x] 3.3 Document `roadmap reorder` with optional `--priority`, `--before`, and `--after` behavior
- [x] 3.4 Document `roadmap cancel RM-xxx` with snapshot, changelog, and active OpenSpec handling
- [x] 3.5 Document `roadmap replan` as archive unfinished plan plus create new `idea` items

## 4. Revision History Files

- [x] 4.1 Add or update templates for `revisions/changelog.md`
- [x] 4.2 Add or update templates for `revisions/snapshots/` item snapshots
- [x] 4.3 Add or update template guidance for batch replan revision files
- [x] 4.4 Define changelog fields for time, action, item ids, reason, change summary, snapshot/revision path, and related OpenSpec change

## 5. Scripts And Sync

- [x] 5.1 Update `validate.py` to enforce the minimal status model after roadmap data migration
- [x] 5.2 Update validation for changelog, snapshots, and batch replan revision structure where deterministic
- [x] 5.3 Preserve existing `list.py` and `rebuild_index.py` behavior under the new status model
- [x] 5.4 Add or update apply-start behavior that maps linked `ready -> active` and sets `started_at`
- [x] 5.5 Document that `sdlc-orchestrator` owns the post-archive gate and routes archive success to `sdlc-roadmap done`
- [x] 5.6 Implement or document `sdlc-roadmap done` as the roadmap-side `active -> done` mutation invoked by the orchestrator
- [x] 5.7 Keep `sync.py` report-oriented for lifecycle mismatch diagnostics, not as the primary archive trigger

## 6. Roadmap Data Updates

- [x] 6.1 Update RM-SDLC-002 title and scope to `Roadmap Revision Workflow`
- [x] 6.2 Remove patch-oriented acceptance criteria from RM-SDLC-002
- [x] 6.3 Rebuild `.ai/roadmap/index.json` after roadmap item updates
- [x] 6.4 Validate roadmap consistency after migration-sensitive changes

## 7. Tests And Verification

- [x] 7.1 Add tests for minimal status validation and migration-sensitive behavior
- [x] 7.2 Add tests for review workflow prompts, failed review no-op behavior, and review-passed OpenSpec artifact creation
- [x] 7.3 Add tests for revise snapshot and changelog behavior
- [x] 7.4 Add tests for insert default append and before/after placement behavior
- [x] 7.5 Add tests for reorder priority/order behavior without status changes
- [x] 7.6 Add tests for cancel snapshots and active OpenSpec handling
- [x] 7.7 Add tests for replan preservation, active decisions, and batch revision output
- [x] 7.8 Add tests for apply-start `ready -> active` transition
- [x] 7.9 Add tests for roadmap-side `done` mutation when invoked by orchestrator routing
- [x] 7.10 Add tests or documentation checks for orchestrator post-archive gate expectations and mismatch reporting
- [x] 7.11 Run existing `sdlc-roadmap` tests to confirm MVP behavior remains intact or is intentionally migrated
- [x] 7.12 Run OpenSpec status checks and roadmap validation
