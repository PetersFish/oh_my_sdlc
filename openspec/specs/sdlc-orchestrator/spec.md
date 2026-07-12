## ADDED Requirements

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

### Requirement: Workflow Runtime Coordination
The `sdlc-orchestrator` skill SHALL use the SDLC workflow runtime for stateful SDLC runs, while remaining the policy, user interaction, and worker dispatch layer.

### Requirement: Roadmap-Governed Hook Routing
The dev-orchestrator SHALL route roadmap-governed lifecycle hook work to a dedicated `roadmap-agent` lifecycle worker while remaining a routing, readiness, and evidence coordination layer. The `roadmap-agent` SHALL use the existing `sdlc-roadmap` skill for roadmap domain mutations.

#### Scenario: Ready hook routes to roadmap agent
- **WHEN** a workflow run has pending hook `roadmap_status_ready_if_linked`
- **THEN** the orchestrator SHALL dispatch `roadmap-agent` through lifecycle dispatch hooks and SHALL NOT use general task dispatch or edit roadmap item files directly

#### Scenario: Apply-start hook routes to roadmap agent
- **WHEN** a workflow run has pending hook `roadmap_apply_start_if_ready`
- **THEN** the orchestrator SHALL dispatch `roadmap-agent` through lifecycle dispatch hooks and SHALL NOT use general task dispatch or edit roadmap item files directly

#### Scenario: Done hook continues to route to roadmap agent
- **WHEN** a workflow run has pending hook `roadmap_done_if_relevant`
- **THEN** the orchestrator SHALL dispatch `roadmap-agent` through lifecycle dispatch hooks and SHALL rely on workflow runtime hook validation before claiming lifecycle completion

#### Scenario: Roadmap agent uses roadmap skill
- **WHEN** `roadmap-agent` performs a roadmap lifecycle transition
- **THEN** it SHALL load and follow the existing `sdlc-roadmap` skill rather than implementing a separate roadmap state machine

#### Scenario: General task dispatch is not used for governed roadmap hooks
- **WHEN** roadmap hook work affects workflow lifecycle state
- **THEN** the orchestrator SHALL NOT use the General Task dispatch path because that path skips `before-dispatch` and `after-dispatch`

#### Scenario: Orchestrator records evidence through runtime
- **WHEN** a roadmap worker reports that a linked item transition is complete
- **THEN** the orchestrator SHALL use `workflow.py resolve`, `workflow.py record-evidence`, or `workflow.py complete-hook` as appropriate to record observed state and SHALL NOT remove hooks by directly editing run JSON

#### Scenario: Orchestrator reports blocked roadmap mismatch
- **WHEN** `workflow.py complete-hook` blocks with `domain_state_mismatch` for a roadmap lifecycle hook
- **THEN** the orchestrator SHALL report the expected roadmap status, the observed roadmap status, and the next recommended `sdlc-roadmap` action

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

### Requirement: Route Decision Output
The `sdlc-orchestrator` skill SHALL produce a concise route decision before delegating to downstream workflows. The route decision SHALL make the next action match the selected route and SHALL NOT present direct execution as the default next action for `spec-driven-*` routes.

#### Scenario: Route decision includes required fields
- **WHEN** the orchestrator classifies a user request
- **THEN** it SHALL state the route, reason, required gates, expected artifacts, and next action

#### Scenario: Orchestrator delegates rather than duplicates
- **WHEN** a route requires debugging, TDD, review, verification, Roadmap, EvalOps, OpenSpec, or Memory behavior
- **THEN** the orchestrator SHALL invoke or recommend the responsible skill instead of duplicating that skill's detailed workflow

#### Scenario: Propose route binds next action
- **WHEN** the orchestrator selects `spec-driven-propose-flow`
- **THEN** the next action SHALL be to create OpenSpec proposal artifacts through `openspec-propose` unless the user explicitly says to skip OpenSpec or direct-execute

#### Scenario: Incremental route binds next action
- **WHEN** the orchestrator selects `spec-driven-incremental-flow`
- **THEN** the next action SHALL be to create an OpenSpec change through `openspec-new-change` unless the user explicitly says to skip OpenSpec or direct-execute

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

### Requirement: AI Skill Development EvalOps Gate
The `sdlc-orchestrator` skill SHALL gate new AI skill development and material AI behavior changes through EvalOps coverage, human-approved golden cases, implementation, and final golden eval reporting.

#### Scenario: EvalOps coverage precedes implementation
- **WHEN** a change creates a new AI skill or materially changes skill, agent, prompt, workflow, RAG pipeline, or other AI behavior
- **THEN** the orchestrator SHALL route to `sdlc-evalops` for coverage definition before implementation begins, unless the user explicitly confirms an EvalOps exception

#### Scenario: Human confirmation required before golden promotion
- **WHEN** candidate cases are drafted for an AI behavior target
- **THEN** the orchestrator SHALL require human confirmation before treating those cases as golden regression cases

#### Scenario: Human confirmation boundaries are explicit
- **WHEN** the orchestrator coordinates EvalOps gates
- **THEN** it SHALL distinguish assistant-generated drafts from user-approved decisions, especially for target registration, coverage acceptance, golden case promotion, and EvalOps exceptions

#### Scenario: Implementation starts after required pre-implementation gates
- **WHEN** an AI behavior change has required EvalOps coverage and any required OpenSpec artifacts
- **THEN** the orchestrator MAY route to implementation through the selected downstream workflow

#### Scenario: Final golden eval is required before completion claim
- **WHEN** an EvalOps-gated AI behavior implementation completes
- **THEN** the orchestrator SHALL require a final golden eval for the affected target or explicitly report the blocked runner dependency before claiming completion

#### Scenario: Final summary reports golden eval evidence
- **WHEN** final golden eval evidence is available
- **THEN** the orchestrator SHALL report target id, case counts, export freshness status, eval command, pass/fail result count, and report path

### Requirement: EvalOps Exception Handling
The `sdlc-orchestrator` skill SHALL make EvalOps exceptions explicit and human-confirmed.

#### Scenario: User explicitly confirms EvalOps exception
- **WHEN** the user explicitly says to skip or defer EvalOps for an AI behavior change
- **THEN** the orchestrator MAY proceed after acknowledging the exception and naming the residual risk

#### Scenario: Ambiguous user instruction does not skip EvalOps
- **WHEN** the user says "go ahead", "start", "implement", or equivalent after an EvalOps-gated route
- **THEN** the orchestrator SHALL continue the EvalOps-gated route rather than treating the instruction as permission to skip EvalOps

### Requirement: Plan Mode Handoff Compliance
The `sdlc-orchestrator` skill SHALL align Plan Mode handoff language with the selected route.

#### Scenario: Propose flow handoff names OpenSpec proposal
- **WHEN** the orchestrator is in Plan Mode and has selected `spec-driven-propose-flow`
- **THEN** the final handoff SHALL say that after leaving Plan Mode it can create an OpenSpec proposal/change, not that it can directly execute the implementation plan

#### Scenario: Incremental flow handoff names OpenSpec change creation
- **WHEN** the orchestrator is in Plan Mode and has selected `spec-driven-incremental-flow`
- **THEN** the final handoff SHALL say that after leaving Plan Mode it can create or continue the OpenSpec change, not that it can directly execute the implementation plan

### Requirement: Ambiguous Execution Requests Respect Prior Route
The `sdlc-orchestrator` skill SHALL treat ambiguous execution requests as instructions to continue the previously selected route, not as permission to bypass route governance.

#### Scenario: Execute plan after propose route continues OpenSpec
- **WHEN** the user says "execute plan", "go ahead", "start", or equivalent after the orchestrator selected `spec-driven-propose-flow`
- **THEN** the orchestrator SHALL continue by invoking `openspec-propose` or ask whether the user wants to explicitly skip OpenSpec

#### Scenario: Execute plan after incremental route continues OpenSpec
- **WHEN** the user says "execute plan", "go ahead", "start", or equivalent after the orchestrator selected `spec-driven-incremental-flow`
- **THEN** the orchestrator SHALL continue by invoking `openspec-new-change` or ask whether the user wants to explicitly skip OpenSpec

#### Scenario: Explicit opt-out allows direct execution
- **WHEN** the user explicitly says to skip OpenSpec, bypass governance, or directly execute despite a `spec-driven-*` route
- **THEN** the orchestrator MAY proceed outside the selected OpenSpec route after acknowledging the opt-out

### Requirement: Execution Path Choice Uses Question Tool
The `sdlc-orchestrator` skill SHALL use the `question` tool when available for mutually exclusive execution-path choices.

#### Scenario: Mutually exclusive paths use question tool
- **WHEN** the orchestrator must ask the user to choose between OpenSpec governance and direct execution
- **THEN** it SHALL use the `question` tool if available, with the recommended route listed first

#### Scenario: Tool unavailable falls back to text
- **WHEN** the `question` tool is unavailable
- **THEN** the orchestrator SHALL present the same mutually exclusive choices as concise text and ask the user to choose explicitly

### Requirement: EvalOps Lifecycle State Enforcement

The `sdlc-orchestrator` SHALL track EvalOps gate state across the change lifecycle and SHALL NOT permit forward progress past a gate until the required condition is met. For EvalOps-gated changes, the orchestrator SHALL NOT claim completion unless the full lifecycle loop has been satisfied.

The lifecycle states are:
1. No coverage → coverage reviewed (gate: user confirms coverage.yaml review)
2. Cases in inbox → cases accepted (gate: mandatory triage from sdlc-evalops)
3. Cases accepted → cases golden (gate: user confirms golden promotion)
4. Coverage + golden cases → implementation (gate: pre-implementation assets ready)
5. Implementation → pytest pass (gate: TDD verification)
6. Pytest pass → golden eval run (gate: run Promptfoo golden eval)
7. Golden eval pass → completion (gate: all evals green)
8. Golden eval fail → failure analysis (gate: user-confirmed fix plan before any repair)

#### Scenario: Implementation blocked before coverage is reviewed
- **WHEN** an EvalOps-gated change is classified and the target coverage is not reviewed
- **THEN** the orchestrator SHALL route to `sdlc-evalops` for coverage definition before routing to implementation
- **AND** the orchestrator SHALL NOT proceed to implementation unless the user explicitly confirms an EvalOps exception

#### Scenario: Implementation blocked before required golden cases exist
- **WHEN** an EvalOps-gated change has reviewed coverage but no golden cases for critical dimensions
- **THEN** the orchestrator SHALL report "no golden cases available for critical coverage dimensions"
- **AND** the orchestrator SHALL route back to `sdlc-evalops` for case generation and promotion

#### Scenario: Pytest pass before golden eval
- **WHEN** implementation completes for an EvalOps-gated change
- **THEN** the orchestrator SHALL require pytest to pass before running golden eval
- **AND** if pytest fails, the orchestrator SHALL route to `systematic-debugging` or `test-driven-development`

#### Scenario: Golden eval required before completion claim
- **WHEN** pytest passes for an EvalOps-gated change
- **THEN** the orchestrator SHALL require golden eval to run for the affected target
- **AND** the orchestrator SHALL explicitly report the golden eval status before claiming completion

#### Scenario: Golden eval failure blocks completion and triggers analysis
- **WHEN** golden eval returns failures
- **THEN** the orchestrator SHALL NOT claim completion
- **AND** the orchestrator SHALL route to `sdlc-evalops` for failure classification and a user-confirmed fix plan
- **AND** the orchestrator SHALL NOT permit direct fix or modification until the fix plan is confirmed

#### Scenario: User explicitly accepts residual eval risk
- **WHEN** golden eval returns failures and the user explicitly accepts the residual risk without fixing the failures
- **THEN** the orchestrator MAY proceed only as an EvalOps exception
- **AND** the orchestrator SHALL report the change as completed with known eval failures, not as golden-eval-pass

#### Scenario: Golden eval passes and completion is claimed
- **WHEN** golden eval returns all pass for an EvalOps-gated change
- **THEN** the orchestrator MAY claim completion with golden eval evidence in the final summary
- **AND** the summary SHALL include target id, case counts, export freshness status, eval command, pass/fail result count, and report path

#### Scenario: Completion cannot be claimed without golden eval
- **WHEN** implementation has completed but golden eval has not been run
- **THEN** the orchestrator SHALL report the blocked state explicitly: "Golden eval not yet run for target `<target-id>`"
- **AND** the orchestrator SHALL NOT claim the change is done

### Requirement: EvalOps Inbox-After-Capture Gate

When the current session creates or generates EvalOps cases for an inbox during an EvalOps-gated change, the orchestrator SHALL detect this state and require the user to complete triage before routing to implementation.

#### Scenario: Inbox cases require triage before implementation
- **WHEN** the orchestrator is about to route to implementation for an EvalOps-gated change
- **AND** there are unsorted inbox cases for the target
- **THEN** the orchestrator SHALL pause and ask whether to proceed to triage or continue without triaging the new cases

#### Scenario: User bypasses inbox triage explicitly
- **WHEN** the user explicitly says to skip triage for inbox cases and proceed to implementation
- **THEN** the orchestrator MAY proceed after acknowledging the exception and naming the residual risk of untriaged cases

### Requirement: Final Golden Eval Evidence in Completion Summary

When the orchestrator claims completion for an EvalOps-gated change, the final summary SHALL include structured golden eval evidence. The summary SHALL distinguish the pass state (all green) from failure (blocked) from unavailable (no golden cases yet).

#### Scenario: Pass state includes full evidence
- **WHEN** golden eval passes and completion is claimed
- **THEN** the summary SHALL report target id, total/passed/failed case counts, export freshness status, eval command used, pass/fail result count, and report path

#### Scenario: Blocked state reports what is missing
- **WHEN** golden eval cannot run (e.g., no golden cases exist, runner unavailable, API key not set)
- **THEN** the orchestrator SHALL report the specific blocked dependency
- **AND** the orchestrator SHALL NOT claim the eval passed

#### Scenario: Failure state provides diagnostic information
- **WHEN** golden eval fails
- **THEN** the summary SHALL report the failure count and reference the failure classification from `sdlc-evalops`
- **AND** the orchestrator SHALL NOT claim completion
