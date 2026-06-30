# run-directory-unification

Consolidate all run artifacts (JSON state, plans, handoffs, logs) under a single `<run_id>/` directory with `run.json` as the canonical run state file.

## ADDED Requirements

### Requirement: Unified Run Directory Layout
The system SHALL store all run artifacts under `active/<run_id>/` for active runs and `history/<run_id>/` for done runs, with `run.json` as the canonical state file inside the run directory.

#### Scenario: Active run directory contains run.json
- **WHEN** a workflow run is created
- **THEN** `active/<run_id>/run.json` SHALL exist containing the full run state
- **AND** `active/<run_id>.json` SHALL NOT exist

#### Scenario: Active run directory contains artifact subdirectories
- **WHEN** a workflow run is active
- **THEN** the run directory `active/<run_id>/` SHALL contain `plans/`, `handoffs/`, and `logs/` subdirectories alongside `run.json`

#### Scenario: History run directory contains run.json
- **WHEN** a workflow run reaches `done`
- **THEN** `history/<run_id>/run.json` SHALL exist containing the final run state
- **AND** `history/<run_id>.json` SHALL NOT be created for new runs

#### Scenario: Pointer file is unchanged
- **WHEN** `current.json` exists as a pointer
- **THEN** it SHALL contain ONLY `{"run_id": "<run_id>"}` and SHALL NOT contain the run directory path

### Requirement: Directory-Level Archiving
When a run reaches `done`, the runtime SHALL move the entire `active/<run_id>/` directory to `history/<run_id>/`, preserving all artifacts (plans, handoffs, logs) alongside the run state.

#### Scenario: Done moves entire run directory
- **WHEN** `workflow.py done` succeeds
- **THEN** the entire `active/<run_id>/` directory SHALL be moved to `history/<run_id>/`
- **AND** `active/<run_id>/` SHALL NOT exist
- **AND** `history/<run_id>/run.json` SHALL exist
- **AND** `history/<run_id>/` SHALL contain any `plans/`, `handoffs/`, `logs/` that were present in `active/<run_id>/`

#### Scenario: Advance to done moves entire run directory
- **WHEN** `workflow.py advance` transitions to `done` phase
- **THEN** the entire `active/<run_id>/` directory SHALL be moved to `history/<run_id>/`
- **AND** the pointer SHALL be cleared to `{}`

#### Scenario: Done removes pointer after directory move
- **WHEN** `workflow.py done` or `advance` to `done` succeeds
- **THEN** `current.json` SHALL be cleared to `{}`

### Requirement: Directory-Level Cancellation
When a run is cancelled, the runtime SHALL remove the entire `active/<run_id>/` directory.

#### Scenario: Cancel removes entire run directory
- **WHEN** `workflow.py cancel-run` succeeds for a run
- **THEN** the entire `active/<run_id>/` directory SHALL be removed
- **AND** the pointer SHALL be cleared if it pointed to the cancelled run

#### Scenario: Cancel does not write history
- **WHEN** `workflow.py cancel-run` succeeds
- **THEN** no history file SHALL be created for the cancelled run

### Requirement: Active Run Listing from Directories
The runtime SHALL discover active runs by scanning subdirectories under `active/` rather than flat JSON files.

#### Scenario: Active run listing discovers run directories
- **WHEN** `_list_active_runs()` runs
- **THEN** it SHALL iterate `active/` subdirectories and read `run.json` from each

#### Scenario: Status lists active runs from directories
- **WHEN** `workflow.py status` lists active runs
- **THEN** it SHALL find run state from `active/<run_id>/run.json` in each subdirectory

#### Scenario: Governance-check scans active run directories
- **WHEN** `workflow.py governance-check` scans active runs
- **THEN** it SHALL read `active/<run_id>/run.json` from each subdirectory

### Requirement: Backward-Compatible History Reading
The runtime SHALL support reading both old-style flat JSON files (`history/<run_id>.json`) and new-style directory-based state (`history/<run_id>/run.json`).

#### Scenario: Governance-check reads new-style history
- **WHEN** `workflow.py governance-check` scans history and finds `history/<run_id>/run.json`
- **THEN** it SHALL read the run state from that file

#### Scenario: Governance-check reads old-style history
- **WHEN** `workflow.py governance-check` scans history and finds `history/<run_id>.json` (flat file)
- **THEN** it SHALL read the run state from the flat file without error

#### Scenario: New run writes only new-style history
- **WHEN** a new run is created and archived
- **THEN** it SHALL write only `history/<run_id>/run.json` and SHALL NOT create `history/<run_id>.json`
