## ADDED Requirements

### Requirement: Workflow Runtime Coordination
The `sdlc-orchestrator` skill SHALL use the SDLC workflow runtime for stateful SDLC runs, while remaining the policy, user interaction, and worker dispatch layer.

#### Scenario: Orchestrator starts workflow run
- **WHEN** a user request starts a new SDLC workflow subject
- **THEN** the orchestrator SHALL call `workflow.py start` with the selected workflow and primary subject before dispatching downstream workers

#### Scenario: Orchestrator resumes matching workflow run
- **WHEN** a user request explicitly resumes a workflow or references the same subject as an active run
- **THEN** the orchestrator SHALL call `workflow.py resume` and continue from the returned phase, block state, and next allowed actions

#### Scenario: Orchestrator checks readiness before worker dispatch
- **WHEN** the orchestrator is about to invoke a phase worker
- **THEN** it SHALL call `workflow.py readiness` and SHALL NOT invoke the worker when `phase_readiness.ready` is false

#### Scenario: Orchestrator records worker completion through runtime
- **WHEN** a worker skill completes a phase or hook action
- **THEN** the orchestrator SHALL call the relevant `workflow.py` command to record evidence, complete the phase or hook, and advance only through guarded workflow transitions

#### Scenario: Orchestrator handles blocked states
- **WHEN** `workflow.py` reports a blocked state
- **THEN** the orchestrator SHALL explain the block reason and use the runtime's next allowed actions to ask the user or route the appropriate resolver

#### Scenario: Orchestrator does not hand-edit workflow state
- **WHEN** workflow run state must change
- **THEN** the orchestrator SHALL use `workflow.py` rather than directly editing `.ai/workflows/runs/current.json`

## MODIFIED Requirements

### Requirement: SDLC Orchestrator Skill
The system SHALL provide an `sdlc-orchestrator` skill that acts as the SDLC entrypoint for workflow routing, workflow runtime coordination, and gate coordination without replacing downstream skills. Route decisions SHALL be action-binding: once the orchestrator selects a route, the immediate next action MUST follow that route unless the user explicitly opts out or selects a different route. For stateful SDLC flows, the orchestrator SHALL use the workflow runtime to start or resume runs, check phase readiness, dispatch allowed workers, and enforce required hooks before completion.

#### Scenario: Small change routes to Superpowers direct
- **WHEN** a user requests a low-risk local change such as a typo fix, small documentation update, single-file bugfix, or local prompt tweak
- **THEN** the orchestrator SHALL route the task to Superpowers direct execution without creating an OpenSpec change

#### Scenario: Medium change routes to spec-driven propose flow
- **WHEN** a user requests a medium formal change that benefits from OpenSpec artifacts but does not need step-by-step artifact review
- **THEN** the orchestrator SHALL route the task to `openspec-propose -> apply -> archive` using the `spec-driven` schema and SHALL track the flow through the SDLC workflow runtime when the task is part of an SDLC run

#### Scenario: Very complex change routes to incremental spec-driven flow
- **WHEN** a user requests a very complex formal change involving ambiguous scope, high-risk architecture, cross-module impact, or a need for iterative human review
- **THEN** the orchestrator SHALL route the task to `openspec-new-change -> openspec-continue-change -> apply -> archive` using the `spec-driven` schema and SHALL track the flow through the SDLC workflow runtime when the task is part of an SDLC run

#### Scenario: Roadmap signal routes to roadmap first
- **WHEN** a user request involves MVP/V2/V3/Later planning, roadmap capture, roadmap item promotion, or long-term prioritization
- **THEN** the orchestrator SHALL route the task through `sdlc-roadmap` before any OpenSpec change is created

#### Scenario: AI behavior target uses EvalOps gate
- **WHEN** a change creates or expands behavior for a skill, agent, prompt, workflow, RAG pipeline, or other AI behavior target
- **THEN** the orchestrator SHALL require the relevant EvalOps gate before implementation begins, unless an explicit EvalOps exception applies

#### Scenario: New AI skill development uses EvalOps target workspace
- **WHEN** a user asks to create a new AI skill or materially change AI skill behavior
- **THEN** the orchestrator SHALL identify or create the relevant EvalOps target id and require target-scoped EvalOps coverage under `.ai/evals/targets/<target-id>/` before implementation begins, unless the user explicitly confirms an exception

#### Scenario: Completed durable change prompts memory sync
- **WHEN** a completed change introduces durable architecture decisions, repository conventions, pitfalls, module behavior, or stable operational knowledge
- **THEN** the orchestrator SHALL prompt for or route to repository memory sync according to the active workflow

#### Scenario: Stateful workflow completion requires runtime completion
- **WHEN** a task is tracked by an active workflow run
- **THEN** the orchestrator SHALL NOT claim lifecycle completion until `workflow.py` reports the run can reach `done`

### Requirement: OpenSpec Step Review Summary
The `sdlc-orchestrator` skill SHALL reduce human review burden by summarizing OpenSpec artifact steps in chat and SHALL align the recommended next step with the active workflow runtime state when a run is active.

#### Scenario: Propose flow summary
- **WHEN** `openspec-propose` creates multiple OpenSpec artifacts in one step
- **THEN** the orchestrator SHALL summarize what was generated and identify the files and sections the user should focus on before implementation

#### Scenario: Incremental flow summary
- **WHEN** `openspec-continue-change` creates one OpenSpec artifact
- **THEN** the orchestrator SHALL summarize that artifact and identify its highest-value sections for user confirmation before continuing

#### Scenario: Apply summary
- **WHEN** OpenSpec apply work completes or pauses
- **THEN** the orchestrator SHALL summarize completed tasks, verification evidence, unresolved risks, and the next recommended workflow step

#### Scenario: Summary respects active workflow state
- **WHEN** an OpenSpec step completes inside an active workflow run
- **THEN** the orchestrator SHALL use `workflow.py` to determine whether the next workflow action is worker dispatch, input resolution, hook handling, or blocked-state handling
