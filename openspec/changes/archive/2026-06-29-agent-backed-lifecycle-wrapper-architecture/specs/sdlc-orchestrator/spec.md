## MODIFIED Requirements

### Requirement: sdlc-orchestrator is downgraded to manual trigger only
The `sdlc-orchestrator` skill SHALL be restricted to explicit manual invocation. It SHALL NOT auto-trigger on generic phrases such as "new development task", "any new development task", "how should I do this", or equivalent. The skill remains available as a legacy reference for policy documentation, route decision templates, and user-interaction patterns.

#### Scenario: sdlc-orchestrator triggers only on explicit invocation
- **WHEN** the user says "use sdlc-orchestrator" or "run the SDLC orchestrator"
- **THEN** the skill MAY trigger
- **WHEN** the user says "start workflow", "how should I approach this", or describes a new development task
- **THEN** the skill SHALL NOT auto-trigger; routing SHALL go through `dev-orchestrator` instead

#### Scenario: dev-orchestrator is the default SDLC routing entry point
- **WHEN** a new development task arrives and SDLC routing is needed
- **THEN** `dev-orchestrator` SHALL be the default agent for route classification and execution dispatch; `sdlc-orchestrator` SHALL NOT be triggered

#### Scenario: sdlc-orchestrator retains legacy documentation
- **WHEN** a user explicitly invokes `sdlc-orchestrator`
- **THEN** it SHALL produce route decisions, policy guidance, and review summaries following its documented patterns, but it SHALL NOT directly dispatch implementation work; for execution, it SHALL recommend routing through `dev-orchestrator`
