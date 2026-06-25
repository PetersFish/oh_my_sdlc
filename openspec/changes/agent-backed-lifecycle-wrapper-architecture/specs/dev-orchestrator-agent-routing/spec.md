## ADDED Requirements

### Requirement: dev-orchestrator is a top-level agent that routes phase actions to specialized sub-agents
The system SHALL provide a `dev-orchestrator` top-level agent (on par with opencode `plan`/`build` agents, NOT a subagent of `sdlc-orchestrator`) that receives the current allowed phase action from `workflow.py`, selects the appropriate specialized agent, collects structured evidence, and returns normalized results to the workflow runtime. `dev-orchestrator` MAY dispatch `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, or `finish-agent` as its own subagents.

#### Scenario: dev-orchestrator receives allowed action and selects agent
- **WHEN** `workflow.py` reports the current phase and allowed workers for an active run
- **THEN** `dev-orchestrator` SHALL select the matching specialized agent (`plan-agent`, `implement-agent`, `test-agent`, `review-agent`, or `finish-agent`) based on the phase-agent mapping

#### Scenario: dev-orchestrator collects structured evidence
- **WHEN** a specialized agent completes its work
- **THEN** `dev-orchestrator` SHALL collect structured evidence from the agent output and normalize it into the evidence keys required by the current phase's exit criteria

#### Scenario: dev-orchestrator does not own state transitions
- **WHEN** agent work is complete and evidence is collected
- **THEN** `dev-orchestrator` SHALL NOT directly modify workflow state; it SHALL return normalized results and delegate state transitions to `workflow.py` commands (`record-evidence`, `complete-phase`, `advance`)

#### Scenario: dev-orchestrator reports blocker when agent fails
- **WHEN** a specialized agent fails to produce required evidence or reports an unrecoverable error
- **THEN** `dev-orchestrator` SHALL return a structured blocker with the failure reason, affected phase, and recommended remediation action

### Requirement: dev-orchestrator manages safe parallel dispatch
The system SHALL own parallel dispatch at the `dev-orchestrator` level for independent work packages with disjoint files or modules.

#### Scenario: dev-orchestrator identifies parallelizable work packages
- **WHEN** the current phase involves multiple independent work items across disjoint files or modules
- **THEN** `dev-orchestrator` SHALL split the work into separate packages that do not share files or modules

#### Scenario: dev-orchestrator dispatches parallel implement-agent instances
- **WHEN** safe parallel work packages are identified
- **THEN** `dev-orchestrator` SHALL dispatch each package to an independent `implement-agent` instance and collect per-package evidence

#### Scenario: dev-orchestrator runs integration verification after parallel work
- **WHEN** all parallel `implement-agent` instances complete
- **THEN** `dev-orchestrator` SHALL trigger final integration verification through `test-agent` before reporting phase completion

#### Scenario: dev-orchestrator rejects non-disjoint parallel dispatch
- **WHEN** proposed parallel work packages share files or modules
- **THEN** `dev-orchestrator` SHALL NOT dispatch them in parallel and SHALL return a blocker explaining the conflict
