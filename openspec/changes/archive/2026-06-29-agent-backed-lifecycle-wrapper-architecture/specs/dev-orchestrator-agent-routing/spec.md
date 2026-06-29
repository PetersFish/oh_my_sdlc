## ADDED Requirements

### Requirement: dev-orchestrator is a top-level agent that routes phase actions to specialized sub-agents
The system SHALL provide a `dev-orchestrator` top-level agent (on par with opencode `plan`/`build` agents, NOT a subagent of `sdlc-orchestrator`) that receives the current allowed phase action from `workflow.py`, selects the appropriate specialized agent, collects structured evidence, and returns normalized results to the workflow runtime. `dev-orchestrator` MAY dispatch `plan-agent`, `implement-agent`, `test-agent`, `review-agent`, or `finish-agent` as its own subagents.

#### Scenario: dev-orchestrator receives allowed action and selects agent
- **WHEN** `workflow.py` reports the current phase and allowed workers for an active run
- **THEN** `dev-orchestrator` SHALL select the matching specialized agent (`plan-agent`, `implement-agent`, `test-agent`, `review-agent`, or `finish-agent`) based on the phase-agent mapping

#### Scenario: dev-orchestrator collects structured evidence
- **WHEN** a specialized agent completes its work
- **THEN** `dev-orchestrator` SHALL collect structured evidence from the agent output and normalize it into the evidence keys required by the current phase's exit criteria

#### Scenario: dev-orchestrator consumes the shared evidence envelope
- **WHEN** a specialized agent returns from execution
- **THEN** `dev-orchestrator` SHALL consume the shared evidence envelope fields including `agent`, `status`, `phase`, `slice_id`, `flow_type`, `evidence`, `artifacts`, `blockers`, and `recommended_next_action`

#### Scenario: dev-orchestrator does not own state transitions
- **WHEN** agent work is complete and evidence is collected
- **THEN** `dev-orchestrator` SHALL NOT directly modify workflow state; it SHALL return normalized results and delegate state transitions to `workflow.py` commands (`record-evidence`, `complete-phase`, `advance`)

#### Scenario: dev-orchestrator reports blocker when agent fails
- **WHEN** a specialized agent fails to produce required evidence or reports an unrecoverable error
- **THEN** `dev-orchestrator` SHALL return a structured blocker with the failure reason, affected phase, and recommended remediation action

#### Scenario: verification failures route back to implement-agent by default
- **WHEN** `test-agent` reports verification failure without requirement or design ambiguity
- **THEN** `dev-orchestrator` SHALL route the blocker back to `implement-agent` for the next implementation iteration

#### Scenario: verification ambiguity routes back to plan-agent
- **WHEN** `test-agent` reports requirement ambiguity or design uncertainty
- **THEN** `dev-orchestrator` SHALL route the blocker to `plan-agent` instead of defaulting directly to another implementation iteration

#### Scenario: dev-orchestrator forwards handoff artifact paths
- **WHEN** a specialized agent emits `artifacts.handoff_path` or `artifacts.raw_log_paths[]`
- **THEN** `dev-orchestrator` SHALL make those artifact references available to the next agent that needs cross-agent context

#### Scenario: verification failure keeps the slice in the implement-test loop
- **WHEN** `test-agent` reports an executable verification failure
- **THEN** `dev-orchestrator` SHALL keep the same work package active, preserve the blocker evidence, and redispatch `implement-agent` rather than advancing the phase

#### Scenario: phase completion requires test-agent success
- **WHEN** `implement-agent` reports success but `test-agent` has not yet returned passing verification evidence
- **THEN** `dev-orchestrator` SHALL NOT request phase completion, advancement, or `review-agent` execution for that work package

#### Scenario: deterministic routing ignores handoff prose and raw logs
- **WHEN** `dev-orchestrator` decides whether to redispatch, review, complete a phase, or advance a run
- **THEN** it SHALL rely on structured evidence and blocker fields rather than parsing handoff Markdown prose or raw log content

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

### Requirement: dev-orchestrator applies dispatch lifecycle hooks
The system SHALL apply a thin lifecycle-control layer around agent dispatch with `before_dispatch` and `after_dispatch` hook points. These hooks SHALL control when agent work may start and how agent results become workflow evidence, but SHALL NOT directly mutate workflow run files.

#### Scenario: before_dispatch validates run state
- **WHEN** `dev-orchestrator` is about to dispatch a specialized agent
- **THEN** `before_dispatch` SHALL read the active workflow run state and validate that the current phase, requested action, and `flow_type` allow the selected agent to run

#### Scenario: before_dispatch records agent phase intent
- **WHEN** `before_dispatch` accepts a dispatch request
- **THEN** it SHALL request workflow evidence recording for dispatch intent, including `evidence.agent_phase`, through `workflow.py record-evidence` rather than writing run state directly

#### Scenario: before_dispatch fails closed on invalid state
- **WHEN** the current run state does not allow the requested agent action, or required dispatch inputs such as `flow_type` are missing
- **THEN** `before_dispatch` SHALL return a structured blocker with the phase, action, selected agent, failure reason, and recommended workflow runtime command

#### Scenario: after_dispatch consumes normalized results
- **WHEN** a specialized agent returns from execution
- **THEN** `after_dispatch` SHALL consume the normalized result returned by wrappers or agents, including `status`, `evidence`, `artifacts`, `blockers`, and recommended next action

#### Scenario: after_dispatch requests deterministic workflow transitions
- **WHEN** normalized evidence satisfies the current phase requirements
- **THEN** `after_dispatch` SHALL request state transitions only through workflow runtime commands such as `record-evidence`, `complete-phase`, `advance`, or `block`

#### Scenario: dispatch hooks do not own workflow state
- **WHEN** dispatch lifecycle hooks run
- **THEN** they SHALL NOT directly create, modify, delete, or archive files under `.ai/workflows/runs/`; `workflow.py` remains the sole owner of workflow state mutation
