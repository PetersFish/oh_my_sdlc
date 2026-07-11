## ADDED Requirements

### Requirement: Stable workflow CLI facade
The system SHALL retain `.ai/workflows/scripts/workflow.py` as the executable public entry point and SHALL preserve every existing command name, argument, exit code, JSON output contract, and supported root-resolution behavior during modularization.

#### Scenario: Existing command invocation remains compatible
- **WHEN** a caller invokes an existing command through `.ai/workflows/scripts/workflow.py` against the same workspace fixture and arguments used before modularization
- **THEN** the command produces the same exit status, observable JSON fields, and workflow state effects

#### Scenario: Public script remains directly executable
- **WHEN** a caller executes `.ai/workflows/scripts/workflow.py --help`
- **THEN** the process succeeds and exposes the existing command surface through the modular runtime

### Requirement: Responsibility-based runtime modules
The workflow runtime SHALL place cohesive implementation responsibilities in an importable `workflow_runtime` package while keeping CLI composition separate from state persistence, definition handling, domain loading, policy evaluation, dispatch processing, lifecycle commands, and governance diagnostics.

#### Scenario: Runtime modules import independently
- **WHEN** the supported runtime modules are imported in a fresh Python process
- **THEN** all imports complete without circular-import errors or command execution side effects

#### Scenario: Lower-level module is tested through its public internal API
- **WHEN** a test invokes an extracted state, definition, domain, or policy operation directly
- **THEN** the operation can be verified without invoking unrelated lifecycle commands

### Requirement: Persisted workflow behavior is unchanged
The modular runtime SHALL preserve the `.ai/workflows/runs/` directory layout, run-state schema, phase and transition rules, block and gate behavior, evidence handling, and active-to-history lifecycle semantics.

#### Scenario: Run state round trip preserves the contract
- **WHEN** the modular runtime creates, saves, reloads, advances, and completes a run in a temporary workspace
- **THEN** the persisted paths and state fields match the existing runtime contract

#### Scenario: Invalid transition remains rejected
- **WHEN** a caller attempts a transition that the current workflow definition does not allow
- **THEN** the modular runtime rejects it with the same observable status, reason, next action, and state preservation behavior

### Requirement: Centralized run-state mutation
The workflow runtime MUST route creation and mutation of workflow run pointers, active runs, and history runs through the extracted state I/O module, and read-only domain loaders and governance checks MUST NOT mutate workflow or domain state.

#### Scenario: State API performs the expected write
- **WHEN** a state mutation operation is invoked in a temporary workspace
- **THEN** only the contractually expected files under `.ai/workflows/runs/` are created or changed

#### Scenario: Read-only operation leaves workspace unchanged
- **WHEN** a domain loader or governance-check operation reads a prepared workspace
- **THEN** a before-and-after filesystem snapshot shows no created, modified, or deleted files

### Requirement: Behavior-preserving verification coverage
The change SHALL retain the existing subprocess-level workflow regression suite and SHALL add focused executable tests for module imports, state round trips, definition validation, policy metadata isolation, and read-only loader behavior.

#### Scenario: Broken facade delegation is detected
- **WHEN** the facade cannot import or invoke the modular CLI
- **THEN** a focused import test or existing subprocess-level command test fails

#### Scenario: Parsed but unused behavior is detected
- **WHEN** a command still parses its arguments but an extracted handler fails to apply the corresponding state or output behavior
- **THEN** an executable CLI scenario fails based on the observed output or persisted state rather than source vocabulary

### Requirement: Bootstrap and distribution parity
The bootstrap system SHALL install the same workflow facade, runtime package files, and workflow definition that exist in the live runtime, and synchronization checks SHALL detect missing, stale, or extra governed runtime module files in canonical and project-level distributed templates.

#### Scenario: Bootstrapped runtime executes
- **WHEN** project foundations are initialized into a temporary workspace
- **THEN** the installed `workflow.py` can import its installed `workflow_runtime` package and successfully execute a validation or status command

#### Scenario: Missing nested module causes drift failure
- **WHEN** a governed runtime package file is absent or stale in the canonical template or one distributed copy
- **THEN** the corresponding read-only sync check exits non-zero and identifies the mismatched nested path

#### Scenario: Complete synchronization restores parity
- **WHEN** live-to-canonical synchronization and canonical-to-distribution are run for the modular runtime
- **THEN** subsequent live, canonical, and distributed checks pass for the complete governed module inventory
