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

#### Scenario: New AI skill development uses EvalOps target workspace
- **WHEN** a user asks to create a new AI skill or materially change AI skill behavior
- **THEN** the orchestrator SHALL identify or create the relevant EvalOps target id and require target-scoped EvalOps coverage under `.ai/evals/targets/<target-id>/` before implementation begins, unless the user explicitly confirms an exception

#### Scenario: Completed durable change prompts memory sync
- **WHEN** a completed change introduces durable architecture decisions, repository conventions, pitfalls, module behavior, or stable operational knowledge
- **THEN** the orchestrator SHALL prompt for or route to repository memory sync according to the active workflow

### Requirement: Route Decision Output
The `sdlc-orchestrator` skill SHALL produce a concise route decision before delegating to downstream workflows. The route decision SHALL make the next action match the selected route and SHALL NOT present direct execution as the default next action for `spec-driven-*` routes.

#### Scenario: Route decision includes required fields
- **WHEN** the orchestrator classifies a user request
- **THEN** it SHALL state the route, reason, required gates, expected artifacts, and next action

#### Scenario: Route decision names EvalOps target for AI behavior changes
- **WHEN** a request creates or modifies an AI behavior target
- **THEN** the route decision SHALL name the target id when known or state that target identification is the next EvalOps step

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
