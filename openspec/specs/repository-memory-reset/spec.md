# sdlc-repository-memory-reset

Safely reset and reinitialize repository memory. Handles backup, deletion, re-initialization, optional sync, and post-reset validation with interactive confirmation at each destructive step.

## Requirements

### Requirement: Reset detects existing memory state
`sdlc-repository-memory-reset` SHALL check whether `.ai-memory/` exists at the repository root before proceeding. If it does not exist, the skill SHALL report that no memory exists and offer to run `sdlc-repository-memory-init` directly. If it exists, the skill SHALL check git status and report whether `.ai-memory/` has uncommitted changes.

#### Scenario: Memory exists with clean git state
- **WHEN** `.ai-memory/` exists and all files under `.ai-memory/` are committed
- **THEN** the skill SHALL report that memory exists with clean git state and proceed to reset confirmation

#### Scenario: Memory exists with dirty git state
- **WHEN** `.ai-memory/` exists and has uncommitted or unstaged changes
- **THEN** the skill SHALL report the dirty state and list changed files before proceeding to reset confirmation

#### Scenario: Memory does not exist
- **WHEN** `.ai-memory/` does not exist at the repository root
- **THEN** the skill SHALL report that no repository memory is present and ask whether to run `sdlc-repository-memory-init` instead

### Requirement: Interactive reset confirmation with backup option
`sdlc-repository-memory-reset` SHALL present the user with three choices before deleting `.ai-memory/`: backup then delete, delete without backup, or cancel. If the user chooses backup, the skill SHALL copy `.ai-memory/` to a timestamped backup directory before deletion.

#### Scenario: User chooses backup then delete
- **WHEN** the user selects "backup then delete"
- **THEN** the skill SHALL copy `.ai-memory/` to `/tmp/ai-memory-reset-<timestamp>/` (or an equivalent safe location), report the backup path, then delete `.ai-memory/`

#### Scenario: User chooses delete without backup
- **WHEN** the user selects "delete without backup"
- **THEN** the skill SHALL delete `.ai-memory/` and report that no backup was created

#### Scenario: User cancels reset
- **WHEN** the user selects "cancel"
- **THEN** the skill SHALL stop without modifying `.ai-memory/` and report that reset was cancelled

### Requirement: Re-initialize after successful deletion
After deleting `.ai-memory/`, `sdlc-repository-memory-reset` SHALL run the `sdlc-repository-memory-init` workflow to recreate the directory structure, manifest, index, review-queue, discovery-prefs, and .gitignore.

#### Scenario: Successful re-initialization after reset
- **WHEN** `.ai-memory/` has been deleted by the reset flow
- **THEN** the skill SHALL invoke `sdlc-repository-memory-init` and report which files and directories were created

#### Scenario: Re-initialization fails
- **WHEN** the init workflow fails after deletion
- **THEN** the skill SHALL report the failure and note that `.ai-memory/` is missing, advising the user to re-run init

### Requirement: Interactive sync prompt after re-initialization
After successful re-initialization, `sdlc-repository-memory-reset` SHALL ask the user whether to run `sdlc-repository-memory-sync`. The default SHALL be interactive: the user explicitly chooses to sync or to stop after init.

#### Scenario: User chooses to sync after reset
- **WHEN** the user selects "run sync now" after re-init completes
- **THEN** the skill SHALL invoke `sdlc-repository-memory-sync` and report the sync outcome

#### Scenario: User chooses to stop after init only
- **WHEN** the user selects "stop after init" after re-init completes
- **THEN** the skill SHALL report that memory has been reset and re-initialized, and sync is available to run separately

### Requirement: Post-reset validation
After reset, re-init, and optional sync, `sdlc-repository-memory-reset` SHALL run `validate_memory.py` and report validation results. Validation failures SHALL be reported but SHALL NOT block the reset from being considered complete.

#### Scenario: Validation passes after reset
- **WHEN** `validate_memory.py` returns valid after the reset workflow
- **THEN** the skill SHALL report validation success as part of the reset summary

#### Scenario: Validation fails after reset
- **WHEN** `validate_memory.py` returns errors after the reset workflow
- **THEN** the skill SHALL report the validation errors and advise the user to re-run memory sync

### Requirement: Reset never auto-commits
`sdlc-repository-memory-reset` SHALL NOT create git commits under any circumstances. Git state reporting is informational only.

#### Scenario: Reset completes without git commit
- **WHEN** the reset workflow completes (with or without sync)
- **THEN** the skill SHALL NOT run `git commit`, `git add`, or any other git write operation

### Requirement: Reset summary output
`sdlc-repository-memory-reset` SHALL output a summary after completion reporting: whether backup was created and its location, the re-init result, the sync result (if sync was run), and the validation result.

#### Scenario: Full reset with backup and sync
- **WHEN** the user completes a reset with backup, re-init, sync, and validation
- **THEN** the summary SHALL include backup path, created directories, sync ID, and validation status
