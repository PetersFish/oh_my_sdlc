## MODIFIED Requirements

### Requirement: SDLC Orchestrator Skill
The system SHALL provide an `sdlc-orchestrator` skill that acts as the SDLC entrypoint for workflow routing and gate coordination without replacing downstream skills. Route decisions SHALL be action-binding: once the orchestrator selects a route, the immediate next action MUST follow that route unless the user explicitly opts out or selects a different route.

#### Scenario: Small change routes to Superpowers direct
- **WHEN** a user requests a low-risk local change such as a typo fix, small documentation update, single-file bugfix, or local prompt tweak
- **THEN** the orchestrator SHALL route the task to Superpowers direct execution without creating an OpenSpec change

#### Scenario: Medium change routes to spec-driven propose flow
- **WHEN** a user requests a medium formal change that benefits from OpenSpec artifacts but does not need step-by-step artifact review
- **THEN** the orchestrator SHALL route the task to `openspec-propose -> apply -> archive` using the `spec-driven` schema

#### Scenario: Very complex change routes to incremental spec-driven flow
- **WHEN** a user requests a very complex formal change involving ambiguous scope, high-risk architecture, cross-module impact, or a need for iterative human review
- **THEN** the orchestrator SHALL route the task to `openspec-new-change -> openspec-continue-change -> apply -> archive` using the `spec-driven` schema

#### Scenario: Roadmap signal routes to roadmap first
- **WHEN** a user request involves MVP/V2/V3/Later planning, roadmap capture, roadmap item promotion, or long-term prioritization
- **THEN** the orchestrator SHALL route the task through `sdlc-roadmap` before any OpenSpec change is created

#### Scenario: AI behavior target uses EvalOps gate
- **WHEN** a change creates or expands behavior for a skill, agent, prompt, workflow, RAG pipeline, or other AI behavior target
- **THEN** the orchestrator SHALL require the relevant EvalOps gate before implementation begins, unless an explicit EvalOps exception applies

#### Scenario: Completed durable change prompts memory sync
- **WHEN** a completed change introduces durable architecture decisions, repository conventions, pitfalls, module behavior, or stable operational knowledge
- **THEN** the orchestrator SHALL prompt for or route to repository memory sync according to the active workflow

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

## ADDED Requirements

### Requirement: Plan Mode Handoff Compliance
The `sdlc-orchestrator` skill SHALL align Plan Mode handoff language with the selected route.

#### Scenario: Propose flow handoff names OpenSpec proposal
- **WHEN** the orchestrator is in Plan Mode and has selected `spec-driven-propose-flow`
- **THEN** the final handoff SHALL say that after leaving Plan Mode it can create an OpenSpec proposal/change, not that it can directly execute the implementation plan

#### Scenario: Incremental flow handoff names OpenSpec change creation
- **WHEN** the orchestrator is in Plan Mode and has selected `spec-driven-incremental-flow`
- **THEN** the final handoff SHALL say that after leaving Plan Mode it can create or continue the OpenSpec change, not that it can directly execute the implementation plan

#### Scenario: Direct flow handoff may name direct execution
- **WHEN** the orchestrator is in Plan Mode and has selected `superpowers-direct`
- **THEN** the final handoff MAY say that after leaving Plan Mode it can directly execute the task

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
