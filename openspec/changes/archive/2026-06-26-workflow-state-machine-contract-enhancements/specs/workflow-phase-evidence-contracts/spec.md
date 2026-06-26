## ADDED Requirements

### Requirement: Workflow phases may declare required evidence keys
The system SHALL allow workflow phase definitions to declare `evidence_keys` as a phase-local list of required evidence paths that must be satisfied before phase completion.

#### Scenario: Workflow definition accepts evidence keys
- **WHEN** `.ai/workflows/definitions/sdlc-main.yaml` or another workflow definition is validated
- **THEN** a phase MAY declare `evidence_keys` as a list of required evidence paths

#### Scenario: Evidence keys are validated structurally
- **WHEN** a phase declares `evidence_keys`
- **THEN** the runtime SHALL require the field to be a list of non-empty strings

#### Scenario: Evidence keys do not complete the phase by themselves
- **WHEN** a phase declares `evidence_keys` and matching evidence exists
- **THEN** the phase SHALL still require `complete-phase` to run before it is marked complete

### Requirement: Required evidence keys gate phase completion
The system SHALL fail closed when a phase declares required `evidence_keys` and the current run does not contain non-empty values for all declared keys.

#### Scenario: Missing evidence key blocks completion
- **WHEN** `workflow.py complete-phase` runs for a phase that declares `evidence_keys`
- **AND** at least one declared key is missing from run evidence
- **THEN** the runtime SHALL fail phase completion and report the missing evidence keys

#### Scenario: Empty evidence value blocks completion
- **WHEN** `workflow.py complete-phase` runs for a phase that declares `evidence_keys`
- **AND** a declared key exists but its value is empty
- **THEN** the runtime SHALL fail phase completion and report the empty evidence key

#### Scenario: Completion succeeds after required evidence is recorded
- **WHEN** `workflow.py complete-phase` runs for a phase that declares `evidence_keys`
- **AND** every declared evidence key has a non-empty value
- **THEN** the runtime MAY complete the phase if all other exit criteria also pass
