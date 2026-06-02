## ADDED Requirements

### Requirement: Bootstrap execution order
`sdlc-project-bootstrap` SHALL execute initialization steps in a fixed order: AGENTS.md, OpenSpec/schema (via `sdlc-openspec-init`), repository memory. If a step cannot proceed safely, the skill SHALL stop and report the failing step before continuing.

#### Scenario: Full bootstrap on empty project
- **WHEN** a project has no AGENTS.md, no OpenSpec configuration, and no `.ai-memory/`
- **THEN** the skill SHALL create AGENTS.md, invoke `sdlc-openspec-init`, and invoke `sdlc-repository-memory-init` in that order

#### Scenario: Partial bootstrap stops on failure
- **WHEN** a step fails with a non-recoverable error
- **THEN** the skill SHALL report the failure and stop without executing remaining steps

### Requirement: Dry-run preview
`sdlc-project-bootstrap` SHALL support dry-run mode that reports all planned actions without modifying any files.

#### Scenario: Dry-run on empty project
- **WHEN** dry-run mode is invoked on a project with no initialized infrastructure
- **THEN** the skill SHALL report the planned actions (create AGENTS.md, init OpenSpec, install schema, init memory) without creating or modifying any files

#### Scenario: Dry-run on partially initialized project
- **WHEN** dry-run mode is invoked on a project where some steps are already initialized
- **THEN** the skill SHALL report only the missing steps as planned actions, and report already-initialized steps as skipped

### Requirement: AGENTS.md initialization
`sdlc-project-bootstrap` SHALL initialize AGENTS.md at the repository root using the baseline template bundled at `templates/AGENTS.md`.

#### Scenario: AGENTS.md does not exist
- **WHEN** AGENTS.md is missing at the repository root
- **THEN** the skill SHALL create AGENTS.md from the bundled template `templates/AGENTS.md`

#### Scenario: AGENTS.md exists and is complete
- **WHEN** AGENTS.md exists and already contains all standard blocks
- **THEN** the skill SHALL report AGENTS.md as already initialized and make no changes

#### Scenario: AGENTS.md exists but missing standard blocks
- **WHEN** AGENTS.md exists but some standard blocks are missing
- **THEN** the skill SHALL append only the missing blocks without modifying or removing existing content

#### Scenario: AGENTS.md duplicate detection
- **WHEN** the skill considers appending a standard block
- **THEN** the skill SHALL check for the block's presence (by heading or key content) and skip appending if already present

### Requirement: Repository memory reminder is not in baseline template
The bundled AGENTS.md template SHALL NOT include the Repository Memory reminder block. That block SHALL be appended by `sdlc-repository-memory-init` or recommended for manual addition.

#### Scenario: Template excludes memory reminder
- **WHEN** the template `templates/AGENTS.md` is inspected
- **THEN** it SHALL NOT contain a "## Repository Memory" section or equivalent memory-load instruction

### Requirement: OpenSpec initialization delegation
`sdlc-project-bootstrap` SHALL delegate OpenSpec initialization, schema discovery, default schema selection, and schema installation to `sdlc-openspec-init`.

#### Scenario: Delegation to openspec-init
- **WHEN** the bootstrap reaches the OpenSpec step
- **THEN** the skill SHALL invoke `sdlc-openspec-init` to handle OpenSpec detection, CLI init, schema listing, default schema selection, and schema installation

#### Scenario: openspec-init reports already initialized
- **WHEN** `sdlc-openspec-init` reports that OpenSpec and schema are already present
- **THEN** the skill SHALL report OpenSpec as already initialized and proceed to the next step

#### Scenario: Default schema selection is surfaced
- **WHEN** `sdlc-openspec-init` prompts the user to choose a default schema
- **THEN** the bootstrap summary SHALL surface the selected schema name before proceeding

#### Scenario: AI tools selection is surfaced
- **WHEN** `sdlc-openspec-init` prompts the user to choose one or more AI tools
- **THEN** the bootstrap summary SHALL surface the selected tool list before proceeding

### Requirement: Repository memory initialization
`sdlc-project-bootstrap` SHALL delegate repository memory initialization to `sdlc-repository-memory-init`. This step SHALL run only after AGENTS.md and OpenSpec initialization have completed.

#### Scenario: Memory is already initialized
- **WHEN** `.ai-memory/manifest.json` exists at the project root
- **THEN** the skill SHALL report repository memory as already initialized and skip the step

#### Scenario: Memory is not initialized
- **WHEN** `.ai-memory/manifest.json` does not exist at the project root
- **THEN** the skill SHALL invoke `sdlc-repository-memory-init` to create the memory structure

#### Scenario: Memory sync is not auto-run
- **WHEN** repository memory initialization completes
- **THEN** the skill SHALL NOT automatically run `sdlc-repository-memory-sync`

### Requirement: Idempotence
Running `sdlc-project-bootstrap` multiple times on the same project SHALL produce the same end state without overwriting or duplicating existing content.

#### Scenario: Second bootstrap run is a no-op
- **WHEN** the skill is run on a project where all three steps are already initialized
- **THEN** the skill SHALL report all steps as already initialized and make no changes

#### Scenario: Second bootstrap run does not create duplicates
- **WHEN** the skill is run on a project where AGENTS.md exists but other steps are missing
- **THEN** the skill SHALL preserve the existing AGENTS.md content and only initialize the missing steps

### Requirement: Summary reporting
After completing all steps, `sdlc-project-bootstrap` SHALL output a summary of actions taken and suggested next steps.

#### Scenario: Full bootstrap summary
- **WHEN** all three steps complete successfully
- **THEN** the summary SHALL report created, skipped, and appended actions for each step

#### Scenario: Partial bootstrap summary
- **WHEN** one or more steps are skipped because they are already initialized
- **THEN** the summary SHALL distinguish newly-created resources from already-initialized resources

#### Scenario: Suggested next steps
- **WHEN** the summary is reported
- **THEN** the skill SHALL suggest next actions (e.g., creating an OpenSpec change, running memory sync) without executing them automatically
