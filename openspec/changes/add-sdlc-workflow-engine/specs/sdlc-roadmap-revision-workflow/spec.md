## MODIFIED Requirements

### Requirement: Apply And Completion State Transitions
The system SHALL derive roadmap state transitions from workflow events rather than requiring users to directly edit status fields.

#### Scenario: Review-passed change creation makes item ready
- **WHEN** OpenSpec artifacts are complete for a linked roadmap item after review has passed
- **THEN** the orchestrator SHALL route the roadmap item through the appropriate roadmap mutation so its status becomes `ready`

#### Scenario: Apply starts ready item
- **WHEN** apply or implementation starts for a linked `ready` roadmap item
- **THEN** the orchestrator SHALL route the roadmap item through the appropriate roadmap mutation so its status becomes `active` and `started_at` is set

#### Scenario: Block idea apply
- **WHEN** the user attempts to apply an `idea` roadmap item
- **THEN** the system prompts the user to complete review first

#### Scenario: Manual done
- **WHEN** the user marks an `active` roadmap item done after implementation and verification
- **THEN** the item status becomes `done` and `completed_at` is set

### Requirement: Orchestrator-Routed Completion
The system SHALL rely on workflow-managed post-archive actions to trigger roadmap completion after OpenSpec archive succeeds. `sdlc-orchestrator` SHALL coordinate the post-archive hook through the workflow runtime, and `sdlc-roadmap` SHALL remain the owner of roadmap item mutation.

#### Scenario: Workflow registers roadmap post-archive hook
- **WHEN** OpenSpec archive succeeds for a workflow-tracked change
- **THEN** the workflow runtime SHALL register `roadmap_done_if_relevant` as a pending post-archive hook

#### Scenario: Orchestrator routes archived change to roadmap done
- **WHEN** `roadmap_done_if_relevant` finds exactly one roadmap item with matching `openspec_change` and status `active`
- **THEN** the orchestrator SHALL route to `sdlc-roadmap done <item-id>`

#### Scenario: Roadmap done mutates active item
- **WHEN** `sdlc-roadmap done <item-id>` is invoked for an `active` roadmap item
- **THEN** the roadmap item status becomes `done`, completion metadata is updated, the index is rebuilt, and validation runs

#### Scenario: Workflow verifies roadmap done before completing hook
- **WHEN** the orchestrator has invoked `sdlc-roadmap done <item-id>`
- **THEN** the workflow runtime SHALL verify the linked roadmap item has `status: done` and non-null `completed_at` before completing `roadmap_done_if_relevant`

#### Scenario: Archive has no roadmap match
- **WHEN** OpenSpec archive succeeds but no roadmap item references the change id
- **THEN** the workflow runtime SHALL complete `roadmap_done_if_relevant` with `no_linked_item` evidence and SHALL NOT guess an item

#### Scenario: Archive matches already done roadmap item
- **WHEN** OpenSpec archive succeeds and the matching roadmap item is already `done` with non-null `completed_at`
- **THEN** the workflow runtime SHALL complete `roadmap_done_if_relevant` idempotently

#### Scenario: Archive matches non-active item
- **WHEN** OpenSpec archive succeeds and the matching roadmap item is `idea`, `ready`, or `cancelled`
- **THEN** the workflow runtime SHALL block with `domain_state_mismatch` and SHALL NOT route a roadmap status overwrite

#### Scenario: Archive matches multiple roadmap items
- **WHEN** OpenSpec archive succeeds and multiple roadmap items reference the same change id
- **THEN** the workflow runtime SHALL block with `user_decision_required`, return candidates, and wait for the orchestrator to ask the user which allowed action to take

#### Scenario: Workflow cannot complete while roadmap hook pending
- **WHEN** `roadmap_done_if_relevant` remains pending
- **THEN** the workflow SHALL NOT transition to `done`
