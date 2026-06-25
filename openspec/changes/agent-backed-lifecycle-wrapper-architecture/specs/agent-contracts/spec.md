## ADDED Requirements

### Requirement: plan-agent behavior contract
The system SHALL provide a `plan-agent` with fixed responsibilities: design clarification, plan production, and TDD-aware task planning, without executing code.

#### Scenario: plan-agent uses brainstorming for design clarification
- **WHEN** `plan-agent` encounters design ambiguity or unclear requirements
- **THEN** it SHALL use `brainstorming` to clarify before producing a plan

#### Scenario: plan-agent routes spec-flow through spec wrapper
- **WHEN** the run's `flow_type` is `spec-flow`
- **THEN** `plan-agent` SHALL call the spec wrapper for OpenSpec propose, new change, or continue, depending on the existing change state

#### Scenario: plan-agent routes lightweight-flow through writing-plans
- **WHEN** the run's `flow_type` is `lightweight-flow`
- **THEN** `plan-agent` SHALL use `writing-plans`

#### Scenario: plan-agent produces TDD-aware plan
- **WHEN** producing a plan for any flow type
- **THEN** `plan-agent` SHALL output required failing tests, verification commands, and EvalOps candidates without writing or executing test code

#### Scenario: plan-agent does not execute tests or modify code
- **WHEN** `plan-agent` completes plan production
- **THEN** it SHALL NOT have written test files, modified source files, or executed any test runner

### Requirement: implement-agent behavior contract
The system SHALL provide an `implement-agent` with fixed responsibilities: implementation execution, TDD red/green loops, and worktree management.

#### Scenario: implement-agent routes spec-flow through spec wrapper
- **WHEN** the run's `flow_type` is `spec-flow`
- **THEN** `implement-agent` SHALL call the spec wrapper for OpenSpec apply

#### Scenario: implement-agent routes lightweight-flow through executing-plans
- **WHEN** the run's `flow_type` is `lightweight-flow`
- **THEN** `implement-agent` SHALL use `executing-plans` and `using-git-worktrees`

#### Scenario: implement-agent executes TDD red/green loop for behavior changes
- **WHEN** implementing behavior-changing code
- **THEN** `implement-agent` SHALL: write a failing test, verify the failure, implement the minimal change, and verify the test passes

#### Scenario: implement-agent handles a single bounded implementation slice
- **WHEN** dispatched by `dev-orchestrator`
- **THEN** `implement-agent` SHALL handle one bounded work package and return package-level evidence

### Requirement: test-agent behavior contract
The system SHALL provide a `test-agent` with fixed responsibilities: independent verification, systematic debugging, regression detection, and EvalOps capture.

#### Scenario: test-agent performs independent verification
- **WHEN** `implement-agent` completes implementation for a work package
- **THEN** `test-agent` SHALL run the full test suite and verify all tests pass independently of the implementation that produced them

#### Scenario: test-agent uses systematic debugging for failures
- **WHEN** verification reveals test failures or unexpected behavior
- **THEN** `test-agent` SHALL use `systematic-debugging` before proposing fixes

#### Scenario: test-agent captures EvalOps regression cases
- **WHEN** the change involves AI behavior targets (skills, agents, prompts, workflows, RAG pipelines)
- **THEN** `test-agent` SHALL capture durable regression cases under `.ai/evals/` through `sdlc-evalops`

#### Scenario: test-agent covers both flow types
- **WHEN** dispatched for any flow type (`spec-flow` or `lightweight-flow`)
- **THEN** `test-agent` SHALL perform the same verification, debugging, and EvalOps capture responsibilities

### Requirement: review-agent behavior contract
The system SHALL provide a `review-agent` with fixed responsibilities: code review and verification-before-completion evidence checks.

#### Scenario: review-agent requests code review
- **WHEN** implementation and testing are complete for a phase
- **THEN** `review-agent` SHALL use `requesting-code-review` to verify work meets requirements

#### Scenario: review-agent processes received review feedback
- **WHEN** review feedback is received
- **THEN** `review-agent` SHALL use `receiving-code-review` to process and apply feedback

#### Scenario: review-agent verifies completion evidence
- **WHEN** before claiming work is complete
- **THEN** `review-agent` SHALL use `verification-before-completion` and confirm verification output

### Requirement: finish-agent behavior contract
The system SHALL provide a `finish-agent` with fixed responsibilities: change finalization and workflow cleanup.

#### Scenario: finish-agent archives spec-flow changes
- **WHEN** the run's `flow_type` is `spec-flow` and all verification gates pass
- **THEN** `finish-agent` SHALL call the spec wrapper to archive the OpenSpec change

#### Scenario: finish-agent finishes lightweight-flow branches
- **WHEN** the run's `flow_type` is `lightweight-flow` and all verification gates pass
- **THEN** `finish-agent` SHALL use `finishing-a-development-branch`

#### Scenario: finish-agent runs workflow cleanup for all flows
- **WHEN** finalization is complete
- **THEN** `finish-agent` SHALL execute cleanup through roadmap, memory, and workflow hooks regardless of flow type

### Requirement: agents must not infer flow type from context
The system SHALL ensure flow type is read from the workflow run state rather than inferred by agents.

#### Scenario: agent reads flow_type from run state
- **WHEN** any agent needs to determine routing behavior
- **THEN** it SHALL read `flow_type` from the workflow run state and SHALL NOT derive it from context analysis, file inspection, or user intent heuristics

#### Scenario: agent rejects missing flow_type
- **WHEN** `flow_type` is not present in the workflow run state
- **THEN** the agent SHALL return a blocker indicating that `flow_type` is required and must be set before the agent can proceed
