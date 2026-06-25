## ADDED Requirements

### Requirement: flow type is an explicit workflow state field
The system SHALL record `flow_type` as an explicit field in the workflow run state with possible values `spec-flow` and `lightweight-flow`.

#### Scenario: flow_type set at run creation
- **WHEN** a new workflow run is created for a lifecycle subject
- **THEN** the system SHALL set `flow_type` to either `spec-flow` or `lightweight-flow` based on the subject's governance requirements

#### Scenario: spec-flow requires formal OpenSpec lifecycle
- **WHEN** `flow_type` is `spec-flow`
- **THEN** the system SHALL route through formal OpenSpec phases: propose/new/continue, apply, archive, with full artifact requirements

#### Scenario: lightweight-flow supports development without formal OpenSpec
- **WHEN** `flow_type` is `lightweight-flow`
- **THEN** the system SHALL route through lightweight execution phases without requiring OpenSpec artifacts, while still enforcing planning, implementation, testing, review, and finish gates

#### Scenario: flow names describe governance weight not implementation backend
- **WHEN** documenting or discussing flow types
- **THEN** `spec-flow` SHALL mean a formal OpenSpec lifecycle is required, and `lightweight-flow` SHALL mean it is not; neither name SHALL imply a specific implementation backend (e.g., Superpowers)

#### Scenario: flow_type is not inferred by agents
- **WHEN** an agent needs to determine its routing behavior
- **THEN** it SHALL read `flow_type` from the workflow run state and SHALL NOT derive it from surrounding context

### Requirement: spec-flow routes through spec wrapper for all OpenSpec phases
The system SHALL route `spec-flow` changes through the spec wrapper for OpenSpec propose, new change, continue, apply, and archive phases.

#### Scenario: spec-flow plan phase uses OpenSpec propose
- **WHEN** a `spec-flow` run enters the plan phase with no existing change artifacts
- **THEN** `plan-agent` SHALL call the spec wrapper for `openspec-propose`

#### Scenario: spec-flow implement phase uses OpenSpec apply
- **WHEN** a `spec-flow` run enters the implement phase
- **THEN** `implement-agent` SHALL call the spec wrapper for `openspec-apply-change`

#### Scenario: spec-flow finish phase uses OpenSpec archive
- **WHEN** a `spec-flow` run enters the finish phase after verification passes
- **THEN** `finish-agent` SHALL call the spec wrapper for `openspec-archive-change`

### Requirement: lightweight-flow routes through lightweight execution wrappers
The system SHALL route `lightweight-flow` changes through lightweight execution wrappers while sharing test, review, and cleanup gates with `spec-flow`.

#### Scenario: lightweight-flow plan phase uses writing-plans
- **WHEN** a `lightweight-flow` run enters the plan phase
- **THEN** `plan-agent` SHALL use `writing-plans`

#### Scenario: lightweight-flow implement phase uses executing-plans and git-worktrees
- **WHEN** a `lightweight-flow` run enters the implement phase
- **THEN** `implement-agent` SHALL use `executing-plans` and `using-git-worktrees`

#### Scenario: lightweight-flow finish phase uses finishing-a-development-branch
- **WHEN** a `lightweight-flow` run enters the finish phase after verification passes
- **THEN** `finish-agent` SHALL use `finishing-a-development-branch`

#### Scenario: test and review gates apply to both flow types
- **WHEN** any flow type enters the test or review phase
- **THEN** `test-agent` and `review-agent` SHALL apply the same verification and review requirements regardless of flow type
