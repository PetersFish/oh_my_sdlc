## ADDED Requirements

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
