## ADDED Requirements

### Requirement: Minimal Roadmap Status Model
The system SHALL use `idea`, `ready`, `active`, `done`, and `cancelled` as the roadmap item status model for the revision workflow.

#### Scenario: New item starts as idea
- **WHEN** a roadmap item is created through capture or insert
- **THEN** the item status is `idea`

#### Scenario: Removed statuses are not part of V2 workflow
- **WHEN** roadmap revision workflow behavior is documented or validated
- **THEN** `planned`, `deferred`, and `superseded` are not accepted as active workflow statuses

### Requirement: Roadmap Review Workflow
The system SHALL support review of roadmap ideas before they become ready OpenSpec-backed work.

#### Scenario: Review specified item
- **WHEN** the user requests review for a specific `idea` roadmap item
- **THEN** the system guides review of goal, scope, acceptance criteria, dependencies, priority, and order

#### Scenario: Review unspecified item
- **WHEN** the user requests roadmap review without specifying an item
- **THEN** the system lists unreviewed `idea` items and asks the user to choose one

#### Scenario: Review not passed creates no change
- **WHEN** roadmap review does not pass
- **THEN** the roadmap item remains `idea` and no OpenSpec change is created

#### Scenario: Review passed creates OpenSpec artifacts
- **WHEN** the user confirms that review passed
- **THEN** the system creates complete OpenSpec artifacts for the reviewed roadmap item

#### Scenario: Complete artifacts make item ready
- **WHEN** review has passed and the OpenSpec artifacts are complete
- **THEN** the roadmap item status changes from `idea` to `ready` and `openspec_change` is set

#### Scenario: Ready item prompts next step
- **WHEN** a roadmap item becomes `ready`
- **THEN** the system checks for remaining `idea` items and asks whether to continue review or start applying a ready change

#### Scenario: No remaining ideas prompts OpenSpec creation
- **WHEN** a roadmap item becomes `ready` and no other `idea` items remain
- **THEN** the system asks whether to start applying a ready change

### Requirement: Roadmap Revise Workflow
The system SHALL support traceable content corrections to existing roadmap items.

#### Scenario: Revise saves snapshot
- **WHEN** a roadmap item is revised for content changes
- **THEN** the system saves the previous full item content under the area's `revisions/snapshots/` directory before updating the item

#### Scenario: Revise writes changelog
- **WHEN** a roadmap item is revised
- **THEN** the system appends a changelog entry with time, item id, reason, change summary, snapshot path, and optional related OpenSpec change

#### Scenario: Ready revise may require re-review
- **WHEN** a `ready` roadmap item receives a core semantic revision
- **THEN** the system asks whether the item should remain `ready` or return to `idea` for review

#### Scenario: Active revise warns about OpenSpec sync
- **WHEN** an `active` roadmap item is revised
- **THEN** the system warns that the linked OpenSpec change may also need to be updated

### Requirement: Roadmap Insert Workflow
The system SHALL support adding roadmap items through a single insert workflow.

#### Scenario: Insert without position appends
- **WHEN** the user inserts a roadmap item without `--before` or `--after`
- **THEN** the system appends the new `idea` item to the end of the selected area

#### Scenario: Insert with position places item
- **WHEN** the user inserts a roadmap item with `--before` or `--after`
- **THEN** the system places the new `idea` item relative to the referenced item and updates ordering metadata

#### Scenario: Insert writes changelog
- **WHEN** a roadmap item is inserted
- **THEN** the system writes a changelog entry and does not create a snapshot

### Requirement: Roadmap Reorder Workflow
The system SHALL support implementation order changes through one reorder workflow that can update priority, order, or both.

#### Scenario: Reorder by position
- **WHEN** the user reorders an item with `--before` or `--after`
- **THEN** the system updates the item's order metadata without changing its status

#### Scenario: Reorder by priority
- **WHEN** the user reorders an item with `--priority`
- **THEN** the system updates the item's priority without changing its status

#### Scenario: Reorder writes changelog only
- **WHEN** a roadmap item is reordered
- **THEN** the system writes a changelog entry and does not create a snapshot

### Requirement: Roadmap Cancel Workflow
The system SHALL support cancellation without deleting roadmap item history.

#### Scenario: Cancel non-active item
- **WHEN** an `idea` or `ready` roadmap item is cancelled
- **THEN** the system saves a snapshot, marks the item `cancelled`, writes a changelog entry, and keeps the item file

#### Scenario: Cancel active item asks for OpenSpec decision
- **WHEN** an `active` roadmap item is cancelled
- **THEN** the system asks the user to choose `keep active` or `cancel and remove OpenSpec change`

#### Scenario: Cancel active item and remove change
- **WHEN** the user chooses `cancel and remove OpenSpec change`
- **THEN** the system records the change id and path in revision history, removes the linked OpenSpec change, marks the item `cancelled`, and writes a changelog entry

### Requirement: Roadmap Replan Workflow
The system SHALL support whole-area replanning by replacing unfinished roadmap plans while preserving completed and cancelled history.

#### Scenario: Replan preserves terminal history
- **WHEN** a roadmap area is replanned
- **THEN** the system preserves `done` and `cancelled` items

#### Scenario: Replan archives unfinished plan
- **WHEN** a roadmap area is replanned
- **THEN** the system archives `idea` and `ready` items into a batch revision and creates new roadmap items as `idea`

#### Scenario: Replan handles active items explicitly
- **WHEN** a roadmap area with `active` items is replanned
- **THEN** the system asks for each active item whether to keep it active or cancel it and remove its OpenSpec change

#### Scenario: Replan writes changelog
- **WHEN** a roadmap area is replanned
- **THEN** the system writes a changelog entry summarizing archived items, preserved items, active decisions, new items, and the batch revision path

### Requirement: Apply And Completion State Transitions
The system SHALL derive roadmap state transitions from workflow events rather than requiring users to directly edit status fields.

#### Scenario: Apply starts ready item
- **WHEN** apply or implementation starts for a `ready` roadmap item
- **THEN** the item status becomes `active` and `started_at` is set

#### Scenario: Block idea apply
- **WHEN** the user attempts to apply an `idea` roadmap item
- **THEN** the system prompts the user to complete review first

#### Scenario: Manual done
- **WHEN** the user marks an `active` roadmap item done after implementation and verification
- **THEN** the item status becomes `done` and `completed_at` is set

### Requirement: Orchestrator-Routed Completion
The system SHALL rely on the orchestrator post-archive gate to trigger roadmap completion after OpenSpec archive succeeds.

#### Scenario: Orchestrator routes archived change to roadmap done
- **WHEN** OpenSpec archive succeeds and `sdlc-orchestrator` finds exactly one roadmap item with matching `openspec_change` and status `active`
- **THEN** the orchestrator routes to `sdlc-roadmap done <item-id>`

#### Scenario: Roadmap done mutates active item
- **WHEN** `sdlc-roadmap done <item-id>` is invoked for an `active` roadmap item
- **THEN** the roadmap item status becomes `done`, completion metadata is updated, the index is rebuilt, and validation runs

#### Scenario: Archive has no roadmap match
- **WHEN** OpenSpec archive succeeds but the orchestrator finds no roadmap item referencing the change id
- **THEN** the orchestrator reports a sync mismatch and does not guess an item

#### Scenario: Archive matches non-active item
- **WHEN** OpenSpec archive succeeds and the orchestrator finds a matching roadmap item that is not `active`
- **THEN** the orchestrator reports a sync mismatch and does not route a roadmap status overwrite

### Requirement: Revision Changelog And Snapshot Policy
The system SHALL maintain a unified changelog and selective snapshots for roadmap mutations.

#### Scenario: Every mutation writes changelog
- **WHEN** insert, review, revise, reorder, cancel, replan, apply-start activation, or done changes roadmap state or content
- **THEN** the system appends an entry to the area's `revisions/changelog.md`

#### Scenario: Snapshot only for semantic overwrite or cancellation
- **WHEN** revise or cancel changes a roadmap item
- **THEN** the system saves a full snapshot before changing the item

#### Scenario: Replan uses batch revision
- **WHEN** replan replaces unfinished roadmap plans
- **THEN** the system records the old and new plan in a batch revision instead of creating one snapshot per item
