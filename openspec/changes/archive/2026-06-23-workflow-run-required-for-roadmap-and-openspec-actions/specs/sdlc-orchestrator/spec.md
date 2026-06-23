## ADDED Requirements

### Requirement: Roadmap-First Runtime Governance
The `sdlc-orchestrator` skill SHALL route stateful roadmap mutations through the SDLC workflow runtime before dispatching `sdlc-roadmap` worker actions.

#### Scenario: Roadmap mutation runs preflight before worker dispatch
- **WHEN** the user requests a stateful roadmap mutation such as capture, insert, review, revise, cancel, reorder, replan, or done
- **THEN** the orchestrator SHALL run workflow foundation verification and `workflow.py preflight` for the corresponding roadmap governed action before invoking the roadmap worker

#### Scenario: Roadmap preflight block prevents worker dispatch
- **WHEN** roadmap preflight returns `allowed: false`
- **THEN** the orchestrator SHALL follow or present the returned `next_action` and SHALL NOT invoke the roadmap worker until preflight returns `allowed: true`

#### Scenario: Roadmap worker completion is recorded in runtime
- **WHEN** a roadmap worker completes a governed mutation
- **THEN** the orchestrator SHALL record the worker evidence in the workflow runtime and complete or advance the relevant phase or hook through `workflow.py`

### Requirement: Roadmap Replan Follow-Up Coordination
The `sdlc-orchestrator` skill SHALL handle `roadmap_replan` as a governed batch mutation whose follow-up run handling uses single-subject runtime primitives in a loop.

#### Scenario: Replan evidence drives old run invalidation
- **WHEN** `sdlc-roadmap replan` returns cancelled old roadmap item IDs
- **THEN** the orchestrator SHALL call the runtime's single-subject run invalidation primitive for each cancelled item and report any per-item failure

#### Scenario: Replan evidence drives new run creation
- **WHEN** `sdlc-roadmap replan` returns created new roadmap item IDs
- **THEN** the orchestrator SHALL call the runtime's single-subject start path for each new item and report any per-item failure

#### Scenario: Replan does not use bulk workflow API
- **WHEN** the orchestrator processes roadmap replan evidence
- **THEN** it SHALL loop over single-subject runtime calls rather than relying on a bulk workflow command

### Requirement: Roadmap Promotion Reuses Canonical Run
The orchestrator SHALL treat the existing `roadmap_item` run as the canonical run during roadmap item promotion to an OpenSpec change, rather than starting a duplicate `openspec_change` run.

#### Scenario: Promotion writes change id into canonical run
- **WHEN** a roadmap item is promoted to an OpenSpec change and a `roadmap_item` run already exists
- **THEN** the orchestrator SHALL write `context.change_id` into the existing roadmap item run and advance it to `create_change`

#### Scenario: Promotion does not start a second run
- **WHEN** `openspec_create` preflight runs for a promoted change whose roadmap item run is active
- **THEN** the orchestrator SHALL NOT call `workflow.py start --subject-type openspec_change` and SHALL instead reuse the linked roadmap item run

#### Scenario: Direct openspec change still starts its own run
- **WHEN** the user creates an OpenSpec change directly without a linked roadmap item
- **THEN** the orchestrator MAY start a new `openspec_change/<change-id>` run as before
