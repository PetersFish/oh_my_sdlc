## ADDED Requirements

### Requirement: wrapper contracts define stable module-level interfaces
The system SHALL define wrapper contracts for each lifecycle module (spec, memory, roadmap, eval, planning, implementation, testing, review, finish, verification) that specify inputs, outputs, evidence keys, exit criteria, failure modes, and remediation guidance.

#### Scenario: wrapper contract specifies required inputs
- **WHEN** an agent invokes a wrapper
- **THEN** the wrapper contract SHALL specify what inputs are required, including `workflow_run_id`, `phase`, `action`, `flow_type`, and any module-specific artifact paths or constraints

#### Scenario: wrapper contract specifies output evidence
- **WHEN** an agent completes work through a wrapper
- **THEN** the wrapper contract SHALL specify what structured evidence fields must be returned, including `status`, `evidence`, `artifacts`, and `blockers`

#### Scenario: wrapper contract specifies evidence envelope shape
- **WHEN** a wrapper defines its normalized result
- **THEN** it SHALL define how the result maps into the shared agent evidence envelope, including `agent`, `status`, `phase`, `slice_id`, `flow_type`, normalized `evidence`, `artifacts`, `blockers`, and `recommended_next_action`

#### Scenario: wrapper contract specifies failure modes
- **WHEN** a wrapper encounters an error or cannot complete its work
- **THEN** the wrapper contract SHALL specify the failure mode, recommended remediation action, and whether the failure blocks phase completion

### Requirement: wrapper normalizes agent output into workflow evidence
The system SHALL normalize agent and tool output into standardized workflow evidence at the wrapper boundary.

#### Scenario: wrapper translates tool-specific output to evidence keys
- **WHEN** a concrete worker (OpenSpec, Superpowers, EvalOps, etc.) produces tool-specific output
- **THEN** the wrapper SHALL translate that output into the standardized evidence keys required by the current phase's exit criteria

#### Scenario: wrapper retains raw evidence logs
- **WHEN** normalizing output to standardized evidence
- **THEN** the wrapper SHALL retain the original raw output in a log for post-hoc debugging

#### Scenario: raw logs are exposed by reference
- **WHEN** a wrapper preserves raw output logs
- **THEN** it SHALL expose them through `artifacts.raw_log_paths[]` entries rather than embedding large log bodies directly in structured evidence or handoff prose

#### Scenario: downstream gates do not depend on tool-specific formats
- **WHEN** `workflow.py` validates phase exit criteria
- **THEN** it SHALL only depend on the standardized evidence keys defined in the wrapper contract, not on any tool-specific output format

#### Scenario: wrapper output is consumable by after_dispatch
- **WHEN** a wrapper returns control to `dev-orchestrator`
- **THEN** the wrapper SHALL return a normalized result that `after_dispatch` can consume without tool-specific parsing, including `status`, standardized `evidence`, `artifacts`, `blockers`, and recommended next action

#### Scenario: handoff artifacts remain separate from gate inputs
- **WHEN** a wrapper or agent also produces a handoff Markdown artifact for later subagents
- **THEN** the wrapper SHALL surface its path in `artifacts.handoff_path` while keeping workflow gate inputs in the structured evidence envelope only

#### Scenario: wrapper distinguishes standardized evidence from raw logs
- **WHEN** a wrapper preserves raw agent or tool output
- **THEN** the wrapper SHALL keep raw logs separate from standardized evidence so workflow gates can validate stable evidence keys while debugging can still inspect raw output

#### Scenario: wrapper does not require raw logs for deterministic gates
- **WHEN** `workflow.py` or `dev-orchestrator` evaluates phase completion or routing decisions
- **THEN** the wrapper contract SHALL ensure those decisions do not require parsing raw log content or handoff prose unless a phase explicitly declares a log artifact requirement

#### Scenario: wrapper blocker can stop lifecycle transition
- **WHEN** a wrapper cannot produce required evidence or detects a lifecycle violation
- **THEN** it SHALL return a blocker that `after_dispatch` can pass to the workflow runtime through `workflow.py block` or equivalent runtime command, rather than allowing phase completion to proceed

### Requirement: current skills are mapped as wrapped backends
The system SHALL map existing OpenSpec, Superpowers, Roadmap, Memory, and EvalOps skills as wrapped backends behind the wrapper contracts without changing their user-visible behavior.

#### Scenario: existing skill behavior is preserved
- **WHEN** a wrapper routes to an existing skill backend (OpenSpec, Superpowers, Roadmap, Memory, EvalOps)
- **THEN** the skill's user-visible behavior SHALL be identical to its behavior before wrapper introduction

#### Scenario: new backend can replace wrapped backend
- **WHEN** a replacement implementation is available for a lifecycle module
- **THEN** the wrapper SHALL route to the new backend without requiring changes to workflow phase semantics, agent contracts, or gate definitions

### Requirement: wrapper contract document exists for all lifecycle modules
The system SHALL maintain a wrapper contract document that covers spec, memory, roadmap, eval, planning, implementation, testing, review, finish, and verification modules.

#### Scenario: each module has a documented wrapper contract
- **WHEN** inspecting the wrapper contract document
- **THEN** each lifecycle module SHALL have documented inputs, outputs, evidence keys, exit criteria, failure modes, and remediation guidance
