## ADDED Requirements

### Requirement: Roadmap Worker Boundary Under Workflow Governance
The `sdlc-roadmap` skill SHALL remain the owner of roadmap file mutations while leaving workflow lifecycle coordination to `sdlc-orchestrator` and `workflow.py`.

#### Scenario: Roadmap worker does not own workflow lifecycle
- **WHEN** a roadmap mutation is requested through the SDLC workflow
- **THEN** `sdlc-roadmap` SHALL perform only the roadmap domain mutation and SHALL NOT call `workflow.py start`, `workflow.py preflight`, `workflow.py advance`, or `workflow.py done`

#### Scenario: Roadmap mutation returns evidence
- **WHEN** `sdlc-roadmap` completes a governed mutation
- **THEN** it SHALL provide mutation evidence suitable for the orchestrator to record in workflow runtime state

### Requirement: Roadmap Replan Evidence
The `sdlc-roadmap` replan workflow SHALL emit structured evidence that enables the orchestrator to reconcile workflow runs for old and new roadmap items.

#### Scenario: Replan evidence includes cancelled and created items
- **WHEN** `sdlc-roadmap replan` replaces unfinished roadmap plans
- **THEN** its completion evidence SHALL include cancelled old roadmap item IDs, created new roadmap item IDs, and the batch revision path

#### Scenario: Replan preserves roadmap revision history
- **WHEN** `sdlc-roadmap replan` cancels old items and creates new items
- **THEN** the roadmap batch revision and changelog SHALL record the rationale and item changes so abandoned workflow runs do not need history records
