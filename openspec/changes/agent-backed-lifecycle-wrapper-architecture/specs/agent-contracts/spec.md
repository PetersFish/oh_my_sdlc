## ADDED Requirements

### Requirement: agents emit a structured evidence envelope
The system SHALL require every specialized agent (`plan-agent`, `implement-agent`, `test-agent`, `review-agent`, `finish-agent`) to return a structured evidence envelope that `dev-orchestrator` can consume deterministically.

#### Scenario: evidence envelope contains stable top-level fields
- **WHEN** any specialized agent completes work
- **THEN** it SHALL return top-level fields including `agent`, `status`, `phase`, `slice_id`, `flow_type`, `evidence`, `artifacts`, `blockers`, and `recommended_next_action`

#### Scenario: focused test evidence supports multiple commands
- **WHEN** an agent reports focused test execution
- **THEN** it SHALL emit `evidence.focused_tests` as an array of entries rather than a single scalar command or result

#### Scenario: workflow gates ignore handoff prose
- **WHEN** `dev-orchestrator` or `workflow.py` evaluates whether a phase may proceed
- **THEN** it SHALL rely on the structured evidence envelope and SHALL NOT depend on parsing handoff Markdown prose or raw log text

### Requirement: cross-agent handoff artifacts use a fixed Markdown structure
The system SHALL use a fixed Markdown structure for handoff artifacts whenever one specialized agent needs to leave readable execution context for another.

#### Scenario: handoff artifact contains required sections
- **WHEN** an agent writes a handoff artifact
- **THEN** the artifact SHALL contain `Metadata`, `Objective`, `Work Completed`, `Files / Artifacts Changed`, `Commands Run`, `Evidence Summary`, `Blockers`, `Assumptions`, `Risks / Follow-Ups`, and `Raw Logs`

#### Scenario: handoff metadata identifies the workflow context
- **WHEN** an agent writes a handoff artifact
- **THEN** the `Metadata` section SHALL include at least `Run ID`, `Slice ID`, `Agent`, `Phase`, `Flow Type`, `Status`, and `Recommended Next Agent`

#### Scenario: large logs are referenced rather than inlined
- **WHEN** an agent needs to preserve long command output or failure output for later debugging
- **THEN** it SHALL reference raw log paths from the handoff artifact rather than pasting large logs inline

### Requirement: raw logs are optional debugging artifacts
The system SHALL treat raw logs as optional debugging artifacts rather than required gate inputs.

#### Scenario: raw logs are written when debugging value exists
- **WHEN** an agent encounters a failure, blocker, long command output, or explicit verification/debug session
- **THEN** it SHOULD retain raw logs under `.ai/workflows/runs/<run_id>/logs/<slice_id>/<agent>/...`

#### Scenario: raw log references are attached to agent artifacts
- **WHEN** raw logs are retained
- **THEN** the structured evidence envelope SHALL expose them through `artifacts.raw_log_paths[]`, with metadata such as path, kind, command, and result

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
- **THEN** `implement-agent` SHALL write a failing test, verify the failure, implement the minimal change, and run focused tests to green

#### Scenario: implement-agent handles a single bounded implementation slice
- **WHEN** dispatched by `dev-orchestrator`
- **THEN** `implement-agent` SHALL handle one bounded work package and return package-level evidence

#### Scenario: implement-agent returns focused verification evidence
- **WHEN** `implement-agent` completes a behavior-changing implementation slice
- **THEN** it SHALL return the exact focused test command(s), the focused test result it claims passed, the new or changed test artifacts involved in the TDD loop, the implementation slice identifier needed for independent verification, and any handoff artifact path required by the next agent

### Requirement: test-agent behavior contract
The system SHALL provide a `test-agent` with fixed responsibilities: independent verification, systematic debugging, overfit detection for new or changed TDD tests, broader regression/integration verification, and EvalOps capture.

#### Scenario: test-agent performs independent verification
- **WHEN** `implement-agent` completes implementation for a work package
- **THEN** `test-agent` SHALL rerun the focused tests claimed by `implement-agent`, independently of the implementation step that produced them

#### Scenario: test-agent verifies implement-agent evidence in sequence
- **WHEN** `test-agent` verifies a completed implementation slice
- **THEN** it SHALL rerun the focused tests claimed by `implement-agent` before performing overfit checks or broader regression/integration verification

#### Scenario: test-agent checks new or changed TDD tests for overfit
- **WHEN** `implement-agent` adds or modifies tests as part of a TDD loop
- **THEN** `test-agent` SHALL assess whether those tests are overly coupled to implementation details rather than executable behavior

#### Scenario: test-agent runs broader regression and integration verification
- **WHEN** focused verification passes
- **THEN** `test-agent` SHALL run broader regression or integration verification appropriate to the change scope

#### Scenario: test-agent emits passing verification evidence
- **WHEN** independent verification passes
- **THEN** `test-agent` SHALL emit normalized verification evidence that includes the focused rerun result, the broader regression or integration result, the overfit-check outcome, the recommended next action to proceed to `review-agent`, and any relevant handoff or raw log artifact references

#### Scenario: test-agent uses systematic debugging for failures
- **WHEN** verification reveals test failures or unexpected behavior
- **THEN** `test-agent` SHALL use `systematic-debugging` before emitting a structured blocker with diagnostic evidence and recommended remediation

#### Scenario: test-agent returns executable failures to implement-agent by default
- **WHEN** verification reveals test failures or unexpected behavior without requirement or design ambiguity
- **THEN** `test-agent` SHALL emit a structured blocker back to `implement-agent` for the next implementation iteration, including the failing command or check, observed diagnostic evidence, the affected implementation slice identifier, the recommended next action, and raw log references when needed for reproduction

#### Scenario: test-agent escalates ambiguity to plan-agent
- **WHEN** verification reveals requirement ambiguity or design uncertainty
- **THEN** `test-agent` SHALL escalate to `plan-agent` instead of defaulting directly to another implementation iteration

#### Scenario: test-agent does not modify implementation code by default
- **WHEN** `test-agent` is dispatched for verification
- **THEN** it SHALL NOT directly modify implementation code unless a separate explicit workflow decision authorizes that behavior

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

#### Scenario: review-agent waits for independent verification evidence
- **WHEN** `implement-agent` has reported success but `test-agent` has not yet emitted passing verification evidence
- **THEN** `review-agent` SHALL NOT begin review for that phase

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

#### Scenario: finish-agent requires review and verification evidence
- **WHEN** `finish-agent` evaluates whether finalization may begin
- **THEN** it SHALL require both passing `test-agent` verification evidence and review completion evidence before proceeding

### Requirement: agents must not infer flow type from context
The system SHALL ensure flow type is read from the workflow run state rather than inferred by agents.

#### Scenario: agent reads flow_type from run state
- **WHEN** any agent needs to determine routing behavior
- **THEN** it SHALL read `flow_type` from the workflow run state and SHALL NOT derive it from context analysis, file inspection, or user intent heuristics

#### Scenario: agent rejects missing flow_type
- **WHEN** `flow_type` is not present in the workflow run state
- **THEN** the agent SHALL return a blocker indicating that `flow_type` is required and must be set before the agent can proceed
