# run-legacy-migration

Auto-migrate top-level `runs/handoffs/<run_id>/` and `runs/logs/<run_id>/` directories into the unified `<run_id>/` structure.

## ADDED Requirements

### Requirement: Legacy Handoffs Directory Migration
The system SHALL detect and migrate legacy `runs/handoffs/<run_id>/` directories into `runs/<run_id>/handoffs/` on first access.

#### Scenario: Legacy handoffs directory is migrated on save
- **WHEN** `save_run_state()` writes to `active/<run_id>/run.json`
- **AND** `runs/handoffs/<run_id>/` exists
- **THEN** the contents of `runs/handoffs/<run_id>/` SHALL be moved to `active/<run_id>/handoffs/`
- **AND** `runs/handoffs/<run_id>/` SHALL be removed

#### Scenario: Legacy handoffs directory is migrated on load
- **WHEN** `load_run_state()` reads from `active/<run_id>/run.json`
- **AND** `runs/handoffs/<run_id>/` exists
- **THEN** the contents of `runs/handoffs/<run_id>/` SHALL be moved to `active/<run_id>/handoffs/`
- **AND** `runs/handoffs/<run_id>/` SHALL be removed

#### Scenario: No migration when legacy directory does not exist
- **WHEN** `save_run_state()` or `load_run_state()` runs
- **AND** `runs/handoffs/<run_id>/` does NOT exist
- **THEN** no migration SHALL be attempted

### Requirement: Legacy Logs Directory Migration
The system SHALL detect and migrate legacy `runs/logs/<run_id>/` directories into `runs/<run_id>/logs/` on first access.

#### Scenario: Legacy logs directory is migrated on save
- **WHEN** `save_run_state()` writes to `active/<run_id>/run.json`
- **AND** `runs/logs/<run_id>/` exists
- **THEN** the contents of `runs/logs/<run_id>/` SHALL be moved to `active/<run_id>/logs/`
- **AND** `runs/logs/<run_id>/` SHALL be removed

#### Scenario: Legacy logs directory is migrated on load
- **WHEN** `load_run_state()` reads from `active/<run_id>/run.json`
- **AND** `runs/logs/<run_id>/` exists
- **THEN** the contents of `runs/logs/<run_id>/` SHALL be moved to `active/<run_id>/logs/`
- **AND** `runs/logs/<run_id>/` SHALL be removed

### Requirement: Migration Is Idempotent
The migration SHALL be safe to run multiple times without data loss.

#### Scenario: Migration does not overwrite existing artifacts
- **WHEN** migration runs for a run_id
- **AND** `active/<run_id>/handoffs/` already exists
- **THEN** existing files in `active/<run_id>/handoffs/` SHALL be preserved
- **AND** only non-conflicting files from the legacy directory SHALL be moved

#### Scenario: Migration sentinel prevents re-migration
- **WHEN** migration has completed for a run_id
- **THEN** a sentinel file SHALL be created
- **AND** subsequent migration attempts SHALL be skipped
