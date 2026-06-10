## ADDED Requirements

### Requirement: SDLC Orchestrator Skill
The system SHALL provide an `sdlc-orchestrator` skill that acts as the SDLC entrypoint for workflow routing and gate coordination without replacing downstream skills.

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
The `sdlc-orchestrator` skill SHALL produce a concise route decision before delegating to downstream workflows.

#### Scenario: Route decision includes required fields
- **WHEN** the orchestrator classifies a user request
- **THEN** it SHALL state the route, reason, required gates, expected artifacts, and next action

#### Scenario: Orchestrator delegates rather than duplicates
- **WHEN** a route requires debugging, TDD, review, verification, Roadmap, EvalOps, OpenSpec, or Memory behavior
- **THEN** the orchestrator SHALL invoke or recommend the responsible skill instead of duplicating that skill's detailed workflow

### Requirement: OpenSpec Step Review Summary
The `sdlc-orchestrator` skill SHALL reduce human review burden by summarizing OpenSpec artifact steps in chat.

#### Scenario: Propose flow summary
- **WHEN** `openspec-propose` creates multiple OpenSpec artifacts in one step
- **THEN** the orchestrator SHALL summarize what was generated and identify the files and sections the user should focus on before implementation

#### Scenario: Incremental flow summary
- **WHEN** `openspec-continue-change` creates one OpenSpec artifact
- **THEN** the orchestrator SHALL summarize that artifact and identify its highest-value sections for user confirmation before continuing

#### Scenario: Apply summary
- **WHEN** OpenSpec apply work completes or pauses
- **THEN** the orchestrator SHALL summarize completed tasks, verification evidence, unresolved risks, and the next recommended workflow step
