## ADDED Requirements

### Requirement: Governance Check Command
The workflow runtime SHALL provide a read-only `governance-check` command that detects SDLC lifecycle governance gaps without mutating Roadmap, OpenSpec, Memory, EvalOps, or workflow state.

#### Scenario: Clean state does not block
- **WHEN** there are no dangling archived OpenSpec changes and no active workflow run with unresolved pending hooks
- **THEN** `workflow.py governance-check` SHALL return structured output with `block=false` and no blocking findings

#### Scenario: Command is read-only
- **WHEN** `workflow.py governance-check` runs
- **THEN** it SHALL NOT modify roadmap item files, OpenSpec change files, memory documents, eval assets, or workflow run state

#### Scenario: Command supports explicit root
- **WHEN** `workflow.py --root <path> governance-check` runs
- **THEN** it SHALL inspect SDLC state under the provided root path

### Requirement: Dangling Archive Detection
The governance check SHALL detect archived OpenSpec changes that have no matching active workflow run and no matching completed workflow history run.

#### Scenario: Archived change with no workflow evidence blocks
- **WHEN** an archived OpenSpec change exists under `openspec/changes/archive/`
- **AND** no active run or done history run has `primary_subject.type=openspec_change` and the same change id
- **THEN** `governance-check` SHALL report a `dangling_archive` finding with change id and archive path context

#### Scenario: Active matching run is valid evidence
- **WHEN** an archived OpenSpec change has a matching active workflow run for the same change id
- **THEN** `governance-check` SHALL NOT report that archive as dangling

#### Scenario: Done matching history run is valid evidence
- **WHEN** an archived OpenSpec change has a matching done workflow history run for the same change id
- **THEN** `governance-check` SHALL NOT report that archive as dangling

### Requirement: Pending Hook Detection
The governance check SHALL detect unresolved hooks in active workflow runs and return actionable context for remediation.

#### Scenario: Active run with pending hooks blocks
- **WHEN** the active workflow run has one or more entries in `pending_hooks`
- **THEN** `governance-check` SHALL report a `pending_hooks` finding with run id, change id when available, and pending hook names

#### Scenario: Pending hook remediation identifies follow-up
- **WHEN** `governance-check` reports a `pending_hooks` finding
- **THEN** the finding SHALL include remediation text that names the responsible worker category, requires `workflow.py complete-hook --hook <hook-name>` after worker evidence exists, and states to re-run governance checks until `block=false`

#### Scenario: Multiple finding types combine
- **WHEN** both dangling archives and pending hooks are present
- **THEN** `governance-check` SHALL return `block=true` with findings for both diagnostic categories

### Requirement: Governance Diagnostic Output Contract
The governance check SHALL return a structured JSON contract suitable for CLI adapters and deterministic tests.

#### Scenario: Blocking output includes findings
- **WHEN** governance issues are detected
- **THEN** output SHALL include `block=true` and a `findings` array containing finding type, message, remediation text, and a stable deduplication hash

#### Scenario: Finding hash is stable
- **WHEN** the same unresolved governance finding is detected across repeated checks
- **THEN** the finding hash SHALL remain stable for the same finding identity

#### Scenario: Human-readable remediation is included
- **WHEN** a finding is returned
- **THEN** it SHALL include remediation text that can be shown directly or adapted into an assistant prompt
