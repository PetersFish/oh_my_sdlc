## ADDED Requirements

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
